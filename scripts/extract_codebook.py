# Extraction for categories and harmonization structure
import json
import sys
from pathlib import Path

# Add project root to path so `src` is importable when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.codebook_extractor import extract_variables_with_categories

cycle = "2024"
codebook_path = Path(f"./codebooks/CCHS_{cycle}_DataDictionary_Freqs.pdf")
output_path = Path(f"./harmonization/CCHS_{cycle}.json")

variables = extract_variables_with_categories(codebook_path)

# Save as JSON for harmonization pipeline
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(variables, f, indent=2, ensure_ascii=False)

print(f"Extracted variable/category info saved to {output_path}")
