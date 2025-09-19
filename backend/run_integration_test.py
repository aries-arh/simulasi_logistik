import asyncio
import json
from collections import deque, defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from database import get_db, ProductionSimulationConfigDB, LogisticsSimulationConfigDB
from models import (
    SimulationSetup, LogisticsSimulationSetup, ProcessConfig as Process, Location, TransportUnit, Shift, TransportTask
)
from simulation import SimulationEngine
from logistics_simulation import LogisticsSimulationEngine

# This is a simplified, non-FastAPI way to run the managers
class TestProductionManager:
    def __init__(self, material_request_queue: deque):
        self.engine: Optional[SimulationEngine] = None
        self.material_request_queue = material_request_queue

    def start_simulation(self, setup: SimulationSetup, schedule_file: str, bom_file: str):
        print("Initializing Production Engine...")
        self.engine = SimulationEngine(
            setup, 
            schedule_file=schedule_file, 
            bom_file=bom_file, 
            material_request_queue=self.material_request_queue
        )

    def run_step(self):
        if self.engine and self.engine.status != "finished":
            self.engine.run_step()

class TestLogisticsManager:
    def __init__(self, production_manager: TestProductionManager):
        self.engine: Optional[LogisticsSimulationEngine] = None
        self.production_manager = production_manager

    def start_simulation(self, setup: LogisticsSimulationSetup, mrp_file: str):
        if not self.production_manager or not self.production_manager.engine:
            print("Error: Production engine must be started first.")
            return
        
        print("Initializing Logistics Engine...")
        self.engine = LogisticsSimulationEngine(
            setup=setup,
            material_request_queue=self.production_manager.material_request_queue,
            production_engine=self.production_manager.engine,
            mrp_file=mrp_file
        )

    def run_step(self):
        if self.engine and self.engine.status != "finished":
            self.engine.run_step()

def create_default_setups(db: Session):
    """Creates default simulation setups if none exist."""
    if db.query(ProductionSimulationConfigDB).count() == 0:
        print("No production setup found. Creating a default one.")
        default_prod_setup = SimulationSetup(
            line_processes={
                "Main Line": [
                    Process(name="Assembly", cycle_time=100, num_operators=2, output_to=["Inspection"]),
                    Process(name="Inspection", cycle_time=50, num_operators=1, output_to=["Packing"]),
                    Process(name="Packing", cycle_time=80, num_operators=1, output_to=[])
                ]
            }
        )
        db_setup = ProductionSimulationConfigDB(
            name="Default Production Line",
            description="A simple 3-step production line.",
            config_data=default_prod_setup.model_dump_json()
        )
        db.add(db_setup)

    if db.query(LogisticsSimulationConfigDB).count() == 0:
        print("No logistics setup found. Creating a default one.")
        default_log_setup = LogisticsSimulationSetup(
            locations=[
                Location(name="WAREHOUSE", stock={}),
                Location(name="Assembly", stock={}),
            ],
            transport_units=[
                TransportUnit(name="AGV-01", type="AGV", num_sub_units=1, capacity_per_sub_unit=100)
            ],
            shifts=[
                Shift(name="Day Shift", start_time=0, end_time=28800)
            ],
            tasks=[ # Add a template task
                TransportTask(
                    material="ANY", 
                    quantity=0, 
                    origin="WAREHOUSE", 
                    destination="Assembly", 
                    transport_unit_names=["AGV-01"],
                    loading_time=30,
                    travel_time=120,
                    unloading_time=30,
                    return_time=120,
                    lots_required=1,
                    distance=500
                )
            ]
        )
        db_setup = LogisticsSimulationConfigDB(
            name="Default Logistics",
            description="A simple warehouse-to-line logistics setup.",
            config_data=default_log_setup.model_dump_json()
        )
        db.add(db_setup)
    
    db.commit()

async def main():
    """Main function to run the integrated simulation test."""
    print("--- Starting Integrated Simulation Test ---")
    db: Session = next(get_db())

    # 1. Create default setups if DB is empty
    create_default_setups(db)

    # 2. Fetch setups from DB
    prod_db_setup = db.query(ProductionSimulationConfigDB).first()
    log_db_setup = db.query(LogisticsSimulationConfigDB).first()

    if not prod_db_setup or not log_db_setup:
        print("Failed to create or find setups in the database.")
        return

    print(f"Using Production Setup: '{prod_db_setup.name}'")
    print(f"Using Logistics Setup: '{log_db_setup.name}'")

    prod_setup = SimulationSetup(**json.loads(prod_db_setup.config_data))
    log_setup = LogisticsSimulationSetup(**json.loads(log_db_setup.config_data))

    # 3. Define file paths
    import os
    PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
    schedule_file = os.path.join(PROJECT_ROOT, "20250912-Schedule FA1.csv")
    bom_file = os.path.join(PROJECT_ROOT, "YMATP0200B_BOM_20250911_231232.txt")
    mrp_file = os.path.join(PROJECT_ROOT, "MRP_20250912.txt")

    # 4. Initialize managers and engines
    shared_material_queue = deque()
    prod_manager = TestProductionManager(shared_material_queue)
    log_manager = TestLogisticsManager(prod_manager)

    prod_manager.start_simulation(prod_setup, schedule_file, bom_file)
    log_manager.start_simulation(log_setup, mrp_file)

    if not prod_manager.engine or not log_manager.engine:
        print("Failed to initialize simulation engines.")
        return

    # 5. Run simulation
    print("\n--- Running Simulation Steps ---")
    for i in range(1000): # Run for 1000 steps
        if prod_manager.engine.status == 'finished' and log_manager.engine.status == 'finished':
            print(f"Both simulations finished at step {i}. Exiting.")
            break
        
        prod_manager.run_step()
        log_manager.run_step()

        if i > 0 and i % 200 == 0: # Print status every 200 steps
            print(f"\n--- Status at Step {i} ---")
            prod_status = prod_manager.engine.get_status()
            log_status = log_manager.engine.get_status()
            print(f"Production: {prod_status['completed_units']}/{prod_status['total_production_target']} units completed. Status: {prod_status['status']}")
            print(f"Logistics: {log_status['completed_tasks_count']} tasks completed. {log_status['remaining_tasks_count']} tasks pending. Status: {log_status['status']}")
            print(f"Material Request Queue size: {len(shared_material_queue)}")

    print("\n--- Test Run Finished ---")
    final_prod_status = prod_manager.engine.get_status()
    final_log_status = log_manager.engine.get_status()
    print(f"Final Production Status: {final_prod_status['completed_units']} units completed.")
    print(f"Final Logistics Status: {final_log_status['completed_tasks_count']} tasks completed.")

if __name__ == "__main__":
    asyncio.run(main())