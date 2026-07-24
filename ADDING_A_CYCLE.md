# Adding a New CCHS Cycle

This project already supports multi-cycle analysis. Adding a new cycle is mostly a data + harmonization workflow, plus a small config update so the UI exposes the new year.

## What the app expects

For a new cycle such as `2024`, keep the existing file naming pattern:

```text
data/hs2024_on_distr.parquet
data/hs2024_on_bootwt.parquet
codebooks/CCHS_2024_DataDictionary_Freqs.pdf
harmonization/CCHS_2024.json
```

The loaders and precompute pipeline read cycle-specific files from those names.

## Steps

### 1. Add the raw data files

If you already received parquet files, copy the new cycle's main data and bootstrap weights into `data/`:

```bash
data/hs2024_on_distr.parquet
data/hs2024_on_bootwt.parquet
```

`src/data/loader.py` loads those files dynamically from the cycle value, so matching the naming convention is required.

If your source files arrive as SAS files, you can convert `.sas7bdat` files to parquet before continuing. If you maintain a separate conversion helper outside this repository, update its `sas_files` list for the new cycle and run it in that environment:

```bash
# from the directory containing your SAS helper and data
source <your-venv>/bin/activate
python sas.py
```

That helper writes parquet files beside the SAS inputs.

If you want a repo-local version of the same SAS helper pattern, use `scripts/convert_cycle_to_parquet.py`. It is intentionally simple: update the `cycle` value at the top of the file, make sure the `.sas7bdat` files are in `data/`, then run:

```bash
uv run python scripts/convert_cycle_to_parquet.py
```

Script settings:

- Set `cycle = "2024"` to the cycle you are converting
- Leave `delete_original = False` if you want to keep the `.sas7bdat` source files
- Set `delete_original = True` only if you want the script to remove the SAS files after each parquet file is written

The script writes:

```text
data/hs2024_on_distr.parquet
data/hs2024_on_bootwt.parquet
```

### 2. Add the codebook PDF

Codebooks are not distributed with this repository. Obtain the cycle-specific data dictionary from Statistics Canada's public CCHS documentation, then place it in `codebooks/`:

```bash
codebooks/CCHS_2024_DataDictionary_Freqs.pdf
```

This is the source used to build the cycle JSON used by the harmonization workflow. `scripts/extract_codebook.py` expects the file at `codebooks/CCHS_<year>_DataDictionary_Freqs.pdf`.

### 3. Create `harmonization/CCHS_<year>.json`

Generate a cycle JSON from the codebook. The repository already includes a starter extraction script in `scripts/extract_codebook.py`.

For a new cycle, update the input/output paths in that script or adapt it temporarily to point to the new year, then run:

```bash
uv run python scripts/extract_codebook.py
```

Expected output:

```bash
harmonization/CCHS_2024.json
```

Review the generated JSON before using it downstream. PDF extraction is not guaranteed to produce perfect category mappings.

### 4. Add the cycle to app configuration

Update `config/settings.py`:

- Add the new year to `AVAILABLE_CYCLES`
- Update `DEFAULT_CYCLE` if the new year should be the default selection

Example:

```python
AVAILABLE_CYCLES = ["2021", "2022", "2023", "2024"]
DEFAULT_CYCLE = "2024"
```

This is what drives the cycle selector in the app and the default behavior in the precompute script.

### 5. Regenerate the crosswalk

Update the `cycles` list in `scripts/build_crosswalk.py` so it includes the new year. The script uses the last cycle in that list as the reference cycle, so put the newest year last.

Then rebuild the crosswalk:

```bash
uv run python scripts/build_crosswalk.py
```

Expected output:

```bash
harmonization/crosswalk.json
```

Review the output. The current crosswalk builder uses fuzzy description matching, so manual cleanup is usually required for edge cases.

### 6. Update harmonized categories if needed

If the new cycle introduces new coded values or label changes, update `harmonization/categories.json`.

The app can run with incomplete category harmonization because column renaming is the primary requirement, but multi-cycle interpretation is better if category mappings are reviewed and kept aligned across years.

### 7. Precompute the new cycle

After the raw data, cycle JSON, crosswalk, and categories are ready, build the harmonized precomputed outputs:

```bash
uv run python scripts/precompute_cycles.py --cycles 2024
```

Or rebuild all supported cycles:

```bash
uv run python scripts/precompute_cycles.py
```

Expected outputs in `data/precomputed/`:

```text
harmonized_data_2024.parquet
harmonized_bootstrap_2024.parquet
metadata_2024.pkl
```

### 8. Validate before shipping

Run the validation mode:

```bash
uv run python scripts/precompute_cycles.py --cycles 2024 --validate-only
```

Then start the app and confirm:

- The new cycle appears in the selector
- Single-cycle loading works
- Multi-cycle comparisons include the new year
- Expected harmonized variables appear in search/results

## Required code touchpoints

For most new cycles, these are the files you should expect to update:

- `config/settings.py`
- `scripts/build_crosswalk.py`
- `scripts/extract_codebook.py` or a one-off replacement script
- `harmonization/CCHS_<year>.json`
- `harmonization/crosswalk.json`
- `harmonization/categories.json` when categories change

## Recommended checklist

- Raw parquet files added to `data/`
- Codebook PDF added to `codebooks/`
- `harmonization/CCHS_<year>.json` created and reviewed
- `AVAILABLE_CYCLES` updated
- `crosswalk.json` regenerated and spot-checked
- `categories.json` updated if needed
- Precomputed files generated
- App validated in single-cycle and multi-cycle modes
