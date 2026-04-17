"""Stratified bootstrap analysis for CCHS data.

Computes weighted prevalence of every value of a variable within each level of
a stratifier (e.g. sex, education, urban/rural), with bootstrap confidence
intervals derived from the per-replicate per-stratum totals. Pairs with the
diff/ratio utilities in ``difference.py`` and the equity metrics in
``equity.py``.
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd

from config.settings import (
    BOOTSTRAP_PREFIX,
    CV_ACCEPTABLE,
    CV_USE_CAUTION,
    DEFAULT_WEIGHT_COLUMN,
    MIN_UNWEIGHTED_N,
    STRATIFIER_REGISTRY,
)


def _bootstrap_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith(BOOTSTRAP_PREFIX)]


def _exclude_stratifier_skips(
    df: pd.DataFrame, stratifier_col: str
) -> pd.DataFrame:
    """Drop rows whose stratifier value is a registered skip / refusal code."""
    info = STRATIFIER_REGISTRY.get(stratifier_col)
    if not info:
        return df
    excludes = info.get("exclude_values") or []
    if not excludes:
        return df
    return df[~df[stratifier_col].isin(excludes)]


def _quality_flag(cv: float, n: int) -> str:
    if pd.isna(cv) or pd.isna(n):
        return "suppress"
    if n < MIN_UNWEIGHTED_N:
        return "suppress"
    if cv > CV_USE_CAUTION:
        return "suppress"
    if cv > CV_ACCEPTABLE:
        return "caution"
    return "ok"


def run_bootstrap_stratified(
    merged_data: pd.DataFrame,
    variable_col: str,
    stratifier_col: str,
    weight_col: str = DEFAULT_WEIGHT_COLUMN,
    stratifier_label_col: Optional[str] = None,
) -> pd.DataFrame:
    """Prevalence + bootstrap CIs of ``variable_col`` within each ``stratifier_col`` level.

    Normalisation is *within stratum*: the denominator for a stratum is the
    sum of the (base or replicate) weights over that stratum only. This makes
    each row a conditional prevalence P(variable = value | stratum).

    Returns one row per (Stratum, Value) with: Prevalence, CI Lower/Upper, CV,
    Variance, Weighted Population, unweighted n, and a Quality flag using
    CCHS release rules (n >= 30, CV <= 33.3).
    """
    if variable_col not in merged_data.columns:
        raise KeyError(f"variable_col '{variable_col}' not in data")
    if stratifier_col not in merged_data.columns:
        raise KeyError(f"stratifier_col '{stratifier_col}' not in data")

    df = _exclude_stratifier_skips(merged_data, stratifier_col)
    df = df.dropna(subset=[variable_col, stratifier_col])
    if df.empty:
        return pd.DataFrame()

    # Categorical (e.g. AgeGroup from pd.cut) breaks arithmetic on the
    # resulting multi-index — cast to object for safe groupby/align.
    if isinstance(df[stratifier_col].dtype, pd.CategoricalDtype):
        df = df.assign(**{stratifier_col: df[stratifier_col].astype(object)})

    boot_cols = _bootstrap_columns(df)
    if not boot_cols:
        raise ValueError(
            "No bootstrap weight columns (BSW*) found — did you merge bootstrap weights?"
        )

    # Totals per stratum — base and each replicate.
    stratum_total_base = df.groupby(stratifier_col)[weight_col].sum()
    stratum_totals_boot = df.groupby(stratifier_col)[boot_cols].sum()

    # Numerators: per (stratum, value), sum of weights.
    numer_base = df.groupby([stratifier_col, variable_col])[weight_col].sum()
    numer_boot = df.groupby([stratifier_col, variable_col])[boot_cols].sum()

    # Unweighted n per cell (respondent count).
    n_unw = df.groupby([stratifier_col, variable_col]).size().rename("n")

    # Align stratum totals to each (stratum, value) row to avoid any Index-
    # arithmetic foot-guns (e.g. categorical indexes).
    strata_level = numer_base.index.get_level_values(0)
    base_denom = pd.Series(
        stratum_total_base.reindex(strata_level).to_numpy(),
        index=numer_base.index,
        dtype="float64",
    )
    base_prev = (numer_base / base_denom) * 100

    boot_strata = numer_boot.index.get_level_values(0)
    total_by_row = stratum_totals_boot.reindex(boot_strata)
    total_by_row.index = numer_boot.index
    replicate_prev = numer_boot.div(total_by_row) * 100

    # Variance across replicates is the mean squared deviation from base.
    variance = ((replicate_prev.sub(base_prev, axis=0)) ** 2).mean(axis=1)
    std_dev = np.sqrt(variance)
    ci_lower = base_prev - 1.96 * std_dev
    ci_upper = base_prev + 1.96 * std_dev
    cv = (std_dev / base_prev) * 100

    result = pd.DataFrame(
        {
            "Stratum": base_prev.index.get_level_values(0),
            "Value": base_prev.index.get_level_values(1),
            "Prevalence": base_prev.values,
            "Weighted Population": numer_base.values,
            "Variance": variance.values,
            "Standard Deviation": std_dev.values,
            "CI Lower": ci_lower.values,
            "CI Upper": ci_upper.values,
            "CV (%)": cv.values,
            "Error": 1.96 * std_dev.values,
            "n": n_unw.reindex(base_prev.index).values,
        }
    ).reset_index(drop=True)

    result["Quality"] = [
        _quality_flag(cv_, n_) for cv_, n_ in zip(result["CV (%)"], result["n"])
    ]

    if stratifier_label_col and stratifier_label_col in df.columns:
        label_lookup = (
            df[[stratifier_col, stratifier_label_col]]
            .dropna()
            .drop_duplicates()
            .set_index(stratifier_col)[stratifier_label_col]
            .to_dict()
        )
        result["Stratum Label"] = result["Stratum"].map(label_lookup)
    else:
        info = STRATIFIER_REGISTRY.get(stratifier_col, {})
        value_labels = info.get("value_labels") or {}
        if value_labels:
            result["Stratum Label"] = result["Stratum"].map(value_labels)

    return result


def apply_suppression(
    results: pd.DataFrame,
    value_columns: Sequence[str] = (
        "Prevalence",
        "CI Lower",
        "CI Upper",
        "Variance",
        "Standard Deviation",
    ),
) -> pd.DataFrame:
    """Blank out numeric estimates for rows flagged ``Quality == 'suppress'``."""
    if "Quality" not in results.columns:
        return results
    suppressed = results.copy()
    mask = suppressed["Quality"].eq("suppress")
    for col in value_columns:
        if col in suppressed.columns:
            suppressed.loc[mask, col] = np.nan
    return suppressed
