# CCHS Bootstrap Analysis Tool

A local Streamlit application for public health analysts and epidemiologists who
work with Canadian Community Health Survey (CCHS) data. It supports geographic
filtering, bootstrap prevalence estimates, CCHS release-quality indicators,
age-stratified analysis, exports, and comparisons across annual cycles.

> **Project status:** This is a public-health-unit analytical tool under active
> validation. It is not an official Statistics Canada product. Analysts remain
> responsible for following their CCHS data-sharing agreements, organizational
> privacy policies, and applicable release standards.

Full documentation, including the methodology and code reference, is published
at <https://wdgph.github.io/CCHS/> (see [Enabling the docs site](#enabling-the-docs-site)
if it isn't live yet).

## Analysis modes

- **Single Cycle** calculates estimates for one CCHS year.
- **Multi-Cycle Trends** calculates each selected year independently and compares
  the resulting estimates across years.

Multi-Cycle Trends does **not** pool respondent-level records or weights across
cycles. Cycle pooling is a requested future feature and will require a separately
validated statistical design before implementation.

### Future cycle-pooling work

Pooling is intentionally out of scope for the current release. A future design
must define combined-cycle weights, target population and time-period semantics,
variance estimation, cycle effects, comparability rules, and release-quality
validation before any pooled estimate is exposed in the interface.

Supported configurations currently include CCHS 2021, 2022, 2023, and 2024.

## Bring your own data

The repository does not distribute CCHS respondent data, bootstrap weights, or
codebook PDFs. Public health units run the application locally with files they
are authorized to use.

Place cycle files under `data/` using this convention:

```text
data/
├── hs2021_on_distr.parquet
├── hs2021_on_bootwt.parquet
├── hs2022_on_distr.parquet
├── hs2022_on_bootwt.parquet
├── hs2023_on_distr.parquet
├── hs2023_on_bootwt.parquet
├── hs2024_on_distr.parquet
└── hs2024_on_bootwt.parquet
```

Main files must include `ONT_ID`, `WTS_S`, and the variables being analyzed.
Bootstrap files must include `ONT_ID` and replicate-weight columns beginning with
`BSW`. The application validates one-to-one joins. Multi-cycle trend processing
also attaches the cycle year to both frames so identifiers cannot cross-join
between years.

`data/` and local codebook PDFs are Git-ignored. Do not commit CCHS microdata,
derived respondent-level files, bootstrap weights, or codebooks.

The `harmonization/CCHS_<year>.json`, `crosswalk.json`, and `categories.json`
files are also Git-ignored and not distributed with this repository, since
they are extracted from codebook documentation each organization must obtain
under its own CCHS agreement. Generate them locally with
`scripts/extract_codebook.py`, `scripts/build_crosswalk.py`, and
`scripts/harmonize_categories.py` - see
[Adding a New CCHS Cycle](ADDING_A_CYCLE.md) and
[Third-party data and metadata](THIRD_PARTY_DATA.md).

## Install and run locally

Requirements:

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/WDGPH/CCHS.git
cd CCHS
uv sync --locked
uv run streamlit run app.py
```

Open <http://127.0.0.1:8501>.

`pyproject.toml` and `uv.lock` are the authoritative dependency files. This
project intentionally does not maintain `requirements.txt`.

The committed `.streamlit/config.toml` binds the application to localhost and
disables Streamlit usage-statistics collection. Routine analysis reads local
files and performs calculations locally.

## Multi-cycle trend workflow

1. Select **Multi-Cycle Trends**.
2. Choose two or more cycles.
3. Select geography and inclusion filters.
4. Choose variables available across the selected cycles.
5. Run the analysis.
6. Review cycle-specific estimates, confidence intervals, release flags, and
   trend charts.

Harmonized names make equivalent variables easier to compare, but analysts must
still confirm that concepts and response categories are comparable across years.
The generated crosswalk uses automated matching and requires subject-matter
review.

## Statistical outputs

For each variable value, the tool reports:

- weighted prevalence and population
- unweighted numerator and denominator
- bootstrap variance and standard error
- confidence interval using the documented CCHS `z = 2.0` convention
- coefficient of variation
- CCHS 2022+ A/E/F release category and action

Release flags are displayed by default for supported 2022+ cycles. Analysts
should suppress category F estimates and apply their organization's complete
review and rounding process before publication.

See:

- [Bootstrap analysis methodology](bootstrap_analysis_documentation.md)
- [CCHS 2024 data-quality standards](docs/CCHS_2024_Data_Quality_Standards.md)
- [Privacy and security overview](docs/CCHS_Data_Privacy_Security_Guide.md)

## Precomputing harmonized files

Precomputing can improve local performance without changing the statistical
method:

```bash
uv run python scripts/precompute_cycles.py
uv run python scripts/precompute_cycles.py --validate-only
```

Generated files remain under `data/precomputed/` and are ignored by Git. Metadata
is stored as JSON; regenerate older precomputed outputs that used pickle.

## Adding a cycle

See [Adding a New CCHS Cycle](ADDING_A_CYCLE.md). Codebook extraction uses the
declared `pypdf` dependency:

```bash
uv run python scripts/extract_codebook.py
```

Review all extracted descriptions, categories, and generated crosswalk mappings
before analytical use.

## Development

Install the locked development environment and run the synthetic-data test suite:

```bash
uv sync --locked --dev
uv run pytest -q
uv run python -m compileall -q app.py config scripts src
```

Tests and continuous integration do not require CCHS data.

## Documentation site

The docs site is built with [MkDocs](https://www.mkdocs.org/) and the
[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme,
pulling its content from this README and the other project markdown files.

```bash
uv sync --group docs
uv run mkdocs serve
```

Open <http://127.0.0.1:8000>. Edits to the markdown files it references are
picked up automatically.

### Enabling the docs site

The `docs` workflow (`.github/workflows/docs.yml`) builds the site on every
push to `main` and publishes it to the `gh-pages` branch. To serve it on
GitHub Pages:

1. Go to the repository's **Settings** tab.
2. Navigate to **Pages** in the left sidebar.
3. Under **Source**, select **Deploy from a branch**.
4. Choose the **gh-pages** branch and **/ (root)** folder.
5. Click **Save**.

The site becomes available at `https://wdgph.github.io/CCHS/` after the first
successful run of the workflow on `main`.

## Repository structure

```text
app.py                 Streamlit entry point
config/                Application and analysis settings
src/analysis/           Bootstrap and quality calculations
src/data/               Loading, harmonization, and preprocessing
src/ui/                 Streamlit interface components
harmonization/          Cycle metadata, crosswalks, and lookup tables
scripts/                Local conversion and precompute utilities
tests/                  Synthetic-data tests
```

## Data and metadata provenance

See [Third-party data and metadata](THIRD_PARTY_DATA.md). The repository's MIT
license applies to project code; it does not replace the terms governing CCHS
data or third-party metadata.

## Contributing and security

- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Code of conduct](CODE_OF_CONDUCT.md)

## License

Project code is licensed under the [MIT License](LICENSE).
