import json
import os
import sys
from pathlib import Path

# Add project root to path so `src` is importable when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.harmonizer import auto_harmonize

cycles = ["2021", "2022", "2023", "2024"]
harmonization_dir = "./harmonization"

# Load crosswalk
with open(os.path.join(harmonization_dir, "crosswalk.json"), encoding="utf-8") as f:
    crosswalk = json.load(f)

# Load variable/category metadata for each cycle
cycle_vars = {}
for cycle in cycles:
    with open(os.path.join(harmonization_dir, f"CCHS_{cycle}.json"), encoding="utf-8") as f:
        cycle_vars[cycle] = json.load(f)

# Harmonize common categories for all cycles
harmonized = {}
for concept_var, mapping in crosswalk.items():
    harmonized[concept_var] = {
        "harmonized_categories": [],
        "mappings": {}
    }
    all_hcats = set()
    for cycle in cycles:
        var = mapping.get(cycle)
        cats = cycle_vars[cycle].get(var, {}).get("categories", {}) if var else {}
        cat_map = {}
        for code, label in cats.items():
            hcat = auto_harmonize(label)
            cat_map[code] = hcat
            all_hcats.add(hcat)
        harmonized[concept_var]["mappings"][cycle] = cat_map
    harmonized[concept_var]["harmonized_categories"] = sorted(list(all_hcats))

with open(os.path.join(harmonization_dir, "categories.json"), "w", encoding="utf-8") as f:
    json.dump(harmonized, f, indent=2, ensure_ascii=False)

print("Category harmonization saved to categories.json")
