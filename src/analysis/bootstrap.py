"""Bootstrap analysis functions for CCHS data."""

import numpy as np
import pandas as pd
from config.settings import BOOTSTRAP_PREFIX, DEFAULT_WEIGHT_COLUMN
from src.analysis.quality import QUALITY_FLAG_CYCLES, apply_cchs_quality_flags


def run_bootstrap_analysis_for_all_values(
    merged_data,
    variable_col,
    weight_col=DEFAULT_WEIGHT_COLUMN,
    standards_cycle=None,
):
    """
    Perform bootstrap analysis using vectorized groupby operations.
    Computes weighted prevalences and bootstrap variances.
    """
    # Identify bootstrap weight columns (those starting with 'BSW')
    bootstrap_cols = [col for col in merged_data.columns if col.startswith(BOOTSTRAP_PREFIX)]
    
    # Precompute total weights for base and bootstrap replicates
    total_weight_base = merged_data[weight_col].sum()
    total_weights_boot = {col: merged_data[col].sum() for col in bootstrap_cols}
    
    # Compute weighted sums for the base weight grouped by the selected variable
    base_numerators = merged_data.groupby(variable_col)[weight_col].sum()
    base_prevalence = (base_numerators / total_weight_base) * 100
    unweighted_numerators = merged_data.groupby(variable_col).size()
    unweighted_denominator = merged_data[variable_col].notna().sum()

    # Weighted population for each group (sum of weights)
    weighted_population = base_numerators

    # OPTIMIZED: Compute all bootstrap replicates at once using vectorized operations
    # Group by variable and sum all bootstrap columns simultaneously
    bootstrap_sums = merged_data.groupby(variable_col)[bootstrap_cols].sum()
    
    # Convert total weights to Series for vectorized division
    total_weights_series = pd.Series(total_weights_boot, name='total_weights')
    
    # Vectorized calculation: divide each bootstrap sum by its corresponding total weight
    replicate_prevalence_df = bootstrap_sums.div(total_weights_series, axis=1) * 100

    # Compute variance, standard deviation, confidence intervals, etc.
    variance = ((replicate_prevalence_df.sub(base_prevalence, axis=0))**2).mean(axis=1)
    std_dev = np.sqrt(variance)
    ci_lower = base_prevalence - 1.96 * std_dev
    ci_upper = base_prevalence + 1.96 * std_dev
    cv = (std_dev / base_prevalence) * 100

    result_df = pd.DataFrame({
        'Value': base_prevalence.index,
        'Prevalence': base_prevalence.values,
        'Unweighted Numerator': unweighted_numerators.reindex(base_prevalence.index).values,
        'Unweighted Denominator': unweighted_denominator,
        'Weighted Population': weighted_population.values,
        'Variance': variance.values,
        'Standard Deviation': std_dev.values,
        'CI Lower': ci_lower.values,
        'CI Upper': ci_upper.values,
        'CV (%)': cv.values,
        'Error': 1.96 * std_dev.values  # for error bars in plots
    }).reset_index(drop=True)

    if str(standards_cycle) in QUALITY_FLAG_CYCLES:
        result_df = apply_cchs_quality_flags(result_df)

    return result_df
