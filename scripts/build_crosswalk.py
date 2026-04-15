import json
import os
import difflib

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

# Use the most recent cycle as reference
reference_cycle = cycles[-1]
reference_vars = descriptions[reference_cycle]

crosswalk = {}
for ref_var, ref_desc in reference_vars.items():
    crosswalk[ref_var] = {reference_cycle: ref_var}
    for cycle in cycles[:-1]:
        # Fuzzy match by description
        candidates = descriptions[cycle]
        best_match = difflib.get_close_matches(ref_desc, candidates.values(), n=1, cutoff=0.6)
        if best_match:
            # Find the variable name for the best match
            for var, desc in candidates.items():
                if desc == best_match[0]:
                    crosswalk[ref_var][cycle] = var
                    break
        else:
            crosswalk[ref_var][cycle] = None

# Save crosswalk
with open(os.path.join(data_dir, "crosswalk.json"), "w", encoding="utf-8") as f:
    json.dump(crosswalk, f, indent=2, ensure_ascii=False)

print(f"Crosswalk saved to {os.path.join(data_dir, 'crosswalk.json')}")
