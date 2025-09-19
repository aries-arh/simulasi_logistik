import os
import pandas as pd
from collections import defaultdict
from backend.data_loader import load_schedule, load_bom, load_mrp_data

# Define file paths (adjust if necessary)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_FILE = os.path.join(PROJECT_ROOT, "20250915-Schedule FA1.csv")
BOM_FILE = os.path.join(PROJECT_ROOT, "YMATP0200B_BOM_20250915_230046.txt")
MRP_FILE = os.path.join(PROJECT_ROOT, "MRP_20250915.txt")

def analyze_data_connections():
    print("=== Data Connection Analysis for Integrated Simulation ===\n")

    # Load data
    print("Loading Schedule data...")
    schedule_df = load_schedule(SCHEDULE_FILE)
    if schedule_df.empty:
        print("ERROR: Failed to load schedule data.")
        return

    print("Loading BOM data...")
    bom_data = load_bom(BOM_FILE)
    if not bom_data:
        print("ERROR: Failed to load BOM data.")
        return

    print("Loading MRP data...")
    mrp_data = load_mrp_data(MRP_FILE)
    if not mrp_data:
        print("ERROR: Failed to load MRP data.")
        return

    print("All data loaded successfully.\n")

    # Extract unique parts from schedule
    schedule_parts = set(schedule_df['PART NO'].dropna().unique())
    print(f"Schedule: {len(schedule_parts)} unique parts found.")

    # Extract parent parts from BOM
    bom_parents = set(bom_data.keys())
    print(f"BOM: {len(bom_parents)} parent parts found.")

    # Extract components from BOM
    bom_components = set()
    for components in bom_data.values():
        for comp in components:
            bom_components.add(comp['component'])
    print(f"BOM: {len(bom_components)} unique components found.")

    # Extract materials from MRP
    mrp_materials = set(mrp_data.keys())
    print(f"MRP: {len(mrp_materials)} materials found.")

    # Extract issue locations from MRP
    mrp_locations = set()
    for data in mrp_data.values():
        if 'issue_location' in data:
            mrp_locations.add(data['issue_location'])
    print(f"MRP: {len(mrp_locations)} unique issue locations found: {sorted(mrp_locations)}\n")

    # Analysis 1: Schedule parts in BOM
    parts_in_schedule_not_in_bom = schedule_parts - bom_parents
    parts_in_bom_not_in_schedule = bom_parents - schedule_parts
    common_parts = schedule_parts & bom_parents

    print("=== Connection Analysis: Schedule ↔ BOM ===")
    print(f"Parts in Schedule but not in BOM: {len(parts_in_schedule_not_in_bom)}")
    if parts_in_schedule_not_in_bom:
        print(f"  Examples: {list(parts_in_schedule_not_in_bom)[:5]}")
    print(f"Parts in BOM but not in Schedule: {len(parts_in_bom_not_in_schedule)}")
    if parts_in_bom_not_in_schedule:
        print(f"  Examples: {list(parts_in_bom_not_in_schedule)[:5]}")
    print(f"Common parts: {len(common_parts)} ({len(common_parts)/len(schedule_parts)*100:.1f}% of schedule parts)\n")

    # Analysis 2: BOM components in MRP
    components_in_bom_not_in_mrp = bom_components - mrp_materials
    materials_in_mrp_not_in_bom = mrp_materials - bom_components
    common_materials = bom_components & mrp_materials

    print("=== Connection Analysis: BOM ↔ MRP ===")
    print(f"Components in BOM but not in MRP: {len(components_in_bom_not_in_mrp)}")
    if components_in_bom_not_in_mrp:
        print(f"  Examples: {list(components_in_bom_not_in_mrp)[:5]}")
    print(f"Materials in MRP but not in BOM: {len(materials_in_mrp_not_in_bom)}")
    if materials_in_mrp_not_in_bom:
        print(f"  Examples: {list(materials_in_mrp_not_in_bom)[:5]}")
    print(f"Common materials: {len(common_materials)} ({len(common_materials)/len(bom_components)*100:.1f}% of BOM components)\n")

    # Analysis 3: End-to-end connection for scheduled parts
    connected_parts = set()
    disconnected_parts = set()
    missing_components = defaultdict(list)

    for part in schedule_parts:
        if part in bom_data:
            part_components = [comp['component'] for comp in bom_data[part]]
            missing_for_part = [comp for comp in part_components if comp not in mrp_materials]
            if not missing_for_part:
                connected_parts.add(part)
            else:
                disconnected_parts.add(part)
                missing_components[part] = missing_for_part
        else:
            disconnected_parts.add(part)

    print("=== End-to-End Connection Analysis: Schedule → BOM → MRP ===")
    print(f"Fully connected parts (BOM and MRP data available): {len(connected_parts)} ({len(connected_parts)/len(schedule_parts)*100:.1f}%)")
    print(f"Disconnected parts: {len(disconnected_parts)}")
    if disconnected_parts:
        print(f"  Examples: {list(disconnected_parts)[:5]}")
        print("  Reasons:")
        for part in list(disconnected_parts)[:3]:
            if part not in bom_data:
                print(f"    {part}: No BOM data")
            else:
                print(f"    {part}: Missing MRP for components: {missing_components[part][:3]}")

    # Summary
    print("\n=== Summary ===")
    connectivity_score = (len(common_parts) / len(schedule_parts) + len(common_materials) / len(bom_components)) / 2 * 100
    print(".1f")

    if connectivity_score > 80:
        print("✅ High connectivity: Integrated simulation should run well.")
    elif connectivity_score > 50:
        print("⚠️ Moderate connectivity: Simulation may run but with some missing data.")
    else:
        print("❌ Low connectivity: Significant data gaps may prevent proper simulation.")

    print("\nRecommendations:")
    if parts_in_schedule_not_in_bom:
        print("- Add BOM data for scheduled parts not found in BOM.")
    if components_in_bom_not_in_mrp:
        print("- Add MRP data for BOM components not found in MRP.")
    if len(mrp_locations) == 0:
        print("- MRP data lacks issue locations; logistics may not function properly.")

if __name__ == "__main__":
    analyze_data_connections()
