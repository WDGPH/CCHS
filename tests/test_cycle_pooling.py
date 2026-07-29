from __future__ import annotations

import pandas as pd
import pytest

from src.analysis.bootstrap import run_cycle_pooled_analysis
from src.data.harmonizer import POOLED_VALUE_COLUMN, prepare_pooled_variable


def test_pooling_scales_weights_to_average_annual_population():
    data = pd.DataFrame(
        {
            "CYCLE": ["2022", "2022", "2023", "2023"],
            "OUTCOME": [0, 1, 0, 1],
            "WTS_S": [1.0, 3.0, 2.0, 2.0],
            "BSW1": [1.0, 3.0, 2.0, 2.0],
            "BSW2": [1.0, 3.0, 2.0, 2.0],
        }
    )

    result = run_cycle_pooled_analysis(
        data, "OUTCOME", expected_cycles=["2022", "2023"]
    ).set_index("Value")

    assert result.loc[1, "Prevalence"] == pytest.approx(62.5)
    assert result.loc[1, "Weighted Population"] == pytest.approx(2.5)
    assert result.loc[0, "Weighted Population"] == pytest.approx(1.5)
    assert result.loc[1, "Standard Deviation"] == pytest.approx(0.0)
    assert result.loc[1, "Unweighted Numerator"] == 2
    assert result.loc[1, "Unweighted Denominator"] == 4
    assert result.loc[1, "Cycle Count"] == 2
    assert result.loc[1, "Pooled Cycles"] == "2022, 2023"


def test_pooling_sums_independent_cycle_variance_contributions():
    data = pd.DataFrame(
        {
            "CYCLE": ["2022", "2022", "2023", "2023"],
            "OUTCOME": [0, 1, 0, 1],
            "WTS_S": [1.0, 1.0, 1.0, 1.0],
            "BSW1": [1.2, 0.8, 1.2, 0.8],
            "BSW2": [0.8, 1.2, 0.8, 1.2],
        }
    )

    result = run_cycle_pooled_analysis(data, "OUTCOME").set_index("Value")

    # Each annual estimate has variance 100. Averaging two independent cycles
    # gives 100 / 2 = 50, rather than pairing same-numbered replicates and
    # implicitly treating their movements as correlated.
    assert result.loc[1, "Prevalence"] == pytest.approx(50.0)
    assert result.loc[1, "Variance"] == pytest.approx(50.0)
    assert result.loc[1, "Standard Deviation"] == pytest.approx(50.0**0.5)


def test_pooling_supports_more_than_two_cycles():
    rows = []
    for cycle in ("2021", "2022", "2023"):
        rows.extend(
            [
                {"CYCLE": cycle, "OUTCOME": 0, "WTS_S": 1.0, "BSW1": 1.0},
                {"CYCLE": cycle, "OUTCOME": 1, "WTS_S": 1.0, "BSW1": 1.0},
            ]
        )

    result = run_cycle_pooled_analysis(pd.DataFrame(rows), "OUTCOME")

    assert set(result["Cycle Count"]) == {3}
    assert result["Weighted Population"].sum() == pytest.approx(2.0)
    assert result["Prevalence"].tolist() == pytest.approx([50.0, 50.0])


def test_pooling_rejects_one_cycle():
    data = pd.DataFrame(
        {
            "CYCLE": ["2023", "2023"],
            "OUTCOME": [0, 1],
            "WTS_S": [1.0, 1.0],
            "BSW1": [1.0, 1.0],
        }
    )

    with pytest.raises(ValueError, match="at least two"):
        run_cycle_pooled_analysis(data, "OUTCOME")


def test_pooling_rejects_selected_cycle_lost_after_filtering():
    data = pd.DataFrame(
        {
            "CYCLE": ["2022", "2022", "2023", "2023"],
            "OUTCOME": [0, 1, 0, 1],
            "WTS_S": [1.0, 1.0, 1.0, 1.0],
            "BSW1": [1.0, 1.0, 1.0, 1.0],
        }
    )

    with pytest.raises(ValueError, match="missing: 2024"):
        run_cycle_pooled_analysis(
            data,
            "OUTCOME",
            expected_cycles=["2022", "2023", "2024"],
        )


def test_pooling_rejects_incomplete_replicate_weights():
    data = pd.DataFrame(
        {
            "CYCLE": ["2022", "2023"],
            "OUTCOME": [0, 1],
            "WTS_S": [1.0, 1.0],
            "BSW1": [1.0, None],
        }
    )

    with pytest.raises(ValueError, match="missing main or bootstrap weights"):
        run_cycle_pooled_analysis(data, "OUTCOME")


def test_pooling_harmonizes_different_cycle_codes_to_shared_labels():
    data = pd.DataFrame(
        {
            "CYCLE": ["2022", "2023"],
            "OUTCOME": [1, 7],
        }
    )
    categories = {
        "OUTCOME": {
            "mappings": {
                "2022": {"1": "Yes"},
                "2023": {"7": "Yes"},
            }
        }
    }

    prepared, variable, harmonized = prepare_pooled_variable(
        data, "OUTCOME", categories
    )

    assert variable == POOLED_VALUE_COLUMN
    assert harmonized is True
    assert prepared[variable].tolist() == ["Yes", "Yes"]


def test_pooling_rejects_partial_category_harmonization():
    data = pd.DataFrame(
        {
            "CYCLE": ["2022", "2023"],
            "OUTCOME": [1, 1],
        }
    )
    categories = {
        "OUTCOME": {"mappings": {"2022": {"1": "Yes"}, "2023": {}}}
    }

    with pytest.raises(ValueError, match="incomplete.*2023"):
        prepare_pooled_variable(data, "OUTCOME", categories)


def test_pooling_rejects_unmapped_observed_category():
    data = pd.DataFrame(
        {
            "CYCLE": ["2022", "2023"],
            "OUTCOME": [1, 9],
        }
    )
    categories = {
        "OUTCOME": {
            "mappings": {
                "2022": {"1": "Yes"},
                "2023": {"1": "Yes"},
            }
        }
    }

    with pytest.raises(ValueError, match="unmapped value.*9"):
        prepare_pooled_variable(data, "OUTCOME", categories)
