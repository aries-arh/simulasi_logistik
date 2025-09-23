import asyncio
import logging
import json
import os
import pandas as pd
import io
import shutil
import csv
import threading
import time
from typing import List, Optional, Dict, Deque
from collections import deque, defaultdict
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, UploadFile, File, Request, BackgroundTasks
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
from production_engine_v2 import ProductionEngineV2
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
    version="3.4.0",
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

# --- Simulation Managers (V1 - Original) ---
class ProductionSimulationManager:
    def __init__(self):
        self.engine: Optional[SimulationEngine] = None
        self.task: Optional[asyncio.Task] = None
        self.material_request_queue = deque()
        self._queue_lock = threading.Lock()
        self.sync_status = {"is_running": False, "last_sync_time": None, "queue_size": 0, "processed_requests": 0, "sync_errors": 0}

    def start_simulation(self, setup: SimulationSetup, schedule_file: str, bom_file: str):
        self.stop_simulation()
        try:
            self.engine = SimulationEngine(setup=setup, schedule_file=schedule_file, bom_file=bom_file, material_request_queue=self.material_request_queue)
            self.sync_status["is_running"] = True
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
            await asyncio.sleep(0)
        print("Production simulation background task finished.")

    def get_status(self):
        if not self.engine or self.engine.status in ["finished", "stopped"]:
            base_status = {"status": "stopped"}
        else:
            base_status = self.engine.get_status()
        with self._queue_lock:
            self.sync_status["queue_size"] = len(self.material_request_queue)
            self.sync_status["last_sync_time"] = datetime.now()
        base_status["sync_status"] = self.sync_status.copy()
        return base_status

    def stop_simulation(self):
        if self.task and not self.task.done():
            self.task.cancel()
        self.engine = None
        with self._queue_lock:
            self.material_request_queue.clear()
        self.sync_status["is_running"] = False
        return {"message": "Production simulation stopped and cleared."}

class LogisticsSimulationManager:
    def __init__(self):
        self.engine: Optional[LogisticsSimulationEngine] = None
        self.task: Optional[asyncio.Task] = None
        self.production_manager: Optional[ProductionSimulationManager] = None
        self.sync_status = {"is_running": False, "last_sync_time": None, "processed_requests": 0, "active_deliveries": 0, "sync_errors": 0}

    def set_production_manager(self, manager: ProductionSimulationManager):
        self.production_manager = manager

    def start_simulation(self, setup: LogisticsSimulationSetup, db: Session, master_locations: List[MasterLocation] = []):
        self.stop_simulation()
        if not self.production_manager or not self.production_manager.engine:
            raise HTTPException(status_code=400, detail="Production simulation must be running before starting logistics.")
        try:
            self.engine = LogisticsSimulationEngine(setup=setup, material_request_queue=self.production_manager.material_request_queue, production_engine=self.production_manager.engine, mrp_file=CURRENT_MRP_FILE, master_locations=master_locations)
            self.sync_status["is_running"] = True
            self.task = asyncio.create_task(self.run_background_simulation())
            return {"message": "Logistics simulation started."}
        except Exception as e:
            logger.error(f"Error starting logistics simulation: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(e))

    async def run_background_simulation(self):
        print("Starting logistics simulation...")
        while self.engine and self.engine.status != "finished":
            self.engine.run_step()
            await asyncio.sleep(0)
        print("Logistics simulation finished.")

    def get_status(self):
        if not self.engine:
            base_status = {"status": "stopped"}
        else:
            base_status = self.engine.get_status()
        if self.engine:
            self.sync_status["active_deliveries"] = len(self.engine.in_progress_tasks)
        base_status["sync_status"] = self.sync_status.copy()
        return base_status

    def stop_simulation(self):
        if self.task and not self.task.done():
            self.task.cancel()
        self.engine = None
        self.sync_status["is_running"] = False
        return {"message": "Logistics simulation stopped."}

# --- Simulation Managers (V2 - New) ---
class ProductionSimulationManagerV2:
    def __init__(self):
        self.engine: Optional[ProductionEngineV2] = None

    def setup_simulation(self, setup: SimulationSetup, schedule_file: str, bom_file: str):
        self.stop_simulation()
        try:
            self.engine = ProductionEngineV2(
                setup=setup,
                schedule_file=schedule_file,
                bom_file=bom_file,
                material_request_queue=deque()
            )
        except Exception as e:
            logger.error(f"Error setting up production simulation V2: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(e))

    def run_simulation_loop(self):
        if not self.engine:
            print("ERROR: V2 simulation engine not setup. Cannot run.")
            return
        print("Starting production simulation V2 background task...")
        while self.engine and self.engine.status != "finished":
            self.engine.run_step()
            time.sleep(0.1) # Prevent runaway clock when idle
        print("Production simulation V2 background task finished.")

    def get_status(self):
        if not self.engine or self.engine.status in ["finished", "stopped"]:
            return {"status": "stopped"}
        return self.engine.get_status()

    def stop_simulation(self):
        self.engine = None
        return {"message": "Production simulation V2 stopped and cleared."}

# --- Instantiate Managers ---
prod_sim_manager = ProductionSimulationManager()
log_sim_manager = LogisticsSimulationManager()
log_sim_manager.set_production_manager(prod_sim_manager)
prod_sim_manager_v2 = ProductionSimulationManagerV2()


# --- Master Data Management Endpoints ---

@app.get("/master/process-templates/", response_model=List[MasterProcessTemplate])
def get_all_process_templates(db: Session = Depends(get_db)):
    templates = db.query(MasterProcessTemplateDB).all()
    return templates

@app.post("/master/process-templates/", response_model=MasterProcessTemplate, status_code=status.HTTP_201_CREATED)
def create_process_template(template: MasterProcessTemplateCreate, db: Session = Depends(get_db)):
    db_template = MasterProcessTemplateDB(**template.dict())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

@app.put("/master/process-templates/{template_id}", response_model=MasterProcessTemplate)
def update_process_template(template_id: int, template: MasterProcessTemplateCreate, db: Session = Depends(get_db)):
    db_template = db.query(MasterProcessTemplateDB).filter(MasterProcessTemplateDB.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Process template not found")
    
    for key, value in template.dict().items():
        setattr(db_template, key, value)
        
    db.commit()
    db.refresh(db_template)
    return db_template

@app.delete("/master/process-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_process_template(template_id: int, db: Session = Depends(get_db)):
    db_template = db.query(MasterProcessTemplateDB).filter(MasterProcessTemplateDB.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Process template not found")
    
    db.delete(db_template)
    db.commit()
    return {"ok": True}

@app.get("/master/locations/", response_model=List[MasterLocation])
def get_all_locations(db: Session = Depends(get_db)):
    locations = db.query(MasterLocationDB).all()
    return [MasterLocation.from_orm(l) for l in locations]

@app.post("/master/locations/", response_model=MasterLocation, status_code=status.HTTP_201_CREATED)
def create_location(location: MasterLocationCreate, db: Session = Depends(get_db)):
    db_location = MasterLocationDB(**location.dict())
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location

@app.get("/master/transport-units/", response_model=List[MasterTransportUnit])
def get_all_transport_units(db: Session = Depends(get_db)):
    units = db.query(MasterTransportUnitDB).all()
    return [MasterTransportUnit.from_orm(u) for u in units]

@app.post("/master/transport-units/", response_model=MasterTransportUnit, status_code=status.HTTP_201_CREATED)
def create_transport_unit(unit: MasterTransportUnitCreate, db: Session = Depends(get_db)):
    db_unit = MasterTransportUnitDB(**unit.dict())
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return db_unit

@app.get("/setups/production/", response_model=List[SavedProductionSetupInfo])
def get_all_production_setups(db: Session = Depends(get_db)):
    setups = db.query(ProductionSimulationConfigDB).all()
    return [SavedProductionSetupInfo.from_orm(s) for s in setups]

@app.get("/setups/logistics/", response_model=List[SavedLogisticsSetupInfo])
def get_all_logistics_setups(db: Session = Depends(get_db)):
    setups = db.query(LogisticsSimulationConfigDB).all()
    return [SavedLogisticsSetupInfo.from_orm(s) for s in setups]


# --- File Upload Endpoints ---

@app.post("/upload/schedule")
async def upload_schedule_file(file: UploadFile = File(...)):
    file_path = os.path.join(PROJECT_ROOT, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "path": file_path}

@app.post("/upload/bom")
async def upload_bom_file(file: UploadFile = File(...)):
    file_path = os.path.join(PROJECT_ROOT, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "path": file_path}

@app.post("/upload/mrp")
async def upload_mrp_file(file: UploadFile = File(...)):
    file_path = os.path.join(PROJECT_ROOT, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "path": file_path}


# --- Data Summary Endpoints ---

@app.get("/data/schedule/summary")
def get_schedule_summary(filename: str):
    schedule_file_path = os.path.join(PROJECT_ROOT, filename)
    if not os.path.exists(schedule_file_path):
        raise HTTPException(status_code=404, detail=f"Schedule file '{filename}' not found. Please upload one first.")

    try:
        df = load_schedule(schedule_file_path)
        filename = os.path.basename(schedule_file_path)

        df['LINE'].ffill(inplace=True)
        valid_lines_df = df[df['LINE'].str.contains('FA1-L', na=False)]
        total_lines = valid_lines_df['LINE'].nunique()

        order_col = next((col for col in df.columns if 'NO. URUT' in col), None)
        if not order_col:
            raise ValueError("Could not find 'NO. URUT' column in the schedule.")
        
        total_orders = pd.to_numeric(df[order_col], errors='coerce').notna().sum()

        date_cols = [col for col in df.columns if pd.to_datetime(col, format='%d-%b', errors='coerce') is not pd.NaT]
        date_range_str = ""
        if date_cols:
            sorted_dates = sorted([pd.to_datetime(d, format='%d-%b') for d in date_cols])
            start_date = sorted_dates[0].strftime('%d %b')
            end_date = sorted_dates[-1].strftime('%d %b')
            date_range_str = f"{start_date} - {end_date}"

        return {
            "summary": {
                "filename": filename,
                "unique_lines": valid_lines_df['LINE'].unique().tolist(),
                "total_orders": int(total_orders),
                "date_range": date_range_str
            }
        }

    except Exception as e:
        logger.error(f"Error generating schedule summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse schedule file: {str(e)}")

@app.get("/data/bom/summary")
def get_bom_summary(filename: str):
    bom_file_path = os.path.join(PROJECT_ROOT, filename)
    if not os.path.exists(bom_file_path):
        raise HTTPException(status_code=404, detail=f"BOM file '{filename}' not found.")
    
    bom_data = load_bom(bom_file_path)
    parent_parts = len(bom_data)
    total_components = sum(len(components) for components in bom_data.values())
    
    return {
        "summary": {
            "filename": filename,
            "parent_parts": parent_parts,
            "total_components": total_components
        }
    }

@app.get("/data/mrp/summary")
def get_mrp_summary(filename: str):
    mrp_file_path = os.path.join(PROJECT_ROOT, filename)
    if not os.path.exists(mrp_file_path):
        raise HTTPException(status_code=404, detail=f"MRP file '{filename}' not found.")
    
    mrp_data = load_mrp_data(mrp_file_path)
    
    return {
        "summary": {
            "filename": filename,
            "total_materials": len(mrp_data)
        }
    }

@app.get("/debug/schedule")
def debug_schedule(filename: str):
    schedule_file_path = os.path.join(PROJECT_ROOT, filename)
    if not os.path.exists(schedule_file_path):
        raise HTTPException(status_code=404, detail=f"Schedule file '{filename}' not found.")
    
    df = load_schedule(schedule_file_path)
    return df.head().to_dict(orient='records')


# --- V2 Endpoints ---
@app.post("/v2/production/run")
def run_production_simulation_v2(run_config: ProductionRunConfig, background_tasks: BackgroundTasks):
    try:
        # Ensure schedule_file_name is always a string
        schedule_file_name = os.path.basename(run_config.schedule_file) if run_config.schedule_file else os.path.basename(CURRENT_SCHEDULE_FILE or "")
        # Ensure bom_file_name is always a string
        bom_file_name = os.path.basename(run_config.bom_file) if run_config.bom_file else os.path.basename(CURRENT_BOM_FILE or "")

        print(f"DEBUG: run_config.schedule_file received: {run_config.schedule_file}")
        print(f"DEBUG: schedule_file_name extracted: {schedule_file_name}")
        schedule_path = os.path.join(PROJECT_ROOT, schedule_file_name)
        print(f"DEBUG: schedule_path for simulation: {schedule_path}")

        bom_path = os.path.join(PROJECT_ROOT, bom_file_name)
        print(f"DEBUG: bom_path for simulation: {bom_path}")

        if not os.path.exists(schedule_path):
            raise HTTPException(status_code=404, detail=f"Schedule file not found: {schedule_file_name}")
        if not os.path.exists(bom_path):
            raise HTTPException(status_code=404, detail=f"BOM file not found: {bom_file_name}")

        setup = SimulationSetup(**run_config.dict(exclude={'schedule_file', 'bom_file'}))
        
        prod_sim_manager_v2.setup_simulation(setup, schedule_path, bom_path)
        background_tasks.add_task(prod_sim_manager_v2.run_simulation_loop)
        
        return {"message": "Production simulation V2 started in background."}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing /v2/production/run: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"An unexpected error occurred: {e}")

@app.get("/v2/production/status")
def get_production_simulation_v2_status():
    return prod_sim_manager_v2.get_status()

@app.post("/v2/production/stop")
def stop_production_simulation_v2():
    return prod_sim_manager_v2.stop_simulation()

# --- Original (V1) Endpoints ---
@app.post("/production/run")
def run_production_simulation(run_config: ProductionRunConfig):
    # This endpoint remains unchanged
    try:
        schedule_file_name = os.path.basename(run_config.schedule_file) if run_config.schedule_file else os.path.basename(CURRENT_SCHEDULE_FILE)
        bom_file_name = os.path.basename(run_config.bom_file) if run_config.bom_file else os.path.basename(CURRENT_BOM_FILE)
        schedule_path = os.path.join(PROJECT_ROOT, schedule_file_name)
        bom_path = os.path.join(PROJECT_ROOT, bom_file_name)
        if not os.path.exists(schedule_path) or not os.path.exists(bom_path):
            raise HTTPException(status_code=404, detail="Schedule or BOM file not found")
        setup = SimulationSetup(**run_config.dict(exclude={'schedule_file', 'bom_file'}))
        return prod_sim_manager.start_simulation(setup, schedule_path, bom_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ... (Keep all other original endpoints for logistics, integrated sim, setups, etc.)

# --- Health Check and Root ---
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running"}

@app.get("/")
def root():
    return {"message": "Production & Logistics Simulator API", "version": "3.4.0", "docs": "/docs"}
