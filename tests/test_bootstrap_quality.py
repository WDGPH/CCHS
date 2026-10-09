from __future__ import annotations

import math

import pandas as pd
import pytest

from src.analysis.bootstrap import run_bootstrap_analysis_for_all_values
from src.analysis.quality import (
    calculate_effective_sample_size,
    classify_proportion_release,
)


def test_bootstrap_analysis_returns_cycle_quality_fields():
    data = pd.DataFrame(
        {
            "OUTCOME": [0, 0, 1, 1],
            "WTS_S": [1.0, 1.0, 1.0, 1.0],
            "BSW1": [1.2, 1.2, 0.8, 0.8],
            "BSW2": [0.8, 0.8, 1.2, 1.2],
        }
    )

    result = run_bootstrap_analysis_for_all_values(
        data, "OUTCOME", standards_cycle="2024"
    )

    assert result["Prevalence"].tolist() == [50.0, 50.0]
    assert result["Standard Deviation"].tolist() == pytest.approx([10.0, 10.0])
    assert result["Error"].tolist() == pytest.approx([20.0, 20.0])
    assert "Release Category" in result.columns
    assert set(result["Release Category"]).issubset({"A", "E", "F"})


def test_effective_sample_size_uses_proportions():
    effective_n = calculate_effective_sample_size(50.0, 10.0)
    assert effective_n == pytest.approx(100.0)


def test_zero_and_hundred_percent_are_suppressed():
    for prevalence in (0.0, 100.0):
        result = classify_proportion_release(
            prevalence_pct=prevalence,
            cv_pct=10.0,
            numerator_n=100,
            denominator_n=200,
        )
        assert result["Release Category"] == "F"
        assert result["Release Action"] == "Suppress"


def test_zero_cv_has_infinite_effective_sample_size():
    assert math.isinf(calculate_effective_sample_size(50.0, 0.0))


def test_single_cycle_excludes_null_outcomes_from_all_denominators():
    data = pd.DataFrame({
        "OUTCOME": [1, 1, 0, None], "WTS_S": [1., 1., 1., 999.],
        "BSW1": [1., 1., 1., 99999.],
    })
    result = run_bootstrap_analysis_for_all_values(data, "OUTCOME").set_index("Value")
    assert result.loc[1, "Prevalence"] == pytest.approx(200 / 3)
    assert result.loc[1, "Unweighted Denominator"] == 3
    assert result.loc[1, "Variance"] == pytest.approx(0.)


def test_coded_skips_remain_in_the_analysis_denominator():
    data = pd.DataFrame({
        "OUTCOME": ["Yes", "Valid skip", None],
        "WTS_S": [1., 3., 999.], "BSW1": [1., 3., 99999.],
    })
    result = run_bootstrap_analysis_for_all_values(data, "OUTCOME").set_index("Value")
    assert result.loc["Yes", "Prevalence"] == pytest.approx(25.)
    assert result.loc["Yes", "Unweighted Denominator"] == 2


def test_analysis_rejects_an_empty_response_denominator():
    data = pd.DataFrame({"OUTCOME": [None], "WTS_S": [1.], "BSW1": [1.]})
    with pytest.raises(ValueError, match="non-missing responses"):
        run_bootstrap_analysis_for_all_values(data, "OUTCOME")
