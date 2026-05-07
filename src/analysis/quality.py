"""Helpers for applying CCHS 2022+ data quality reporting standards."""

from __future__ import annotations

import math
from typing import Optional

import pandas as pd


QUALITY_FLAG_CYCLES = {"2022", "2023", "2024"}


def calculate_effective_sample_size(prevalence_pct: float, cv_pct: float) -> Optional[float]:
    """
    Calculate effective sample size for a proportion estimate.

    Formula from the CCHS 2022+ standards:
    (1 - p) / (p * CV^2)
    where p and CV are expressed as proportions, not percentages.
    """
    if pd.isna(prevalence_pct) or pd.isna(cv_pct):
        return None

    p_hat = prevalence_pct / 100.0
    cv = cv_pct / 100.0

    if p_hat <= 0 or p_hat >= 1:
        return None

    if cv < 0:
        return None

    if math.isclose(cv, 0.0):
        return math.inf

    denominator = p_hat * (cv ** 2)
    if math.isclose(denominator, 0.0):
        return math.inf

    return (1 - p_hat) / denominator


def classify_proportion_release(
    prevalence_pct: float,
    cv_pct: float,
    numerator_n: Optional[float],
    denominator_n: Optional[float],
    ci_lower: Optional[float] = None,
    ci_upper: Optional[float] = None,
) -> dict:
    """
    Classify a proportion estimate using the CCHS 2022+ A/E/F rules.
    """
    effective_n = calculate_effective_sample_size(prevalence_pct, cv_pct)

    result = {
        "Release Category": "F",
        "Release Action": "Suppress",
        "Effective Sample Size": effective_n,
        "Release Reason": "Insufficient information to classify",
    }

    if pd.isna(prevalence_pct) or pd.isna(cv_pct):
        result["Release Reason"] = "Missing prevalence or coefficient of variation"
        return result

    if prevalence_pct <= 0 or prevalence_pct >= 100:
        result["Release Reason"] = "Estimates of 0% or 100% should never be released"
        return result

    if ci_lower is not None and ci_upper is not None:
        if not pd.isna(ci_lower) and not pd.isna(ci_upper):
            if math.isclose(ci_lower, ci_upper):
                result["Release Reason"] = "Confidence interval has zero length"
                return result
            if ci_lower < 0 or ci_upper > 100:
                result["Release Reason"] = "Confidence interval bounds are implausible"
                return result

    n1 = float(numerator_n) if numerator_n is not None and not pd.isna(numerator_n) else None
    n2 = float(denominator_n) if denominator_n is not None and not pd.isna(denominator_n) else None

    if n1 is None or n2 is None or effective_n is None:
        result["Release Reason"] = "Missing numerator, denominator, or effective sample size"
        return result

    if n2 < 50:
        result["Release Reason"] = "Denominator unweighted count is below 50"
        return result

    if n1 < 10:
        result["Release Reason"] = "Numerator unweighted count is below 10"
        return result

    if effective_n < 30:
        result["Release Reason"] = "Effective sample size is below 30"
        return result

    if n2 >= 100 and effective_n >= 60:
        result["Release Category"] = "A"
        result["Release Action"] = "Release with no warning"
        result["Release Reason"] = "Denominator >= 100 and effective sample size >= 60"
        return result

    result["Release Category"] = "E"
    result["Release Action"] = "Release with caution warning"
    result["Release Reason"] = "Releasable, but does not meet the no-warning threshold"
    return result


def apply_cchs_quality_flags(result_df: pd.DataFrame) -> pd.DataFrame:
    """Append CCHS 2022+ release-quality fields to a result dataframe."""
    if result_df.empty:
        return result_df

    classified = result_df.apply(
        lambda row: classify_proportion_release(
            prevalence_pct=row.get("Prevalence"),
            cv_pct=row.get("CV (%)"),
            numerator_n=row.get("Unweighted Numerator"),
            denominator_n=row.get("Unweighted Denominator"),
            ci_lower=row.get("CI Lower"),
            ci_upper=row.get("CI Upper"),
        ),
        axis=1,
        result_type="expand",
    )

    return pd.concat([result_df, classified], axis=1)
