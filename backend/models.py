from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime

# --- Production Simulation Models ---

class ProcessConfig(BaseModel):
    name: str = Field(..., title="Process Name", description="Name of the production process step.")
    cycle_time: float = Field(..., gt=0, title="Cycle Time", description="Time in seconds to complete one unit.")
    num_operators: int = Field(..., gt=0, title="Number of Operators", description="How many operators are assigned to this process.")
    ng_rate: float = Field(default=0.0, ge=0.0, le=1.0, title="NG Rate", description="No Good (defect) rate, from 0.0 to 1.0.")
    repair_time: float = Field(default=0.0, ge=0.0, title="Repair Time", description="Time in seconds to fix an NG unit.")
    input_from: List[str] = Field(default_factory=list, title="Input From", description="List of process names from which this process receives units.")
    output_to: List[str] = Field(default_factory=list, title="Output To", description="List of process names to which this process sends units.")
    join_type: Optional[str] = Field(None, title="Join Type", description="Type of join for multiple inputs: 'AND' (all inputs required) or 'OR' (any input sufficient).")

class SimulationSetup(BaseModel):
    line_processes: Dict[str, List[ProcessConfig]] = Field(
        ...,
        title="Line-specific Process Configurations",
        description="A dictionary mapping line names to their list of process configurations."
    )

class OldSimulationSetup(BaseModel):
    processes: List[ProcessConfig] = Field(..., min_items=1, title="Process List", description="The list of process configurations.")

# --- Logistics Simulation Models (Refactored for Per-Material Simulation) ---

class Location(BaseModel):
    name: str = Field(..., title="Location Name", description="Unique name for a location.")
    # REFACTORED: Stock is now a dictionary of Material -> Quantity
    stock: Dict[str, int] = Field(default_factory=dict, title="Stock", description="Stock per material at this location.")

class TransportUnit(BaseModel):
    name: str = Field(..., title="Transport Unit Name", description="Name of the transport unit (e.g., 'Forklift 1', 'Kururu A').")
    type: str = Field(..., title="Transport Unit Type", description="Type of the transport unit (e.g., 'Forklift', 'Kururu', 'AGV', 'Manual').")
    num_sub_units: int = Field(default=1, gt=0, title="Number of Sub-units", description="Number of sub-units (e.g., wagons in a train).")
    capacity_per_sub_unit: int = Field(default=1, gt=0, title="Capacity per Sub-unit", description="Capacity of each sub-unit in lots.")

    @property
    def total_capacity(self) -> int:
        return self.num_sub_units * self.capacity_per_sub_unit

class TransportTask(BaseModel):
    origin: str = Field(..., title="Origin Location", description="Name of the starting location for the task.")
    destination: str = Field(..., title="Destination Location", description="Name of the ending location for the task.")
    # REFACTORED: Task is now per-material
    material: str = Field(..., title="Material ID", description="The specific material to be transported.")
    lots_required: int = Field(..., gt=0, title="Lots Required", description="Number of lots of the material to transport.")
    parent_part: Optional[str] = Field(None, title="Parent Part", description="The parent part number that this material is for.")
    target_process: Optional[str] = Field(None, title="Target Process", description="The name of the target process within the destination location.")
    
    distance: float = Field(..., gt=0, title="Distance", description="Distance between origin and destination in meters.")
    travel_time: float = Field(..., gt=0, title="Travel Time", description="Time in seconds to travel from origin to destination.")
    loading_time: float = Field(..., ge=0, title="Loading Time", description="Time in seconds to load goods at the origin.")
    unloading_time: float = Field(..., ge=0, title="Unloading Time", description="Time in seconds to unload goods at the destination.")
    return_time: Optional[float] = Field(None, gt=0, title="Return Time", description="Time in seconds to return to the origin. Defaults to travel_time if not set.")
    transport_unit_names: List[str] = Field(..., min_items=1, title="Transport Unit Names", description="List of transport unit names assigned to this task.")
    unit_start_delay: int = Field(default=0, ge=0, title="Unit Start Delay", description="Delay in seconds between each unit starting the task.")
    
    # Runtime fields
    current_load_in_lots: Optional[int] = Field(None, description="Runtime field to store the actual load of a trip in lots.")

    @validator('return_time', pre=True, always=True)
    def set_return_time(cls, v, values):
        if v is None and 'travel_time' in values:
            return values['travel_time']
        return v

class Shift(BaseModel):
    start_time: int = Field(..., ge=0, title="Shift Start Time")
    end_time: int = Field(..., gt=0, title="Shift End Time")

class ScheduledEvent(BaseModel):
    name: str = Field(..., title="Event Name")
    start_time: int = Field(..., ge=0, title="Event Start Time")
    duration: int = Field(..., gt=0, title="Event Duration")
    recurrence_rule: str = Field(default="none", title="Recurrence Rule", description="e.g., 'none', 'daily'")

class LogisticsSimulationSetup(BaseModel):
    locations: List[Location] = Field(..., min_items=2, title="Locations")
    transport_units: List[TransportUnit] = Field(..., min_items=1, title="Transport Units")
    tasks: List[TransportTask] = Field(..., min_items=1, title="Transport Tasks")
    # REMOVED: units_per_lot is now handled per-material via the comparison file
    workday_start_time: int = Field(default=0, ge=0, title="Workday Start Time")
    workday_end_time: int = Field(default=28800, gt=0, title="Workday End Time")
    shifts: List[Shift] = Field(default_factory=list, title="Shifts")
    scheduled_events: List[ScheduledEvent] = Field(default_factory=list, title="Scheduled Events")
    abnormality_rate: float = Field(default=0.0, ge=0.0, le=1.0, title="Abnormality Rate")
    abnormality_duration: int = Field(default=0, ge=0, title="Abnormality Duration")

# --- Schemas for Saved Setups ---

# --- Production ---
class SavedProductionSetupBase(BaseModel):
    name: str = Field(..., title="Scenario Name")
    description: Optional[str] = Field(None, title="Scenario Description")

class SavedProductionSetupCreate(SavedProductionSetupBase):
    setup_data: SimulationSetup

class SavedProductionSetupInfo(SavedProductionSetupBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SavedProductionSetupFull(SavedProductionSetupInfo):
    setup_data: SimulationSetup

# --- Logistics ---
class SavedLogisticsSetupBase(BaseModel):
    name: str = Field(..., title="Scenario Name")
    description: Optional[str] = Field(None, title="Scenario Description")

class SavedLogisticsSetupCreate(SavedLogisticsSetupBase):
    setup_data: LogisticsSimulationSetup

class SavedLogisticsSetupInfo(SavedLogisticsSetupBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SavedLogisticsSetupFull(SavedLogisticsSetupInfo):
    setup_data: LogisticsSimulationSetup

# --- Master Data Schemas ---

# Master Location
class MasterLocationBase(BaseModel):
    name: str = Field(..., title="Location Name")
    description: Optional[str] = Field(None, title="Location Description")
    lines: List[str] = Field(default_factory=list, title="Production Lines", description="List of production lines at this location.")
    # NOTE: Master stock is generic; simulation-specific stock is now per-material.
    stock: int = Field(default=0, ge=0, title="Stock", description="Current stock at this master location.")

class MasterLocationCreate(MasterLocationBase):
    pass

class MasterLocation(MasterLocationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Master Transport Unit
class MasterTransportUnitBase(BaseModel):
    name: str = Field(..., title="Transport Unit Name")
    type: str = Field(..., title="Transport Unit Type", description="e.g., 'Kururu', 'Forklift', 'AGV', 'Manual'")
    num_sub_units: int = Field(default=1, gt=0, title="Number of Sub-units", description="e.g., wagons in a train")
    capacity_per_sub_unit: int = Field(default=1, gt=0, title="Capacity per Sub-unit", description="e.g., lots per wagon")
    description: Optional[str] = Field(None, title="Unit Description")

class MasterTransportUnitCreate(MasterTransportUnitBase):
    pass

class MasterTransportUnit(MasterTransportUnitBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Master Process Template
class MasterProcessTemplateBase(BaseModel):
    name: str = Field(..., title="Process Template Name")
    cycle_time: float = Field(..., gt=0, title="Cycle Time (seconds)")
    num_operators: int = Field(..., gt=0, title="Number of Operators")
    ng_rate: float = Field(default=0.0, ge=0.0, le=1.0, title="NG Rate (0.0 to 1.0)")
    repair_time: float = Field(default=0.0, ge=0.0, title="Repair Time (seconds)")
    input_from_names: Optional[List[str]] = Field(default_factory=list, title="Input From Process Names")
    output_to_names: Optional[List[str]] = Field(default_factory=list, title="Output To Process Names")
    join_type: Optional[str] = Field(None, title="Join Type", description="AND or OR for multiple inputs")
    description: Optional[str] = Field(None, title="Template Description")

class MasterProcessTemplateCreate(MasterProcessTemplateBase):
    pass

class MasterProcessTemplate(MasterProcessTemplateBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True