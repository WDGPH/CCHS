from __future__ import annotations

import pandas as pd

from src.data.loader import build_harmonization_mapping, restore_geography_aliases


def test_build_harmonization_mapping_renames_available_columns():
    crosswalk = {
        "HARMONIZED_A": {"2021": "OLD_A", "2022": "NEW_A"},
        "HARMONIZED_B": {"2021": "OLD_B", "2022": "NEW_B"},
    }

    rename_dict, available_vars = build_harmonization_mapping(
        crosswalk, "2021", ["OLD_A", "UNRELATED"]
    )

    assert rename_dict == {"OLD_A": "HARMONIZED_A"}
    assert available_vars == ["HARMONIZED_A"]


def test_build_harmonization_mapping_skips_not_available_and_missing_columns():
    crosswalk = {
        "HARMONIZED_A": {"2021": "Not Available"},
        "HARMONIZED_B": {"2021": None},
        "HARMONIZED_C": {"2021": "MISSING_FROM_DATA"},
    }

    rename_dict, available_vars = build_harmonization_mapping(
        crosswalk, "2021", ["SOME_OTHER_COLUMN"]
    )

    assert rename_dict == {}
    assert available_vars == []


def test_build_harmonization_mapping_prefers_identity_mapping_on_collision():
    # Two harmonized variables both point at the same source column for this
    # cycle (e.g. an alias entry landing on an exact-match geography column).
    # The identity mapping (name unchanged) must win so geography columns
    # aren't renamed away by alias entries encountered later.
    crosswalk = {
        "GEODVOHR": {"2021": "GEODVHR4"},
        "GEODVHR4": {"2021": "GEODVHR4"},
    }

    rename_dict, available_vars = build_harmonization_mapping(
        crosswalk, "2021", ["GEODVHR4"]
    )

    assert rename_dict == {"GEODVHR4": "GEODVHR4"}
    assert available_vars == ["GEODVHR4"]


def test_restore_geography_aliases_backfills_from_alias_column():
    df = pd.DataFrame({"GEODVOHR": [35, 42]})

    restored = restore_geography_aliases(df)

    assert restored["GEODVHR4"].tolist() == [35, 42]


def test_restore_geography_aliases_leaves_existing_column_untouched():
    df = pd.DataFrame({"GEODVHR4": [1], "GEODVOHR": [2]})

    restored = restore_geography_aliases(df)

    assert restored["GEODVHR4"].tolist() == [1]
