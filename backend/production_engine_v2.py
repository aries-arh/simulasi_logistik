import random
import math
from collections import deque, defaultdict
from datetime import datetime
from models import SimulationSetup, ProcessConfig
from data_loader import load_schedule
from bom_service import BOMService
import pandas as pd
from typing import Optional

class ProductionEngineV2:
    def __init__(self, setup: SimulationSetup, schedule_file: str, bom_service: BOMService, material_request_queue: deque, target_date: Optional[str] = None):
        self.setup = setup
        self.target_date = target_date
        self.time = 0
        self.completed_units = 0
        self.scrapped_units = 0
        self.status = "initializing"
        self.material_request_queue = material_request_queue
        self.operator_groups = {}

        self.shift_manager = {
            'shifts': [
                {'name': 'Shift 1', 'start_hour': 7, 'end_hour': 15},
                {'name': 'Shift 2', 'start_hour': 15, 'end_hour': 23},
                {'name': 'Shift 3', 'start_hour': 23, 'end_hour': 7} # Wraps around midnight
            ],
            'current_day': 0,
            'current_shift_index': 0
        }

        # --- Time and Shift Management ---
        # For production simulation, always start from the beginning of the first shift
        # Don't fast-forward to current real time - let it run at normal speed
        now = datetime.now()
        first_shift_start_hour = self.shift_manager['shifts'][0]['start_hour']
        
        # Set simulation start time to target date at first shift start hour
        # If target_date is provided, use it; otherwise use today
        if target_date:
            try:
                # Parse target date format (e.g., "6-Oct" or "29-Sep")
                from dateutil import parser
                target_datetime = parser.parse(target_date, default=now)
                self.simulation_start_time = target_datetime.replace(hour=first_shift_start_hour, minute=0, second=0, microsecond=0)
            except:
                # Fallback to today if parsing fails
                self.simulation_start_time = now.replace(hour=first_shift_start_hour, minute=0, second=0, microsecond=0)
        else:
            self.simulation_start_time = now.replace(hour=first_shift_start_hour, minute=0, second=0, microsecond=0)
        
        # Always start simulation from the beginning (time = 0)
        self.time = 0

        self.seconds_per_step = 1  # Each step is one second
        self.simulation_speed = setup.simulation_speed if hasattr(setup, 'simulation_speed') else 1.0

        self.schedule_df = load_schedule(schedule_file)
        print(f"DEBUG: ProductionEngineV2 loading schedule from: {schedule_file}")
        self.schedule_df.columns = self.schedule_df.columns.map(str)

        self.bom_service = bom_service # Use the passed BOM service
        
        if self.schedule_df.empty:
            raise ValueError("Gagal memuat data jadwal. Simulasi tidak dapat dimulai.")

        self.lines = defaultdict(lambda: {
            "production_orders": deque(),
            "processes": {},
            "status": "pending",
            "total_line_target": 0,
            "last_start_time": -999999
        })
        
        self._initialize_operator_groups()
        self._initialize_lines_and_orders()
        
        # Calculate realistic progress based on current real time
        # If user starts simulation at 9 AM, units should show appropriate progress
        # self._calculate_realistic_progress()

        self.total_production_target = sum(line['total_line_target'] for line in self.lines.values())

        if self.total_production_target == 0:
            raise ValueError("Tidak ada order produksi yang valid ditemukan dalam jadwal.")

        self.status = "ready" # Initialize as ready, run_simulation will set to running
        print(f"Production Engine V2 Initialized for lines: {list(self.lines.keys())}. Total Target: {self.total_production_target} units.")

    def run_simulation(self):
        self.status = "running"
        print("INFO: Simulation started.")
        while self.status == "running" and self.completed_units + self.scrapped_units < self.total_production_target:
            self.run_step()
            # In a real async application, this would use asyncio.sleep.
            # For now, we assume run_step is fast or the simulation loop is controlled externally.
            
            # Check if simulation is finished
            if self.completed_units + self.scrapped_units >= self.total_production_target:
                self.status = "finished"
                print("INFO: Simulation finished.")
                break
            
            # Check for external stop signal (e.g., from stop_simulation method)
            if self.status == "stopped":
                print("INFO: Simulation stopped by external signal.")
                break

    def stop_simulation(self):
        self.status = "stopped"
        print("INFO: Simulation received stop signal.")

    def is_running(self):
        return self.status in ["running", "ready"]

    def _initialize_operator_groups(self):
        """
        Initializes operator groups from the schedule data.
        """
        if 'GROUP_KERJA' not in self.schedule_df.columns or 'JML_OPR_DIRECT' not in self.schedule_df.columns:
            print("WARNING: Operator group columns ('GROUP_KERJA', 'JML_OPR_DIRECT') not found. Operator constraints will not be simulated.")
            return

        # Group by line to get the meta data for each line, then group by work group
        line_meta = self.schedule_df.groupby('LINE').first().reset_index()

        for _, row in line_meta.iterrows():
            group_name = row.get('GROUP_KERJA')
            num_operators = row.get('JML_OPR_DIRECT', 0)
            
            if pd.isna(group_name) or not group_name:
                continue

            # Parse multiple groups separated by '+'
            if '+' in str(group_name):
                groups = [g.strip() for g in str(group_name).split('+') if g.strip()]
                operators_per_group = int(num_operators) // len(groups) if groups else int(num_operators)
                if operators_per_group == 0:
                    operators_per_group = 1
                
                for group in groups:
                    if group not in self.operator_groups:
                        self.operator_groups[group] = {'total': 0, 'available': 0}
                    self.operator_groups[group]['total'] += operators_per_group
                    self.operator_groups[group]['available'] += operators_per_group
            else:
                # Single group
                if group_name not in self.operator_groups:
                    self.operator_groups[group_name] = {'total': 0, 'available': 0}
                self.operator_groups[group_name]['total'] += int(num_operators)
                self.operator_groups[group_name]['available'] += int(num_operators)

        print(f"INFO: Initialized operator groups: {self.operator_groups}")

    def _initialize_lines_and_orders(self):
        orders_by_line = self._create_production_orders_by_line()

        sanitized_line_processes = {k.strip(): v for k, v in self.setup.line_processes.items()}

        for line_name, orders in orders_by_line.items():
            line = self.lines[line_name]
            line["production_orders"] = orders
            line["total_line_target"] = len(orders)
            # Always set status to running if there are orders, never idle
            line["status"] = "running" if len(orders) > 0 else "pending"
            print(f"DEBUG: {line_name} - Loaded {len(orders)} production orders, status: {line['status']}")

            # Get the group_kerja for this line
            line_info = self.schedule_df[self.schedule_df['LINE'] == line_name]
            if not line_info.empty:
                line['group_kerja'] = line_info.iloc[0].get('GROUP_KERJA')
            else:
                line['group_kerja'] = None

            # Create processes dynamically based on operator count
            line_info = self.schedule_df[self.schedule_df['LINE'] == line_name]
            if not line_info.empty:
                schedule_operators = line_info.iloc[0].get('JML_OPR_DIRECT', 0)
                group_kerja = line_info.iloc[0].get('GROUP_KERJA', '')
                
                print(f"DEBUG: {line_name} - JML_OPR_DIRECT: {schedule_operators}, GROUP_KERJA: '{group_kerja}'")
                
                if pd.notna(schedule_operators) and schedule_operators > 0:
                    # For production simulation, use total operators directly
                    # Don't divide by groups - each line should use all its operators
                    operators_per_group = int(schedule_operators)
                    
                    print(f"DEBUG: {line_name} - Using total operators: {operators_per_group}")
                    
                    # Create one process with all operators
                    process_name = "Assembly"
                    
                    # Get ST (Standard Time) from schedule for cycle time
                    st_raw = line_info.iloc[0].get('ST', 60)  # Default to 60 seconds if no ST
                    if not isinstance(st_raw, (int, float)) or st_raw <= 0:
                        st_time = 60  # Default to 60 seconds
                    else:
                        st_time = st_raw  # Already in seconds from data_loader.py
                    
                    # Create process config with ST as cycle time
                    process_config = ProcessConfig(
                        name=process_name,
                        cycle_time=st_time,  # Use ST as cycle time
                        num_operators=operators_per_group,  # Use total operators for this line
                        ng_rate=0.01,  # Default NG rate
                        input_from=[],  # Starting process
                        output_to=[]  # Final process
                    )
                    
                    line["processes"][process_name] = {
                        "config": process_config,
                        "queue_in": defaultdict(deque),
                        "units_in_process": [],
                        "queue_out": deque(),
                        "stock": defaultdict(float),
                        "pending_requests": set(),
                        "is_waiting_for_material": False,
                        "materials_waiting_for": []
                    }
                    print(f"DEBUG: {line_name} - Created process: {process_name} with {operators_per_group} operators")
                    
                    print(f"INFO: Created 1 process for {line_name} with {operators_per_group} operators (ST: {st_time}s)")
                else:
                    print(f"WARNING: No valid operator count found for line {line_name} - schedule_operators: {schedule_operators}")
                    # Fallback: create default process if no valid operator count
                    self._create_default_process_for_line(line_name, line)
            else:
                print(f"WARNING: No schedule data found for line {line_name}")
                # Fallback: create default process if no schedule data
                self._create_default_process_for_line(line_name, line)

        # Pre-populate stock for production simulation - always start with full stock
        for line_name, line_data in self.lines.items():
            if line_data["processes"]:
                # Find the first process (the one with no inputs from other processes)
                first_process_name = None
                for p_name, p_data in line_data["processes"].items():
                    if not p_data["config"].input_from:
                        first_process_name = p_name
                        break
                if not first_process_name:
                    first_process_name = next(iter(line_data["processes"]))

                process_data = line_data["processes"][first_process_name]
                
                # Calculate total components needed for all orders in this line
                total_components = defaultdict(int)
                orders = orders_by_line.get(line_name, deque())
                for order in orders:
                    part_no = order['part_no']
                    bom_for_part = self.bom_service.get_components(part_no)
                    for item in bom_for_part:
                        total_components[item['component']] += item['quantity']
                
                # If no orders found for this line, try to get BOM from schedule data
                if not total_components:
                    line_schedule = self.schedule_df[self.schedule_df['LINE'] == line_name]
                    if not line_schedule.empty:
                        # Get first part from schedule for this line
                        first_part = line_schedule.iloc[0]['PART NO']
                        bom_for_part = self.bom_service.get_components(first_part)
                        for item in bom_for_part:
                            total_components[item['component']] += item['quantity'] * 100  # Default quantity
                        print(f"DEBUG: {line_name} - No orders found, using schedule BOM for {first_part}")
                
                # Set stock to total needed + 50% buffer for production simulation
                for component, qty in total_components.items():
                    buffer_qty = int(qty * 1.5)  # 50% buffer
                    process_data["stock"][component] = max(process_data["stock"].get(component, 0), buffer_qty)
                    print(f"DEBUG: {line_name} - Set stock for {component}: {process_data['stock'][component]} (needed: {qty}, buffer: {buffer_qty})")

    def _create_default_process_for_line(self, line_name: str, line: dict):
        """
        Creates a default process for a line when no valid operator data is found.
        """
        print(f"INFO: Creating default process for {line_name}")
        
        # Check if there's a configuration in setup.line_processes
        sanitized_line_processes = {k.strip(): v for k, v in self.setup.line_processes.items()}
        
        if line_name in sanitized_line_processes:
            # Use configuration from setup
            processes_config = sanitized_line_processes[line_name]
            print(f"INFO: Using setup configuration for {line_name}: {len(processes_config)} processes")
            
            for process_config in processes_config:
                process_name = process_config.name
                
                line["processes"][process_name] = {
                    "config": process_config,
                    "queue_in": defaultdict(deque),
                    "units_in_process": [],
                    "queue_out": deque(),
                    "stock": defaultdict(float),
                    "pending_requests": set(),
                    "is_waiting_for_material": False,
                    "materials_waiting_for": []
                }
                print(f"DEBUG: {line_name} - Created process from setup: {process_name}")
        else:
            # Create a single default process
            process_name = "Assembly_1"
            process_config = ProcessConfig(
                name=process_name,
                cycle_time=60,  # Default 60 seconds
                num_operators=1,  # Default 1 operator
                ng_rate=0.01,  # Default NG rate
                input_from=[],  # Starting process
                output_to=[]  # Final process
            )
            
            line["processes"][process_name] = {
                "config": process_config,
                "queue_in": defaultdict(deque),
                "units_in_process": [],
                "queue_out": deque(),
                "stock": defaultdict(float),
                "pending_requests": set(),
                "is_waiting_for_material": False,
                "materials_waiting_for": []
            }
            print(f"DEBUG: {line_name} - Created default process: {process_name}")

    def _create_production_orders_by_line(self) -> defaultdict:
        orders_by_line = defaultdict(deque)
        
        schedule_order_col = 'NO. URUT'
        if schedule_order_col not in self.schedule_df.columns:
            alt_col = next((col for col in self.schedule_df.columns if 'NO. URUT' in col), None)
            if alt_col:
                schedule_order_col = alt_col
            else:
                raise ValueError(f"Kolom urutan '{schedule_order_col}' tidak ditemukan di file schedule.")
        
        self.schedule_df[schedule_order_col] = pd.to_numeric(self.schedule_df[schedule_order_col], errors='coerce')
        self.schedule_df.dropna(subset=[schedule_order_col, 'PART NO'], inplace=True)
        self.schedule_df = self.schedule_df[self.schedule_df['PART NO'].str.strip() != '']
        self.schedule_df = self.schedule_df.sort_values(by=schedule_order_col).reset_index(drop=True)

        if self.target_date:
            # Normalize date from frontend, e.g., '29-Sep'
            def normalize_date_token(token: str) -> str:
                token = (token or "").strip().replace(" ", "-")
                token = token.replace("Sept", "Sep")
                parts = token.split("-")
                if len(parts) == 2:
                    day, mon = parts
                    mon = mon[:1].upper() + mon[1:].lower()
                    token = f"{day}-{mon}"
                return token
            
            normalized_date = normalize_date_token(self.target_date)
            schedule_col_base = f"SCH_{normalized_date}"
            schedule_cols = [col for col in self.schedule_df.columns if col.startswith(schedule_col_base)]
            print(f"INFO: Running simulation for specific date: {self.target_date} -> columns {schedule_cols}")
        else:
            # Fallback to original behavior if no date is specified
            schedule_cols = [col for col in self.schedule_df.columns if col.startswith('SCH_')]
            print(f"INFO: No target date specified. Running for all schedule columns: {schedule_cols}")

        if not schedule_cols:
            print(f"INFO: No schedule columns found. No production orders will be loaded.")
            return orders_by_line

        print(f"INFO: Loading production orders from schedule columns: {schedule_cols}")

        for _, row in self.schedule_df.iterrows():
            try:
                total_quantity = 0
                for col in schedule_cols:
                    if pd.notna(row[col]) and row[col] > 0:
                        total_quantity += int(row[col])
                
                if total_quantity > 0:
                    line_name = row['LINE']
                    model = row['MODEL']
                    part_no = row['PART NO']
                    
                    takt_time = row.get('TAKT_TIME', 0)
                    if not isinstance(takt_time, (int, float)) or takt_time <= 0:
                        # Use ST as fallback for takt time if TAKT_TIME is 0 or invalid
                        st_fallback = row.get('ST', 60)  # Already in seconds
                        takt_time = max(st_fallback, 60)  # Minimum 60 seconds
                        print(f"WARNING: Invalid Takt Time ({takt_time}) for part {part_no}. Using ST as fallback: {takt_time}s")
                    else:
                        # TAKT_TIME is already in seconds from data_loader.py
                        takt_time = takt_time

                    # Get ST (already in seconds from data_loader.py)
                    st_raw = row['ST']
                    if not isinstance(st_raw, (int, float)) or st_raw <= 0:
                        st_seconds = 60  # Default to 60 seconds
                    else:
                        st_seconds = st_raw  # Already in seconds from data_loader.py
                    
                    for _ in range(total_quantity):
                        orders_by_line[line_name].append({
                            'part_no': part_no,
                            'model': model,
                            'quantity': 1,
                            'st': st_seconds,  # ST in seconds
                            'takt_time': takt_time,
                            'original_sequence_no': row[schedule_order_col],
                            'status': 'pending',
                            'is_started': False # Initialize is_started flag
                        })
            except (ValueError, TypeError, KeyError) as e:
                print(f"ERROR processing row: {row}, error: {e}")
                continue
                
        return orders_by_line

    # def _calculate_realistic_progress(self):
    #     """Calculate realistic progress based on current real time.
    #     If simulation starts at 9 AM, units should show appropriate progress."""
    #     now = datetime.now()
    #     
    #     # Calculate how much time has passed since simulation start time
    #     time_passed_since_start = (now - self.simulation_start_time).total_seconds()
    #     
    #     # Only calculate if we're past the simulation start time
    #     if time_passed_since_start > 0:
    #         print(f"DEBUG: Calculating realistic progress - {time_passed_since_start} seconds since simulation start")
    #         
    #         # Set simulation time to current real time
    #         self.time = time_passed_since_start
    #         
    #         # Process units that should be in progress based on real time
    #         for line_name, line_data in self.lines.items():
    #             if not line_data["production_orders"]:
    #                 continue
    #             
    #             # Calculate how many units should have been started/completed
    #             current_order = line_data["production_orders"][0]
    #             takt_time = current_order.get('takt_time', 60)
    #             cycle_time = current_order.get('st', 60)
    #             
    #             # Calculate units based on ST and Takt Time
    #             # Units completed = (time_passed - ST) / Takt_Time + 1
    #             # Units in progress = if (time_passed % Takt_Time) < ST
    #             
    #             units_completed = 0
    #             units_in_progress = 0
    #             
    #             if time_passed_since_start >= cycle_time and takt_time > 0:
    #                 # At least one unit can be completed
    #                 units_completed = int((time_passed_since_start - cycle_time) / takt_time) + 1
    #                 
    #                 # Check if there's a unit currently in progress
    #                 remaining_time_after_last_completion = time_passed_since_start - (units_completed - 1) * takt_time - cycle_time
    #                 if remaining_time_after_last_completion > 0 and remaining_time_after_last_completion < cycle_time:
    #                     units_in_progress = 1
    #             
    #             total_units_started = units_completed + units_in_progress
    #             
    #             print(f"DEBUG: {line_name} - Units completed: {units_completed}, in progress: {units_in_progress}, total started: {total_units_started}")
    #             
    #             # Start units that should be in progress
    #             for process_name, process_data in line_data["processes"].items():
    #                 config = process_data["config"]
    #                 
    #                 # Clear existing units and add realistic ones
    #                 process_data["units_in_process"] = []
    #                 
    #                 # Add units that should be in progress based on ST and Takt Time
    #                 for i in range(min(total_units_started, config.num_operators)):
    #                     if line_data["production_orders"]:
    #                         order = line_data["production_orders"][0]
    #                         
    #                         # Calculate realistic start time for this unit
    #                         unit_start_time = i * takt_time
    #                         
    #                         # Calculate progress based on elapsed time
    #                         elapsed_time = time_passed_since_start - unit_start_time
    #                         
    #                         if elapsed_time >= cycle_time:
    #                             # This unit should be completed
    #                             print(f"DEBUG: {line_name} unit {i} should be completed (elapsed: {elapsed_time}s >= cycle: {cycle_time}s)")
    #                             # Count as completed but don't remove from queue yet (let normal process handle it)
    #                             continue
    #                         elif elapsed_time > 0:
    #                             # This unit should be in progress
    #                             progress_percent = min(100, max(0, int((elapsed_time / cycle_time) * 100)))
    #                             remaining_time = max(0, cycle_time - elapsed_time)
    #                             
    #                             unit = {
    #                                 'start_time': unit_start_time,
    #                                 'part_no': order['part_no'],
    #                                 'model': order['model'],
    #                                 'st': order['st'],
    #                                 'cycle_time': cycle_time,
    #                                 'progress': progress_percent,
    #                                 'remaining_time': remaining_time,
    #                                 'elapsed_time': elapsed_time
    #                             }
    #                             process_data["units_in_process"].append(unit)
    #                             
    #                             print(f"DEBUG: {line_name} unit {i} in progress - elapsed: {elapsed_time}s, cycle: {cycle_time}s, progress: {progress_percent}%, remaining: {remaining_time}s")
    #                 
    #                 # Update last start time
    #                 if process_data["units_in_process"]:
    #                     line_data["last_start_time"] = (len(process_data["units_in_process"]) - 1) * takt_time

    def _fast_forward_to_current_time(self):
        """Fast-forward simulation to current real time, marking completed orders as done."""
        for line_name, line_data in self.lines.items():
            cumulative_time = 0
            orders_to_keep = deque()
            finished_count = 0
            
            for order in line_data["production_orders"]:
                takt_time = order.get('takt_time', 0)
                # Use ST (Standard Time) as cycle time if takt_time is not available
                if takt_time <= 0:
                    takt_time = order.get('st', 60)  # Default to 60 seconds if no ST
                
                if cumulative_time + takt_time < self.time:
                    cumulative_time += takt_time
                    self.completed_units += 1
                    finished_count += 1
                else:
                    orders_to_keep.append(order)
            
            line_data["production_orders"] = orders_to_keep
            print(f"INFO: Fast-forwarded line {line_name}. Marked {finished_count} orders as complete.")


    def has_process(self, line_name: str, process_name: str) -> bool:
        return line_name in self.lines and process_name in self.lines[line_name]["processes"]

    def add_stock(self, destination: str, material: str, quantity: int):
        print(f"Attempting to add stock: dest={destination}, mat={material}, qty={quantity}")
        if ':' in destination:
            line_name, process_name = destination.split(':', 1)
            if line_name in self.lines and process_name in self.lines[line_name]["processes"]:
                process_data = self.lines[line_name]["processes"][process_name]
                process_data["stock"][material] += quantity
                if material in process_data["pending_requests"]:
                    process_data["pending_requests"].remove(material)
                process_data["materials_waiting_for"] = [m for m in process_data["materials_waiting_for"] if m['material'] != material]
                if not process_data["pending_requests"]:
                     process_data["is_waiting_for_material"] = False
            else:
                print(f"Warning: Tried to add stock to a non-existent line/process: {destination}")
        else:
            process_name = destination
            for line_name in self.lines:
                if process_name in self.lines[line_name]["processes"]:
                    process_data = self.lines[line_name]["processes"][process_name]
                    process_data["stock"][material] += quantity
                    if material in process_data["pending_requests"]:
                        process_data["pending_requests"].remove(material)
                    process_data["materials_waiting_for"] = [m for m in process_data["materials_waiting_for"] if m['material'] != material]
                    if not process_data["pending_requests"]:
                         process_data["is_waiting_for_material"] = False
                    return
            print(f"Warning: Process '{process_name}' not found in any line.")

    def run_step(self):
        if self.status != "running": 
            return

        try:
            current_sim_datetime = self.simulation_start_time + pd.Timedelta(seconds=self.time)
            current_shift = self.shift_manager['shifts'][self.shift_manager['current_shift_index']]

            is_working_hour = False
            start_hour = current_shift['start_hour']
            end_hour = current_shift['end_hour']

            if start_hour < end_hour: # Shift is on the same day
                if start_hour <= current_sim_datetime.hour < end_hour:
                    is_working_hour = True
            else: # Shift wraps around midnight
                if current_sim_datetime.hour >= start_hour or current_sim_datetime.hour < end_hour:
                    is_working_hour = True
        except Exception as e:
            print(f"ERROR in shift management: {e}")
            # Continue with simulation even if shift management fails
            is_working_hour = True

        if not is_working_hour:
            # Advance time to the next shift
            self.shift_manager['current_shift_index'] = (self.shift_manager['current_shift_index'] + 1) % len(self.shift_manager['shifts'])
            next_shift = self.shift_manager['shifts'][self.shift_manager['current_shift_index']]
            
            # If we moved to the first shift, it's a new day
            if self.shift_manager['current_shift_index'] == 0:
                current_sim_datetime += pd.Timedelta(days=1)

            # Set time to the start of the next shift
            next_shift_start_time = current_sim_datetime.replace(hour=next_shift['start_hour'], minute=0, second=0, microsecond=0)
            
            # If the calculated start time is in the past, add a day (for midnight wrap)
            if next_shift_start_time < current_sim_datetime:
                next_shift_start_time += pd.Timedelta(days=1)

            self.time = (next_shift_start_time - self.simulation_start_time).total_seconds()
            return # Skip the rest of the step

        self.time += self.seconds_per_step

        try:
            for line_name, line_data in self.lines.items():
                # Keep line running if there are still orders to process
                if len(line_data["production_orders"]) > 0:
                    line_data["status"] = "running"
                
                if line_data["status"] != "running": 
                    continue
                    
                for process_name, process_data in line_data["processes"].items():
                    try:
                        config = process_data["config"]
                        finished_units, remaining_units = [], []
                        
                        for unit in process_data["units_in_process"]:
                            # Use the ST from the order as the cycle time
                            cycle_time = unit.get('st', config.cycle_time) 
                            if not isinstance(cycle_time, (int, float)) or cycle_time <= 0:
                                cycle_time = 60 # Default fallback

                            if self.time - unit['start_time'] >= cycle_time:
                                finished_units.append(unit)
                            else:
                                remaining_units.append(unit)
                                
                        process_data["units_in_process"] = remaining_units
                        
                        for unit_info in finished_units:
                            # In production simulation mode, no need to manage operator availability

                            if not config.output_to:
                                if random.random() > config.ng_rate: 
                                    self.completed_units += 1
                                else: 
                                    self.scrapped_units += 1

                                # Find the original order and decrement its quantity
                                for i, order in enumerate(line_data["production_orders"]):
                                    if order.get('original_sequence_no') == unit_info.get('original_sequence_no'):
                                        order['quantity'] -= 1
                                        if order['quantity'] <= 0:
                                            # Remove the order and reset its is_started flag
                                            line_data["production_orders"].pop(i)
                                            # Ensure the last_start_time is reset or handled for the next order
                                            line_data['last_start_time'] = -999999 # Reset to allow next unit to start
                                            print(f"DEBUG: Completed order {order.get('part_no')} - reset last_start_time")
                                        break

                            else:
                                for next_process_name in config.output_to:
                                    if next_process_name in line_data["processes"]:
                                        line_data["processes"][next_process_name]["queue_in"][process_name].append(unit_info)
                    except Exception as e:
                        print(f"ERROR in process {process_name} on line {line_name}: {e}")
                        continue
                        
                for process_name in line_data["processes"]:
                    try:
                        self.start_new_units(line_name, process_name)
                    except Exception as e:
                        print(f"ERROR starting new units for process {process_name} on line {line_name}: {e}")
                        continue
                        
        except Exception as e:
            print(f"ERROR in production step: {e}")
            # Continue simulation even if there's an error

    def start_new_units(self, line_name: str, process_name: str):
        line_data = self.lines[line_name]
        process_data = line_data["processes"][process_name]
        config = process_data["config"]

        # In production simulation mode, operators are always available
        # Skip operator availability check for production-only simulation
        process_data['is_waiting_for_operator'] = False

        if process_data.get("is_waiting_for_material", False):
            print(f"DEBUG: {line_name}:{process_name} waiting for materials")
            return

        # Takt time check will be handled in the unit processing loop below

        print(f"DEBUG: {line_name}:{process_name} - Starting unit processing loop. Current units: {len(process_data['units_in_process'])}/{config.num_operators}")
        
        # Check if enough time has passed since last unit start (takt time logic)
        can_start_unit = True
        if line_data["production_orders"]:
            order = line_data["production_orders"][0]
            takt_time = order.get('takt_time', 0)
            # Use ST (Standard Time) as takt time if takt_time is not available or too small
            if takt_time <= 0:
                takt_time = min(order.get('st', 3600), 3600)  # Use ST but cap at 3600 seconds (1 hour) for production simulation
            
            time_since_last_start = self.time - line_data['last_start_time']
            can_start_unit = time_since_last_start >= takt_time
            
            print(f"DEBUG: {line_name}:{process_name} takt check - self.time: {self.time}, last_start_time: {line_data['last_start_time']}, takt_time: {takt_time}, time_diff: {time_since_last_start}, can_start_unit: {can_start_unit}")
        
        # Only start one unit if takt time allows and operator is available
        # In production simulation mode, always try to start units if we have orders
        if can_start_unit and len(process_data["units_in_process"]) < 1:
            unit_to_process = None
            unit_from_upstream = None

            if config.input_from:
                for input_proc_name in config.input_from:
                    if process_data["queue_in"][input_proc_name]:
                        unit_from_upstream = process_data["queue_in"][input_proc_name].popleft()
                        break
            
            if unit_from_upstream:
                unit_to_process = unit_from_upstream
                unit_to_process['start_time'] = self.time
                unit_to_process['cycle_time'] = config.cycle_time
                process_data["units_in_process"].append(unit_to_process)
                line_data['last_start_time'] = self.time # Update last_start_time for the line
                print(f"DEBUG: {line_name}:{process_name} - Started unit from upstream. Unit start_time: {unit_to_process['start_time']}, cycle_time: {unit_to_process['cycle_time']}")
            
            elif line_data["production_orders"] and not line_data["production_orders"][0].get('is_started', False):
                order = line_data["production_orders"][0]
                part_no = order['part_no']
                bom_for_part = self.bom_service.get_components(part_no)
                print(f"DEBUG: Checking BOM for part {part_no}: {bom_for_part}")

                # Initialize has_all_materials
                has_all_materials = True

                if not bom_for_part:
                    print(f"WARNING: No BOM found for part {part_no}. Production will proceed without material consumption.")
                    has_all_materials = True
                else:
                    # Unified material check logic
                    has_all_materials = True
                    for item in bom_for_part:
                        if process_data["stock"].get(item['component'], 0) < item['quantity']:
                            has_all_materials = False
                            break
                    
                    if not has_all_materials:
                        # In production simulation mode, skip to next model if stock is insufficient
                        if self.setup.ignore_material_availability:
                            print(f"DEBUG: {line_name}:{process_name} - Insufficient stock for {part_no}, skipping to next order")
                            # Remove current order and try next one
                            if line_data["production_orders"]:
                                skipped_order = line_data["production_orders"].popleft()
                                print(f"DEBUG: Skipped order: {skipped_order['part_no']} ({skipped_order['model']})")
                            # Set unit_to_process to None to prevent processing this order
                            unit_to_process = None
                        else:
                            process_data["is_waiting_for_material"] = True
                            
                            # If in integrated mode, request materials
                            materials_to_request = []
                            for item in bom_for_part:
                                component, required_qty = item['component'], item['quantity']
                                if process_data["stock"].get(component, 0) < required_qty:
                                    if component not in process_data["pending_requests"]:
                                        needed_qty = required_qty - process_data["stock"].get(component, 0)
                                        request_qty = max(needed_qty, int(needed_qty * 1.5))
                                        materials_to_request.append({
                                            'material': component, 
                                            'quantity': request_qty,
                                            'destination': f"{line_name}:{process_name}", 
                                            'parent_part': part_no,
                                            'priority': 'high'
                                        })
                            
                            if materials_to_request:
                                for req in materials_to_request:
                                    self.material_request_queue.appendleft(req)
                                    process_data["pending_requests"].add(req['material'])
                                process_data["materials_waiting_for"] = [{'material': r['material'], 'needed': r['quantity']} for r in materials_to_request]
                            # Set unit_to_process to None to prevent processing this order
                            unit_to_process = None
                    else:
                        # We have all materials, proceed with production
                        # Consume materials
                        for item in bom_for_part:
                            process_data["stock"][item['component']] -= item['quantity']
                        
                        # Create a new unit and add it to units_in_process
                        unit_to_process = {
                            "part_no": part_no,
                            "model": order['model'],
                            "start_time": self.time, # Assign the current simulation time as start time
                            "st": order.get('st', config.cycle_time), # Use ST from order, fallback to process cycle time
                            "original_sequence_no": order.get('original_sequence_no') # Add original_sequence_no
                        }
                        process_data["units_in_process"].append(unit_to_process)
                        line_data['last_start_time'] = self.time # Update last_start_time for the line
                        order['is_started'] = True # Mark order as started
                        print(f"DEBUG: {line_name}:{process_name} - Started unit from order. Unit start_time: {unit_to_process['start_time']}, cycle_time: {unit_to_process['st']}")

                        # Decrement the quantity in the current production order.
                        # This quantity is for total orders to be made. Individual units are tracked in units_in_process.
                        # The order is only fully consumed when all its units are completed.
                        # For sequential processing, we only start one unit at a time from an order.
                        # So, we don't decrement quantity here immediately.
                        # The order should be popleft only when it's fully completed (all units produced).
                        # Let's add a mechanism to track units from an order.
                        
                        # No, the quantity is for total orders to be made.
                        # When a unit is started, we mark the order as 'is_started'.
                        # When a unit is finished, if it's the last unit for that order, then we remove the order.

            if unit_to_process:
                # Remove the block that appends unit_to_process again and updates last_start_time again
                # It's already handled in the if/elif blocks above
                
                # We need to ensure that the order's quantity is decremented ONLY when a unit is completed and removed.
                # For now, the 'is_started' flag helps to prevent starting multiple units from the same order if we are
                # only processing one unit at a time.
                print(f"DEBUG: Started unit {unit_to_process.get('part_no', 'unknown')} ({unit_to_process.get('model', 'unknown')}) in {line_name}:{process_name}")
            else:
                if not can_start_unit:
                    print(f"DEBUG: {line_name}:{process_name} - Cannot start unit due to takt time constraint")
                elif len(process_data["units_in_process"]) >= 1: # Changed from config.num_operators
                    print(f"DEBUG: {line_name}:{process_name} - Cannot start unit, one unit is already in process ({len(process_data['units_in_process'])}/1)")
                elif not line_data["production_orders"]:
                    print(f"DEBUG: {line_name}:{process_name} - No production orders available")
                else:
                    print(f"DEBUG: {line_name}:{process_name} - No unit to process (orders: {len(line_data['production_orders'])}, upstream: {unit_from_upstream is not None})")

    def _sanitize_for_json(self, data):
        if isinstance(data, dict) or isinstance(data, defaultdict):
            return {str(key): self._sanitize_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_for_json(element) for element in data]
        elif isinstance(data, float):
            if not math.isfinite(data):
                return None
        return data

    def get_status(self):
        lines_status = {}
        for line_name, line_data in self.lines.items():
            process_status = {}
            for p_name, p_data in line_data["processes"].items():
                config = p_data["config"]
                units_in_process_details = []
                for unit in p_data["units_in_process"]:
                    cycle_time = unit.get('cycle_time', config.cycle_time)
                    if not isinstance(cycle_time, (int, float)) or cycle_time <= 0:
                        cycle_time = 60
                    
                    # Calculate progress based on cycle time
                    elapsed_time = self.time - unit.get('start_time', self.time)
                    progress = min(100, max(0, int((elapsed_time / cycle_time) * 100)))
                    
                    # Calculate remaining time
                    remaining_time = max(0, cycle_time - elapsed_time)
                    
                    part_no = unit.get('part_no', 'unknown')
                    model = unit.get('model', 'unknown')
                    child_parts = self.bom_service.get_components(part_no)
                    
                    units_in_process_details.append({
                        'progress': progress, 
                        'part_no': part_no, 
                        'model': model, 
                        'cycle_time': cycle_time,
                        'remaining_time': remaining_time,
                        'elapsed_time': elapsed_time,
                        'child_parts': child_parts
                    })
                process_status[p_name] = {
                    "queue_in": sum(len(q) for q in p_data["queue_in"].values()),
                    "units_in_process": units_in_process_details,
                    "queue_out": len(p_data["queue_out"]),
                    "name": config.name,
                    "num_operators": config.num_operators,
                    "input_from": config.input_from,
                    "output_to": config.output_to,
                    "stock": dict(p_data["stock"]),
                    "is_waiting_for_material": p_data.get("is_waiting_for_material", False),
                    "materials_waiting_for": p_data.get("materials_waiting_for", []),
                    "is_waiting_for_operator": p_data.get("is_waiting_for_operator", False)
                }
            current_order_info = None
            if line_data["production_orders"]:
                current_order = line_data["production_orders"][0]
                child_parts = self.bom_service.get_components(current_order.get("part_no"))
                # Get takt time and convert from minutes to seconds if needed
                takt_time_raw = current_order.get("takt_time", 0)
                if takt_time_raw > 0 and takt_time_raw < 3600:  # If it looks like minutes (less than 1 hour in seconds)
                    takt_time_display = takt_time_raw * 60  # Convert minutes to seconds
                else:
                    takt_time_display = takt_time_raw  # Already in seconds
                
                # Get ST (already in seconds from data_loader.py)
                st_raw = current_order.get("st", 0)
                st_display = st_raw  # Already in seconds from data_loader.py
                
                current_order_info = {
                    "part_no": current_order.get("part_no"),
                    "model": current_order.get("model"),
                    "sequence_no": current_order.get("original_sequence_no"),
                    "st": st_display,
                    "takt_time": takt_time_display,
                    "total_line_target": line_data["total_line_target"],
                    "child_parts": child_parts
                }
            else:
                # If no active orders, try to get info from the original schedule
                line_schedule = self.schedule_df[self.schedule_df['LINE'] == line_name]
                if not line_schedule.empty:
                    # Get the first part in the schedule for that line
                    first_part_in_schedule = line_schedule.iloc[0]
                    part_no = first_part_in_schedule.get("PART NO")
                    if part_no:
                        child_parts = self.bom_service.get_components(part_no)
                        # Get takt time and convert from minutes to seconds if needed
                        takt_time_raw = first_part_in_schedule.get("TAKT_TIME", 0)
                        if takt_time_raw > 0 and takt_time_raw < 3600:  # If it looks like minutes (less than 1 hour in seconds)
                            takt_time_display = takt_time_raw * 60  # Convert minutes to seconds
                        else:
                            takt_time_display = takt_time_raw  # Already in seconds
                        
                        # Get ST (already in seconds from data_loader.py)
                        st_raw = first_part_in_schedule.get("ST", 0)
                        st_display = st_raw  # Already in seconds from data_loader.py
                        
                        current_order_info = {
                            "part_no": part_no,
                            "model": first_part_in_schedule.get("MODEL"),
                            "sequence_no": first_part_in_schedule.get("NO. URUT"),
                            "st": st_display,
                            "takt_time": takt_time_display,
                            "total_line_target": line_data["total_line_target"],
                            "child_parts": child_parts
                        }

            current_processing_products = []
            for p_data in line_data["processes"].values():
                for unit in p_data["units_in_process"]:
                    cycle_time = unit.get('st', config.cycle_time)
                    if not isinstance(cycle_time, (int, float)) or cycle_time <= 0:
                        cycle_time = 60
                    current_processing_products.append({
                        "part_no": unit.get("part_no", "unknown"),
                        "model": unit.get("model", "unknown"),
                        "progress": min(100, int(((self.time - unit.get('start_time', self.time)) / cycle_time) * 100))
                    })
            print(f"DEBUG: {line_name} - Current processing products: {current_processing_products}")

            # Calculate takt time countdown for next unit
            takt_countdown = 0
            if line_data["production_orders"]:
                current_order = line_data["production_orders"][0]
                takt_time = current_order.get('takt_time', 0)
                print(f"DEBUG: get_status - Line: {line_name}, Part No: {current_order.get('part_no')}, Takt Time used for countdown: {takt_time}")
                # Ensure takt_time is valid, fallback to 60 seconds if not
                if not isinstance(takt_time, (int, float)) or takt_time <= 0:
                    takt_time = 60 # Fallback to 60 seconds if invalid

                # Use simulation time for countdown calculation
                time_since_last_start = self.time - line_data.get('last_start_time', 0)
                takt_countdown = max(0, takt_time - time_since_last_start)

            lines_status[line_name] = {
                "status": line_data["status"],
                "total_line_target": line_data["total_line_target"],
                "remaining_orders": len(line_data["production_orders"]),
                "current_order": current_order_info,
                "current_processing_products": current_processing_products,
                "processes": process_status,
                "takt_countdown": takt_countdown,
                "last_start_time": line_data.get('last_start_time', 0)
            }
        total_progress = 0
        if self.total_production_target > 0:
            total_progress = ((self.completed_units + self.scrapped_units) / self.total_production_target) * 100
        
        current_sim_datetime = self.simulation_start_time + pd.Timedelta(seconds=self.time)
        current_shift_name = self.shift_manager['shifts'][self.shift_manager['current_shift_index']]['name']
        
        # Calculate simulation speed based on configured speed, not real time ratio
        real_time_elapsed = (datetime.now() - self.simulation_start_time).total_seconds()
        simulation_time_elapsed = self.time
        # Use configured simulation speed instead of calculating from real time
        speed_ratio = self.simulation_speed

        final_status = {
            "status": self.status,
            "target_date": self.target_date, # Add the target date here
            "current_time": self.time,
            "simulation_timestamp": current_sim_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "real_time_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "simulation_speed": self.simulation_speed,
            "actual_speed_ratio": round(speed_ratio, 2),
            "current_day": 1,  # Always start from day 1 for production simulation
            "current_shift_name": current_shift_name,
            "completed_units": self.completed_units,
            "scrapped_units": self.scrapped_units,
            "total_production_target": self.total_production_target,
            "production_progress": total_progress,
            "lines": lines_status,
        }
        return self._sanitize_for_json(final_status)