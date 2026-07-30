"""Bootstrap analysis functions for CCHS data."""

import numpy as np
import pandas as pd
from config.settings import BOOTSTRAP_PREFIX, CONFIDENCE_Z, DEFAULT_WEIGHT_COLUMN
from src.analysis.quality import QUALITY_FLAG_CYCLES, apply_cchs_quality_flags


def _bootstrap_columns(data):
    """Return replicate-weight columns in their existing file order."""
    return [col for col in data.columns if col.startswith(BOOTSTRAP_PREFIX)]


def _validate_pooling_inputs(data, variable_col, weight_col, cycle_col):
    required = {cycle_col, variable_col, weight_col}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(
            "Cycle pooling is missing required column(s): "
            + ", ".join(sorted(missing))
        )

    cycles = [str(value) for value in data[cycle_col].dropna().unique()]
    if len(cycles) < 2:
        raise ValueError("Cycle pooling requires at least two non-empty cycles.")

    bootstrap_cols = _bootstrap_columns(data)
    if not bootstrap_cols:
        raise ValueError("Cycle pooling requires bootstrap replicate weights.")

    weight_cols = [weight_col, *bootstrap_cols]
    if data[weight_cols].isna().any().any():
        raise ValueError(
            "Cycle pooling found missing main or bootstrap weights. Ensure every "
            "selected cycle has the same complete replicate-weight columns."
        )

    numeric_weights = data[weight_cols].apply(pd.to_numeric, errors="coerce")
    if numeric_weights.isna().any().any():
        raise ValueError("Cycle pooling requires numeric survey weights.")
    if not np.isfinite(numeric_weights.to_numpy()).all():
        raise ValueError("Cycle pooling requires finite survey weights.")
    if (numeric_weights < 0).any().any():
        raise ValueError("Cycle pooling does not allow negative survey weights.")
    if numeric_weights[weight_col].sum() <= 0:
        raise ValueError("Cycle pooling requires a positive total survey weight.")

    return cycles, bootstrap_cols, numeric_weights


def run_cycle_pooled_analysis(
    merged_data,
    variable_col,
    weight_col=DEFAULT_WEIGHT_COLUMN,
    cycle_col="CYCLE",
    standards_cycle=None,
    expected_cycles=None,
):
    """Estimate prevalence for the average population across pooled cycles.

    Each cycle contributes its annual survey weights divided by the number of
    cycles. The pooled weighted population therefore represents an average
    annual population, rather than the sum of annual populations.

    CCHS cycles are independent samples. For each cycle, replicate estimates
    replace only that cycle's scaled main weights with its scaled bootstrap
    weights while the other cycles remain at their main weights. The pooled
    variance is the sum of those cycle-specific replicate variances. This
    avoids the arbitrary cross-cycle covariance introduced by pairing
    replicate numbers from independent cycle files.
    """
    cycles, bootstrap_cols, numeric_weights = _validate_pooling_inputs(
        merged_data, variable_col, weight_col, cycle_col
    )
    if expected_cycles is not None:
        expected = {str(cycle) for cycle in expected_cycles}
        observed = set(cycles)
        if observed != expected:
            missing = sorted(expected - observed)
            unexpected = sorted(observed - expected)
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if unexpected:
                details.append("unexpected: " + ", ".join(unexpected))
            raise ValueError(
                "All selected cycles must contain records after filtering ("
                + "; ".join(details)
                + ")."
            )
    data = merged_data.copy()
    data[[weight_col, *bootstrap_cols]] = numeric_weights

    cycle_count = len(cycles)
    scale = 1.0 / cycle_count
    grouped = data.groupby(variable_col, dropna=True)
    base_numerators = grouped[weight_col].sum() * scale
    total_weight_base = data[weight_col].sum() * scale
    base_prevalence = base_numerators / total_weight_base * 100
    unweighted_numerators = grouped.size().reindex(base_prevalence.index)
    unweighted_denominator = data[variable_col].notna().sum()

    variance = pd.Series(0.0, index=base_prevalence.index)
    for cycle in cycles:
        cycle_mask = data[cycle_col].astype(str).eq(cycle)
        cycle_data = data.loc[cycle_mask]

        cycle_main_denominator = cycle_data[weight_col].sum() * scale
        other_denominator = total_weight_base - cycle_main_denominator
        replicate_denominators = (
            cycle_data[bootstrap_cols].sum(axis=0) * scale + other_denominator
        )
        if (replicate_denominators <= 0).any():
            raise ValueError(
                f"Cycle {cycle} has a non-positive pooled bootstrap denominator."
            )

        cycle_main_numerators = (
            cycle_data.groupby(variable_col, dropna=True)[weight_col]
            .sum()
            .reindex(base_prevalence.index, fill_value=0.0)
            * scale
        )
        other_numerators = base_numerators - cycle_main_numerators
        cycle_bootstrap_numerators = (
            cycle_data.groupby(variable_col, dropna=True)[bootstrap_cols]
            .sum()
            .reindex(base_prevalence.index, fill_value=0.0)
            * scale
        )
        replicate_prevalence = (
            cycle_bootstrap_numerators.add(other_numerators, axis=0)
            .div(replicate_denominators, axis=1)
            * 100
        )
        cycle_variance = (
            replicate_prevalence.sub(base_prevalence, axis=0).pow(2).mean(axis=1)
        )
        variance = variance.add(cycle_variance, fill_value=0.0)

    std_dev = np.sqrt(variance)
    ci_lower = base_prevalence - CONFIDENCE_Z * std_dev
    ci_upper = base_prevalence + CONFIDENCE_Z * std_dev
    cv = std_dev.div(base_prevalence).mul(100)

    result_df = pd.DataFrame(
        {
            "Value": base_prevalence.index,
            "Prevalence": base_prevalence.values,
            "Unweighted Numerator": unweighted_numerators.values,
            "Unweighted Denominator": unweighted_denominator,
            "Weighted Population": base_numerators.values,
            "Variance": variance.values,
            "Standard Deviation": std_dev.values,
            "CI Lower": ci_lower.values,
            "CI Upper": ci_upper.values,
            "CV (%)": cv.values,
            "Error": CONFIDENCE_Z * std_dev.values,
            "Pooled Cycles": ", ".join(cycles),
            "Cycle Count": cycle_count,
        }
    ).reset_index(drop=True)

    if str(standards_cycle) in QUALITY_FLAG_CYCLES:
        result_df = apply_cchs_quality_flags(result_df)

    return result_df


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
    bootstrap_cols = _bootstrap_columns(merged_data)
    
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
    ci_lower = base_prevalence - CONFIDENCE_Z * std_dev
    ci_upper = base_prevalence + CONFIDENCE_Z * std_dev
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
        'Error': CONFIDENCE_Z * std_dev.values  # for error bars in plots
    }).reset_index(drop=True)

    if str(standards_cycle) in QUALITY_FLAG_CYCLES:
        result_df = apply_cchs_quality_flags(result_df)

    return result_df
