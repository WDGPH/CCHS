"""Streamlit UI for Tier 1 advanced analytics.

Exposes three panels that all share a single variable picker:

* **Stratified prevalence** — per-level estimates with CI/CV/n and a quality flag.
* **Group contrast** — one group vs another, with correct bootstrap SE on the
  difference (not CI-overlap), plus prevalence ratio and odds ratio.
* **Equity** — absolute gap, relative ratio, SII, RII on an ordered stratifier.
* **Benchmark** — PHU-vs-Ontario or PHU-vs-PHU contrast, plus a league table.

The module is intentionally self-contained so it can be dropped into main.py's
tab list with a single call to ``render_advanced_analytics_tab``.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st

from config.settings import (
    CV_ACCEPTABLE,
    CV_USE_CAUTION,
    DEFAULT_WEIGHT_COLUMN,
    KNOWN_HEALTH_REGION_LABELS,
    MIN_UNWEIGHTED_N,
    STRATIFIER_REGISTRY,
)
from src.analysis.benchmark import benchmark_against, rank_phu_on_outcome
from src.analysis.difference import contrast_all_values
from src.analysis.equity import equity_summary
from src.analysis.stratified import apply_suppression, run_bootstrap_stratified


QUALITY_BADGE = {
    "ok": ("✅", "Release as-is"),
    "caution": ("⚠️", f"CV {CV_ACCEPTABLE:.1f}–{CV_USE_CAUTION:.1f}% — use with caution"),
    "suppress": (
        "🚫",
        f"Suppress (n<{MIN_UNWEIGHTED_N} or CV>{CV_USE_CAUTION:.1f}%)",
    ),
}


def _available_stratifiers(df: pd.DataFrame) -> list[str]:
    """Which registered stratifiers actually have data in this frame?"""
    return [col for col in STRATIFIER_REGISTRY if col in df.columns]


def _stratum_label(code, stratifier_col: str, df: pd.DataFrame) -> str:
    """Prefer the harmonized *_label column; fall back to the registry."""
    label_col = f"{stratifier_col}_label"
    if label_col in df.columns:
        lookup = (
            df[[stratifier_col, label_col]]
            .dropna()
            .drop_duplicates()
            .set_index(stratifier_col)[label_col]
            .to_dict()
        )
        if code in lookup:
            return str(lookup[code])
    registry = STRATIFIER_REGISTRY.get(stratifier_col, {})
    value_labels = registry.get("value_labels") or {}
    try:
        return str(value_labels.get(int(code), code))
    except (TypeError, ValueError):
        return str(code)


def _render_stratified_panel(
    merged_data: pd.DataFrame,
    variable: str,
    stratifier_col: str,
    weight_col: str,
    variable_description: Optional[str] = None,
) -> pd.DataFrame:
    info = STRATIFIER_REGISTRY[stratifier_col]
    st.markdown(
        f"**Outcome:** `{variable}`"
        + (f" — {variable_description}" if variable_description else "")
    )
    st.markdown(f"**Stratifier:** {info['label']} (`{stratifier_col}`)")

    label_col = f"{stratifier_col}_label" if f"{stratifier_col}_label" in merged_data.columns else None
    with st.spinner("Computing stratified bootstrap..."):
        strat = run_bootstrap_stratified(
            merged_data,
            variable,
            stratifier_col,
            weight_col=weight_col,
            stratifier_label_col=label_col,
        )
    if strat.empty:
        st.warning("No rows after excluding skip / missing codes.")
        return strat

    if "Stratum Label" not in strat.columns:
        strat["Stratum Label"] = strat["Stratum"].apply(
            lambda x: _stratum_label(x, stratifier_col, merged_data)
        )

    suppressed = apply_suppression(strat)
    display = suppressed.copy()
    display["Quality"] = display["Quality"].map(lambda k: f"{QUALITY_BADGE[k][0]} {k}")

    cols = [
        "Stratum",
        "Stratum Label",
        "Value",
        "Prevalence",
        "CI Lower",
        "CI Upper",
        "CV (%)",
        "n",
        "Quality",
    ]
    cols = [c for c in cols if c in display.columns]
    st.dataframe(
        display[cols]
        .style.format(
            {
                "Prevalence": "{:.2f}",
                "CI Lower": "{:.2f}",
                "CI Upper": "{:.2f}",
                "CV (%)": "{:.1f}",
            }
        )
        .background_gradient(subset=["Prevalence"], cmap="viridis"),
        use_container_width=True,
    )
    st.caption(
        "Suppression rule: n < {n_min} or CV > {cv_hi:.1f}% → estimate suppressed. "
        "CV {cv_lo:.1f}–{cv_hi:.1f}% flagged as *caution*.".format(
            n_min=MIN_UNWEIGHTED_N, cv_lo=CV_ACCEPTABLE, cv_hi=CV_USE_CAUTION
        )
    )
    return strat


def _render_contrast_panel(
    merged_data: pd.DataFrame,
    variable: str,
    stratifier_col: str,
    weight_col: str,
) -> None:
    levels = sorted(merged_data[stratifier_col].dropna().unique().tolist())
    excludes = STRATIFIER_REGISTRY[stratifier_col].get("exclude_values") or []
    levels = [lv for lv in levels if lv not in excludes]
    if len(levels) < 2:
        st.info("Need at least two non-skip levels to compute a contrast.")
        return

    label_map = {lv: _stratum_label(lv, stratifier_col, merged_data) for lv in levels}

    col_a, col_b = st.columns(2)
    with col_a:
        group_a = st.selectbox(
            "Group A",
            options=levels,
            format_func=lambda x: f"{label_map[x]} ({x})",
            key=f"contrast_a_{variable}_{stratifier_col}",
        )
    with col_b:
        default_b_idx = 1 if levels[0] == group_a else 0
        group_b = st.selectbox(
            "Group B",
            options=[lv for lv in levels if lv != group_a],
            index=0,
            format_func=lambda x: f"{label_map[x]} ({x})",
            key=f"contrast_b_{variable}_{stratifier_col}",
        )

    with st.spinner("Running bootstrap contrast..."):
        table = contrast_all_values(
            merged_data,
            variable,
            stratifier_col,
            group_a,
            group_b,
            weight_col=weight_col,
            label_a=label_map[group_a],
            label_b=label_map[group_b],
        )
    if table.empty:
        st.warning("No values produced a contrast.")
        return

    st.dataframe(
        table.style.format(
            {
                "Prevalence A (%)": "{:.2f}",
                "Prevalence B (%)": "{:.2f}",
                "Difference (pp)": "{:+.2f}",
                "Prevalence Ratio": "{:.2f}",
                "Odds Ratio": "{:.2f}",
                "z": "{:.2f}",
                "p-value": "{:.4f}",
            },
            na_rep="—",
        ),
        use_container_width=True,
    )
    st.caption(
        "p-values come from a two-sided z-test using the bootstrap SE of the **difference** — "
        "this is the correct test; the older CI-overlap method is overly conservative."
    )


def _render_equity_panel(
    stratified: pd.DataFrame,
    stratifier_col: str,
) -> None:
    info = STRATIFIER_REGISTRY.get(stratifier_col, {})
    if not info.get("ordered"):
        st.info(
            f"Equity gradient metrics (SII/RII) need an *ordered* stratifier. "
            f"`{stratifier_col}` is categorical — only gap and ratio will be computed."
        )
    if stratified is None or stratified.empty:
        st.warning("Run the stratified analysis above first.")
        return
    summary = equity_summary(stratified, stratifier_col)
    if summary.empty:
        st.warning("No equity summary could be produced.")
        return
    st.dataframe(
        summary.style.format(
            {
                "Prev. advantaged (%)": "{:.2f}",
                "Prev. disadvantaged (%)": "{:.2f}",
                "Absolute gap (pp)": "{:+.2f}",
                "Relative ratio": "{:.2f}",
                "SII (pp)": "{:+.2f}",
                "RII": "{:.2f}",
            },
            na_rep="—",
        ),
        use_container_width=True,
    )
    st.caption(
        "SII = disadvantaged-minus-advantaged prevalence from a population-weighted "
        "regression across the whole ordered distribution (positive = burden on "
        "disadvantaged group). RII > 1 means the disadvantaged group has a higher "
        "rate at the extreme of the ordered scale."
    )


def _render_benchmark_panel(
    local_merged: pd.DataFrame,
    province_merged: Optional[pd.DataFrame],
    variable: str,
    weight_col: str,
    local_label: str,
) -> None:
    if province_merged is None:
        st.info(
            "Benchmarking needs an *unfiltered* province-wide merged dataset. "
            "Wire `st.session_state['province_merged']` in the loading path to enable this."
        )
        return

    phu_codes = sorted(KNOWN_HEALTH_REGION_LABELS.keys())
    comparator = st.radio(
        "Compare against",
        options=["Ontario (all PHUs)", "Specific PHU(s)", "League table across all PHUs"],
        horizontal=True,
        key=f"bench_choice_{variable}",
    )
    if comparator == "Ontario (all PHUs)":
        with st.spinner("Computing Ontario benchmark..."):
            table = benchmark_against(
                local_merged, province_merged, variable, comparator="ontario",
                weight_col=weight_col, local_label=local_label,
            )
        st.dataframe(
            table.style.format({c: "{:.2f}" for c in table.columns if "Prevalence" in c or c == "Difference (pp)"}),
            use_container_width=True,
        )
    elif comparator == "Specific PHU(s)":
        selected = st.multiselect(
            "Comparator PHU(s)",
            options=phu_codes,
            format_func=lambda c: f"{KNOWN_HEALTH_REGION_LABELS.get(c, c)} ({c})",
            key=f"bench_phus_{variable}",
        )
        if not selected:
            st.info("Pick at least one PHU.")
            return
        with st.spinner("Computing PHU benchmark..."):
            table = benchmark_against(
                local_merged, province_merged, variable, comparator="phu",
                comparator_health_region_codes=selected, weight_col=weight_col,
                local_label=local_label,
            )
        st.dataframe(table, use_container_width=True)
    else:
        value = st.selectbox(
            "Outcome value to rank on",
            options=sorted(local_merged[variable].dropna().unique().tolist()),
            key=f"bench_value_{variable}",
        )
        with st.spinner("Building league table..."):
            ranked = rank_phu_on_outcome(province_merged, variable, value, phu_codes, weight_col=weight_col)
        if ranked.empty:
            st.warning("No PHUs returned an estimate.")
            return
        st.dataframe(
            ranked.style.format(
                {"Prevalence (%)": "{:.2f}", "CI Lower": "{:.2f}", "CI Upper": "{:.2f}", "CV (%)": "{:.1f}"}
            ),
            use_container_width=True,
        )


def render_advanced_analytics_tab(
    merged_data: pd.DataFrame,
    selected_variables: list[str],
    weight_col: str = DEFAULT_WEIGHT_COLUMN,
    province_merged: Optional[pd.DataFrame] = None,
    local_label: str = "Local PHU",
    variable_descriptions: Optional[dict] = None,
) -> None:
    """Render the full Tier 1 analytics tab. Call from main.py inside ``with tab_advanced:``."""
    if merged_data is None or not selected_variables:
        st.info("Run the base bootstrap analysis first — then pick a variable here.")
        return

    available = _available_stratifiers(merged_data)
    if not available:
        st.error(
            "None of the registered stratifiers are present in the current dataset. "
            "Check that the cycle was harmonized correctly."
        )
        return

    col_var, col_strat = st.columns(2)
    with col_var:
        variable = st.selectbox(
            "Variable to analyze",
            options=selected_variables,
            format_func=lambda v: (
                f"{v} — {variable_descriptions[v]}" if variable_descriptions and v in variable_descriptions else v
            ),
            key="adv_variable",
        )
    with col_strat:
        stratifier = st.selectbox(
            "Stratifier",
            options=available,
            format_func=lambda s: f"{STRATIFIER_REGISTRY[s]['label']} ({s})",
            key="adv_stratifier",
        )

    variable_description = (variable_descriptions or {}).get(variable)

    sub_stratified, sub_contrast, sub_equity, sub_benchmark = st.tabs(
        ["📊 Stratified prevalence", "⚖️ Group contrast", "📈 Equity gradient", "🏙️ Benchmark"]
    )

    with sub_stratified:
        stratified = _render_stratified_panel(
            merged_data, variable, stratifier, weight_col, variable_description
        )
        st.session_state[f"_strat_cache_{variable}_{stratifier}"] = stratified

    with sub_contrast:
        _render_contrast_panel(merged_data, variable, stratifier, weight_col)

    with sub_equity:
        stratified_cached = st.session_state.get(f"_strat_cache_{variable}_{stratifier}")
        _render_equity_panel(stratified_cached, stratifier)

    with sub_benchmark:
        _render_benchmark_panel(
            merged_data, province_merged, variable, weight_col, local_label
        )
