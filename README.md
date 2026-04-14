# CCHS Bootstrap Analysis Tool

A comprehensive Streamlit application for analyzing Canadian Community Health Survey (CCHS) data using bootstrap statistical methods. This tool provides an intuitive interface for geographic filtering, variable selection, and statistical analysis with confidence intervals.

## 📋 Overview

This application performs bootstrap analysis on CCHS Ontario data with **multi-cycle support**, allowing users to:
- **Multi-cycle analysis**: Compare data across CCHS 2021, 2022, and 2023 cycles
- **Variable harmonization**: Use pre-harmonized variable names across cycles
- Filter data by geographic regions (districts, municipalities, multiple health regions / public health units)
- Select multiple variables for analysis
- Calculate prevalence rates with bootstrap confidence intervals
- Generate cross-tabulation reports and cycle comparisons
- Perform age-stratified analysis
- Export results in multiple formats

## 🗂️ Required Data Files

### Data Directory Structure

Place the following files in the `data/` directory:

```
data/
├── hs2021_on_distr.parquet          # CCHS 2021 main data
├── hs2021_on_bootwt.parquet         # CCHS 2021 bootstrap weights
├── hs2022_on_distr.parquet          # CCHS 2022 main data
├── hs2022_on_bootwt.parquet         # CCHS 2022 bootstrap weights
├── hs2023_on_distr.parquet          # CCHS 2023 main data
├── hs2023_on_bootwt.parquet         # CCHS 2023 bootstrap weights
└── CCHS_YYYY_Recoded_Variables.csv  # Variable descriptions (per cycle)
```

### Harmonization Files

Pre-computed harmonization files (already included in repository):

```
harmonization/
├── CCHS_2021.json      # Variable descriptions & categories for 2021
├── CCHS_2022.json      # Variable descriptions & categories for 2022
├── CCHS_2023.json      # Variable descriptions & categories for 2023
├── crosswalk.json      # Variable name mappings across cycles
└── categories.json     # Harmonized category labels
```

**Note**: These harmonization files are built using scripts (see [HARMONIZATION_WORKFLOW.md](HARMONIZATION_WORKFLOW.md))

### Data File Specifications

- **hsYYYY_on_distr.parquet**: Main survey data with respondent records
- **hsYYYY_on_bootwt.parquet**: Bootstrap weights (columns starting with 'BSW')
- **CCHS_YYYY_Recoded_Variables.csv**: Must contain 'Variable' and 'Description' columns

## 🚀 Installation & Setup (Local Python)

### Prerequisites
```bash
python 3.11+
# Install uv (fast Python package/dependency manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
# Ensure ~/.local/bin or the suggested path is on your PATH
uv --version
```

### Install Dependencies (creates .venv automatically)
```bash
uv sync
```

### Run the Application
```bash
uv run streamlit run main.py
```
(Or activate the environment: `source .venv/bin/activate` then `streamlit run main.py`.)

> Note: requirements.txt retained only for legacy workflows; authoritative dependencies live in pyproject.toml.

## 🐳 Docker Deployment

Docker image now uses uv + pyproject.toml for deterministic dependency resolution.

### 1. Build Image
```bash
docker build -t cchs-bootstrap:latest .
```

### 2. Run Container (bind local data directory read-only)
```bash
docker run -d \
  --name cchs-bootstrap \
  -p 8501:8501 \
  -v "$(pwd)/data:/app/data:ro" \
  cchs-bootstrap:latest
```
Then open: http://localhost:8501

### 3. Environment Variables (optional)
Set inside `docker run -e KEY=value` or compose file.

### 4. Docker Compose (with live code reload optional)
```bash
docker compose up --build
```
(Compose file maps `./data` and exposes port 8501.)

### 5. Production Tips
- Deterministic lock: run `uv lock` (already implicit with `uv sync --frozen`) before building to freeze versions.
- Multi-arch build: `docker buildx build --platform linux/amd64,linux/arm64 -t registry.local/cchs-bootstrap:latest --push .`

### 6. Updating
```bash
docker pull <registry>/cchs-bootstrap:latest
docker stop cchs-bootstrap && docker rm cchs-bootstrap
# rerun docker run ...
```

## 🎯 Features

### 1. Multi-Cycle Analysis (NEW!)
- **Cycle Selection**: Choose between single-cycle or multi-cycle analysis
- **Harmonized Variables**: Automatic variable name harmonization across cycles
- **Cycle Comparisons**: Side-by-side comparison of prevalence rates
- **Trend Analysis**: Visualize changes across cycles with line charts
- **Fast Loading**: Pre-computed harmonization for instant data loading

### 2. Variable Search & Selection
- **Search by Code**: Find variables using CCHS variable codes (e.g., GEN_005)
- **Search by Description**: Search within variable descriptions using keywords
- **Multi-select**: Choose multiple variables for batch analysis
- **Harmonized View**: See common variables available across all selected cycles

### 3. Geographic Filtering
- **District-level**: Filter by GEODVCSD codes
- **Municipality**: Configurable municipality shortcuts per public health unit
- **Health Region**: Filter by one or more GEODVHR4 codes

### 4. Bootstrap Analysis
- Calculates weighted prevalence rates
- Computes 95% confidence intervals
- Provides coefficient of variation (CV)
- Uses vectorized operations for performance

### 5. Results & Visualization
- **Single-Cycle**: Interactive tables with gradient styling and bar charts with error bars
- **Multi-Cycle**: Comparison tables, trend lines, grouped bar charts, and statistical summaries
- Cross-tabulation pivot tables
- Age-stratified analysis

### 6. Export Options
- CSV format for data analysis
- Excel format with multiple worksheets
- Multi-cycle exports with separate sheets per cycle
- Customizable variable naming for reports

## 📊 Analysis Workflow

### Step 1: Apply Geographic Filters
1. Select desired geographic boundaries in the sidebar
2. Choose from district, municipality, or health region filters
3. Click "Apply Geographic Filters"

### Step 2: Merge Data
1. Review the filtered data preview
2. Click "Merge Data with Bootstrap Weights"

### Step 3: Configure Analysis
1. Select variables using the search functionality
2. Review selected variables with descriptions
3. Configure weight column (defaults to WTS_S)

### Step 4: Run Analysis
1. Click "Run Bootstrap Analysis"
2. Monitor progress for multiple variables
3. View individual variable results

### Step 5: Review Results
- **Crosstab Report**: Pivot table of all results
- **Age Group Analysis**: Age-stratified breakdown
- **Data Export**: Download results in preferred format

## 🔧 Technical Details

### Bootstrap Methodology
The application uses the bootstrap replication method for variance estimation:

1. **Base Prevalence**: Calculated using survey weights (WTS_S)
2. **Bootstrap Replicates**: Uses all BSW* columns for variance estimation
3. **Confidence Intervals**: 95% CI using normal approximation
4. **Performance**: Vectorized operations for processing multiple bootstrap weights

### Key Functions

#### `load_data()`
- Loads main data and bootstrap weights from parquet files
- Implements caching for performance

#### `run_bootstrap_analysis_for_all_values()`
- Core bootstrap analysis function
- Vectorized computation of prevalence and confidence intervals
- Returns comprehensive statistics for each variable value

#### `create_age_groups()`
- Creates standardized age groups: 0-17, 18-24, 25-44, 45-64, 65+
- Used for age-stratified analysis

#### `apply_region_filter()`
- Dynamically applies geographic filters
- Supports multiple filter types simultaneously

### Performance Optimizations
- **Data Caching**: Uses `@st.cache_data` for data loading
- **Vectorized Operations**: Bootstrap calculations use pandas vectorization
- **Memory Efficiency**: Processes data in chunks for large datasets
- **Progress Tracking**: Real-time progress updates for long-running analyses

### Dependency Management
- Managed via `pyproject.toml` + uv.
- Update / add a package: `uv add package_name` then commit updated pyproject.toml (and lock file if generated).

## 🎨 User Interface

### Design Features
- **Modern CSS Styling**: Custom color scheme with gradients
- **Responsive Layout**: Adapts to different screen sizes
- **Interactive Elements**: Hover effects and smooth transitions
- **Progress Indicators**: Real-time analysis progress
- **Metric Cards**: Key statistics display
- **Tabbed Interface**: Organized results presentation

### Color Scheme
- Primary: #005568 (Dark teal)
- Secondary: #00928F (Teal)
- Accent: #78A22F (Green)
- Background: Clean whites and light grays

## 📈 Output Interpretation

### Result Columns
- **Value**: Category/value of the selected variable
- **Prevalence**: Weighted prevalence percentage
- **Variance**: Bootstrap variance estimate
- **Standard Deviation**: Square root of variance
- **CI Lower/Upper**: 95% confidence interval bounds
- **CV (%)**: Coefficient of variation percentage
- **Error**: Margin of error for visualization

### Quality Indicators
- **CV < 16.6%**: Acceptable precision
- **CV 16.6-33.3%**: Use with caution
- **CV > 33.3%**: Unreliable, suppress if necessary

## 📚 Further Reading

For an in-depth explanation of the statistical methodology and formulas used, see the [Bootstrap Analysis Documentation](bootstrap_analysis_documentation.md).

## 🔍 Troubleshooting

### Common Issues

#### Data Loading Errors
```
Error: One or both of the required parquet files are missing.
```
**Solution**: Ensure data files are in the correct `data/` directory

#### Memory Issues
```
Memory error during bootstrap analysis
```
**Solution**: Reduce the number of variables analyzed simultaneously

#### Empty Results
```
No data after applying filters
```
**Solution**: Check geographic filter settings, ensure codes match data

### Environment Issues
```
uv: command not found
```
Install uv and ensure PATH updated (restart shell) or invoke via full path printed after install.

### Performance Tips
- Start with single variable analysis for large datasets
- Use geographic filters to reduce data size
- Close browser tabs to free memory during analysis

## 📝 Configuration

### Geographic Codes
Update the predefined geographic codes in the main function:
```python
wellington_codes = {3523017: 'Erin', ...}
guelph_codes = {3523008: 'Guelph'}
dufferin_codes = {3522014: 'Orangeville', ...}
```

### Styling Customization
Modify CSS variables in the `st.markdown()` section:
```css
:root {
    --primary: #005568;
    --secondary: #00928F;
    --accent: #78A22F;
}
```

## 📊 Example Use Cases

### Public Health Analysis
- Prevalence of health conditions by municipality
- Age-specific health behavior patterns
- Geographic disparities in health outcomes

### Policy Research
- Cross-tabulation of multiple health indicators
- Confidence intervals for reliable estimates
- Export-ready tables for reports

### Academic Research
- Bootstrap variance estimation
- Complex survey data analysis
- Reproducible research workflows

## 🤝 Contributing

This project is internal to WDG Public Health. For guidelines on contributing, see [CONTRIBUTING.md](CONTRIBUTING.md).


---

*For technical support or questions about CCHS methodology, consult Statistics Canada documentation.*
