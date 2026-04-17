"""Unit tests for Tier 1 analytics.

Synthetic data is constructed so that invariants are easy to verify without
needing the real parquet files. Bootstrap replicate weights perturb the base
weights slightly so variance is non-zero but small.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.analysis.stratified import run_bootstrap_stratified, apply_suppression
from src.analysis.difference import (
    bootstrap_contrast,
    contrast_all_values,
    contrast_two_frames,
)
from src.analysis.equity import calculate_gap, calculate_sii_rii, equity_summary


def _make_synthetic(n_per_group: int = 500, seed: int = 0) -> pd.DataFrame:
    """Two-group, binary-outcome frame with BSW replicate weights.

    Group 1: outcome prevalence ~= 30%. Group 2: outcome prevalence ~= 60%.
    Base weight = 1 everywhere; each replicate gets multiplicative noise.
    """
    rng = np.random.default_rng(seed)
    outcome = np.concatenate(
        [
            rng.binomial(1, 0.30, n_per_group),
            rng.binomial(1, 0.60, n_per_group),
        ]
    )
    group = np.concatenate([np.ones(n_per_group), np.full(n_per_group, 2)])
    base = pd.DataFrame({"OUTCOME": outcome, "GROUP": group, "WTS_S": 1.0})
    n_replicates = 50
    for i in range(n_replicates):
        base[f"BSW{i}"] = rng.uniform(0.9, 1.1, size=len(base))
    return base


def _make_ordered(n_per_group: int = 400, seed: int = 1) -> pd.DataFrame:
    """Three-level EDDVR3 stratifier with a monotonic burden gradient.

    EDDVR3 encoding from the registry: 1 = less than secondary (most
    disadvantaged), 2 = secondary graduate, 3 = post-secondary (most
    advantaged). We set burden to decrease with rising education so the
    SII is positive (disadvantaged > advantaged): 50% → 30% → 15%.
    """
    rng = np.random.default_rng(seed)
    prevs = {1: 0.50, 2: 0.30, 3: 0.15}
    outcome_parts, strata_parts = [], []
    for s, p in prevs.items():
        outcome_parts.append(rng.binomial(1, p, n_per_group))
        strata_parts.append(np.full(n_per_group, s))
    base = pd.DataFrame(
        {
            "OUTCOME": np.concatenate(outcome_parts),
            "EDDVR3": np.concatenate(strata_parts),
            "WTS_S": 1.0,
        }
    )
    for i in range(50):
        base[f"BSW{i}"] = rng.uniform(0.95, 1.05, size=len(base))
    return base


def test_stratified_bootstrap_recovers_group_prevalences():
    data = _make_synthetic(n_per_group=2000)
    result = run_bootstrap_stratified(data, "OUTCOME", "GROUP")
    pos_rows = result[result["Value"] == 1].set_index("Stratum")
    # With n=2000 per group, observed prevalence should be within 3pp of truth.
    assert abs(pos_rows.loc[1.0, "Prevalence"] - 30.0) < 3
    assert abs(pos_rows.loc[2.0, "Prevalence"] - 60.0) < 3
    assert set(result["Quality"].unique()).issubset({"ok", "caution", "suppress"})


def test_stratified_bootstrap_excludes_skip_values():
    data = _make_synthetic()
    # Spike some rows with the SDCDVIMM skip code 9.
    data["SDCDVIMM"] = 1
    data.loc[:50, "SDCDVIMM"] = 9
    cleaned = run_bootstrap_stratified(data, "OUTCOME", "SDCDVIMM")
    assert 9 not in cleaned["Stratum"].tolist()


def test_apply_suppression_blanks_out_bad_rows():
    data = _make_synthetic()
    result = run_bootstrap_stratified(data, "OUTCOME", "GROUP")
    # Force a suppress flag.
    result.loc[0, "Quality"] = "suppress"
    suppressed = apply_suppression(result)
    assert np.isnan(suppressed.loc[0, "Prevalence"])
    assert np.isnan(suppressed.loc[0, "CI Lower"])
    # Other rows untouched.
    assert not np.isnan(suppressed.loc[1, "Prevalence"])


def test_bootstrap_contrast_detects_real_difference():
    data = _make_synthetic()
    contrast = bootstrap_contrast(data, "OUTCOME", "GROUP", 1.0, 2.0, value=1)
    # True difference 30 - 60 = -30 pp.
    assert -40 < contrast.difference < -20
    assert contrast.se_difference > 0
    assert contrast.p_value < 0.001  # huge effect, tiny p


def test_bootstrap_contrast_zero_when_data_duplicated():
    """When both 'groups' are literally the same rows, difference is exactly 0."""
    rng = np.random.default_rng(42)
    base = pd.DataFrame(
        {
            "OUTCOME": rng.binomial(1, 0.4, 1000),
            "WTS_S": 1.0,
        }
    )
    for i in range(50):
        base[f"BSW{i}"] = rng.uniform(0.95, 1.05, size=len(base))
    a = base.assign(GROUP=1)
    b = base.assign(GROUP=2)
    combined = pd.concat([a, b], ignore_index=True)
    contrast = bootstrap_contrast(combined, "OUTCOME", "GROUP", 1, 2, value=1)
    assert contrast.difference == pytest.approx(0.0, abs=1e-9)
    assert contrast.se_difference == pytest.approx(0.0, abs=1e-9)


def test_contrast_all_values_returns_row_per_value():
    data = _make_synthetic()
    table = contrast_all_values(data, "OUTCOME", "GROUP", 1.0, 2.0)
    assert set(table["Value"].unique()) == {0, 1}


def test_contrast_two_frames_matches_single_frame():
    data = _make_synthetic()
    a = data[data["GROUP"] == 1].reset_index(drop=True)
    b = data[data["GROUP"] == 2].reset_index(drop=True)
    single = bootstrap_contrast(data, "OUTCOME", "GROUP", 1.0, 2.0, value=1)
    split = contrast_two_frames(a, b, "OUTCOME", value=1)
    assert abs(single.difference - split.difference) < 1e-6
    assert abs(single.prev_a - split.prev_a) < 1e-6


def test_equity_gap_picks_extremes_by_default():
    data = _make_ordered()
    stratified = run_bootstrap_stratified(data, "OUTCOME", "EDDVR3")
    gap = calculate_gap(stratified, value=1)
    # Prev goes 50% → 30% → 15% for EDDVR3 levels 1 → 3.
    # calculate_gap picks the lowest-prev row as "advantaged", highest as "disadvantaged".
    assert gap["advantaged_stratum"] == 3
    assert gap["disadvantaged_stratum"] == 1
    assert 25 < gap["gap_pp"] < 45


def test_sii_positive_when_burden_falls_on_disadvantaged():
    data = _make_ordered()
    stratified = run_bootstrap_stratified(data, "OUTCOME", "EDDVR3")
    sii_rii = calculate_sii_rii(stratified, value=1, stratifier_col="EDDVR3")
    # With prev going 15 → 30 → 50 as stratum rises, the slope across cumulative
    # population share is positive → SII (bottom-minus-top of fitted line) is positive.
    assert sii_rii["sii"] > 0
    # RII > 1 because predicted bottom > predicted top.
    assert sii_rii["rii"] > 1


def test_sii_rii_nan_for_unordered_stratifier():
    data = _make_synthetic()
    stratified = run_bootstrap_stratified(data, "OUTCOME", "GROUP")
    out = calculate_sii_rii(stratified, value=1, stratifier_col="GROUP")
    assert np.isnan(out["sii"])
    assert "not ordered" in out["reason"]


def test_equity_summary_has_row_per_value():
    data = _make_ordered()
    stratified = run_bootstrap_stratified(data, "OUTCOME", "EDDVR3")
    summary = equity_summary(stratified, "EDDVR3")
    assert set(summary["Value"].unique()) == {0, 1}
    assert "SII (pp)" in summary.columns
    assert "Absolute gap (pp)" in summary.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
