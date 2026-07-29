from __future__ import annotations

import pandas as pd
import pytest

from src.data.loader import merge_data


merge_data_uncached = merge_data.__wrapped__


def test_single_cycle_merge_is_one_to_one():
    survey = pd.DataFrame({"ONT_ID": [1, 2], "WTS_S": [10.0, 20.0]})
    bootstrap = pd.DataFrame({"ONT_ID": [1, 2], "BSW1": [11.0, 19.0]})

    merged = merge_data_uncached(survey, bootstrap)

    assert len(merged) == len(survey)
    assert merged["BSW1"].tolist() == [11.0, 19.0]


def test_repeated_ids_across_cycles_do_not_cross_join():
    survey = pd.DataFrame(
        {
            "CYCLE": ["2023", "2024"],
            "ONT_ID": [1, 1],
            "WTS_S": [10.0, 20.0],
        }
    )
    bootstrap = pd.DataFrame(
        {
            "CYCLE": ["2023", "2024"],
            "ONT_ID": [1, 1],
            "BSW1": [9.0, 21.0],
        }
    )

    merged = merge_data_uncached(survey, bootstrap)

    assert len(merged) == len(survey)
    assert merged["BSW1"].tolist() == [9.0, 21.0]


def test_cycle_column_is_required_on_both_frames():
    survey = pd.DataFrame(
        {"CYCLE": ["2024"], "ONT_ID": [1], "WTS_S": [10.0]}
    )
    bootstrap = pd.DataFrame({"ONT_ID": [1], "BSW1": [9.0]})

    with pytest.raises(ValueError, match="CYCLE column on both"):
        merge_data_uncached(survey, bootstrap)


def test_duplicate_cycle_identifier_is_rejected():
    survey = pd.DataFrame(
        {"CYCLE": ["2024"], "ONT_ID": [1], "WTS_S": [10.0]}
    )
    bootstrap = pd.DataFrame(
        {
            "CYCLE": ["2024", "2024"],
            "ONT_ID": [1, 1],
            "BSW1": [9.0, 11.0],
        }
    )

    with pytest.raises(pd.errors.MergeError):
        merge_data_uncached(survey, bootstrap)
