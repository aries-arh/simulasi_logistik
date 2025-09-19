import asyncio
import logging
import json
import os
import pandas as pd
import io
import shutil
import csv
import threading
from typing import List, Optional, Dict, Deque
from collections import deque, defaultdict
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, UploadFile, File, Request
from pydantic import BaseModel, Field, validator, ValidationError
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from models import (
    SimulationSetup, LogisticsSimulationSetup, SavedProductionSetupCreate, 
    SavedProductionSetupInfo, SavedProductionSetupFull, SavedLogisticsSetupCreate,
    SavedLogisticsSetupInfo, SavedLogisticsSetupFull, MasterLocation, Location, ProcessConfig, 
    MasterLocationCreate, MasterTransportUnit, MasterTransportUnitCreate, 
    MasterProcessTemplate, MasterProcessTemplateCreate, OldSimulationSetup
)
from simulation import SimulationEngine
from logistics_simulation import LogisticsSimulationEngine
from data_loader import load_bom, load_mrp_data, load_schedule
from database import (
    create_db_and_tables, get_db, ProductionSimulationConfigDB, 
    LogisticsSimulationConfigDB, SimulationRunDB, MasterLocationDB, 
    MasterTransportUnitDB, MasterProcessTemplateDB
)

load_dotenv()

# --- Basic Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT, 'sql_app.db')}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Global state for file paths ---
CURRENT_SCHEDULE_FILE = os.path.join(PROJECT_ROOT, "20250912-Schedule FA1.csv")
CURRENT_BOM_FILE = os.path.join(PROJECT_ROOT, "YMATP0200B_BOM_20250911_231232.txt")
CURRENT_MRP_FILE = os.path.join(PROJECT_ROOT, "MRP_20250912.txt")

app = FastAPI(
    title="Production and Logistics Simulator API",
    description="API for running and monitoring integrated production and logistics simulations.",
    version="3.3.0",
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# --- Pydantic Models for API ---
class ProductionRunConfig(SimulationSetup):
    schedule_file: Optional[str] = None
    bom_file: Optional[str] = None

# --- File Upload and Data Management ---
@app.post("/upload/{file_type}")
async def upload_file(file_type: str, file: UploadFile = File(...)):
    global CURRENT_SCHEDULE_FILE, CURRENT_BOM_FILE, CURRENT_MRP_FILE
    
    if file_type not in ["schedule", "bom", "mrp"]:
        raise HTTPException(status_code=400, detail="Invalid file type specified.")

    file_path = os.path.join(PROJECT_ROOT, file.filename)
    
    try:
        # Read the entire file into memory to avoid issues with partially written files
        # or files being changed during upload.
        contents = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(contents)
        
        if file_type == "schedule":
            CURRENT_SCHEDULE_FILE = file_path
        elif file_type == "bom":
            CURRENT_BOM_FILE = file_path
        elif file_type == "mrp":
            CURRENT_MRP_FILE = file_path
            
        return {"success": True, "message": f"{file_type.capitalize()} file '{file.filename}' uploaded successfully.", "filePath": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
    finally:
        await file.close()

@app.get("/data/schedule/summary")
def get_schedule_summary_endpoint():
    if not os.path.exists(CURRENT_SCHEDULE_FILE):
        raise HTTPException(status_code=404, detail="Schedule file not found. Please upload one.")
    
    schedule_df = load_schedule(CURRENT_SCHEDULE_FILE)
    if schedule_df.empty:
        # The loader function already prints detailed errors.
        raise HTTPException(status_code=400, detail="Failed to load or parse schedule data. Check backend console for errors.")

    # --- Dynamic Day Summary Logic ---
    today = datetime.now()
    day_abbr = today.strftime('%a') # e.g., 'Mon', 'Tue'
    today_col_name = f'SCH_{day_abbr}'

    today_summary = {
        'day_name': day_abbr,
        'col_name': today_col_name,
        'total_units': 0,
        'unique_models': 0,
        'unique_part_nos': 0,
        'found': False
    }

    if today_col_name in schedule_df.columns:
        # Ensure the column is numeric, coercing errors
        schedule_df[today_col_name] = pd.to_numeric(schedule_df[today_col_name], errors='coerce').fillna(0)
        
        total_units = int(schedule_df[today_col_name].sum())
        # Filter for rows where there is actual production scheduled for today
        active_rows = schedule_df[schedule_df[today_col_name] > 0]

        today_summary.update({
            'total_units': total_units,
            'unique_models': int(active_rows['MODEL'].nunique()),
            'unique_part_nos': int(active_rows['PART NO'].nunique()),
            'found': True
        })

    summary = {
        'total_rows': len(schedule_df),
        'columns': list(schedule_df.columns),
        'today_summary': today_summary,
        'unique_lines': [line for line in schedule_df['LINE'].unique().tolist() if pd.notna(line)] # Filter out NaN values
    }
    
    return {"success": True, "summary": summary}

@app.get("/data/mrp/summary")
def get_mrp_summary_endpoint():
    if not os.path.exists(CURRENT_MRP_FILE):
        raise HTTPException(status_code=404, detail="MRP file not found. Please upload one.")
    mrp_data = load_mrp_data(CURRENT_MRP_FILE)
    if not mrp_data:
        return {"error": "No MRP data available"}
    
    locations = set(d['issue_location'] for d in mrp_data.values() if 'issue_location' in d)
    summary = {
        'materials_count': len(mrp_data),
        'unique_locations': list(locations)
    }
    return {"success": True, "summary": summary}

@app.get("/data/bom/summary")
def get_bom_summary_endpoint():
    if not os.path.exists(CURRENT_BOM_FILE):
        raise HTTPException(status_code=404, detail="BOM file not found. Please upload one.")
    bom_data = load_bom(CURRENT_BOM_FILE)
    if not bom_data:
        return {"error": "No BOM data available"}

    total_components = sum(len(components) for components in bom_data.values())
    avg_components = total_components / len(bom_data) if bom_data else 0
    summary = {
        'parent_parts_count': len(bom_data),
        'total_components': total_components,
        'average_components_per_parent': round(avg_components, 2)
    }
    return {"success": True, "summary": summary}

# --- Simulation Managers ---
class ProductionSimulationManager:
    def __init__(self):
        self.engine: Optional[SimulationEngine] = None
        self.task: Optional[asyncio.Task] = None
        self.material_request_queue = deque()
        self._queue_lock = threading.Lock()
        self.sync_status = {
            "is_running": False,
            "last_sync_time": None,
            "queue_size": 0,
            "processed_requests": 0,
            "sync_errors": 0
        }

    def start_simulation(self, setup: SimulationSetup, schedule_file: str, bom_file: str):
        self.stop_simulation()

        try:
            self.engine = SimulationEngine(
                setup=setup,
                schedule_file=schedule_file,
                bom_file=bom_file,
                material_request_queue=self.material_request_queue
            )
            self.sync_status["is_running"] = True
            self.sync_status["last_sync_time"] = datetime.now()
            self.sync_status["processed_requests"] = 0
            self.sync_status["sync_errors"] = 0
            self.task = asyncio.create_task(self.run_background_simulation())
            return {"message": "Production simulation started successfully."}
        except Exception as e:
            logger.error(f"Error starting production simulation: {e}", exc_info=True)
            self.sync_status["sync_errors"] += 1
            raise HTTPException(status_code=400, detail=str(e))

    async def run_background_simulation(self):
        print("Starting production simulation background task...")
        while self.engine and self.engine.status != "finished":
            self.engine.run_step()
            await asyncio.sleep(0)  # Run as fast as possible
        print("Production simulation background task finished.")

    def get_status(self):
        if not self.engine or self.engine.status in ["finished", "stopped"]:
            base_status = {"status": "stopped"}
        else:
            base_status = self.engine.get_status()

        # Add synchronization status
        with self._queue_lock:
            self.sync_status["queue_size"] = len(self.material_request_queue)
            self.sync_status["last_sync_time"] = datetime.now()

        base_status["sync_status"] = self.sync_status.copy()
        return base_status

    def stop_simulation(self):
        if self.task and not self.task.done():
            self.task.cancel()
            print("Production simulation task cancelled.")
        self.engine = None
        with self._queue_lock:
            self.material_request_queue.clear()
        self.sync_status["is_running"] = False
        self.sync_status["last_sync_time"] = datetime.now()
        return {"message": "Production simulation stopped and cleared."}

class LogisticsSimulationManager:
    def __init__(self):
        self.engine: Optional[LogisticsSimulationEngine] = None
        self.task: Optional[asyncio.Task] = None
        self.production_manager: Optional[ProductionSimulationManager] = None
        self.sync_status = {
            "is_running": False,
            "last_sync_time": None,
            "processed_requests": 0,
            "active_deliveries": 0,
            "sync_errors": 0
        }

    def set_production_manager(self, manager: ProductionSimulationManager):
        self.production_manager = manager

    def start_simulation(self, setup: LogisticsSimulationSetup, db: Session, master_locations: List[MasterLocation] = []):
        self.stop_simulation()
        if not self.production_manager or not self.production_manager.engine:
            raise HTTPException(status_code=400, detail="Production simulation must be running before starting logistics.")

        try:
            self.engine = LogisticsSimulationEngine(
                setup=setup,
                material_request_queue=self.production_manager.material_request_queue,
                production_engine=self.production_manager.engine,
                mrp_file=CURRENT_MRP_FILE,
                master_locations=master_locations
            )
            self.sync_status["is_running"] = True
            self.sync_status["last_sync_time"] = datetime.now()
            self.sync_status["processed_requests"] = 0
            self.sync_status["active_deliveries"] = 0
            self.sync_status["sync_errors"] = 0
            self.task = asyncio.create_task(self.run_background_simulation())
            return {"message": "Logistics simulation started."}
        except Exception as e:
            logger.error(f"Error starting logistics simulation: {e}", exc_info=True)
            self.sync_status["sync_errors"] += 1
            raise HTTPException(status_code=400, detail=str(e))

    async def run_background_simulation(self):
        print("Starting logistics simulation...")
        while self.engine and self.engine.status != "finished":
            self.engine.run_step()
            await asyncio.sleep(1)
        print("Logistics simulation finished.")

    def get_status(self):
        if not self.engine:
            base_status = {"status": "stopped"}
        else:
            base_status = self.engine.get_status()

        # Update synchronization status
        self.sync_status["last_sync_time"] = datetime.now()
        if self.engine:
            self.sync_status["active_deliveries"] = len(self.engine.in_progress_tasks)

        base_status["sync_status"] = self.sync_status.copy()
        return base_status

    def stop_simulation(self):
        if self.task and not self.task.done():
            self.task.cancel()
        self.engine = None
        self.sync_status["is_running"] = False
        self.sync_status["last_sync_time"] = datetime.now()
        return {"message": "Logistics simulation stopped."}

# Instantiate and cross-link managers
prod_sim_manager = ProductionSimulationManager()
log_sim_manager = LogisticsSimulationManager()
log_sim_manager.set_production_manager(prod_sim_manager)

# --- Production Simulation Endpoints ---
@app.post("/production/run")
def run_production_simulation(run_config: ProductionRunConfig):
    try:
        schedule_file_name = os.path.basename(run_config.schedule_file) if run_config.schedule_file else os.path.basename(CURRENT_SCHEDULE_FILE)
        bom_file_name = os.path.basename(run_config.bom_file) if run_config.bom_file else os.path.basename(CURRENT_BOM_FILE)

        schedule_path = os.path.join(PROJECT_ROOT, schedule_file_name)
        bom_path = os.path.join(PROJECT_ROOT, bom_file_name)

        if not os.path.exists(schedule_path):
            raise HTTPException(status_code=404, detail=f"Schedule file not found: {schedule_file_name}")
        if not os.path.exists(bom_path):
            raise HTTPException(status_code=404, detail=f"BOM file not found: {bom_file_name}")

        setup = SimulationSetup(**run_config.dict(exclude={'schedule_file', 'bom_file'}))

        return prod_sim_manager.start_simulation(setup, schedule_path, bom_path)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing /production/run: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"An unexpected error occurred: {e}")

@app.post("/production/stop")
def stop_production_simulation():
    return prod_sim_manager.stop_simulation()

@app.get("/production/status")
def get_production_simulation_status():
    return prod_sim_manager.get_status()

# --- Logistics Simulation Endpoints ---
@app.post("/logistics/run")
def run_logistics_simulation(setup: LogisticsSimulationSetup, db: Session = Depends(get_db)):
    try:
        return log_sim_manager.start_simulation(setup, db)
    except Exception as e:
        logger.error(f"Error starting logistics simulation: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/logistics/stop")
def stop_logistics_simulation():
    return log_sim_manager.stop_simulation()

@app.get("/logistics/status")
def get_logistics_simulation_status():
    return log_sim_manager.get_status()

@app.post("/logistics/pause")
def pause_logistics_simulation():
    if log_sim_manager.engine:
        log_sim_manager.engine.pause_simulation()
        return {"message": "Logistics simulation paused."}
    return {"error": "No logistics simulation running."}

@app.post("/logistics/resume")
def resume_logistics_simulation():
    if log_sim_manager.engine:
        log_sim_manager.engine.resume_simulation()
        return {"message": "Logistics simulation resumed."}
    return {"error": "No logistics simulation running."}

@app.post("/logistics/speed/{speed}")
def set_logistics_simulation_speed(speed: float):
    if log_sim_manager.engine:
        log_sim_manager.engine.set_speed(speed)
        return {"message": f"Logistics simulation speed set to {speed}."}
    return {"error": "No logistics simulation running."}

# --- Integrated Simulation Endpoint ---
@app.post("/simulation/start-integrated/{prod_setup_id}/{log_setup_id}")
async def start_integrated_simulation(
    prod_setup_id: int,
    log_setup_id: int,
    db: Session = Depends(get_db),
    use_master_locations: bool = False,
    assembly_operators: int = 2,
    packing_operators: int = 1,
):
    prod_setup = None
    # 1. Load Production Setup or create a default empty one
    if prod_setup_id == 0:
        # Convention: ID 0 means use a default, empty setup
        print("Production Setup ID is 0. Using default empty setup.")
        prod_setup = SimulationSetup(line_processes={})
    else:
        prod_db_setup = db.query(ProductionSimulationConfigDB).filter(ProductionSimulationConfigDB.id == prod_setup_id).first()
        if not prod_db_setup:
            raise HTTPException(status_code=404, detail=f"Production setup with id {prod_setup_id} not found")
        
        try:
            # Try to load with the new model
            prod_setup = SimulationSetup(**json.loads(prod_db_setup.config_data))
        except ValidationError as e:
            # If new model fails, try to load with the old model and convert
            try:
                old_prod_setup = OldSimulationSetup(**json.loads(prod_db_setup.config_data))
                # Convert old format to new format
                prod_setup = SimulationSetup(
                    line_processes={
                        "default_line": old_prod_setup.processes # Assign all old processes to a 'default_line'
                    }
                )
            except Exception as inner_e:
                raise HTTPException(status_code=500, detail=f"Failed to parse production setup (old or new format): {inner_e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse production setup: {e}")

    # 2. Override process operators from query params
    if prod_setup and prod_setup.line_processes:
        for line_name, processes_list in prod_setup.line_processes.items():
            for process in processes_list:
                if process.name.lower() == 'assembly':
                    process.num_operators = assembly_operators
                elif process.name.lower() == 'packing':
                    process.num_operators = packing_operators

    # 3. Start Production Simulation (using global files)
    prod_sim_manager.start_simulation(prod_setup, CURRENT_SCHEDULE_FILE, CURRENT_BOM_FILE)

    # Give it a moment to initialize before starting logistics
    await asyncio.sleep(0.1)

    # 4. Load Logistics Setup
    log_db_setup = db.query(LogisticsSimulationConfigDB).filter(LogisticsSimulationConfigDB.id == log_setup_id).first()
    if not log_db_setup:
        raise HTTPException(status_code=404, detail=f"Logistics setup with id {log_setup_id} not found")
    
    try:
        log_setup = LogisticsSimulationSetup(**json.loads(log_db_setup.config_data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse logistics setup: {e}")

    # 5. Handle master locations override
    master_locs = []
    if use_master_locations:
        master_locs_db = db.query(MasterLocationDB).all()
        if master_locs_db:
            # Convert DB objects to Pydantic models
            master_locs = [MasterLocation.from_orm(loc) for loc in master_locs_db]
            log_setup.locations = [Location(name=loc.name, stock={}) for loc in master_locs]

    # 6. Start Logistics Simulation
    log_sim_manager.start_simulation(log_setup, db, master_locations=master_locs)

    return {"message": "Integrated simulation started successfully."}


# --- Setup Management Endpoints ---
@app.get("/setups/production/", response_model=List[SavedProductionSetupInfo])
def get_production_setups(db: Session = Depends(get_db)):
    return db.query(ProductionSimulationConfigDB).all()

@app.get("/setups/logistics/", response_model=List[SavedLogisticsSetupInfo])
def get_logistics_setups(db: Session = Depends(get_db)):
    return db.query(LogisticsSimulationConfigDB).all()

@app.post("/setups/production/")
def create_production_setup(setup: SavedProductionSetupCreate, db: Session = Depends(get_db)):
    db_setup = ProductionSimulationConfigDB(
        name=setup.name,
        description=setup.description,
        config_data=setup.setup_data.model_dump_json()
    )
    db.add(db_setup)
    db.commit()
    db.refresh(db_setup)
    return {"id": db_setup.id, "message": "Production setup created successfully."}

@app.post("/setups/logistics/")
async def create_logistics_setup(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    try:
        setup = SavedLogisticsSetupCreate(**data)
        db_setup = LogisticsSimulationConfigDB(
            name=setup.name,
            description=setup.description,
            config_data=setup.setup_data.model_dump_json()
        )
        db.add(db_setup)
        db.commit()
        db.refresh(db_setup)
        return {"id": db_setup.id, "message": "Logistics setup created successfully."}
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

# --- Master Data Management Endpoints ---
@app.get("/master/locations/", response_model=List[MasterLocation])
def get_master_locations(db: Session = Depends(get_db)):
    return db.query(MasterLocationDB).all()

@app.post("/master/locations/")
def create_master_location(location: MasterLocationCreate, db: Session = Depends(get_db)):
    db_location = MasterLocationDB(**location.dict())
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location

@app.put("/master/locations/{location_id}")
def update_master_location(location_id: int, location: MasterLocationCreate, db: Session = Depends(get_db)):
    db_location = db.query(MasterLocationDB).filter(MasterLocationDB.id == location_id).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Location not found")
    for key, value in location.dict().items():
        setattr(db_location, key, value)
    db.commit()
    db.refresh(db_location)
    return db_location

@app.delete("/master/locations/{location_id}")
def delete_master_location(location_id: int, db: Session = Depends(get_db)):
    db_location = db.query(MasterLocationDB).filter(MasterLocationDB.id == location_id).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Location not found")
    db.delete(db_location)
    db.commit()
    return {"message": "Location deleted successfully"}

@app.get("/master/transport-units/", response_model=List[MasterTransportUnit])
def get_master_transport_units(db: Session = Depends(get_db)):
    return db.query(MasterTransportUnitDB).all()

@app.post("/master/transport-units/")
def create_master_transport_unit(unit: MasterTransportUnitCreate, db: Session = Depends(get_db)):
    db_unit = MasterTransportUnitDB(**unit.dict())
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return db_unit

@app.put("/master/transport-units/{unit_id}")
def update_master_transport_unit(unit_id: int, unit: MasterTransportUnitCreate, db: Session = Depends(get_db)):
    db_unit = db.query(MasterTransportUnitDB).filter(MasterTransportUnitDB.id == unit_id).first()
    if not db_unit:
        raise HTTPException(status_code=404, detail="Transport unit not found")
    for key, value in unit.dict().items():
        setattr(db_unit, key, value)
    db.commit()
    db.refresh(db_unit)
    return db_unit

@app.delete("/master/transport-units/{unit_id}")
def delete_master_transport_unit(unit_id: int, db: Session = Depends(get_db)):
    db_unit = db.query(MasterTransportUnitDB).filter(MasterTransportUnitDB.id == unit_id).first()
    if not db_unit:
        raise HTTPException(status_code=404, detail="Transport unit not found")
    db.delete(db_unit)
    db.commit()
    return {"message": "Transport unit deleted successfully"}

@app.get("/master/process-templates/", response_model=List[MasterProcessTemplate])
def get_master_process_templates(db: Session = Depends(get_db)):
    templates = db.query(MasterProcessTemplateDB).all()
    for t in templates:
        t.input_from_names = json.loads(t.input_from_names) if t.input_from_names else []
        t.output_to_names = json.loads(t.output_to_names) if t.output_to_names else []
    return templates

@app.post("/master/process-templates/")
def create_master_process_template(template: MasterProcessTemplateCreate, db: Session = Depends(get_db)):
    db_template = MasterProcessTemplateDB(
        name=template.name,
        description=template.description,
        cycle_time=template.cycle_time,
        num_operators=template.num_operators,
        ng_rate=template.ng_rate,
        repair_time=template.repair_time,
        join_type=template.join_type,
        input_from_names=json.dumps(template.input_from_names),
        output_to_names=json.dumps(template.output_to_names)
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

@app.put("/master/process-templates/{template_id}")
def update_master_process_template(template_id: int, template: MasterProcessTemplateCreate, db: Session = Depends(get_db)):
    db_template = db.query(MasterProcessTemplateDB).filter(MasterProcessTemplateDB.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Process template not found")
    db_template.name = template.name
    db_template.description = template.description
    db_template.cycle_time = template.cycle_time
    db_template.num_operators = template.num_operators
    db_template.ng_rate = template.ng_rate
    db_template.repair_time = template.repair_time
    db_template.join_type = template.join_type
    db_template.input_from_names = json.dumps(template.input_from_names)
    db_template.output_to_names = json.dumps(template.output_to_names)
    db.commit()
    db.refresh(db_template)
    return db_template

@app.delete("/master/process-templates/{template_id}")
def delete_master_process_template(template_id: int, db: Session = Depends(get_db)):
    db_template = db.query(MasterProcessTemplateDB).filter(MasterProcessTemplateDB.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Process template not found")
    db.delete(db_template)
    db.commit()
    return {"message": "Process template deleted successfully"}

# --- Health Check and Root ---
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running"}

@app.get("/")
def root():
    return {"message": "Production & Logistics Simulator API", "version": "3.3.0", "docs": "/docs"}
