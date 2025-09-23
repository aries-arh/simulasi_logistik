#!/usr/bin/env python3
"""
Test script to run integrated simulation for a few steps and check debug logs.
"""

import sys
import os
from collections import deque

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.models import SimulationSetup, LogisticsSimulationSetup, ProcessConfig, Location, TransportUnit, TransportTask
from backend.simulation import SimulationEngine
from backend.logistics_simulation import LogisticsSimulationEngine

def test_integrated_simulation():
    print("🔍 Testing integrated simulation...")

    try:
        # Create production setup
        prod_setup = SimulationSetup(line_processes={
            "FA1-L01": [
                ProcessConfig(
                    name="Assembly",
                    cycle_time=60.0,
                    num_operators=2,
                    ng_rate=0.0,
                    repair_time=0.0,
                    input_from=[],
                    output_to=["Packing"]
                ),
                ProcessConfig(
                    name="Packing",
                    cycle_time=30.0,
                    num_operators=1,
                    ng_rate=0.0,
                    repair_time=0.0,
                    input_from=["Assembly"],
                    output_to=[]
                )
            ]
        })

        # Create logistics setup
        log_setup = LogisticsSimulationSetup(
            locations=[
                Location(name="WAREHOUSE", stock={"MATERIAL_A": 100}),
                Location(name="ASSEMBLY", stock={})
            ],
            transport_units=[
                TransportUnit(name="Kururu 1", type="Kururu", num_sub_units=1, capacity_per_sub_unit=10),
                TransportUnit(name="Kururu 2", type="Kururu", num_sub_units=1, capacity_per_sub_unit=10),
                TransportUnit(name="Kururu 3", type="Kururu", num_sub_units=1, capacity_per_sub_unit=10)
            ],
            tasks=[
                TransportTask(
                    origin="WAREHOUSE",
                    destination="ASSEMBLY",
                    material="MATERIAL_A",
                    lots_required=1,
                    distance=100,
                    travel_time=30,
                    loading_time=10,
                    unloading_time=10,
                    transport_unit_names=["Kururu 1", "Kururu 2", "Kururu 3"]
                )
            ]
        )

        material_queue = deque()

        # Start production
        prod_engine = SimulationEngine(
            setup=prod_setup,
            schedule_file="20250912-Schedule FA1.csv",
            bom_file="YMATP0200B_BOM_20250911_231232.txt",
            material_request_queue=material_queue
        )

        # Start logistics
        log_engine = LogisticsSimulationEngine(
            setup=log_setup,
            material_request_queue=material_queue,
            production_engine=prod_engine,
            mrp_file="MRP_20250912.txt"
        )

        print("✅ Engines initialized.")

        # Run a few steps
        for step in range(50):
            print(f"\n--- Step {step+1} ---")
            prod_engine.run_step()
            log_engine.run_step()

            print(f"Material requests pending: {len(material_queue)}")
            print(f"Available tasks: {len(log_engine.available_tasks)}")
            idle_units = [name for name, status in log_engine.transport_units_status.items() if status["status"] == "idle"]
            print(f"Idle units: {idle_units}")

        print("\nFinal status:")
        for name, status in log_engine.transport_units_status.items():
            print(f"  {name}: {status['status']} at {status['current_location']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_integrated_simulation()
