# Bootstrap Analysis Documentation

## Overview
Bootstrap analysis is a statistical resampling technique used to estimate the variability (such as variance, standard deviation, and confidence intervals) of a statistic (e.g., prevalence) by repeatedly sampling from the data with replacement. In this project, bootstrapping is used to provide robust estimates of prevalence and associated uncertainty for survey data, accounting for complex survey design via bootstrap weights.

Null outcomes are excluded from main-weight, replicate-weight, and unweighted
denominators together. Explicit survey response codes (including valid skip,
not stated, and refusal) remain categories in the default analysis. To estimate
among retained response categories, use the response-domain recalculation option.
Pooling stops if a selected cycle has no non-null responses for the variable.

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

## Pooled-cycle estimates

Cycle Pooling combines two or more independent annual samples. With `K` cycles,
the application divides each cycle's main and bootstrap weights by `K`, so a
weighted population is interpreted as an average annual population over the
pooled period. It is not the sum of the annual populations.

For variance estimation, one cycle's scaled bootstrap weights replace its
scaled main weights while all other cycles remain at their scaled main weights.
The mean squared replicate deviation is calculated for each cycle, and these
independent-cycle variance contributions are summed. This avoids imposing a
dependence on the alignment of replicate numbers across separate annual files.

The results table's **Recalculate %** option reruns the analysis on records in
the displayed response categories. Main and replicate denominators, variance,
confidence intervals, sample counts, and release flags all use that response
domain. Intervals are never obtained by scaling the original interval. A separate
CSV download contains the recalculated results; the main export retains the
original analysis. Recalculation is unavailable without respondent data and
stops if a selected cycle has no records in the retained response domain.

Only variables present in every cycle are offered. Cycle-specific data-dictionary
categories take precedence over generated category mappings. Observed response
codes must map completely in every selected cycle when categorical metadata is
available; otherwise the pooled estimate is stopped. All selected cycles must
also retain records after filtering and provide complete, finite, non-negative
main and replicate weights.
Every input record must have a non-null, non-blank cycle identifier. Each cycle
must have a positive main-weight total in the analyzed response domain; a cycle
with records but zero main weight cannot count toward the annual average.

## Key Functions
- `run_bootstrap_analysis_for_all_values`: Core function for bootstrap analysis.
- `run_cycle_pooled_analysis`: Pooled ratio estimates with separate cycle replicate perturbations.
- `prepare_pooling_population`: Common-age restriction and checks for known design/geography breaks.
- `recalculate_response_domain`: Re-estimates retained response categories using their replicate weights.
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

## Methodology decisions and source guidance

Sources checked on 2026-10-09. These references establish the basis and limits
of each rule; engineering checks are identified separately from survey-provider
requirements. Tests use synthetic records and contain no local variable metadata.

| Decision | Method followed | Source and exact location |
| --- | --- | --- |
| Average-period weighting | Divide annual main and replicate weights by the same `K`; interpret totals as an average population and ratios as period estimates. | Thomas and Wannell (2009), **The pooled approach**, [Combining cycles of the Canadian Community Health Survey](https://www150.statcan.gc.ca/n1/pub/82-003-x/2009001/article/10795/findings-resultats-eng.htm); CCHS 2010 User Guide, **8.8 Weighting for a two-year file**, [annual-weight halving](https://www.statcan.gc.ca/en/statistical-programs/document/3226_D7_T9_V8). |
| Prevalence | Ratio of weighted characteristic total to the weighted total of the specified response domain. | CCHS 2024 methodology, **Estimation**, [Statistics Canada survey 3226](https://www23.statcan.gc.ca/imdb/p2SV.pl?Function=getSurvey&Id=1531795). |
| Common age population | Use the intersection of covered ages: 12+ for 2021–2022, 18+ when 2023 or 2024 is selected. This restriction is an application choice derived from the documented coverage. | **Target population** in the [2022 methodology](https://www23.statcan.gc.ca/imdb/p2SV.pl?Function=getSurvey&Id=1383236), [2023 methodology](https://www23.statcan.gc.ca/imdb/p2SV.pl?Function=getSurvey&Id=1496481), and [2024 methodology](https://www23.statcan.gc.ca/imdb/p2SV.pl?Function=getSurvey&Id=1531795). |
| Review of known design changes | Require analyst review when combining pre-2022 and redesigned years. An acknowledgement records review; it does not establish comparability. | CCHS 2023 methodology, **Description**, redesign discussion; Thomas and Wannell (2009), **An evolving survey**. |
| Geography | For geographic filters spanning configured census vintages, require boundary/code review. The 2016/2021 vintage values come from the local cycle dictionaries' `GEODVCSD` descriptions and must be checked against the authorized original dictionaries. | Thomas and Wannell (2009), **Changes in geography**. Exact local dictionary editions are local provenance inputs and are not distributed in Git. |
| Response domains and missingness | Choose the analytical domain explicitly. Exclude null outcomes from every denominator together; preserve coded skips by default. Re-estimate each replicate when the domain changes. This complete-case estimand is an application choice, not imputation or a correction for nonresponse bias. | Gagné, Roberts and Keown (2014), **Problem-specific checklist**, items 2 and 6; **Software-specific checklist**, items 3–5; [Weighted estimation and bootstrap variance estimation for analyzing survey data](https://www150.statcan.gc.ca/n1/pub/12-002-x/2014001/article/11901-eng.htm). |
| Replicate variance specification | Use squared deviations about the full-sample estimate with explicit replicate scaling; verify weight type and scaling for the supplied files. | Lumley, **svrepdesign**, arguments `mse`, `scale`, `rscales`, `combined.weights`, and `bootstrap.average`, [official survey package documentation](https://r-survey.r-forge.r-project.org/pkgdown/docs/reference/svrepdesign.html). |
| Label normalization | NFKC normalization and case folding reconcile spelling representation; description/category matching is a screening check. Reject duplicate or malformed labels rather than infer a recode. | [Python Unicode normalization](https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize) and [case folding](https://docs.python.org/3/library/stdtypes.html#str.casefold); substantive comparability remains subject-matter review under Thomas and Wannell (2009). |
| Input integrity and stale results | Reject incomplete identities, invalid weights, or empty selected domains; discard prepared results when their inputs change. | Application engineering safeguards, verified by regression tests; these are not claimed as separately prescribed Statistics Canada rules. |
| Release indicators and confidence convention | Existing implementation uses `z=2`, and A/E/F proportion rules transcribed from the CCHS 2024 guide. | [Local transcription of Sections 10–11](docs/CCHS_2024_Data_Quality_Standards.md), August 2025 edition. The original guide is not available in this checkout; those edition-specific rules still require source verification before publication. |

### Exact pooled estimator

Let `D_c` be cycle `c`'s weighted total in the response domain and `N_cg` its
weighted total for category `g`. For `K` annual cycles:

$$
\widehat P_g = \frac{1}{K}\sum_c N_{cg},\qquad
\widehat p_g = 100\frac{\sum_c N_{cg}}{\sum_c D_c}.
$$

Let `N_cg^(b)` and `D_c^(b)` use cycle `c`'s supplied replicate `b`.
The implementation's cycle-specific perturbation and variance are:

$$
\widehat p_g^{(c,b)} =
100\frac{\sum_{j\ne c}N_{jg}+N_{cg}^{(b)}}{\sum_{j\ne c}D_j+D_c^{(b)}},
\qquad
\widehat V_g = \sum_c\frac{1}{B}\sum_{b=1}^{B}
\left(\widehat p_g^{(c,b)}-\widehat p_g\right)^2.
$$

This is a separate-cycle replicate construction. It is **not** the separate
approach of averaging annual prevalences, and is **not** a claim that Statistics
Canada prescribes this exact construction for every annual weight release.
With equal cycle totals and invariant replicate domain totals, it reduces to
the independent-sample variance identity for an average. For nonlinear ratios
with changing domain totals, it must be assessed as the stated replicate design.

The formula is reproducible in `survey::svrepdesign` by constructing `K*B`
weight columns: in column `(c,b)`, use cycle `c`'s replicate weights divided by
`K`, and all other cycles' main weights divided by `K`. Specify
`type="other"`, `combined.weights=TRUE`, `scale=1/B`,
`rscales=rep(1,K*B)`, and `mse=TRUE`; estimate a binary category indicator
using `svymean`. This specifies the calculation exactly rather than relying on
software defaults.

### Independent numerical benchmark

Run `Rscript scripts/validate_pooled_variance.R` with the `survey` package
installed. The fixture contains six synthetic records across three cycles, with
unequal annual totals and changing replicate totals. On 2026-10-09, the script
was executed using R 4.6.0 and `survey` 4.5 through webR 0.6.0. It returned
prevalence **45%** and variance **85.542898251371724 percentage-points squared**.
`tests/test_cycle_pooling.py::test_pooled_variance_matches_external_r_survey_benchmark`
checks the Python implementation against those independently computed values.
This check covers the specified separate-cycle replicate design, not an official
combined CCHS weight release.

### Conditions requiring data-provider confirmation

- Annual samples must support the independence assumption. A year label alone
  cannot establish this, especially where frames or sampled units overlap.
- The supplied `BSW` columns must be full replicate weights with the assumed
  `1/B` variance scale. Averaged bootstrap weights may require an additional
  factor; Gagné et al. (2014), **Problem-specific checklist**, item 6.4, requires
  checking this against survey documentation. The application does not infer or
  apply an unknown factor.
- An externally reproduced calculation verifies software arithmetic, not
  the suitability of a particular annual weight release for this pooled design.
  No agreement with an official combined-cycle file or Bootvar result is
  claimed without a corresponding benchmark and its source weight specification.
- Minimum age, code normalization, and description matching do not harmonize
  question universes, collection-mode effects, geography boundaries, or missing
  response mechanisms. The analyst review remains necessary.
