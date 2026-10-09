import json
import os
import sys
from pathlib import Path

# Add project root to path so `src` is importable when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.harmonizer import build_crosswalk

# Paths to harmonized JSONs for each cycle
data_dir = "./harmonization"
cycles = ["2021", "2022", "2023", "2024"]
cycle_files = {cycle: os.path.join(data_dir, f"CCHS_{cycle}.json") for cycle in cycles}

# Load variable descriptions for each cycle
descriptions = {}
for cycle, path in cycle_files.items():
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        descriptions[cycle] = {var: v["description"] for var, v in data.items()}

# Use the most recent cycle (last in the list) as reference
crosswalk = build_crosswalk(cycles, descriptions)

# Save crosswalk
with open(os.path.join(data_dir, "crosswalk.json"), "w", encoding="utf-8") as f:
    json.dump(crosswalk, f, indent=2, ensure_ascii=False)

print(f"Crosswalk saved to {os.path.join(data_dir, 'crosswalk.json')}")
