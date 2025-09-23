import random
import math
from collections import deque, defaultdict
from datetime import datetime
from models import SimulationSetup, ProcessConfig
from data_loader import load_schedule, load_bom
import pandas as pd

class ProductionEngineV2:
    def __init__(self, setup: SimulationSetup, schedule_file: str, bom_file: str, material_request_queue: deque):
        self.setup = setup
        self.time = 0
        self.completed_units = 0
        self.scrapped_units = 0
        self.status = "initializing"
        self.material_request_queue = material_request_queue

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
        now = datetime.now()
        first_shift_start_hour = self.shift_manager['shifts'][0]['start_hour']
        self.simulation_start_time = now.replace(hour=first_shift_start_hour, minute=0, second=0, microsecond=0)
        
        # Fast-forward time to current real time if it's past the start of the day
        seconds_since_start_of_day = (now - self.simulation_start_time).total_seconds()
        if seconds_since_start_of_day > 0:
            self.time = seconds_since_start_of_day
        else:
            self.time = 0 # It's before the first shift starts

        self.seconds_per_step = 1  # Each step is one second

        self.schedule_df = load_schedule(schedule_file)
        print(f"DEBUG: ProductionEngineV2 loading schedule from: {schedule_file}")
        self.schedule_df.columns = self.schedule_df.columns.map(str)

        self.bom_data = load_bom(bom_file)
        
        if self.schedule_df.empty or not self.bom_data:
            raise ValueError("Gagal memuat data jadwal atau BOM. Simulasi tidak dapat dimulai.")

        self.lines = defaultdict(lambda: {
            "production_orders": deque(),
            "processes": {},
            "status": "pending",
            "total_line_target": 0,
            "last_start_time": -999999
        })
        
        self._initialize_lines_and_orders()

        self.total_production_target = sum(line['total_line_target'] for line in self.lines.values())

        if self.total_production_target == 0:
            raise ValueError("Tidak ada order produksi yang valid ditemukan dalam jadwal.")

        self.status = "running"
        print(f"Production Engine V2 Initialized for lines: {list(self.lines.keys())}. Total Target: {self.total_production_target} units.")

    def _initialize_lines_and_orders(self):
        orders_by_line = self._create_production_orders_by_line()

        sanitized_line_processes = {k.strip(): v for k, v in self.setup.line_processes.items()}

        for line_name, orders in orders_by_line.items():
            line = self.lines[line_name]
            line["production_orders"] = orders
            line["total_line_target"] = len(orders)
            line["status"] = "running"

            stripped_line_name = line_name.strip()
            processes_for_line = sanitized_line_processes.get(stripped_line_name, [])

            if not processes_for_line:
                print(f"CRITICAL WARNING: No processes found for line '{stripped_line_name}' from the schedule. This line will not produce anything.")

            for process_config in processes_for_line:
                line["processes"][process_config.name] = {
                    "config": process_config,
                    "queue_in": defaultdict(deque),
                    "units_in_process": [],
                    "queue_out": deque(),
                    "stock": defaultdict(float),
                    "pending_requests": set(),
                    "is_waiting_for_material": False,
                    "materials_waiting_for": []
                }

    def _create_production_orders_by_line(self) -> defaultdict:
        orders_by_line = defaultdict(deque)
        
        schedule_order_col = 'NO. URUT SCHEDULE (REVISI 0)'
        if schedule_order_col not in self.schedule_df.columns:
            alt_col = next((col for col in self.schedule_df.columns if 'NO. URUT' in col), None)
            if alt_col:
                schedule_order_col = alt_col
            else:
                raise ValueError(f"Kolom urutan '{schedule_order_col}' tidak ditemukan di file schedule.")
        
        self.schedule_df[schedule_order_col] = pd.to_numeric(self.schedule_df[schedule_order_col], errors='coerce')
        self.schedule_df.dropna(subset=[schedule_order_col], inplace=True)
        self.schedule_df = self.schedule_df.sort_values(by=schedule_order_col).reset_index(drop=True)



        # --- CORRECTED LOGIC: Use day of week to find column ---
        day_of_week = datetime.now().strftime('%a') # e.g., 'Mon', 'Tue'
        today_column = f"SCH_{day_of_week}"
        
        if today_column not in self.schedule_df.columns:
            print(f"INFO: No schedule column found for today '{today_column}'. No production orders will be loaded.")
            return orders_by_line

        print(f"INFO: Loading production orders for today's schedule column: {today_column}")

        for _, row in self.schedule_df.iterrows():
            try:
                if pd.notna(row[today_column]) and row[today_column] > 0:
                    quantity = int(row[today_column])
                    line_name = row['LINE']
                    model = row['MODEL']
                    part_no = row['PART NO']
                    for _ in range(quantity):
                            orders_by_line[line_name].append({
                                'part_no': part_no,
                                'model': model,
                                'quantity': 1,
                                'st': row['ST'],
                                'takt_time': row['TAKT_TIME'],
                                'original_sequence_no': row[schedule_order_col],
                                'status': 'pending'
                            })
            except (ValueError, TypeError, KeyError):
                continue
                
        return orders_by_line

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
        if self.status != "running": return

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

        for line_name, line_data in self.lines.items():
            if line_data["status"] != "running": continue
            for process_name, process_data in line_data["processes"].items():
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
                    if not config.output_to:
                        if random.random() > config.ng_rate: self.completed_units += 1
                        else: self.scrapped_units += 1
                    else:
                        for next_process_name in config.output_to:
                            if next_process_name in line_data["processes"]:
                                line_data["processes"][next_process_name]["queue_in"][process_name].append(unit_info)
            for process_name in line_data["processes"]:
                self.start_new_units(line_name, process_name)

    def start_new_units(self, line_name: str, process_name: str):
        line_data = self.lines[line_name]
        process_data = line_data["processes"][process_name]
        config = process_data["config"]

        if process_data.get("is_waiting_for_material", False):
            return

        # Check for Takt Time if this is a starting process
        if not config.input_from and line_data["production_orders"]:
            order = line_data["production_orders"][0]
            takt_time = order.get('takt_time', 0)
            if self.time - line_data['last_start_time'] < takt_time:
                return

        while len(process_data["units_in_process"]) < config.num_operators:
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
            
            elif line_data["production_orders"]:
                order = line_data["production_orders"][0]
                part_no = order['part_no']
                bom_for_part = self.bom_data.get(part_no, [])
                print(f"DEBUG: Checking BOM for part {part_no}: {bom_for_part}")

                if not bom_for_part:
                    print(f"WARNING: No BOM found for part {part_no}. Production will proceed without material consumption.")

                if bom_for_part:
                    has_all_materials = True
                    materials_to_request = []
                    for item in bom_for_part:
                        component, required_qty = item['component'], item['quantity']
                        if process_data["stock"].get(component, 0) < required_qty:
                            has_all_materials = False
                            if component not in process_data["pending_requests"]:
                                needed_qty = required_qty - process_data["stock"].get(component, 0)
                                request_qty = min(needed_qty * 2, required_qty * 2)
                                request = {
                                    'material': component, 'quantity': request_qty,
                                    'destination': f"{line_name}:{process_name}", 'parent_part': part_no
                                }
                                materials_to_request.append(request)
                    
                    if not has_all_materials:
                        if materials_to_request:
                            self.material_request_queue.extend(materials_to_request)
                            for req in materials_to_request:
                                process_data["pending_requests"].add(req['material'])
                            process_data["is_waiting_for_material"] = True
                            process_data["materials_waiting_for"] = [{'material': r['material'], 'needed': r['quantity']} for r in materials_to_request]
                        break

                consumed_order = line_data["production_orders"].popleft()
                bom_for_part = self.bom_data.get(consumed_order['part_no'], [])
                for item in bom_for_part:
                    if item['component'] in process_data["stock"]:
                        process_data["stock"][item['component']] -= item['quantity']
                
                unit_to_process = {
                    'start_time': self.time, 'part_no': consumed_order['part_no'],
                    'model': consumed_order['model'], 'cycle_time': consumed_order['st']
                }
            else:
                break

            if unit_to_process:
                process_data["units_in_process"].append(unit_to_process)
                if not config.input_from:
                    line_data['last_start_time'] = self.time
            else:
                break

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
                    cycle_time = unit.get('st', config.cycle_time)
                    if not isinstance(cycle_time, (int, float)) or cycle_time <= 0:
                        cycle_time = 60
                    progress = min(100, int(((self.time - unit.get('start_time', self.time)) / cycle_time) * 100))
                    units_in_process_details.append({'progress': progress, 'part_no': unit.get('part_no', 'unknown'), 'model': unit.get('model', 'unknown')})
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
                    "materials_waiting_for": p_data.get("materials_waiting_for", [])
                }
            current_order_info = None
            if line_data["production_orders"]:
                current_order = line_data["production_orders"][0]
                current_order_info = {
                    "part_no": current_order.get("part_no"),
                    "model": current_order.get("model"),
                    "sequence_no": current_order.get("original_sequence_no"),
                    "st": current_order.get("st"),
                    "takt_time": current_order.get("takt_time"),
                    "total_line_target": line_data["total_line_target"]
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

            lines_status[line_name] = {
                "status": line_data["status"],
                "total_line_target": line_data["total_line_target"],
                "remaining_orders": len(line_data["production_orders"]),
                "current_order": current_order_info,
                "current_processing_products": current_processing_products,
                "processes": process_status
            }
        total_progress = 0
        if self.total_production_target > 0:
            total_progress = ((self.completed_units + self.scrapped_units) / self.total_production_target) * 100
        
        current_sim_datetime = self.simulation_start_time + pd.Timedelta(seconds=self.time)
        current_shift_name = self.shift_manager['shifts'][self.shift_manager['current_shift_index']]['name']

        final_status = {
            "status": self.status,
            "current_time": self.time,
            "simulation_timestamp": current_sim_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "current_day": (current_sim_datetime - self.simulation_start_time).days + 1,
            "current_shift_name": current_shift_name,
            "completed_units": self.completed_units,
            "scrapped_units": self.scrapped_units,
            "total_production_target": self.total_production_target,
            "production_progress": total_progress,
            "lines": lines_status,
        }
        return self._sanitize_for_json(final_status)