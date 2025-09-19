import random
import math
from collections import deque, defaultdict
from datetime import datetime
from models import SimulationSetup, ProcessConfig
from data_loader import load_schedule, load_bom
import pandas as pd

class SimulationEngine:
    def __init__(self, setup: SimulationSetup, schedule_file: str, bom_file: str, material_request_queue: deque):
        self.setup = setup
        self.time = 0
        self.completed_units = 0
        self.scrapped_units = 0
        self.status = "initializing"
        self.material_request_queue = material_request_queue

        self.schedule_df = load_schedule(schedule_file)
        self.bom_data = load_bom(bom_file)
        
        if self.schedule_df.empty or not self.bom_data:
            raise ValueError("Gagal memuat data jadwal atau BOM. Simulasi tidak dapat dimulai.")

        self.lines = defaultdict(lambda: {
            "production_orders": deque(),
            "processes": {},
            "status": "pending",
            "total_line_target": 0
        })
        
        self._initialize_lines_and_orders()

        self.total_production_target = sum(line['total_line_target'] for line in self.lines.values())

        if self.total_production_target == 0:
            raise ValueError("Tidak ada order produksi yang valid ditemukan dalam jadwal.")

        self.status = "running"
        print(f"Production Engine Initialized for lines: {list(self.lines.keys())}. Total Target: {self.total_production_target} units.")
        print("Material requests will be created dynamically as needed during production.")

    def _initialize_lines_and_orders(self):
        orders_by_line = self._create_production_orders_by_line()
        for line_name, orders in orders_by_line.items():
            line = self.lines[line_name]
            line["production_orders"] = orders
            line["total_line_target"] = len(orders)
            line["status"] = "running"
            # Get processes specific to this line, or an empty list if none defined
            for process_config in self.setup.line_processes.get(line_name, []):
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
        self.schedule_df['ST_numeric'] = pd.to_numeric(self.schedule_df['ST'], errors='coerce').fillna(60)

        # Determine current day of week (0=Monday, 6=Sunday)
        current_day = datetime.now().weekday()
        # Map weekday to schedule column (Monday=0 -> SCH_Mon, Sunday=6 -> SCH_Sun)
        day_column_map = {
            0: 'SCH_Mon',  # Monday
            1: 'SCH_Tue',  # Tuesday
            2: 'SCH_Wed',  # Wednesday
            3: 'SCH_Thu',  # Thursday
            4: 'SCH_Fri',  # Friday
            5: 'SCH_Sat',  # Saturday
            6: 'SCH_Sun'   # Sunday
        }

        # Get the schedule column for today
        today_column = day_column_map.get(current_day)
        if not today_column:
            print(f"Warning: Could not determine schedule column for weekday {current_day}")
            return orders_by_line

        print(f"Loading production schedule for today ({today_column})")

        # Only process today's schedule column
        if today_column in self.schedule_df.columns:
            self.schedule_df[today_column] = pd.to_numeric(self.schedule_df[today_column], errors='coerce').fillna(0)
            for _, row in self.schedule_df.iterrows():
                quantity = int(row[today_column])
                if quantity > 0:
                    line_name = row['LINE']
                    model = row['MODEL']
                    part_no = row['PART NO']
                    print(f"Adding {quantity} units of {part_no} (Model: {model}) to line {line_name}")
                    for _ in range(quantity):
                        orders_by_line[line_name].append({
                            'part_no': part_no,
                            'model': model,
                            'quantity': 1,
                            'st': row['ST_numeric'],
                            'status': 'pending'
                        })
        else:
            print(f"Warning: Schedule column {today_column} not found in schedule file")

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
            # Assume destination is process_name, add to the first line that has it
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
        self.time += 1
        for line_name, line_data in self.lines.items():
            if line_data["status"] != "running": continue
            for process_name, process_data in line_data["processes"].items():
                config = process_data["config"]
                finished_units, remaining_units = [], []
                for unit in process_data["units_in_process"]:
                    cycle_time = unit.get('cycle_time', 1)
                    if not isinstance(cycle_time, (int, float)) or cycle_time <= 0:
                        cycle_time = 1
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
        if self.total_production_target > 0 and (self.completed_units + self.scrapped_units) >= self.total_production_target:
            self.status = "finished"

    def start_new_units(self, line_name: str, process_name: str):
        line_data = self.lines[line_name]
        process_data = line_data["processes"][process_name]
        config = process_data["config"]

        if process_data.get("is_waiting_for_material", False):
            return

        while len(process_data["units_in_process"]) < config.num_operators:
            unit_to_process = None
            unit_from_upstream = None

            # First, prioritize pulling units from an upstream process if configured
            if config.input_from:
                for input_proc_name in config.input_from:
                    if process_data["queue_in"][input_proc_name]:
                        unit_from_upstream = process_data["queue_in"][input_proc_name].popleft()
                        break
            
            if unit_from_upstream:
                # If we got a unit from upstream, process it.
                unit_to_process = unit_from_upstream
                unit_to_process['start_time'] = self.time
                unit_to_process['cycle_time'] = config.cycle_time
            
            elif line_data["production_orders"]:
                # If there's no work from upstream, but there are production orders for the line,
                # this process can act as a starting point for a new order.
                # THEREFORE, WE MUST CHECK FOR MATERIALS.
                order = line_data["production_orders"][0]
                part_no = order['part_no']
                bom_for_part = self.bom_data.get(part_no, [])

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
                        break  # Must wait for materials, so stop trying to add units.

                # If we have all materials, consume the order and create the unit.
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
                # No work from upstream and no new orders for the line.
                break

            if unit_to_process:
                process_data["units_in_process"].append(unit_to_process)
            else:
                break

    def _sanitize_for_json(self, data):
        if isinstance(data, dict) or isinstance(data, defaultdict):
            return {str(key): self._sanitize_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_for_json(element) for element in data]
        elif isinstance(data, float):
            if not math.isfinite(data):
                return None  # Replace non-finite floats with null
        return data

    def get_status(self):
        lines_status = {}
        for line_name, line_data in self.lines.items():
            process_status = {}
            for p_name, p_data in line_data["processes"].items():
                config = p_data["config"]
                units_in_process_details = []
                for unit in p_data["units_in_process"]:
                    cycle_time = unit.get('cycle_time', 1)
                    if not isinstance(cycle_time, (int, float)) or cycle_time <= 0:
                        cycle_time = 1
                    progress = min(100, int(((self.time - unit.get('start_time', self.time)) / cycle_time) * 100))
                    units_in_process_details.append({'progress': progress, 'part_no': unit.get('part_no', 'unknown'), 'model': unit.get('model', 'unknown')})
                process_status[p_name] = {
                    "queue_in": sum(len(q) for q in p_data["queue_in"].values()),
                    "units_in_process": units_in_process_details,
                    "queue_out": len(p_data["queue_out"]),
                    "name": config.name,
                    "num_operators": config.num_operators,
                    "stock": dict(p_data["stock"]),
                    "is_waiting_for_material": p_data.get("is_waiting_for_material", False),
                    "materials_waiting_for": p_data.get("materials_waiting_for", [])
                }
            current_order_info = None
            if line_data["production_orders"]:
                current_order = line_data["production_orders"][0]
                current_order_info = {
                    "part_no": current_order.get("part_no"),
                    "model": current_order.get("model")
                }

            # Add currently processing product info per line
            current_processing_products = []
            for p_data in line_data["processes"].values():
                for unit in p_data["units_in_process"]:
                    current_processing_products.append({
                        "part_no": unit.get("part_no", "unknown"),
                        "model": unit.get("model", "unknown"),
                        "progress": min(100, int(((self.time - unit.get('start_time', self.time)) / unit.get('cycle_time', 1)) * 100))
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
        final_status = {
            "status": self.status,
            "current_time": self.time,
            "completed_units": self.completed_units,
            "scrapped_units": self.scrapped_units,
            "total_production_target": self.total_production_target,
            "production_progress": total_progress,
            "lines": lines_status,
        }
        return self._sanitize_for_json(final_status)
