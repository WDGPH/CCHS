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
