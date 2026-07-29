# Bootstrap Analysis Documentation

## Overview
Bootstrap analysis is a statistical resampling technique used to estimate the variability (such as variance, standard deviation, and confidence intervals) of a statistic (e.g., prevalence) by repeatedly sampling from the data with replacement. In this project, bootstrapping is used to provide robust estimates of prevalence and associated uncertainty for survey data, accounting for complex survey design via bootstrap weights.

## Process Steps

### 1. Data Preparation
- **Load Main Data**: The main survey data is loaded from a Parquet file.
- **Load Bootstrap Weights**: Bootstrap replicate weights are loaded from a separate Parquet file.
- **Merge Data**: The main data and bootstrap weights are merged on a unique identifier (e.g., `ONT_ID`).
- **Filtering**: Data can be filtered by geographic or demographic criteria before analysis.

### 2. Running the Bootstrap Analysis
- **Function**: `run_bootstrap_analysis_for_all_values(merged_data, variable_col, weight_col)`
- **Inputs**:
  - `merged_data`: DataFrame containing both main data and bootstrap weights.
  - `variable_col`: The categorical variable for which prevalence is calculated.
  - `weight_col`: The main survey weight column (e.g., `WTS_S`).
- **Process**:
  1. Identify all bootstrap weight columns (e.g., columns starting with `BSW`).
  2. For each value in the selected variable:
     - Calculate the weighted sum (numerator) for the main weight and each bootstrap weight.
     - Calculate the total sum of weights (denominator) for the main and each bootstrap weight.
     - Compute prevalence as (weighted sum / total weight) * 100 for both main and bootstrap weights.
  3. Calculate variance, standard deviation, and confidence intervals (typically 95%) using the distribution of bootstrap replicate prevalences.
  4. Calculate the coefficient of variation (CV) and error margin.
  5. Calculate the weighted population (sum of weights) for each group.
- **Outputs**: DataFrame with columns for Value, Prevalence, Weighted Population, Variance, Standard Deviation, CI Lower, CI Upper, CV (%), and Error.

### 3. Display and Interpretation
- **Results Table**: Shows prevalence, weighted population, and uncertainty metrics for each value of the variable.
- **Crosstab Report**: Allows comparison of prevalence and weighted population across multiple variables and values.
- **Visualization**: Bar charts with error bars visualize prevalence and uncertainty.

## Key Functions
- `run_bootstrap_analysis_for_all_values`: Core function for bootstrap analysis.
- `display_results`: Presents results in a styled table and chart.
- `display_crosstab_report`: Generates crosstab reports for prevalence and weighted population.

## Formulas Used in Bootstrap Analysis

Let:
- $i$ index the records in the dataset
- $g$ index the groups (values) of the variable being analyzed
- $w_i$ be the main survey weight for record $i$
- $w_{i}^{(b)}$ be the $b$-th bootstrap weight for record $i$
- $y_i$ be an indicator variable (1 if record $i$ is in group $g$, 0 otherwise)
- $B$ be the number of bootstrap replicates

### Weighted Population
For group $g$:
$$
\text{Weighted Population}_g = \sum_{i \in g} w_i
$$

### Weighted Prevalence (Main Weight)
For group $g$:
$$
\text{Prevalence}_g = \frac{\sum_{i \in g} w_i}{\sum_{i} w_i} \times 100
$$

### Weighted Prevalence (Bootstrap Replicates)
For each bootstrap replicate $b$:
$$
\text{Prevalence}_g^{(b)} = \frac{\sum_{i \in g} w_{i}^{(b)}}{\sum_{i} w_{i}^{(b)}} \times 100
$$

### Variance (Bootstrap)
$$
\text{Variance}_g = \frac{1}{B} \sum_{b=1}^{B} \left( \text{Prevalence}_g^{(b)} - \text{Prevalence}_g \right)^2
$$

### Standard Deviation
$$
\text{StdDev}_g = \sqrt{\text{Variance}_g}
$$

### 95% Confidence Interval
$$
\text{CI Lower}_g = \text{Prevalence}_g - 2.0 \times \text{StdDev}_g
$$
$$
\text{CI Upper}_g = \text{Prevalence}_g + 2.0 \times \text{StdDev}_g
$$

### Coefficient of Variation (CV)
$$
\text{CV}_g = \frac{\text{StdDev}_g}{\text{Prevalence}_g} \times 100
$$

### Error Margin (for error bars)
$$
\text{Error}_g = 2.0 \times \text{StdDev}_g
$$

## Notes
- **Weighted Population**: Represents the estimated population size for each group, calculated as the sum of survey weights.
- **Confidence Intervals**: Calculated using the CCHS reporting convention of estimate ± 2.0 × bootstrap standard error.
- **Bootstrap Weights**: Account for survey design and provide more accurate variance estimates than simple random sampling.

## Example Usage
```python
result_df = run_bootstrap_analysis_for_all_values(merged_data, 'SEX', 'WTS_S')
display_results(result_df, 'SEX')
```

## References
- [Statistics Canada: Bootstrap Weights](https://www150.statcan.gc.ca/n1/pub/12-002-x/2011001/article/11425-eng.html)
- [Bootstrap Methods and Their Application (Davison & Hinkley, 1997)](https://www.cambridge.org/core/books/bootstrap-methods-and-their-application/)
