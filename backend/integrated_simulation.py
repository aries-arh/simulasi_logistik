from collections import deque
from typing import Optional, Callable
import pandas as pd
from datetime import datetime

from models import SimulationSetup, LogisticsSetup, IntegratedSimulationConfig
from production_engine_v2 import ProductionEngineV2
from logistics_simulation import LogisticsSimulation
from data_loader import load_schedule, load_mrp_data
from bom_service import BOMService

class IntegratedSimulation:
    def __init__(
        self,
        production_setup: SimulationSetup,
        logistics_setup: LogisticsSetup,
        schedule_file: str,
        mrp_filename: Optional[str],
        material_data_df: pd.DataFrame,
        bom_service: BOMService, # Added bom_service
        target_date: Optional[str] = None
    ):
        self.material_request_queue = deque()
        
        self.production_engine = ProductionEngineV2(
            setup=production_setup,
            schedule_file=schedule_file,
            bom_service=bom_service, # Pass bom_service instance
            material_request_queue=self.material_request_queue,
            target_date=target_date
        )
        
        self.logistics_simulation = LogisticsSimulation(
            setup=logistics_setup,
            material_data_df=material_data_df,
            mrp_filename=mrp_filename,
            material_request_queue=self.material_request_queue
        )
        
        self.time = 0
        self.status = "initializing"
        self.simulation_start_time = datetime.now() # For integrated simulation, start time is now

    def run_step(self):
        if self.status != "running":
            return

        # 1. Run a step of production simulation
        self.production_engine.run_step()

        # 2. Run a step of logistics simulation
        #    Logistics simulation needs to check the material_request_queue
        #    and if a delivery is completed, it needs to update production_engine's stock
        self.logistics_simulation.run_step(production_add_stock_callback=self.production_engine.add_stock)

        # 3. Advance integrated simulation time
        self.time += self.production_engine.seconds_per_step # Use production engine's step size for time sync

        # 4. Check for termination conditions
        # Integrated simulation finishes when production is finished
        if self.production_engine.status == "finished":
            self.status = "finished"
        elif self.production_engine.status == "stopped" or self.logistics_simulation.status == "stopped":
            self.status = "stopped"

    def get_status(self):
        return {
            "integrated_time": self.time,
            "integrated_status": self.status,
            "production_status": self.production_engine.get_status(),
            "logistics_status": self.logistics_simulation.get_status()
        }

    def run_simulation(self):
        self.status = "running"
        print("INFO: Integrated Simulation started.")
        # Run until production is finished or explicitly stopped
        while self.status == "running" and self.production_engine.status != "finished":
            self.run_step()
            # In a real async application, this would use asyncio.sleep.
            # For now, we assume run_step is fast or the simulation loop is controlled externally.
            
            # Check for external stop signal
            if self.status == "stopped":
                print("INFO: Integrated Simulation stopped by external signal.")
                break
        
        if self.production_engine.status == "finished":
            self.status = "finished"
            print("INFO: Integrated Simulation finished (Production completed).")
        elif self.status == "running": # Should not happen if loop condition is correct
            self.status = "stopped"
            print("INFO: Integrated Simulation stopped unexpectedly.")

    def stop_simulation(self):
        self.status = "stopped"
        self.production_engine.stop_simulation()
        self.logistics_simulation.stop_simulation()
        print("INFO: Integrated Simulation received stop signal.")


# Global variable to hold the integrated simulation instance
integrated_sim_instance: Optional[IntegratedSimulation] = None

def start_integrated_simulation(
    production_setup: SimulationSetup,
    logistics_setup: LogisticsSetup,
    schedule_file: str,
    mrp_filename: Optional[str],
    material_data_df: pd.DataFrame,
    target_date: Optional[str] = None
):
    global integrated_sim_instance
    if integrated_sim_instance and integrated_sim_instance.status == "running":
        integrated_sim_instance.stop_simulation()

    # Create a single instance of the BOM service
    bom_service = BOMService()

    integrated_sim_instance = IntegratedSimulation(
        production_setup=production_setup,
        logistics_setup=logistics_setup,
        schedule_file=schedule_file,
        mrp_filename=mrp_filename,
        material_data_df=material_data_df,
        bom_service=bom_service, # Pass the service instance
        target_date=target_date
    )
    integrated_sim_instance.run_simulation()
    return integrated_sim_instance.get_status()

def get_integrated_simulation_status():
    global integrated_sim_instance
    if integrated_sim_instance:
        return integrated_sim_instance.get_status()
    return {"integrated_status": "not_running", "message": "Integrated simulation not started."}

def stop_integrated_simulation():
    global integrated_sim_instance
    if integrated_sim_instance:
        integrated_sim_instance.stop_simulation()
        return {"message": "Integrated simulation stopped."}
    return {"message": "No integrated simulation running."}
