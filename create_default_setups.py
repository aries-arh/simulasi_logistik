#!/usr/bin/env python3
"""
Script untuk membuat setup default untuk simulasi terintegrasi
"""

import json
import sys
import os

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.main import get_db, ProductionSimulationConfigDB, LogisticsSimulationConfigDB
from backend.database import create_db_and_tables

def create_default_production_setup():
    """Create a default production setup"""
    return {
        "line_processes": {
            "Main Line": [
                {
                    "name": "Assembly",
                    "cycle_time": 60,
                    "num_operators": 3,
                    "ng_rate": 0.05,
                    "repair_time": 30,
                    "input_from": [],
                    "output_to": ["Packaging"],
                    "join_type": None
                },
                {
                    "name": "Packaging",
                    "cycle_time": 30,
                    "num_operators": 2,
                    "ng_rate": 0.02,
                    "repair_time": 15,
                    "input_from": ["Assembly"],
                    "output_to": [],
                    "join_type": "AND"
                }
            ]
        }
    }

def create_default_logistics_setup():
    """Create a default logistics setup"""
    return {
        "locations": [
            {
                "name": "WAREHOUSE",
                "stock": {
                    "V874062": 1000,  # HEADPHONE HANGER SET
                    "VCQ0160": 500,   # SCREW SET
                    "VGF1770": 300,   # RECYCLE LABEL
                    "VGQ6490": 200,   # Other component
                    "V907300": 1000,  # From BOM
                    "V975300": 500,   # From BOM
                    "WX41450": 300    # From BOM
                }
            },
            {
                "name": "Assembly",
                "stock": {}
            },
            {
                "name": "Packaging",
                "stock": {}
            }
        ],
        "transport_units": [
            {
                "name": "Forklift 1",
                "type": "Forklift",
                "num_sub_units": 1,
                "capacity_per_sub_unit": 10
            },
            {
                "name": "Forklift 2",
                "type": "Forklift",
                "num_sub_units": 1,
                "capacity_per_sub_unit": 10
            },
            {
                "name": "Forklift 3",
                "type": "Forklift",
                "num_sub_units": 1,
                "capacity_per_sub_unit": 10
            },
            {
                "name": "Kururu 1",
                "type": "Kururu",
                "num_sub_units": 2,
                "capacity_per_sub_unit": 5
            }
        ],
        "tasks": [],
        "workday_start_time": 0,
        "workday_end_time": 28800,
        "shifts": [
            {
                "start_time": 0,
                "end_time": 28800
            }
        ],
        "scheduled_events": [],
        "abnormality_rate": 0.0,
        "abnormality_duration": 0
    }

def main():
    """Create default setups in database"""
    print("Creating default setups for integrated simulation...")

    # Create database tables
    create_db_and_tables()

    # Get database session
    db = next(get_db())
    
    # Check if setups already exist
    existing_prod = db.query(ProductionSimulationConfigDB).filter(
        ProductionSimulationConfigDB.name == "Default Production Setup"
    ).first()
    
    existing_log = db.query(LogisticsSimulationConfigDB).filter(
        LogisticsSimulationConfigDB.name == "Default Logistics Setup"
    ).first()
    
    # Create production setup if not exists
    if not existing_prod:
        prod_setup = create_default_production_setup()
        db_prod_setup = ProductionSimulationConfigDB(
            name="Default Production Setup",
            description="Default production setup for integrated simulation testing",
            config_data=json.dumps(prod_setup)
        )
        db.add(db_prod_setup)
        print("Created default production setup")
    else:
        print("Default production setup already exists")
    
    # Create logistics setup if not exists
    if not existing_log:
        log_setup = create_default_logistics_setup()
        db_log_setup = LogisticsSimulationConfigDB(
            name="Default Logistics Setup",
            description="Default logistics setup for integrated simulation testing",
            config_data=json.dumps(log_setup)
        )
        db.add(db_log_setup)
        print("Created default logistics setup")
    else:
        print("Default logistics setup already exists")
    
    # Commit changes
    db.commit()
    
    print("\nDefault setups created successfully!")
    print("You can now use these setups for integrated simulation testing")
    print("Open http://localhost:3001 and select 'Integrated Simulation'")

if __name__ == "__main__":
    main()