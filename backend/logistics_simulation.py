import random
from typing import Dict, List, Deque, Optional
from collections import deque, defaultdict
from models import LogisticsSimulationSetup, TransportTask, Location, TransportUnit, MasterLocation
from data_loader import load_mrp_data
from simulation import SimulationEngine # Import Production Engine to add stock

class LogisticsSimulationEngine:
    def __init__(self, setup: LogisticsSimulationSetup, material_request_queue: deque, production_engine: SimulationEngine, mrp_file: str, master_locations: List[MasterLocation] = []):
        # Validate setup
        if not setup.locations:
            raise ValueError("Logistics setup must include at least one location")
        if not setup.transport_units:
            raise ValueError("Logistics setup must include at least one transport unit")
        if setup.workday_start_time >= setup.workday_end_time:
            raise ValueError("Workday start time must be before end time")

        self.setup = setup
        self.status = "initializing"
        self.current_time = self.setup.workday_start_time
        self.is_paused = False
        self.simulation_speed = 1.0

        # Performance monitoring
        self.performance_metrics = {
            "total_requests_processed": 0,
            "total_tasks_completed": 0,
            "average_processing_time": 0,
            "peak_concurrent_units": 0,
            "total_distance_traveled": 0,
            "efficiency_score": 0,
            "step_processing_times": [],
            "average_queue_time": 0,
            "throughput": 0
        }
        self.step_start_time = None
        self.batch_size_requests = 1000  # Max requests to process per step, large to allow parallel
        # Removed batch_size_assignments to allow unlimited assignments for better vehicle utilization

        # Communication with Production Engine
        self.material_request_queue = material_request_queue
        self.production_engine = production_engine

        # Load MRP data to find material origins
        self.mrp_data = load_mrp_data(mrp_file)
        if not self.mrp_data:
            print("Warning: MRP data could not be loaded. Material origins will be unknown.")

        self.location_to_lines_map: Dict[str, List[str]] = {}
        if master_locations:
            for loc in master_locations:
                self.location_to_lines_map[loc.name] = loc.lines

        self.locations: Dict[str, Location] = {loc.name: loc for loc in self.setup.locations}
        self.transport_units_map: Dict[str, TransportUnit] = {unit.name: unit for unit in self.setup.transport_units}

        self.transport_units_status: Dict[str, Dict] = {
            unit.name: {
                "name": unit.name,
                "type": unit.type,
                "status": "idle",
                "current_task": None,
                "current_location": self.find_initial_location(unit.name),
                "progress": 0,
                "stoppage_duration": 0,
                "delay_countdown": 0,
                "current_load_carried_by_unit": {},
            }
            for unit in self.setup.transport_units
        }
        
        self.completed_tasks: List[TransportTask] = []
        self.in_progress_tasks: Dict[int, TransportTask] = {}

        self.completed_tasks_count = 0
        self.completed_tasks_per_unit: Dict[str, int] = {unit.name: 0 for unit in self.setup.transport_units}
        self.task_assignment_index = 0  # For round-robin task assignment to transports

        self.event_log: Deque[str] = deque(maxlen=100)
        
        # If a production engine is present, this is an integrated run.
        # Ignore pre-set tasks and rely solely on dynamic requests.
        if production_engine:
            self.available_tasks: Deque[TransportTask] = deque()
            self._log("Integrated mode: Ignoring pre-set tasks. Waiting for dynamic requests.")
        else:
            self.available_tasks: Deque[TransportTask] = deque(self.setup.tasks)

        self._log("Logistics Simulation Initialized.")

    def _log(self, message: str):
        time_str = f"{int(self.current_time // 3600):02d}:{int((self.current_time % 3600) // 60):02d}:{int(self.current_time % 60):02d}"
        self.event_log.append(f"[{time_str}] {message}")

    def find_initial_location(self, unit_name: str) -> str:
        # A reasonable default: start at the first location defined.
        return self.setup.locations[0].name if self.setup.locations else "Unknown"

    def _process_material_requests(self):
        """Processes pending material requests from production and creates transport tasks.
        Uses batch processing to limit requests per step for performance."""
        processed_requests = 0
        batch_limit = min(self.batch_size_requests, len(self.material_request_queue))

        for i in range(batch_limit):
            try:
                request = self.material_request_queue.popleft()
                material = request.get('material')
                quantity_needed = request.get('quantity')
                full_destination = request.get('destination')
                parent_part = request.get('parent_part')

                if not all([material, quantity_needed, full_destination]):
                    self._log(f"Invalid material request: {request}")
                    print(f"Invalid material request: {request}")
                    continue

                # Parse destination into location and process
                line_name, process_name = None, None
                if ':' in full_destination:
                    line_name, process_name = full_destination.split(':', 1)

                destination_location_name = None
                if line_name:
                    for loc_name, lines in self.location_to_lines_map.items():
                        if line_name in lines:
                            destination_location_name = loc_name
                            break
                
                if not destination_location_name:
                    self._log(f"Warning: Could not find master location for line '{line_name}' from destination '{full_destination}'. Falling back to line name.")
                    destination_location_name = line_name if line_name else full_destination


                origin = self.mrp_data.get(material, {}).get('issue_location', 'WAREHOUSE')

                # Create tasks, now with correct destination and target_process
                unit_names = list(self.transport_units_map.keys())
                # Ensure quantity_needed is an integer
                for _ in range(int(quantity_needed)):
                    new_task = TransportTask(
                        material=material,
                        lots_required=1,
                        parent_part=parent_part,
                        origin=origin,
                        destination=destination_location_name,
                        target_process=process_name,
                        transport_unit_names=unit_names,
                        loading_time=30,
                        travel_time=120,
                        unloading_time=30,
                        return_time=120,
                        distance=500 # Default distance
                    )
                    self.available_tasks.append(new_task)
                    processed_requests += 1
                    self._log(f"Processed request: Deliver 1 lot of {material} to {destination_location_name} (Process: {process_name})")
            except Exception as e:
                self._log(f"Error processing material request: {e}")

        if processed_requests > 0:
            print(f"Logistics: Processed {processed_requests} material requests this step")
            self._log(f"Total material requests processed this step: {processed_requests}")
            self.performance_metrics["total_requests_processed"] += processed_requests

    def is_in_shift(self):
        if not self.setup.shifts:
            return True
        for shift in self.setup.shifts:
            if shift.start_time <= self.current_time < shift.end_time:
                return True
        return False

    def check_scheduled_events(self):
        # This logic remains the same
        pass

    def run_step(self):
        import time
        step_start = time.time()

        if self.is_paused:
            return

        if self.current_time >= self.setup.workday_end_time and not self.in_progress_tasks:
            if self.status != "finished":
                self._log("Workday finished and all tasks are complete. Logistics simulation ending.")
                self.status = "finished"
                self._calculate_final_metrics()
            return

        self.status = "running"
        self.current_time += 1

        # Process new material requests from the production line
        self._process_material_requests()

        if not self.is_in_shift():
            # ... (shift logic remains the same)
            return

        self.check_scheduled_events()

        # Refactored Task Assignment Logic
        idle_units = [name for name, status in self.transport_units_status.items() if status["status"] == "idle"]
        assigned_count = 0
        
        if idle_units and self.available_tasks:
            tasks_to_assign = list(self.available_tasks)
            
            for task in tasks_to_assign:
                if not idle_units:
                    break  # No more idle units

                # Assign the task to the next available idle unit
                unit_name = idle_units.pop(0)
                
                self.in_progress_tasks[id(task)] = task
                self.available_tasks.remove(task)

                unit_status = self.transport_units_status[unit_name]
                unit_status["current_task"] = task
                unit_status["status"] = "loading"
                unit_status["progress"] = 0
                unit_status["current_load_carried_by_unit"] = {task.material: task.lots_required}
                
                assigned_count += 1
                self._log(f"Unit {unit_name} assigned to task for {task.material}. Starts loading at {task.origin}.")

        if assigned_count > 0:
            print(f"Logistics: Assigned {assigned_count} transport units to tasks this step")
            self._log(f"Assigned {assigned_count} transport units to tasks this step")

        # Update performance metrics per step
        concurrent_units = len([u for u in self.transport_units_status.values() if u["status"] not in ["idle", "off_shift"]])
        self.performance_metrics["peak_concurrent_units"] = max(self.performance_metrics["peak_concurrent_units"], concurrent_units)

        # Calculate step processing time
        step_time = time.time() - step_start
        self.performance_metrics["step_processing_times"].append(step_time)
        if len(self.performance_metrics["step_processing_times"]) > 100:  # Keep last 100
            self.performance_metrics["step_processing_times"].pop(0)
        self.performance_metrics["average_processing_time"] = sum(self.performance_metrics["step_processing_times"]) / len(self.performance_metrics["step_processing_times"])

        # Unit state progression logic
        for unit_name, unit_status in self.transport_units_status.items():
            if unit_status["status"] in ["idle", "off_shift", "event", "abnormal"]:
                continue

            task = unit_status.get("current_task")
            if not task:
                unit_status["status"] = "idle"
                continue

            unit_status["progress"] += 1
            
            try:
                if unit_status["status"] == "loading" and unit_status["progress"] >= task.loading_time:
                    unit_status["status"] = "traveling"
                    unit_status["progress"] = 0
                    self._log(f"Unit {unit_name} traveling to {task.destination} with {task.material}.")
                
                elif unit_status["status"] == "traveling" and unit_status["progress"] >= task.travel_time:
                    unit_status["status"] = "unloading"
                    unit_status["current_location"] = task.destination
                    unit_status["progress"] = 0
                    self._log(f"Unit {unit_name} arrived at {task.destination}.")

                elif unit_status["status"] == "unloading" and unit_status["progress"] >= task.unloading_time:
                    # *** KEY INTEGRATION POINT: Add stock to the production process ***
                    if self.production_engine:
                        for material, qty in unit_status["current_load_carried_by_unit"].items():
                            master_location_name = task.destination
                            target_process = task.target_process
                            final_destination = None

                            if master_location_name in self.location_to_lines_map and target_process:
                                lines_at_location = self.location_to_lines_map[master_location_name]
                                for line_name in lines_at_location:
                                    if self.production_engine.has_process(line_name, target_process):
                                        final_destination = f"{line_name}:{target_process}"
                                        break

                            if final_destination:
                                self.production_engine.add_stock(destination=final_destination, material=material, quantity=qty)
                                self._log(f"Delivered {qty} of {material} to destination {final_destination}.")
                            else:
                                # Fallback to old behavior if no suitable line/process is found
                                self.production_engine.add_stock(destination=task.destination, material=material, quantity=qty)
                                self._log(f"Warning: Could not find a matching line and process for destination {master_location_name} and process {target_process}. Delivering to {task.destination}.")
                    
                    unit_status["current_load_carried_by_unit"] = {}
                    unit_status["status"] = "returning"
                    unit_status["progress"] = 0
                    self._log(f"Unit {unit_name} returning to {task.origin}.")

                elif unit_status["status"] == "returning" and unit_status["progress"] >= task.return_time:
                    unit_status["status"] = "idle"
                    unit_status["current_task"] = None
                    unit_status["current_location"] = task.origin
                    self.completed_tasks_per_unit[unit_name] += 1
                    self.completed_tasks.append(task)
                    self.completed_tasks_count += 1
                    del self.in_progress_tasks[id(task)]
                    self._log(f"Unit {unit_name} is now idle.")
            except Exception as e:
                self._log(f"Error processing unit {unit_name} task progression: {e}")
                    
    def get_status(self):
        location_statuses = [{ "name": loc.name, "stock": dict(loc.stock) } for loc in self.locations.values()]
        
        # Enhanced transport unit status with movement details
        enhanced_transport_units = []
        for unit_name, unit_status in self.transport_units_status.items():
            enhanced_status = unit_status.copy()
            if unit_status.get("current_task"):
                task = unit_status["current_task"]
                enhanced_status["current_task"] = {
                    "material": task.material,
                    "origin": task.origin,
                    "destination": task.destination,
                    "parent_part": task.parent_part,
                    "lots_required": task.lots_required,
                    "progress_percentage": self._calculate_task_progress(unit_status)
                }
            enhanced_transport_units.append(enhanced_status)
        
        return {
            "status": self.status,
            "current_time": self.current_time,
            "is_paused": self.is_paused,
            "simulation_speed": self.simulation_speed,
            "workday_start_time": self.setup.workday_start_time,
            "workday_end_time": self.setup.workday_end_time,
            "transport_units": enhanced_transport_units,
            "locations": location_statuses,
            "completed_tasks_count": self.completed_tasks_count,
            "remaining_tasks_count": len(self.available_tasks),
            "in_progress_tasks_count": len(self.in_progress_tasks),
            "completed_tasks_per_unit": self.completed_tasks_per_unit,
            "event_log": list(self.event_log),
            "material_requests_pending": len(self.material_request_queue),
            "mrp_data_loaded": len(self.mrp_data) > 0,
            "mrp_materials_count": len(self.mrp_data),
            "performance_metrics": self.performance_metrics
        }
    
    def _calculate_task_progress(self, unit_status):
        """Calculate the progress percentage of a transport unit's current task."""
        task = unit_status.get("current_task")
        if not task:
            return 0

        status = unit_status["status"]
        progress = unit_status["progress"]

        if status == "loading":
            return min(100, (progress / task.loading_time) * 100)
        elif status == "traveling":
            return min(100, (progress / task.travel_time) * 100)
        elif status == "unloading":
            return min(100, (progress / task.unloading_time) * 100)
        elif status == "returning":
            return min(100, (progress / task.return_time) * 100)
        else:
            return 0

    def pause_simulation(self):
        """Pause the simulation."""
        self.is_paused = True
        self._log("Simulation paused")

    def resume_simulation(self):
        """Resume the simulation."""
        self.is_paused = False
        self._log("Simulation resumed")

    def set_speed(self, speed: float):
        """Set simulation speed."""
        self.simulation_speed = max(0.1, min(10.0, speed))  # Clamp between 0.1 and 10.0
        self._log(f"Simulation speed set to {self.simulation_speed}")

    def _calculate_final_metrics(self):
        """Calculate final performance metrics when simulation ends."""
        total_time = self.current_time - self.setup.workday_start_time
        if total_time > 0:
            self.performance_metrics["efficiency_score"] = (
                self.performance_metrics["total_tasks_completed"] / total_time
            ) * 100
            self.performance_metrics["throughput"] = (
                self.performance_metrics["total_tasks_completed"] / total_time
            )
        if self.performance_metrics["total_requests_processed"] > 0:
            self.performance_metrics["average_queue_time"] = (
                total_time / self.performance_metrics["total_requests_processed"]
            )
        self._log(f"Final performance metrics: {self.performance_metrics}")
