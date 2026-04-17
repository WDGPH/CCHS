"""Benchmarking analyses: local PHU versus Ontario or another PHU.

Uses ``contrast_two_frames`` under the hood so the difference SE uses the
shared bootstrap replicates — the correct way to get inference on the
difference rather than on each arm in isolation.
"""

from __future__ import annotations

from typing import Iterable, Optional

import numpy as np
import pandas as pd

from config.settings import DEFAULT_WEIGHT_COLUMN, KNOWN_HEALTH_REGION_LABELS
from src.analysis.bootstrap import run_bootstrap_analysis_for_all_values
from src.analysis.difference import contrast_two_frames


def _filter_by_health_regions(
    merged: pd.DataFrame, health_region_codes: Optional[Iterable[int]]
) -> pd.DataFrame:
    if "GEODVHR4" not in merged.columns:
        raise KeyError("GEODVHR4 column not found; cannot apply health-region filter")
    if health_region_codes is None:
        return merged  # Ontario = everything
    codes = {int(c) for c in health_region_codes}
    values = pd.to_numeric(merged["GEODVHR4"], errors="coerce").astype("Int64")
    return merged[values.isin(codes)]


def benchmark_against(
    local_data: pd.DataFrame,
    full_province_data: pd.DataFrame,
    variable_col: str,
    comparator: str = "ontario",
    comparator_health_region_codes: Optional[Iterable[int]] = None,
    weight_col: str = DEFAULT_WEIGHT_COLUMN,
    local_label: str = "Local",
) -> pd.DataFrame:
    """Compare prevalence of every value of ``variable_col`` locally vs. a comparator.

    ``local_data`` is already scoped to the PHU of interest. ``full_province_data``
    is the full (unfiltered) merged data — used as the Ontario baseline, or
    subset to ``comparator_health_region_codes`` when benchmarking against
    another PHU.

    Returns a table with prevalence for both scopes, the difference, 95% CI of
    the difference, and a two-sided p-value, one row per outcome value.
    """
    if comparator == "ontario":
        comparator_df = full_province_data
        comp_label = "Ontario"
    elif comparator == "phu":
        if not comparator_health_region_codes:
            raise ValueError("comparator='phu' requires comparator_health_region_codes")
        comparator_df = _filter_by_health_regions(full_province_data, comparator_health_region_codes)
        codes = sorted({int(c) for c in comparator_health_region_codes})
        named = [KNOWN_HEALTH_REGION_LABELS.get(c, f"HR {c}") for c in codes]
        comp_label = " / ".join(named) or "Comparator"
    else:
        raise ValueError(f"unknown comparator '{comparator}'")

    # Base prevalence tables for a quick sanity pane.
    local_results = run_bootstrap_analysis_for_all_values(local_data, variable_col, weight_col)
    comp_results = run_bootstrap_analysis_for_all_values(comparator_df, variable_col, weight_col)

    # One contrast per value.
    values = sorted(local_data[variable_col].dropna().unique().tolist())
    rows = []
    for v in values:
        try:
            c = contrast_two_frames(
                local_data,
                comparator_df,
                variable_col,
                v,
                weight_col=weight_col,
                label_a=local_label,
                label_b=comp_label,
            )
        except ValueError:
            continue
        rows.append(
            {
                "Value": v,
                f"{local_label} Prevalence (%)": c.prev_a,
                f"{comp_label} Prevalence (%)": c.prev_b,
                "Difference (pp)": c.difference,
                "Difference 95% CI": f"({c.ci_difference[0]:.2f}, {c.ci_difference[1]:.2f})",
                "z": c.z_stat,
                "p-value": c.p_value,
                f"n {local_label}": c.n_a,
                f"n {comp_label}": c.n_b,
            }
        )

    table = pd.DataFrame(rows)
    table.attrs["local_full"] = local_results
    table.attrs["comparator_full"] = comp_results
    return table


def rank_phu_on_outcome(
    full_province_data: pd.DataFrame,
    variable_col: str,
    value,
    health_region_codes: Iterable[int],
    weight_col: str = DEFAULT_WEIGHT_COLUMN,
) -> pd.DataFrame:
    """Rank multiple PHUs on a single (variable, value) — for a 'league table' view.

    Useful when an analyst wants to know where WDG sits relative to peer PHUs on
    a specific outcome. Each PHU gets its own bootstrap prevalence + CI.
    """
    rows = []
    for code in health_region_codes:
        subset = _filter_by_health_regions(full_province_data, [code])
        if subset.empty:
            continue
        table = run_bootstrap_analysis_for_all_values(subset, variable_col, weight_col)
        match = table[table["Value"] == value]
        if match.empty:
            continue
        row = match.iloc[0]
        rows.append(
            {
                "PHU code": int(code),
                "PHU": KNOWN_HEALTH_REGION_LABELS.get(int(code), f"HR {code}"),
                "Prevalence (%)": float(row["Prevalence"]),
                "CI Lower": float(row["CI Lower"]),
                "CI Upper": float(row["CI Upper"]),
                "CV (%)": float(row["CV (%)"]),
                "n": int(len(subset)),
            }
        )

    if not rows:
        return pd.DataFrame()
    ranked = pd.DataFrame(rows).sort_values("Prevalence (%)", ascending=False).reset_index(drop=True)
    ranked.insert(0, "Rank", np.arange(1, len(ranked) + 1))
    return ranked
