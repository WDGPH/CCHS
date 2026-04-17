"""Bootstrap differences, prevalence ratios, and odds ratios.

The previous significance check in ``comparison.py`` relied on whether two
independent 95% CIs overlap. That test is known to be overly conservative:
two estimates can be different at p < 0.05 while their individual CIs still
overlap. The functions here compute the variance of the *contrast itself* by
evaluating it on every bootstrap replicate, which is the correct way to
combine survey-bootstrap weights.

All functions expect the merged data (respondent rows + BSW replicate weight
columns). Groups are specified either by a stratifier column + two values, or
by passing two already-filtered frames.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from config.settings import BOOTSTRAP_PREFIX, DEFAULT_WEIGHT_COLUMN


def _fmt_ci(ci: tuple[float, float], placeholder: str = "—") -> str:
    """Render a (low, high) CI tuple, collapsing undefined bounds to a dash.

    The OR/PR become undefined whenever an arm's prevalence hits 0% or 100%
    (the log scale blows up) and ``contrast_two_frames`` deliberately skips
    OR computation. In those cases we return NaN bounds internally — render
    them as a single placeholder instead of leaking 'nan' into the UI.
    """
    lo, hi = ci
    if pd.isna(lo) or pd.isna(hi):
        return placeholder
    return f"({lo:.2f}, {hi:.2f})"


@dataclass
class ContrastResult:
    """A single group-vs-group contrast with bootstrap inference."""

    group_a: str
    group_b: str
    value: object
    prev_a: float
    prev_b: float
    difference: float
    ratio: float
    odds_ratio: float
    se_difference: float
    ci_difference: tuple[float, float]
    se_log_ratio: float
    ci_ratio: tuple[float, float]
    ci_odds_ratio: tuple[float, float]
    z_stat: float
    p_value: float
    n_a: int
    n_b: int

    def as_row(self) -> dict:
        return {
            "Group A": self.group_a,
            "Group B": self.group_b,
            "Value": self.value,
            "Prevalence A (%)": self.prev_a,
            "Prevalence B (%)": self.prev_b,
            "Difference (pp)": self.difference,
            "Difference 95% CI": _fmt_ci(self.ci_difference),
            "Prevalence Ratio": self.ratio,
            "PR 95% CI": _fmt_ci(self.ci_ratio),
            "Odds Ratio": self.odds_ratio,
            "OR 95% CI": _fmt_ci(self.ci_odds_ratio),
            "z": self.z_stat,
            "p-value": self.p_value,
            "n A": self.n_a,
            "n B": self.n_b,
        }


def _bootstrap_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith(BOOTSTRAP_PREFIX)]


def _prevalences(
    df: pd.DataFrame, variable_col: str, weight_col: str, boot_cols: list[str]
) -> tuple[pd.Series, pd.DataFrame]:
    """Return (base prevalence per value, replicate prevalence per value x replicate) in %."""
    total_base = df[weight_col].sum()
    if total_base == 0:
        return pd.Series(dtype=float), pd.DataFrame()
    num_base = df.groupby(variable_col)[weight_col].sum()
    base_prev = (num_base / total_base) * 100

    total_boot = df[boot_cols].sum()
    num_boot = df.groupby(variable_col)[boot_cols].sum()
    replicate_prev = num_boot.div(total_boot, axis=1) * 100
    return base_prev, replicate_prev


def _normal_p_two_sided(z: float) -> float:
    """Two-sided p-value from a standard-normal z, without scipy."""
    if pd.isna(z):
        return np.nan
    # Abramowitz & Stegun 7.1.26 approximation of erf.
    x = abs(z) / np.sqrt(2.0)
    t = 1.0 / (1.0 + 0.3275911 * x)
    a = [0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429]
    y = 1.0 - (((((a[4] * t + a[3]) * t) + a[2]) * t + a[1]) * t + a[0]) * t * np.exp(-x * x)
    return float(2.0 * (1.0 - 0.5 * (1.0 + y)))


def bootstrap_contrast(
    merged_data: pd.DataFrame,
    variable_col: str,
    group_col: str,
    group_a,
    group_b,
    value,
    weight_col: str = DEFAULT_WEIGHT_COLUMN,
    label_a: Optional[str] = None,
    label_b: Optional[str] = None,
) -> ContrastResult:
    """Contrast the prevalence of ``variable_col == value`` between two groups.

    Bootstrap SE is computed directly on the per-replicate contrast, yielding
    correct inference for the *difference*. Ratio/OR CIs use the delta method
    on the log scale.
    """
    df = merged_data.dropna(subset=[variable_col, group_col])
    df_a = df[df[group_col] == group_a]
    df_b = df[df[group_col] == group_b]
    if df_a.empty or df_b.empty:
        raise ValueError(
            f"Empty group in contrast: |A|={len(df_a)}, |B|={len(df_b)} "
            f"(looked for {group_col} in {{{group_a}, {group_b}}})"
        )

    boot_cols = _bootstrap_cols(df)
    if not boot_cols:
        raise ValueError("No bootstrap weight columns (BSW*) in data")

    base_a, rep_a = _prevalences(df_a, variable_col, weight_col, boot_cols)
    base_b, rep_b = _prevalences(df_b, variable_col, weight_col, boot_cols)

    prev_a = float(base_a.get(value, 0.0))
    prev_b = float(base_b.get(value, 0.0))

    rep_a_v = rep_a.loc[value] if value in rep_a.index else pd.Series(0.0, index=boot_cols)
    rep_b_v = rep_b.loc[value] if value in rep_b.index else pd.Series(0.0, index=boot_cols)

    # Per-replicate difference — variance is the mean squared deviation from
    # the base difference (matching the existing bootstrap.py convention).
    diff = prev_a - prev_b
    rep_diff = rep_a_v - rep_b_v
    se_diff = float(np.sqrt(((rep_diff - diff) ** 2).mean()))
    ci_diff = (diff - 1.96 * se_diff, diff + 1.96 * se_diff)
    z_stat = diff / se_diff if se_diff > 0 else np.nan
    p_value = _normal_p_two_sided(z_stat)

    # Prevalence ratio / odds ratio on log scale, then exponentiate CIs.
    ratio = prev_a / prev_b if prev_b > 0 else np.nan
    if prev_b > 0 and prev_a > 0:
        rep_log_ratio = np.log(rep_a_v.replace(0, np.nan)) - np.log(rep_b_v.replace(0, np.nan))
        rep_log_ratio = rep_log_ratio.dropna()
        se_log_ratio = float(np.sqrt(((rep_log_ratio - np.log(ratio)) ** 2).mean()))
        ci_ratio = (
            float(np.exp(np.log(ratio) - 1.96 * se_log_ratio)),
            float(np.exp(np.log(ratio) + 1.96 * se_log_ratio)),
        )
    else:
        se_log_ratio = np.nan
        ci_ratio = (np.nan, np.nan)

    def _odds(p: float) -> float:
        if p <= 0 or p >= 100:
            return np.nan
        p_frac = p / 100.0
        return p_frac / (1.0 - p_frac)

    or_base = _odds(prev_a) / _odds(prev_b) if _odds(prev_b) else np.nan
    if np.isfinite(or_base) and or_base > 0:
        def _rep_odds(series: pd.Series) -> pd.Series:
            p = (series / 100.0).clip(lower=1e-6, upper=1 - 1e-6)
            return p / (1.0 - p)
        rep_or = _rep_odds(rep_a_v) / _rep_odds(rep_b_v)
        rep_log_or = np.log(rep_or.replace(0, np.nan)).dropna()
        se_log_or = float(np.sqrt(((rep_log_or - np.log(or_base)) ** 2).mean()))
        ci_or = (
            float(np.exp(np.log(or_base) - 1.96 * se_log_or)),
            float(np.exp(np.log(or_base) + 1.96 * se_log_or)),
        )
    else:
        ci_or = (np.nan, np.nan)

    return ContrastResult(
        group_a=label_a or str(group_a),
        group_b=label_b or str(group_b),
        value=value,
        prev_a=prev_a,
        prev_b=prev_b,
        difference=diff,
        ratio=ratio,
        odds_ratio=or_base,
        se_difference=se_diff,
        ci_difference=ci_diff,
        se_log_ratio=se_log_ratio,
        ci_ratio=ci_ratio,
        ci_odds_ratio=ci_or,
        z_stat=z_stat,
        p_value=p_value,
        n_a=len(df_a),
        n_b=len(df_b),
    )


def contrast_all_values(
    merged_data: pd.DataFrame,
    variable_col: str,
    group_col: str,
    group_a,
    group_b,
    weight_col: str = DEFAULT_WEIGHT_COLUMN,
    label_a: Optional[str] = None,
    label_b: Optional[str] = None,
) -> pd.DataFrame:
    """Run ``bootstrap_contrast`` on every value of ``variable_col`` — one table."""
    values = sorted(merged_data[variable_col].dropna().unique().tolist())
    rows = []
    for v in values:
        try:
            result = bootstrap_contrast(
                merged_data,
                variable_col,
                group_col,
                group_a,
                group_b,
                v,
                weight_col=weight_col,
                label_a=label_a,
                label_b=label_b,
            )
            rows.append(result.as_row())
        except ValueError:
            continue
    return pd.DataFrame(rows)


def contrast_two_frames(
    data_a: pd.DataFrame,
    data_b: pd.DataFrame,
    variable_col: str,
    value,
    weight_col: str = DEFAULT_WEIGHT_COLUMN,
    label_a: str = "A",
    label_b: str = "B",
) -> ContrastResult:
    """Variant of ``bootstrap_contrast`` when the two groups live in different frames.

    Used for PHU-vs-Ontario benchmarking and cycle-vs-cycle comparisons, where
    the two sides aren't just different rows of the same table but separate
    filtered datasets (possibly with different BSW totals).
    """
    boot_cols_a = _bootstrap_cols(data_a)
    boot_cols_b = _bootstrap_cols(data_b)
    common_boot = [c for c in boot_cols_a if c in boot_cols_b]
    if not common_boot:
        raise ValueError("No shared BSW columns between the two frames")

    base_a, rep_a = _prevalences(data_a, variable_col, weight_col, common_boot)
    base_b, rep_b = _prevalences(data_b, variable_col, weight_col, common_boot)

    prev_a = float(base_a.get(value, 0.0))
    prev_b = float(base_b.get(value, 0.0))
    rep_a_v = rep_a.loc[value] if value in rep_a.index else pd.Series(0.0, index=common_boot)
    rep_b_v = rep_b.loc[value] if value in rep_b.index else pd.Series(0.0, index=common_boot)

    diff = prev_a - prev_b
    rep_diff = rep_a_v - rep_b_v
    se_diff = float(np.sqrt(((rep_diff - diff) ** 2).mean()))
    ci_diff = (diff - 1.96 * se_diff, diff + 1.96 * se_diff)
    z_stat = diff / se_diff if se_diff > 0 else np.nan
    p_value = _normal_p_two_sided(z_stat)

    ratio = prev_a / prev_b if prev_b > 0 else np.nan
    return ContrastResult(
        group_a=label_a,
        group_b=label_b,
        value=value,
        prev_a=prev_a,
        prev_b=prev_b,
        difference=diff,
        ratio=ratio,
        odds_ratio=np.nan,
        se_difference=se_diff,
        ci_difference=ci_diff,
        se_log_ratio=np.nan,
        ci_ratio=(np.nan, np.nan),
        ci_odds_ratio=(np.nan, np.nan),
        z_stat=z_stat,
        p_value=p_value,
        n_a=len(data_a),
        n_b=len(data_b),
    )
