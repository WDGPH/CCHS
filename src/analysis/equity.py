"""Health-equity metrics for stratified CCHS analyses.

Operates on the output of ``run_bootstrap_stratified`` (or anything with the
same columns: ``Stratum``, ``Value``, ``Prevalence``, ``Weighted Population``).

Definitions
-----------
Absolute gap
    Prevalence(most disadvantaged) − Prevalence(most advantaged), in pp.
Relative ratio
    Prevalence(most disadvantaged) / Prevalence(most advantaged).
SII — Slope Index of Inequality
    Coefficient of a (population-weighted) linear regression of prevalence on
    the midpoint of the cumulative population share in each ordered stratum.
    Interpreted as the absolute difference between the very top (rank = 1)
    and the very bottom (rank = 0) of the distribution.
RII — Relative Index of Inequality
    Prevalence predicted at rank 0 divided by the prevalence predicted at
    rank 1 — a unitless ratio summarising relative inequality across the
    full ordered distribution.

For binary or non-ordered stratifiers, only gap/ratio are well-defined, so
``calculate_sii_rii`` will return NaN and a reason in those cases.
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd

from config.settings import STRATIFIER_REGISTRY


def calculate_gap(
    stratified: pd.DataFrame,
    value,
    disadvantaged_stratum=None,
    advantaged_stratum=None,
) -> dict:
    """Absolute gap (pp) and relative ratio between two strata for a given value.

    If the strata aren't specified, picks the stratum with the highest and
    lowest prevalence of ``value`` as a best-effort summary.
    """
    subset = stratified[stratified["Value"] == value]
    if subset.empty:
        return {"gap_pp": np.nan, "ratio": np.nan, "reason": "value not found"}

    if disadvantaged_stratum is None or advantaged_stratum is None:
        sorted_subset = subset.sort_values("Prevalence")
        advantaged_row = sorted_subset.iloc[0]
        disadvantaged_row = sorted_subset.iloc[-1]
    else:
        try:
            advantaged_row = subset[subset["Stratum"] == advantaged_stratum].iloc[0]
            disadvantaged_row = subset[subset["Stratum"] == disadvantaged_stratum].iloc[0]
        except IndexError:
            return {"gap_pp": np.nan, "ratio": np.nan, "reason": "stratum not found"}

    p_adv = float(advantaged_row["Prevalence"])
    p_dis = float(disadvantaged_row["Prevalence"])
    gap = p_dis - p_adv
    ratio = (p_dis / p_adv) if p_adv > 0 else np.nan
    return {
        "gap_pp": gap,
        "ratio": ratio,
        "advantaged_stratum": advantaged_row["Stratum"],
        "disadvantaged_stratum": disadvantaged_row["Stratum"],
        "advantaged_prevalence": p_adv,
        "disadvantaged_prevalence": p_dis,
    }


def _cumulative_midpoints(weights: np.ndarray) -> np.ndarray:
    """Ridit-style midpoints of the cumulative population share per stratum."""
    total = weights.sum()
    if total <= 0:
        return np.full_like(weights, np.nan, dtype=float)
    shares = weights / total
    cum = np.cumsum(shares)
    midpoints = cum - shares / 2.0
    return midpoints


def calculate_sii_rii(
    stratified: pd.DataFrame,
    value,
    stratifier_col: str,
    strata_order: Optional[Sequence] = None,
) -> dict:
    """Slope and Relative Index of Inequality for one outcome value.

    ``strata_order`` should be ordered from *most advantaged* to *least
    advantaged* (or vice versa). If omitted, uses the registry's value_labels
    ordering when available; otherwise sorts the raw stratum codes.
    """
    info = STRATIFIER_REGISTRY.get(stratifier_col, {})
    if not info.get("ordered", False) and strata_order is None:
        return {
            "sii": np.nan,
            "rii": np.nan,
            "reason": "stratifier is not ordered",
        }

    subset = stratified[stratified["Value"] == value].copy()
    if subset.empty or "Weighted Population" not in subset.columns:
        return {"sii": np.nan, "rii": np.nan, "reason": "insufficient data"}

    if strata_order is None:
        value_labels = info.get("value_labels") or {}
        if value_labels:
            strata_order = [k for k in sorted(value_labels.keys()) if k in subset["Stratum"].values]
        else:
            strata_order = sorted(subset["Stratum"].unique().tolist())

    subset = subset.set_index("Stratum").reindex(strata_order).reset_index().dropna(subset=["Prevalence"])
    if len(subset) < 2:
        return {"sii": np.nan, "rii": np.nan, "reason": "need >=2 strata"}

    weights = subset["Weighted Population"].astype(float).to_numpy()
    prevalences = subset["Prevalence"].astype(float).to_numpy()
    midpoints = _cumulative_midpoints(weights)

    if np.any(~np.isfinite(midpoints)):
        return {"sii": np.nan, "rii": np.nan, "reason": "bad midpoints"}

    # Weighted linear regression: minimise sum w_i (y_i - (a + b x_i))^2.
    w = weights / weights.sum()
    x_bar = np.sum(w * midpoints)
    y_bar = np.sum(w * prevalences)
    cov_xy = np.sum(w * (midpoints - x_bar) * (prevalences - y_bar))
    var_x = np.sum(w * (midpoints - x_bar) ** 2)
    if var_x <= 0:
        return {"sii": np.nan, "rii": np.nan, "reason": "degenerate strata"}

    slope = cov_xy / var_x
    intercept = y_bar - slope * x_bar

    pred_at_0 = intercept
    pred_at_1 = intercept + slope
    sii = pred_at_0 - pred_at_1  # prevalence bottom-minus-top (disadvantaged - advantaged)
    rii = (pred_at_0 / pred_at_1) if pred_at_1 > 0 else np.nan

    return {
        "sii": float(sii),
        "rii": float(rii) if np.isfinite(rii) else np.nan,
        "slope": float(slope),
        "intercept": float(intercept),
        "strata_order": list(strata_order),
    }


def equity_summary(
    stratified: pd.DataFrame,
    stratifier_col: str,
    values: Optional[Sequence] = None,
) -> pd.DataFrame:
    """One row per outcome value with gap, ratio, SII, RII for an ordered stratifier."""
    if values is None:
        values = sorted(stratified["Value"].dropna().unique().tolist())
    rows = []
    for v in values:
        gap = calculate_gap(stratified, v)
        sii_rii = calculate_sii_rii(stratified, v, stratifier_col)
        rows.append(
            {
                "Value": v,
                "Advantaged": gap.get("advantaged_stratum"),
                "Disadvantaged": gap.get("disadvantaged_stratum"),
                "Prev. advantaged (%)": gap.get("advantaged_prevalence"),
                "Prev. disadvantaged (%)": gap.get("disadvantaged_prevalence"),
                "Absolute gap (pp)": gap.get("gap_pp"),
                "Relative ratio": gap.get("ratio"),
                "SII (pp)": sii_rii.get("sii"),
                "RII": sii_rii.get("rii"),
            }
        )
    return pd.DataFrame(rows)
