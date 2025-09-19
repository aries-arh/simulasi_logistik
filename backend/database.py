import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Konfigurasi Database
# Get the absolute path to the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the project root (one level up from backend)
PROJECT_ROOT = os.path.dirname(BASE_DIR)
# Construct the absolute path to sql_app.db in the project root
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(PROJECT_ROOT, 'sql_app.db')}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Model Database
class ProductionSimulationConfigDB(Base):
    __tablename__ = "production_simulation_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    config_data = Column(Text, nullable=False) # Menyimpan seluruh konfigurasi sebagai JSON string
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class LogisticsSimulationConfigDB(Base):
    __tablename__ = "logistics_simulation_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    config_data = Column(Text, nullable=False) # Menyimpan seluruh konfigurasi sebagai JSON string
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class SimulationRunDB(Base):
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    config_name = Column(String, nullable=True) # Nama konfigurasi yang digunakan
    workday_end_time = Column(Integer)
    final_completed_tasks_count = Column(Integer)
    final_completed_tasks_per_unit = Column(Text) # Disimpan sebagai JSON string

class MasterLocationDB(Base):
    __tablename__ = "master_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class MasterTransportUnitDB(Base):
    __tablename__ = "master_transport_units"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    type = Column(String, nullable=False)
    num_sub_units = Column(Integer, default=1)
    capacity_per_sub_unit = Column(Integer, default=1)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class MasterProcessTemplateDB(Base):
    __tablename__ = "master_process_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    cycle_time = Column(Float, nullable=False)
    num_operators = Column(Integer, nullable=False)
    ng_rate = Column(Float, nullable=False)
    repair_time = Column(Float, nullable=False)
    input_from_names = Column(Text, nullable=True) # Stores JSON string of List[str]
    output_to_names = Column(Text, nullable=True) # Stores JSON string of List[str]
    join_type = Column(String, nullable=True) # 'AND' or 'OR'
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# Buat tabel database
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

# Dependency untuk mendapatkan sesi database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()