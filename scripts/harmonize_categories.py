import json
import os

cycles = ["2021", "2022", "2023"]
harmonization_dir = "./harmonization"

# Load crosswalk
with open(os.path.join(harmonization_dir, "crosswalk.json"), encoding="utf-8") as f:
    crosswalk = json.load(f)

# Load variable/category metadata for each cycle
cycle_vars = {}
for cycle in cycles:
    with open(os.path.join(harmonization_dir, f"CCHS_{cycle}.json"), encoding="utf-8") as f:
        cycle_vars[cycle] = json.load(f)

# Example: harmonize common categories for all cycles
def auto_harmonize(label):
    l = label.lower()
    if "yes" in l:
        return "Yes"
    if "no" in l:
        return "No"
    if "not stated" in l:
        return "Not stated"
    if "valid skip" in l:
        return "Valid skip"
    if "don’t know" in l or "don't know" in l:
        return "Don't know"
    if "male" in l:
        return "Male"
    if "female" in l:
        return "Female"
    return label.strip()

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
