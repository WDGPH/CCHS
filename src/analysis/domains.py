"""Helpers for selecting response domains for survey analysis."""

import re
import unicodedata

import pandas as pd
import numpy as np

from config.settings import DEFAULT_WEIGHT_COLUMN
from src.analysis.bootstrap import run_bootstrap_analysis_for_all_values, run_cycle_pooled_analysis
from src.data.harmonizer import prepare_pooled_variable


_NONRESPONSE_PATTERN = re.compile(
    r"(?<!\w)(?:valid skip|skip|not stated|don['’]t know|do not know|"
    r"refusal|not applicable|refused|n/a|na|missing|dk|ns)(?!\w)",
    re.IGNORECASE,
)


def is_nonresponse_label(value):
    """Recognize missing/skip labels without matching inside valid words."""
    if pd.isna(value):
        return True
    return bool(_NONRESPONSE_PATTERN.search(unicodedata.normalize("NFKC", str(value))))


def recalculate_response_domain(
    data, variable, retained_values, original_results, *, pooling=False,
    weight_col=DEFAULT_WEIGHT_COLUMN, standards_cycle=None, expected_cycles=None,
    categories=None, cycle_variable_info=None, crosswalk=None,
):
    """Re-estimate a retained response domain using its actual replicate weights.

    Restrict both main and bootstrap denominators to the same records. All
    uncertainty metrics, sample counts, and release flags are recomputed.
    """
    analysis_column = variable
    if pooling:
        data, analysis_column, _ = prepare_pooled_variable(
            data, variable, categories or {},
            cycle_variable_info=cycle_variable_info, crosswalk=crosswalk,
        )
    domain = data.loc[data[analysis_column].isin(retained_values)].copy()
    if domain.empty:
        raise ValueError("No records remain in the selected response domain.")
    if pooling:
        result = run_cycle_pooled_analysis(
            domain, analysis_column, weight_col,
            standards_cycle=standards_cycle, expected_cycles=expected_cycles,
        )
    else:
        weight_columns = [weight_col, *[col for col in domain if col.startswith("BSW")]]
        weights = domain[weight_columns].apply(pd.to_numeric, errors="coerce")
        if (not np.isfinite(weights.to_numpy()).all()
                or (weights < 0).any().any() or (weights.sum() <= 0).any()):
            raise ValueError("The selected response domain has invalid or non-positive weight totals.")
        domain[weight_columns] = weights
        result = run_bootstrap_analysis_for_all_values(
            domain, analysis_column, weight_col, standards_cycle=standards_cycle,
        )

    original = original_results.set_index("Value")
    result["Original Prevalence"] = result["Value"].map(original["Prevalence"])
    if "Label" in original:
        result["Label"] = result["Value"].map(original["Label"])
    if "Variable" in original:
        result["Variable"] = original["Variable"].iloc[0]
    return result
