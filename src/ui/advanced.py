"""Streamlit UI for Tier 1 advanced analytics.

Exposes four question-led analysis paths that share one variable picker:

* **Stratified prevalence** — per-level estimates with CI/CV/n and a quality flag.
* **Group contrast** — one group vs another, with correct bootstrap SE on the
  difference (not CI-overlap), plus prevalence ratio and odds ratio.
* **Equity** — absolute gap, relative ratio, SII, RII on an ordered stratifier.
* **Benchmark** — PHU-vs-Ontario or PHU-vs-PHU contrast, plus a league table.

The module is intentionally self-contained so it can be dropped into main.py's
tab list with a single call to ``render_advanced_analytics_tab``.
"""

from __future__ import annotations

from html import escape
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
from src.analysis.equity import calculate_gap, calculate_sii_rii, equity_summary
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
    # Okabe-Ito-inspired colours: distinguishable for common colour-vision
    # deficiencies. Every use of colour is also paired with a text label.
    "primary": "#0072B2",
    "accent": "#E69F00",
    "accent_soft": "#F6E5B5",
    "danger": "#A51C30",
    "danger_soft": "#F4CDD4",
    "neutral": "#334155",
    "muted": "#94A3B8",
}

ANALYSIS_PATHS = {
    "Describe": {
        "icon": "01",
        "title": "Describe population patterns",
        "question": "How does prevalence vary across population groups?",
        "method": "Weighted prevalence · 95% confidence intervals · release quality",
    },
    "Compare": {
        "icon": "02",
        "title": "Compare two groups",
        "question": "How large is the difference between two selected groups?",
        "method": "Absolute difference · prevalence ratio · bootstrap inference",
    },
    "Equity": {
        "icon": "03",
        "title": "Assess an equity gradient",
        "question": "Is burden distributed unequally across an ordered stratifier?",
        "method": "Absolute gap · relative ratio · SII · RII",
    },
    "Benchmark": {
        "icon": "04",
        "title": "Benchmark place",
        "question": "How does the local estimate compare with Ontario or peer PHUs?",
        "method": "Local comparison · bootstrap difference · PHU ranking",
    },
}


def _inject_advanced_styles() -> None:
    """Small, scoped design layer for the analytics workspace."""
    st.markdown(
        """
        <style>
        .adv-hero {
            background:
                radial-gradient(circle at 92% 12%, rgba(120,162,47,.18), transparent 28%),
                linear-gradient(135deg, #123B45 0%, #0D5661 58%, #0B6670 100%);
            border-radius: 20px;
            color: white;
            margin: .15rem 0 1.1rem;
            overflow: hidden;
            padding: 1.65rem 1.8rem 1.45rem;
            position: relative;
        }
        .adv-kicker {
            color: #D9EFAB;
            font-size: .72rem;
            font-weight: 800;
            letter-spacing: .12em;
            margin-bottom: .55rem;
            text-transform: uppercase;
        }
        .adv-hero h2 {
            color: white;
            font-size: clamp(1.55rem, 2.2vw, 2.15rem);
            letter-spacing: -.025em;
            line-height: 1.12;
            margin: 0;
        }
        .adv-hero p {
            color: #DCECEF;
            font-size: .96rem;
            line-height: 1.55;
            margin: .7rem 0 0;
            max-width: 760px;
        }
        .adv-context {
            align-items: center;
            background: #F6F9F3;
            border: 1px solid #DDE8D2;
            border-radius: 14px;
            display: flex;
            flex-wrap: wrap;
            gap: .55rem 1.25rem;
            margin: .6rem 0 1.2rem;
            padding: .85rem 1rem;
        }
        .adv-context-item { color: #53606A; font-size: .78rem; }
        .adv-context-item strong {
            color: #173E46;
            display: block;
            font-size: .92rem;
            margin-top: .08rem;
        }
        .adv-question {
            background: #F7FAFC;
            border: 1px solid #E2E8F0;
            border-left: 4px solid #78A22F;
            border-radius: 0 13px 13px 0;
            margin: .35rem 0 1rem;
            padding: .9rem 1rem;
        }
        .adv-question-title { color: #123B45; font-size: 1rem; font-weight: 750; }
        .adv-question-copy { color: #53606A; font-size: .86rem; margin-top: .2rem; }
        .adv-section-label {
            color: #667085;
            font-size: .72rem;
            font-weight: 800;
            letter-spacing: .09em;
            margin: 1rem 0 .35rem;
            text-transform: uppercase;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_workspace_header(
    merged_data: pd.DataFrame,
    weight_col: str,
    local_label: str,
) -> None:
    replicate_count = sum(str(c).startswith("BSW") for c in merged_data.columns)
    st.markdown(
        """
        <section class="adv-hero">
          <div class="adv-kicker">CCHS · Decision intelligence</div>
          <h2>Advanced analysis studio</h2>
          <p>Move from a population estimate to a defensible public-health
          comparison. Choose the question first; the workspace will surface
          the right measure, uncertainty, and interpretation.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="adv-context">
          <div class="adv-context-item">Geographic scope<strong>{escape(local_label or 'Current filtered population')}</strong></div>
          <div class="adv-context-item">Analytic records<strong>{len(merged_data):,}</strong></div>
          <div class="adv-context-item">Survey weight<strong>{escape(weight_col)}</strong></div>
          <div class="adv-context-item">Bootstrap replicates<strong>{replicate_count:,}</strong></div>
          <div class="adv-context-item">Interval<strong>95% confidence</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_path_intro(path: str) -> None:
    info = ANALYSIS_PATHS[path]
    st.markdown(
        f"""
        <div class="adv-question">
          <div class="adv-question-title">{escape(info['question'])}</div>
          <div class="adv-question-copy">{escape(info['method'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _value_label(value) -> str:
    return str(int(value)) if isinstance(value, (np.integer, int, float)) and float(value).is_integer() else str(value)


def _outcome_label(value, labels: Optional[dict] = None, include_code: bool = True) -> str:
    """Return a response label, with the source code retained for auditability."""
    code = _value_label(value)
    labels = labels or {}
    label = labels.get(value, labels.get(code))
    if label is None or str(label).strip() in {"", code}:
        return f"Code {code} (label unavailable)"
    return f"{label} (code {code})" if include_code else str(label)


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


def _render_stratified_chart(stratified: pd.DataFrame, value_labels: Optional[dict] = None) -> None:
    values = sorted(stratified["Value"].dropna().unique().tolist())
    if not values:
        return
    selected_value = st.selectbox(
        "Visualize outcome value",
        options=values,
        format_func=lambda value: _outcome_label(value, value_labels),
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
            f"For **{_outcome_label(selected_value, value_labels, include_code=False)}**, "
            f"`{top_row['Stratum Label']}` has the highest "
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


def _prepare_contrast_chart_data(table: pd.DataFrame, value_labels: Optional[dict] = None) -> pd.DataFrame:
    chart_data = table.copy()
    if chart_data.empty:
        return chart_data
    chart_data["Value Label"] = chart_data["Value"].map(
        lambda value: _outcome_label(value, value_labels, include_code=False)
    )
    chart_data["Significance"] = np.where(
        chart_data["p-value"].fillna(1) < 0.05, "p < 0.05", "Not significant"
    )
    return chart_data


def _render_contrast_charts(table: pd.DataFrame, value_labels: Optional[dict] = None) -> None:
    chart_data = _prepare_contrast_chart_data(table, value_labels)
    if chart_data.empty:
        return
    largest_gap = chart_data.loc[chart_data["Difference (pp)"].abs().idxmax()]
    significant = int(chart_data["p-value"].fillna(1).lt(0.05).sum())
    direction = (
        f"{largest_gap['Group A']} higher"
        if largest_gap["Difference (pp)"] > 0
        else f"{largest_gap['Group B']} higher"
    )
    _render_interpretation(
        "What this shows:",
        (
            f"The largest separation is for **{_outcome_label(largest_gap['Value'], value_labels, include_code=False)}**: "
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
            ("Most different response", _outcome_label(largest_gap["Value"], value_labels, include_code=False), "Response with the strongest separation."),
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
    widest_gap = chart_data.loc[chart_data["Absolute gap (pp)"].abs().idxmax()]
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


def _prepare_benchmark_long(table: pd.DataFrame, value_labels: Optional[dict] = None) -> pd.DataFrame:
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
    chart_data["Value Label"] = chart_data["Value"].map(
        lambda value: _outcome_label(value, value_labels, include_code=False)
    )
    long = chart_data.melt(
        id_vars=["Value Label", "Difference (pp)", "p-value"],
        value_vars=prevalence_cols[:2],
        var_name="Series",
        value_name="Prevalence",
    )
    long["Series"] = long["Series"].str.replace(" Prevalence (%)", "", regex=False)
    return long


def _render_benchmark_comparison_chart(
    table: pd.DataFrame,
    title: str,
    value_labels: Optional[dict] = None,
) -> None:
    long = _prepare_benchmark_long(table, value_labels)
    if long.empty:
        return
    chart_data = table.copy()
    strongest = chart_data.loc[chart_data["Difference (pp)"].abs().idxmax()]
    local_col, comp_col = [col for col in chart_data.columns if col.endswith("Prevalence (%)")][:2]
    local_name = local_col.replace(" Prevalence (%)", "")
    comp_name = comp_col.replace(" Prevalence (%)", "")
    direction = local_name if strongest["Difference (pp)"] > 0 else comp_name
    _render_interpretation(
        "What this shows:",
        (
            f"The biggest benchmark difference is for **{_outcome_label(strongest['Value'], value_labels, include_code=False)}**. "
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
    value_labels: Optional[dict] = None,
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
    _render_stratified_chart(suppressed, value_labels)
    display = suppressed.copy()
    display.insert(
        display.columns.get_loc("Value") + 1,
        "Outcome response",
        display["Value"].map(lambda value: _outcome_label(value, value_labels, include_code=False)),
    )
    display["Quality"] = display["Quality"].map(lambda k: f"{QUALITY_BADGE[k][0]} {k}")

    cols = [
        "Stratum",
        "Stratum Label",
        "Value",
        "Outcome response",
        "Prevalence",
        "CI Lower",
        "CI Upper",
        "CV (%)",
        "n",
        "Quality",
    ]
    cols = [c for c in cols if c in display.columns]
    styled = display[cols].style.format(
        {
            "Prevalence": "{:.2f}",
            "CI Lower": "{:.2f}",
            "CI Upper": "{:.2f}",
            "CV (%)": "{:.1f}",
        }
    )
    if "Prevalence" in display and display["Prevalence"].notna().any():
        styled = styled.background_gradient(subset=["Prevalence"], cmap="viridis")
    st.dataframe(styled, use_container_width=True)
    st.caption(
        "Suppression rule: n < {n_min} or CV > {cv_hi:.1f}% → estimate suppressed. "
        "CV {cv_lo:.1f}–{cv_hi:.1f}% flagged as *caution*.".format(
            n_min=MIN_UNWEIGHTED_N, cv_lo=CV_ACCEPTABLE, cv_hi=CV_USE_CAUTION
        )
    )
    st.download_button(
        "Download release-screened table (.csv)",
        data=display[cols].to_csv(index=False).encode("utf-8"),
        file_name=f"{variable}_{stratifier_col}_stratified.csv",
        mime="text/csv",
        help="Suppressed estimate fields remain blank in the downloaded file.",
        key=f"adv_download_stratified_{variable}_{stratifier_col}",
    )
    return strat


def _render_contrast_panel(
    merged_data: pd.DataFrame,
    variable: str,
    stratifier_col: str,
    weight_col: str,
    value_labels: Optional[dict] = None,
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

    _render_contrast_charts(table, value_labels)
    table = table.copy()
    table.insert(
        table.columns.get_loc("Value") + 1,
        "Outcome response",
        table["Value"].map(lambda value: _outcome_label(value, value_labels, include_code=False)),
    )
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
        "The p-value tests compatibility with no difference; it does not measure program "
        "importance. Read it with the absolute difference and its 95% CI. Group-level "
        "contrasts are exploratory and still require a release review before dissemination."
    )


def _render_equity_panel(
    stratified: pd.DataFrame,
    stratifier_col: str,
    value_labels: Optional[dict] = None,
) -> None:
    info = STRATIFIER_REGISTRY.get(stratifier_col, {})
    if not info.get("ordered"):
        st.info(
            f"**{info.get('label', stratifier_col)} does not have a social order.** "
            "An equity gradient needs groups that can be placed from a reference "
            "end to a priority end. Use **Compare two groups** for this stratifier."
        )
        return
    if stratified is None or stratified.empty:
        st.warning("No stratified estimates are available for this selection.")
        return

    screened = apply_suppression(stratified)
    values = sorted(screened["Value"].dropna().unique().tolist())
    selected_value = st.selectbox(
        "Outcome value to assess",
        options=values,
        format_func=lambda value: _outcome_label(value, value_labels),
        key=f"equity_value_{stratifier_col}",
        help="For a binary indicator, choose the value that represents the health outcome or burden of interest.",
    )
    value_rows = screened[screened["Value"] == selected_value].copy()
    value_rows = value_rows.dropna(subset=["Stratum", "Prevalence"])
    if len(value_rows) < 2:
        st.warning("At least two population groups with usable estimates are required.")
        return

    if "Stratum Label" not in value_rows.columns:
        value_rows["Stratum Label"] = value_rows["Stratum"].map(_value_label)
    value_rows["Stratum Label"] = value_rows["Stratum Label"].fillna(
        value_rows["Stratum"].map(_value_label)
    )

    levels = sorted(value_rows["Stratum"].unique().tolist())
    end_levels = [levels[0], levels[-1]]
    labels = value_rows.set_index("Stratum")["Stratum Label"].to_dict()
    st.markdown("**Tell us how to read the social order**")
    st.caption(
        "Equity direction comes from context—not from whichever group happens to have "
        "the highest estimate. Choose the two ends before interpreting the gap."
    )
    end_a, end_b = st.columns(2)
    with end_a:
        reference = st.selectbox(
            "Reference end (more resources / advantage)",
            options=end_levels,
            index=1,
            format_func=lambda x: str(labels.get(x, x)),
            key=f"equity_reference_{stratifier_col}",
        )
    remaining = [level for level in end_levels if level != reference]
    with end_b:
        priority = st.selectbox(
            "Priority end (fewer resources / disadvantage)",
            options=remaining,
            index=0,
            format_func=lambda x: str(labels.get(x, x)),
            key=f"equity_priority_{stratifier_col}",
        )

    gap = calculate_gap(
        screened,
        selected_value,
        advantaged_stratum=reference,
        disadvantaged_stratum=priority,
    )
    reference_prev = gap.get("advantaged_prevalence", np.nan)
    priority_prev = gap.get("disadvantaged_prevalence", np.nan)
    gap_pp = gap.get("gap_pp", np.nan)
    ratio = gap.get("ratio", np.nan)
    reference_label = str(labels.get(reference, reference))
    priority_label = str(labels.get(priority, priority))

    if pd.isna(gap_pp):
        st.warning("The selected end groups do not have enough information for a gap estimate.")
        return

    if abs(gap_pp) < 0.05:
        plain_summary = (
            f"The estimated prevalence is about the same at both ends of the selected social order "
            f"({_format_pct(priority_prev)} vs {_format_pct(reference_prev)})."
        )
    else:
        higher_lower = "higher" if gap_pp > 0 else "lower"
        plain_summary = (
            f"For **{_outcome_label(selected_value, value_labels, include_code=False)}**, prevalence in **{priority_label}** "
            f"is **{abs(gap_pp):.1f} percentage points {higher_lower}** than in **{reference_label}** "
            f"({_format_pct(priority_prev)} vs {_format_pct(reference_prev)})."
        )
    _render_interpretation(
        "What this means:",
        plain_summary,
        "The end-group gap is the easiest equity measure to communicate. It describes a pattern, not a cause. "
        "Check the confidence intervals and estimate quality before using the result for decisions.",
    )
    _render_metric_row(
        [
            ("Priority end", _format_pct(priority_prev), priority_label),
            ("Reference end", _format_pct(reference_prev), reference_label),
            ("Absolute gap", _format_pp(gap_pp), "Priority end minus reference end, in percentage points."),
            ("Relative burden", _format_ratio(ratio), "Priority-end prevalence divided by reference-end prevalence."),
        ]
    )

    order = sorted(levels)
    if order.index(priority) > order.index(reference):
        order = list(reversed(order))
    sii_rii = calculate_sii_rii(
        screened,
        selected_value,
        stratifier_col,
        strata_order=order,
    )

    chart_rows = value_rows.copy()
    chart_rows["Order"] = chart_rows["Stratum"].map({value: i for i, value in enumerate(order)})
    chart_rows = chart_rows.sort_values("Order")
    points = alt.Chart(chart_rows).mark_circle(size=125, color=ANALYTICS_PALETTE["primary"]).encode(
        x=alt.X("Stratum Label:N", sort=chart_rows["Stratum Label"].tolist(), title=None),
        y=alt.Y("Prevalence:Q", title="Prevalence (%)", scale=alt.Scale(zero=True)),
        tooltip=[
            alt.Tooltip("Stratum Label:N", title="Population group"),
            alt.Tooltip("Prevalence:Q", title="Prevalence (%)", format=".1f"),
            alt.Tooltip("CI Lower:Q", title="CI lower", format=".1f"),
            alt.Tooltip("CI Upper:Q", title="CI upper", format=".1f"),
            alt.Tooltip("Quality:N", title="Estimate quality"),
        ],
    )
    intervals = alt.Chart(chart_rows).mark_rule(
        color=ANALYTICS_PALETTE["primary"], strokeWidth=2
    ).encode(
        x=alt.X("Stratum Label:N", sort=chart_rows["Stratum Label"].tolist()),
        y="CI Lower:Q",
        y2="CI Upper:Q",
    )
    line = alt.Chart(chart_rows).mark_line(
        color=ANALYTICS_PALETTE["muted"], strokeDash=[5, 4]
    ).encode(
        x=alt.X("Stratum Label:N", sort=chart_rows["Stratum Label"].tolist()),
        y="Prevalence:Q",
    )
    st.altair_chart(
        (intervals + line + points).properties(
            title="Prevalence across the selected social order",
            height=290,
        ).configure(**_chart_theme()["config"]),
        use_container_width=True,
    )
    st.caption("Left to right: priority end → reference end. Vertical lines are 95% confidence intervals.")

    with st.expander("Across the whole gradient (technical measures)", expanded=False):
        sii, rii = sii_rii.get("sii"), sii_rii.get("rii")
        _render_metric_row(
            [
                (
                    "Modelled absolute inequality (SII)",
                    _format_pp(sii),
                    "Modelled difference between the two ends, using every ordered group.",
                ),
                (
                    "Modelled relative inequality (RII)",
                    _format_ratio(rii),
                    "Modelled priority-to-reference ratio, using every ordered group.",
                ),
            ]
        )
        st.caption(
            "SII and RII use all groups and their weighted population sizes. They are most useful "
            "when the ordering represents a meaningful socioeconomic gradient and the pattern is reasonably monotonic."
        )


def _render_benchmark_panel(
    local_merged: pd.DataFrame,
    province_merged: Optional[pd.DataFrame],
    variable: str,
    weight_col: str,
    local_label: str,
    value_labels: Optional[dict] = None,
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
        _render_benchmark_comparison_chart(table, "Local vs Ontario", value_labels)
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
        _render_benchmark_comparison_chart(table, "Local vs selected PHU comparator", value_labels)
        st.dataframe(table, use_container_width=True)
    else:
        value = st.selectbox(
            "Outcome value to rank on",
            options=sorted(local_merged[variable].dropna().unique().tolist()),
            format_func=lambda value: _outcome_label(value, value_labels),
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
    outcome_value_labels: Optional[dict[str, dict]] = None,
) -> None:
    """Render the guided Tier 1 analytics workspace."""
    if merged_data is None or not selected_variables:
        st.info("Run the base bootstrap analysis first — then pick a variable here.")
        return

    _inject_advanced_styles()
    _render_workspace_header(merged_data, weight_col, local_label)

    available = _available_stratifiers(merged_data)
    if not available:
        st.error(
            "None of the registered stratifiers are present in the current dataset. "
            "Check that the cycle was harmonized correctly."
        )
        return

    st.markdown('<div class="adv-section-label">1 · Define the analysis</div>', unsafe_allow_html=True)
    col_var, col_strat = st.columns((1.25, 1))
    with col_var:
        variable = st.selectbox(
            "Health outcome or indicator",
            options=selected_variables,
            format_func=lambda v: (
                f"{v} — {variable_descriptions[v]}" if variable_descriptions and v in variable_descriptions else v
            ),
            key="adv_variable",
        )
    with col_strat:
        stratifier = st.selectbox(
            "Population stratifier",
            options=available,
            format_func=lambda s: f"{STRATIFIER_REGISTRY[s]['label']} ({s})",
            key="adv_stratifier",
        )

    variable_description = (variable_descriptions or {}).get(variable)
    value_labels = (outcome_value_labels or {}).get(variable, {})
    if variable_description:
        st.caption(f"Indicator definition: {variable_description}")

    st.markdown('<div class="adv-section-label">2 · Choose the public-health question</div>', unsafe_allow_html=True)
    analysis_path = st.radio(
        "Analysis path",
        options=list(ANALYSIS_PATHS),
        format_func=lambda key: f"{ANALYSIS_PATHS[key]['icon']}  {ANALYSIS_PATHS[key]['title']}",
        horizontal=True,
        label_visibility="collapsed",
        key="adv_analysis_path",
    )
    _render_path_intro(analysis_path)

    st.markdown('<div class="adv-section-label">3 · Review the evidence</div>', unsafe_allow_html=True)
    if analysis_path == "Describe":
        stratified = _render_stratified_panel(
            merged_data,
            variable,
            stratifier,
            weight_col,
            variable_description,
            value_labels,
        )
        st.session_state[f"_strat_cache_{variable}_{stratifier}"] = stratified
    elif analysis_path == "Compare":
        _render_contrast_panel(merged_data, variable, stratifier, weight_col, value_labels)
    elif analysis_path == "Equity":
        stratified_cached = st.session_state.get(f"_strat_cache_{variable}_{stratifier}")
        if stratified_cached is None:
            label_col = (
                f"{stratifier}_label"
                if f"{stratifier}_label" in merged_data.columns
                else None
            )
            with st.spinner("Preparing the stratified estimates used by the equity measures..."):
                stratified_cached = run_bootstrap_stratified(
                    merged_data,
                    variable,
                    stratifier,
                    weight_col=weight_col,
                    stratifier_label_col=label_col,
                )
            st.session_state[f"_strat_cache_{variable}_{stratifier}"] = stratified_cached
        _render_equity_panel(stratified_cached, stratifier, value_labels)
    else:
        _render_benchmark_panel(
            merged_data,
            province_merged,
            variable,
            weight_col,
            local_label,
            value_labels,
        )

    with st.expander("Method and interpretation guardrails", expanded=False):
        st.markdown(
            """
            - Estimates are survey-weighted and uncertainty uses the supplied CCHS
              bootstrap replicate weights.
            - A 95% confidence interval describes sampling uncertainty, not bias,
              causality, or program importance.
            - Statistical evidence should be read alongside effect size, estimate
              quality, local context, and feasibility of action.
            - This is descriptive, cross-sectional analysis; observed differences
              should not be interpreted as causal effects.
            """
        )
