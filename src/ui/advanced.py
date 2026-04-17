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

import altair as alt
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

ANALYTICS_PALETTE = {
    "primary": "#0F766E",
    "accent": "#F59E0B",
    "accent_soft": "#FDE68A",
    "danger": "#B91C1C",
    "danger_soft": "#FCA5A5",
    "neutral": "#475569",
    "muted": "#CBD5E1",
}


def _value_label(value) -> str:
    return str(int(value)) if isinstance(value, (np.integer, int, float)) and float(value).is_integer() else str(value)


def _format_pct(value) -> str:
    return "—" if pd.isna(value) else f"{value:.1f}%"


def _format_pp(value) -> str:
    return "—" if pd.isna(value) else f"{value:+.1f} pp"


def _format_ratio(value) -> str:
    return "—" if pd.isna(value) else f"{value:.2f}x"


def _render_interpretation(title: str, summary: str, how_to_read: str) -> None:
    st.markdown(f"**{title}** {summary}")
    with st.expander("How to read this", expanded=False):
        st.caption(how_to_read)


def _render_metric_row(items: list[tuple[str, str, str]]) -> None:
    if not items:
        return
    cols = st.columns(len(items))
    for col, (label, value, help_text) in zip(cols, items):
        col.metric(label, value, help=help_text)


def _chart_theme() -> dict:
    return {
        "config": {
            "view": {"stroke": None},
            "axis": {
                "labelColor": ANALYTICS_PALETTE["neutral"],
                "titleColor": ANALYTICS_PALETTE["neutral"],
                "gridColor": "#E2E8F0",
                "tickColor": "#CBD5E1",
                "domainColor": "#CBD5E1",
            },
            "legend": {
                "labelColor": ANALYTICS_PALETTE["neutral"],
                "titleColor": ANALYTICS_PALETTE["neutral"],
            },
            "title": {"color": ANALYTICS_PALETTE["neutral"], "fontSize": 15},
        }
    }


def _prepare_stratified_chart_data(stratified: pd.DataFrame, value) -> pd.DataFrame:
    chart_data = stratified[stratified["Value"] == value].copy()
    chart_data = chart_data.dropna(subset=["Prevalence", "CI Lower", "CI Upper"])
    if chart_data.empty:
        return chart_data
    chart_data["Stratum Label"] = chart_data["Stratum Label"].fillna(chart_data["Stratum"].map(_value_label))
    chart_data["Quality Label"] = chart_data["Quality"].map(
        {"ok": "Release", "caution": "Use with caution", "suppress": "Suppressed"}
    )
    return chart_data.sort_values("Prevalence", ascending=False)


def _render_stratified_chart(stratified: pd.DataFrame) -> None:
    values = sorted(stratified["Value"].dropna().unique().tolist())
    if not values:
        return
    selected_value = st.selectbox(
        "Visualize outcome value",
        options=values,
        format_func=_value_label,
        key="adv_stratified_value_chart",
    )
    chart_data = _prepare_stratified_chart_data(stratified, selected_value)
    if chart_data.empty:
        st.info("No chartable rows for that outcome value after suppression.")
        return
    top_row = chart_data.iloc[0]
    bottom_row = chart_data.iloc[-1]
    released = int(chart_data["Quality"].eq("ok").sum())
    _render_interpretation(
        "What this shows:",
        (
            f"For outcome value `{_value_label(selected_value)}`, `{top_row['Stratum Label']}` has the highest "
            f"estimated prevalence at {_format_pct(top_row['Prevalence'])}, while "
            f"`{bottom_row['Stratum Label']}` is lowest at {_format_pct(bottom_row['Prevalence'])}."
        ),
        (
            "Longer bars mean higher prevalence. The horizontal line on each bar is the 95% confidence interval. "
            "Green estimates are safer to use, amber should be interpreted carefully, and red estimates are suppressed."
        ),
    )
    _render_metric_row(
        [
            ("Highest stratum", str(top_row["Stratum Label"]), "Stratum with the largest prevalence for the selected value."),
            ("Lowest stratum", str(bottom_row["Stratum Label"]), "Stratum with the smallest prevalence for the selected value."),
            ("Released estimates", f"{released}/{len(chart_data)}", "How many visible estimates are marked as release-quality."),
        ]
    )

    base = alt.Chart(chart_data).encode(
        y=alt.Y("Stratum Label:N", sort="-x", title=None),
        tooltip=[
            alt.Tooltip("Stratum Label:N", title="Stratum"),
            alt.Tooltip("Prevalence:Q", title="Prevalence (%)", format=".2f"),
            alt.Tooltip("CI Lower:Q", title="CI lower", format=".2f"),
            alt.Tooltip("CI Upper:Q", title="CI upper", format=".2f"),
            alt.Tooltip("n:Q", title="n"),
            alt.Tooltip("Quality Label:N", title="Quality"),
        ],
    )
    error_bars = base.mark_rule(strokeWidth=3, opacity=0.7).encode(
        x=alt.X("CI Lower:Q", title="Prevalence (%)"),
        x2="CI Upper:Q",
        color=alt.Color(
            "Quality Label:N",
            scale=alt.Scale(
                domain=["Release", "Use with caution", "Suppressed"],
                range=[
                    ANALYTICS_PALETTE["primary"],
                    ANALYTICS_PALETTE["accent"],
                    ANALYTICS_PALETTE["danger"],
                ],
            ),
            legend=alt.Legend(title="Estimate quality"),
        ),
    )
    bars = base.mark_bar(cornerRadiusEnd=5, height=22).encode(
        x=alt.X("Prevalence:Q", title="Prevalence (%)"),
        color=alt.Color(
            "Quality Label:N",
            scale=alt.Scale(
                domain=["Release", "Use with caution", "Suppressed"],
                range=[
                    ANALYTICS_PALETTE["primary"],
                    ANALYTICS_PALETTE["accent"],
                    ANALYTICS_PALETTE["danger"],
                ],
            ),
            legend=None,
        ),
    )
    labels = base.mark_text(align="left", baseline="middle", dx=6, color=ANALYTICS_PALETTE["neutral"]).encode(
        x="Prevalence:Q",
        text=alt.Text("Prevalence:Q", format=".1f"),
    )
    st.altair_chart(
        (error_bars + bars + labels).properties(height=max(220, 42 * len(chart_data))).configure(**_chart_theme()["config"]),
        use_container_width=True,
    )


def _prepare_contrast_chart_data(table: pd.DataFrame) -> pd.DataFrame:
    chart_data = table.copy()
    if chart_data.empty:
        return chart_data
    chart_data["Value Label"] = chart_data["Value"].map(_value_label)
    chart_data["Significance"] = np.where(
        chart_data["p-value"].fillna(1) < 0.05, "p < 0.05", "Not significant"
    )
    return chart_data


def _render_contrast_charts(table: pd.DataFrame) -> None:
    chart_data = _prepare_contrast_chart_data(table)
    if chart_data.empty:
        return
    largest_gap = chart_data.iloc[chart_data["Difference (pp)"].abs().idxmax()]
    significant = int(chart_data["p-value"].fillna(1).lt(0.05).sum())
    direction = (
        f"{largest_gap['Group A']} higher"
        if largest_gap["Difference (pp)"] > 0
        else f"{largest_gap['Group B']} higher"
    )
    _render_interpretation(
        "What this shows:",
        (
            f"The largest separation is for outcome value `{_value_label(largest_gap['Value'])}`: "
            f"{direction} by {_format_pp(largest_gap['Difference (pp)'])}."
        ),
        (
            "The left chart compares the two groups directly for each outcome value. "
            "The right chart shows the gap between them: bars to the right mean Group A is higher, "
            "bars to the left mean Group B is higher. A p-value below 0.05 suggests the difference is unlikely to be random."
        ),
    )
    _render_metric_row(
        [
            ("Largest gap", _format_pp(largest_gap["Difference (pp)"]), "Biggest prevalence difference between the two selected groups."),
            ("Most different value", _value_label(largest_gap["Value"]), "Outcome value with the strongest separation."),
            ("Statistically clear", f"{significant}/{len(chart_data)}", "Count of outcome values with p-value below 0.05."),
        ]
    )

    left, right = st.columns((1.4, 1))
    with left:
        point_data = chart_data.melt(
            id_vars=["Value Label"],
            value_vars=["Prevalence A (%)", "Prevalence B (%)"],
            var_name="Group",
            value_name="Prevalence",
        )
        point_data["Group"] = point_data["Group"].map(
            {"Prevalence A (%)": chart_data["Group A"].iloc[0], "Prevalence B (%)": chart_data["Group B"].iloc[0]}
        )
        connector = alt.Chart(chart_data).mark_rule(color=ANALYTICS_PALETTE["muted"], strokeWidth=2).encode(
            y=alt.Y("Value Label:N", title=None),
            x=alt.X("Prevalence A (%):Q", title="Prevalence (%)"),
            x2="Prevalence B (%):Q",
            tooltip=[
                alt.Tooltip("Value Label:N", title="Value"),
                alt.Tooltip("Prevalence A (%):Q", title=chart_data["Group A"].iloc[0], format=".2f"),
                alt.Tooltip("Prevalence B (%):Q", title=chart_data["Group B"].iloc[0], format=".2f"),
                alt.Tooltip("Difference (pp):Q", title="Difference (pp)", format="+.2f"),
            ],
        )
        points = alt.Chart(point_data).mark_circle(size=130, opacity=0.95).encode(
            y=alt.Y("Value Label:N", title=None),
            x=alt.X("Prevalence:Q", title="Prevalence (%)"),
            color=alt.Color(
                "Group:N",
                scale=alt.Scale(range=[ANALYTICS_PALETTE["primary"], ANALYTICS_PALETTE["accent"]]),
            ),
            tooltip=[
                alt.Tooltip("Value Label:N", title="Value"),
                alt.Tooltip("Group:N", title="Group"),
                alt.Tooltip("Prevalence:Q", title="Prevalence (%)", format=".2f"),
            ],
        )
        st.altair_chart(
            (connector + points).properties(title="Group comparison", height=max(180, 60 * len(chart_data))).configure(**_chart_theme()["config"]),
            use_container_width=True,
        )
    with right:
        diff_chart = alt.Chart(chart_data).mark_bar(cornerRadius=6).encode(
            y=alt.Y("Value Label:N", title=None, sort="-x"),
            x=alt.X("Difference (pp):Q", title="Difference (pp)"),
            color=alt.Color(
                "Significance:N",
                scale=alt.Scale(
                    domain=["p < 0.05", "Not significant"],
                    range=[ANALYTICS_PALETTE["primary"], ANALYTICS_PALETTE["muted"]],
                ),
                legend=alt.Legend(title="Signal"),
            ),
            tooltip=[
                alt.Tooltip("Value Label:N", title="Value"),
                alt.Tooltip("Difference (pp):Q", title="Difference (pp)", format="+.2f"),
                alt.Tooltip("p-value:Q", format=".4f"),
                alt.Tooltip("Prevalence Ratio:Q", format=".2f"),
                alt.Tooltip("Odds Ratio:Q", format=".2f"),
            ],
        ).properties(title="Difference by outcome value", height=max(180, 60 * len(chart_data)))
        st.altair_chart(diff_chart.configure(**_chart_theme()["config"]), use_container_width=True)


def _prepare_equity_chart_data(summary: pd.DataFrame) -> pd.DataFrame:
    chart_data = summary.copy()
    if chart_data.empty:
        return chart_data
    chart_data["Value Label"] = chart_data["Value"].map(_value_label)
    chart_data["Direction"] = np.where(
        chart_data["Absolute gap (pp)"].fillna(0) >= 0,
        "Higher in disadvantaged group",
        "Higher in advantaged group",
    )
    return chart_data


def _render_equity_charts(summary: pd.DataFrame) -> None:
    chart_data = _prepare_equity_chart_data(summary)
    if chart_data.empty:
        return
    widest_gap = chart_data.iloc[chart_data["Absolute gap (pp)"].abs().idxmax()]
    burden_side = (
        "disadvantaged group"
        if widest_gap["Absolute gap (pp)"] >= 0
        else "advantaged group"
    )
    rii_available = int(chart_data["RII"].notna().sum())
    _render_interpretation(
        "What this shows:",
        (
            f"The strongest equity gap appears for outcome value `{_value_label(widest_gap['Value'])}`. "
            f"The burden is higher in the {burden_side} by {_format_pp(widest_gap['Absolute gap (pp)'])}."
        ),
        (
            "The left chart focuses on the size and direction of the gap between the most advantaged and disadvantaged groups. "
            "Positive values mean the disadvantaged group has a higher prevalence. On the right, RII above 1 means inequality "
            "leans toward the disadvantaged group; values near 1 indicate less relative inequality."
        ),
    )
    _render_metric_row(
        [
            ("Widest gap", _format_pp(widest_gap["Absolute gap (pp)"]), "Largest absolute equity gap across outcome values."),
            ("Highest relative inequality", _format_ratio(chart_data["RII"].max()), "Largest available RII value."),
            ("RII available", f"{rii_available}/{len(chart_data)}", "RII only appears when the stratifier supports ordered inequality metrics."),
        ]
    )

    left, right = st.columns((1.2, 1))
    with left:
        gap_chart = alt.Chart(chart_data).mark_bar(cornerRadius=6).encode(
            y=alt.Y("Value Label:N", title=None, sort="-x"),
            x=alt.X("Absolute gap (pp):Q", title="Absolute gap (pp)"),
            color=alt.Color(
                "Direction:N",
                scale=alt.Scale(
                    domain=["Higher in disadvantaged group", "Higher in advantaged group"],
                    range=[ANALYTICS_PALETTE["danger"], ANALYTICS_PALETTE["primary"]],
                ),
                legend=alt.Legend(title="Gradient"),
            ),
            tooltip=[
                alt.Tooltip("Value Label:N", title="Value"),
                alt.Tooltip("Absolute gap (pp):Q", format="+.2f"),
                alt.Tooltip("Relative ratio:Q", format=".2f"),
                alt.Tooltip("SII (pp):Q", format="+.2f"),
                alt.Tooltip("RII:Q", format=".2f"),
            ],
        ).properties(title="Equity gap", height=max(180, 60 * len(chart_data)))
        st.altair_chart(gap_chart.configure(**_chart_theme()["config"]), use_container_width=True)
    with right:
        rii = chart_data.dropna(subset=["RII"]).copy()
        if rii.empty:
            st.info("RII visual is unavailable for unordered or incomplete stratifiers.")
        else:
            rii_chart = alt.Chart(rii).mark_circle(size=180, opacity=0.9).encode(
                y=alt.Y("Value Label:N", title=None),
                x=alt.X("RII:Q", title="RII"),
                color=alt.condition(
                    alt.datum.RII >= 1,
                    alt.value(ANALYTICS_PALETTE["danger"]),
                    alt.value(ANALYTICS_PALETTE["primary"]),
                ),
                size=alt.Size("Relative ratio:Q", title="Relative ratio"),
                tooltip=[
                    alt.Tooltip("Value Label:N", title="Value"),
                    alt.Tooltip("RII:Q", format=".2f"),
                    alt.Tooltip("Relative ratio:Q", format=".2f"),
                    alt.Tooltip("SII (pp):Q", format="+.2f"),
                ],
            ).properties(title="Relative inequality", height=max(180, 60 * len(rii)))
            rule = alt.Chart(pd.DataFrame({"x": [1]})).mark_rule(
                color=ANALYTICS_PALETTE["muted"], strokeDash=[6, 4]
            ).encode(x="x:Q")
            st.altair_chart((rule + rii_chart).configure(**_chart_theme()["config"]), use_container_width=True)


def _prepare_benchmark_long(table: pd.DataFrame) -> pd.DataFrame:
    chart_data = table.copy()
    if chart_data.empty:
        return chart_data
    # benchmark tables carry DataFrames in .attrs for the full local/comparator
    # summaries; clear them before melt() so pandas doesn't try to compare
    # DataFrame attrs during concat finalization.
    chart_data.attrs = {}
    prevalence_cols = [col for col in chart_data.columns if col.endswith("Prevalence (%)")]
    if len(prevalence_cols) < 2:
        return pd.DataFrame()
    chart_data["Value Label"] = chart_data["Value"].map(_value_label)
    long = chart_data.melt(
        id_vars=["Value Label", "Difference (pp)", "p-value"],
        value_vars=prevalence_cols[:2],
        var_name="Series",
        value_name="Prevalence",
    )
    long["Series"] = long["Series"].str.replace(" Prevalence (%)", "", regex=False)
    return long


def _render_benchmark_comparison_chart(table: pd.DataFrame, title: str) -> None:
    long = _prepare_benchmark_long(table)
    if long.empty:
        return
    chart_data = table.copy()
    strongest = chart_data.iloc[chart_data["Difference (pp)"].abs().idxmax()]
    local_col, comp_col = [col for col in chart_data.columns if col.endswith("Prevalence (%)")][:2]
    local_name = local_col.replace(" Prevalence (%)", "")
    comp_name = comp_col.replace(" Prevalence (%)", "")
    direction = local_name if strongest["Difference (pp)"] > 0 else comp_name
    _render_interpretation(
        "What this shows:",
        (
            f"The biggest benchmark difference is for outcome value `{_value_label(strongest['Value'])}`. "
            f"{direction} is higher by {_format_pp(strongest['Difference (pp)'])}."
        ),
        (
            "Each pair of bars compares local prevalence with the selected benchmark. "
            "Look for the widest separation between the two bars to find the clearest difference."
        ),
    )
    _render_metric_row(
        [
            ("Largest benchmark gap", _format_pp(strongest["Difference (pp)"]), "Biggest local-vs-benchmark difference."),
            ("Local above benchmark", str(int(chart_data["Difference (pp)"].gt(0).sum())), "Number of outcome values where the local estimate is higher."),
            ("Benchmark above local", str(int(chart_data["Difference (pp)"].lt(0).sum())), "Number of outcome values where the benchmark estimate is higher."),
        ]
    )
    chart = alt.Chart(long).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
        x=alt.X("Value Label:N", title="Outcome value"),
        xOffset="Series:N",
        y=alt.Y("Prevalence:Q", title="Prevalence (%)"),
        color=alt.Color(
            "Series:N",
            scale=alt.Scale(range=[ANALYTICS_PALETTE["primary"], ANALYTICS_PALETTE["accent"]]),
            legend=alt.Legend(title=None),
        ),
        tooltip=[
            alt.Tooltip("Value Label:N", title="Value"),
            alt.Tooltip("Series:N", title="Series"),
            alt.Tooltip("Prevalence:Q", format=".2f"),
        ],
    ).properties(title=title, height=max(240, 52 * long["Value Label"].nunique()))
    st.altair_chart(chart.configure(**_chart_theme()["config"]), use_container_width=True)


def _render_league_chart(ranked: pd.DataFrame, local_label: str) -> None:
    chart_data = ranked.copy()
    if chart_data.empty:
        return
    chart_data["Highlight"] = np.where(
        chart_data["PHU"].eq(local_label),
        local_label,
        "Peer PHUs",
    )
    top_row = chart_data.iloc[0]
    local_match = chart_data[chart_data["PHU"].eq(local_label)]
    if not local_match.empty:
        local_row = local_match.iloc[0]
        summary = (
            f"`{local_label}` ranks #{int(local_row['Rank'])} of {len(chart_data)} PHUs with a prevalence of "
            f"{_format_pct(local_row['Prevalence (%)'])}. The current leader is `{top_row['PHU']}` at "
            f"{_format_pct(top_row['Prevalence (%)'])}."
        )
    else:
        summary = (
            f"`{top_row['PHU']}` is currently ranked first at {_format_pct(top_row['Prevalence (%)'])}. "
            f"The chart orders PHUs from highest prevalence to lowest."
        )
    _render_interpretation(
        "What this shows:",
        summary,
        (
            "Bars are ranked from highest to lowest prevalence. If your local PHU is highlighted, "
            "its position shows where it sits relative to peers for the selected outcome value."
        ),
    )
    _render_metric_row(
        [
            ("Top PHU", str(top_row["PHU"]), "Highest prevalence for the selected outcome value."),
            ("Top prevalence", _format_pct(top_row["Prevalence (%)"]), "Estimated prevalence for the top-ranked PHU."),
            ("PHUs compared", str(len(chart_data)), "Number of PHUs included in the league table."),
        ]
    )
    chart = alt.Chart(chart_data).mark_bar(cornerRadiusEnd=5).encode(
        y=alt.Y("PHU:N", sort="-x", title=None),
        x=alt.X("Prevalence (%):Q", title="Prevalence (%)"),
        color=alt.Color(
            "Highlight:N",
            scale=alt.Scale(range=[ANALYTICS_PALETTE["muted"], ANALYTICS_PALETTE["primary"]]),
            legend=alt.Legend(title=None),
        ),
        tooltip=[
            alt.Tooltip("Rank:Q"),
            alt.Tooltip("PHU:N"),
            alt.Tooltip("Prevalence (%):Q", format=".2f"),
            alt.Tooltip("CI Lower:Q", format=".2f"),
            alt.Tooltip("CI Upper:Q", format=".2f"),
        ],
    ).properties(title="League table visual", height=max(320, 24 * len(chart_data)))
    st.altair_chart(chart.configure(**_chart_theme()["config"]), use_container_width=True)


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
    _render_stratified_chart(suppressed)
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

    _render_contrast_charts(table)
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
    _render_equity_charts(summary)
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
        _render_benchmark_comparison_chart(table, "Local vs Ontario")
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
        _render_benchmark_comparison_chart(table, "Local vs selected PHU comparator")
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
        _render_league_chart(ranked, local_label)
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
