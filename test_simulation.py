#!/usr/bin/env python3
"""
Test script untuk memeriksa masalah simulasi
"""

import sys
import os
import json
from collections import deque

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.main import (
    SimulationSetup, LogisticsSimulationSetup, ProcessConfig,
    Location, SimulationEngine,
    LogisticsSimulationEngine, get_db, ProductionSimulationConfigDB,
    LogisticsSimulationConfigDB
)
from backend.models import TransportUnit, TransportTask

def test_file_loading():
    """Test if files can be loaded"""
    print("🔍 Testing file loading...")
    
    schedule_file = "20250912-Schedule FA1.csv"
    bom_file = "YMATP0200B_BOM_20250911_231232.txt"
    mrp_file = "MRP_20250912.txt"
    
    # Test schedule file
    try:
        import pandas as pd
        df = pd.read_csv(schedule_file, skiprows=4, header=None, encoding='latin-1')
        print(f"✅ Schedule file loaded: {len(df)} rows")
    except Exception as e:
        print(f"❌ Schedule file error: {e}")
        return False
    
    # Test BOM file
    try:
        with open(bom_file, 'r', encoding='latin-1') as f:
            lines = f.readlines()
            print(f"✅ BOM file loaded: {len(lines)} lines")
    except Exception as e:
        print(f"❌ BOM file error: {e}")
        return False
    
    # Test MRP file
    try:
        with open(mrp_file, 'r', encoding='latin-1') as f:
            lines = f.readlines()
            print(f"✅ MRP file loaded: {len(lines)} lines")
    except Exception as e:
        print(f"❌ MRP file error: {e}")
        return False
    
    return True

def test_production_simulation():
    """Test production simulation engine"""
    print("\n🔍 Testing production simulation...")
    
    try:
        # Create simple setup
        setup = SimulationSetup(
            processes=[
                ProcessConfig(
                    name="Assembly",
                    cycle_time=60,
                    num_operators=1,
                    ng_rate=0.05,
                    input_from=[],
                    output_to=[]
                )
            ]
        )
        
        # Create material request queue
        material_queue = deque()
        
        # Initialize engine
        engine = SimulationEngine(
            setup=setup,
            schedule_file="20250912-Schedule FA1.csv",
            bom_file="YMATP0200B_BOM_20250911_231232.txt",
            material_request_queue=material_queue
        )
        
        print(f"✅ Production engine initialized")
        print(f"   Status: {engine.status}")
        print(f"   Target: {engine.total_production_target}")
        print(f"   Processes: {list(engine.processes.keys())}")
        
        # Run a few steps
        for i in range(5):
            engine.run_step()
            print(f"   Step {i+1}: Time={engine.time}, Completed={engine.completed_units}")
        
        return True
        
    except Exception as e:
        print(f"❌ Production simulation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_logistics_simulation():
    """Test logistics simulation engine"""
    print("\n🔍 Testing logistics simulation...")
    
    try:
        # Create simple setup
        setup = LogisticsSimulationSetup(
            locations=[
                Location(name="WAREHOUSE", stock={"MATERIAL_A": 100}),
                Location(name="ASSEMBLY", stock={})
            ],
            transport_units=[
                TransportUnit(name="Kururu 1", type="Kururu", num_sub_units=1, capacity_per_sub_unit=10),
                TransportUnit(name="Test 1", type="Test", num_sub_units=1, capacity_per_sub_unit=10)
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
                    transport_unit_names=["Forklift 1"]
                )
            ]
        )
        
        # Create material request queue
        material_queue = deque()
        
        # Initialize engine
        engine = LogisticsSimulationEngine(
            setup=setup,
            material_request_queue=material_queue,
            production_engine=None,
            mrp_file="MRP_20250912.txt"
        )
        
        print(f"✅ Logistics engine initialized")
        print(f"   Status: {engine.status}")
        print(f"   Locations: {list(engine.locations.keys())}")
        print(f"   Transport units: {list(engine.transport_units_map.keys())}")
        
        # Run a few steps
        for i in range(5):
            engine.run_step()
            print(f"   Step {i+1}: Time={engine.current_time}, Completed tasks={engine.completed_tasks_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Logistics simulation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_setups():
    """Test database setups"""
    print("\n🔍 Testing database setups...")
    
    try:
        db = next(get_db())
        
        # Check production setups
        prod_setups = db.query(ProductionSimulationConfigDB).all()
        print(f"✅ Production setups found: {len(prod_setups)}")
        for setup in prod_setups:
            print(f"   - {setup.name} (ID: {setup.id})")
        
        # Check logistics setups
        log_setups = db.query(LogisticsSimulationConfigDB).all()
        print(f"✅ Logistics setups found: {len(log_setups)}")
        for setup in log_setups:
            print(f"   - {setup.name} (ID: {setup.id})")
        
        return len(prod_setups) > 0 and len(log_setups) > 0
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🧪 Testing Simulation Components")
    print("=" * 50)
    
    tests = [
        ("File Loading", test_file_loading),
        ("Database Setups", test_database_setups),
        ("Production Simulation", test_production_simulation),
        ("Logistics Simulation", test_logistics_simulation),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n🎉 All tests passed! Simulations should work.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
