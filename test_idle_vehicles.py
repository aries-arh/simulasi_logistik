#!/usr/bin/env python3
"""
Test script to verify that only 'Kururu' type vehicles are assigned tasks, others remain idle.
"""

import sys
import os
from collections import deque

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.models import TransportUnit, TransportTask, Location, LogisticsSimulationSetup
from backend.logistics_simulation import LogisticsSimulationEngine

def test_vehicle_idle_logic():
    """Test that only Kururu type vehicles get tasks, others idle"""
    print("🔍 Testing vehicle idle logic...")

    try:
        # Create setup with mixed types
        setup = LogisticsSimulationSetup(
            locations=[
                Location(name="WAREHOUSE", stock={"MATERIAL_A": 100}),
                Location(name="ASSEMBLY", stock={})
            ],
            transport_units=[
                TransportUnit(name="Kururu 1", type="Kururu", num_sub_units=1, capacity_per_sub_unit=10),
                TransportUnit(name="Test 1", type="Test", num_sub_units=1, capacity_per_sub_unit=10),
                TransportUnit(name="Test 2", type="Test", num_sub_units=1, capacity_per_sub_unit=10)
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
                    transport_unit_names=["Kururu 1", "Test 1", "Test 2"]
                )
            ]
        )

        material_queue = deque()

        engine = LogisticsSimulationEngine(
            setup=setup,
            material_request_queue=material_queue,
            production_engine=None,
            mrp_file="MRP_20250912.txt"
        )

        print(f"✅ Engine initialized with units: {list(engine.transport_units_map.keys())}")
        print(f"   Types: {[engine.transport_units_map[name].type for name in engine.transport_units_map]}")

        # Check initial statuses
        print("\nInitial statuses:")
        for name, status in engine.transport_units_status.items():
            print(f"   {name} ({engine.transport_units_map[name].type}): {status['status']}")

        # Run steps to assign tasks
        print("\nRunning simulation steps...")
        for i in range(100):  # Run enough steps for task completion
            engine.run_step()
            if engine.completed_tasks_count > 0:
                print(f"Task completed at step {i+1}")
                break

        print("\nFinal statuses:")
        for name, status in engine.transport_units_status.items():
            print(f"   {name} ({engine.transport_units_map[name].type}): {status['status']}")

        print(f"\nCompleted tasks: {engine.completed_tasks_count}")
        print(f"Tasks assigned to units: {engine.completed_tasks_per_unit}")

        # Verify that only Kururu got tasks
        kururu_assigned = engine.completed_tasks_per_unit.get("Kururu 1", 0) > 0
        test1_idle = engine.completed_tasks_per_unit.get("Test 1", 0) == 0
        test2_idle = engine.completed_tasks_per_unit.get("Test 2", 0) == 0

        if kururu_assigned and test1_idle and test2_idle:
            print("✅ SUCCESS: Only Kururu type vehicle was assigned tasks, others remained idle.")
            return True
        else:
            print("❌ FAILURE: Incorrect task assignment.")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vehicle_idle_logic()
    if success:
        print("\n🎉 Test passed!")
    else:
        print("\n⚠️ Test failed!")
