import pandas as pd
from pathlib import Path

cycle = "2024"
delete_original = False
data_dir = Path("data")
sas_files = [
    f"hs{cycle}_on_distr.sas7bdat",
    f"hs{cycle}_on_bootwt.sas7bdat",
]

for sas_file in sas_files:
    input_path = data_dir / sas_file
    output_path = data_dir / sas_file.replace(".sas7bdat", ".parquet")

    print(f"Reading {input_path}...")
    df = pd.read_sas(input_path, format="sas7bdat")

    print(f"Writing {output_path}...")
    df.to_parquet(output_path, engine="pyarrow", index=False)

    if delete_original:
        print(f"Removing {input_path}...")
        input_path.unlink()

print("Conversion complete!")

