from __future__ import annotations

import pandas as pd

from src.data.harmonizer import build_crosswalk, get_common_harmonized_vars


def test_build_crosswalk_matches_by_description_and_uses_last_cycle_as_reference():
    descriptions = {
        "2021": {"OLD_VAR": "Has a family doctor"},
        "2022": {"NEW_VAR": "Has a family doctor"},
    }

    crosswalk = build_crosswalk(["2021", "2022"], descriptions)

    assert crosswalk == {"NEW_VAR": {"2022": "NEW_VAR", "2021": "OLD_VAR"}}


def test_build_crosswalk_records_none_for_unmatched_description():
    descriptions = {
        "2021": {"UNRELATED": "Completely unrelated concept about housing"},
        "2022": {"NEW_VAR": "Has a family doctor"},
    }

    crosswalk = build_crosswalk(["2021", "2022"], descriptions)

    assert crosswalk["NEW_VAR"]["2021"] is None


def test_get_common_harmonized_vars_requires_presence_in_every_cycle():
    crosswalk = {
        "IN_BOTH": {"2021": "OLD_A", "2022": "NEW_A"},
        "ONLY_2022": {"2021": None, "2022": "NEW_B"},
    }
    data_dict = {
        "2021": pd.DataFrame({"OLD_A": [1]}),
        "2022": pd.DataFrame({"NEW_A": [1], "NEW_B": [1]}),
    }

    common = get_common_harmonized_vars(["2021", "2022"], crosswalk, data_dict)

    assert common == ["IN_BOTH"]
