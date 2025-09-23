import sys
import os
sys.path.append('backend')
try:
    from models import SimulationSetup
    print("Models imported successfully!")
    print(f"SimulationSetup: {SimulationSetup}")
except Exception as e:
    print(f"Error importing models: {e}")
    import traceback
    traceback.print_exc()
