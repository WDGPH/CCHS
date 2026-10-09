from __future__ import annotations

import pandas as pd

from src.utils.helpers import (
    get_available_harmonized_vars,
    get_cycle_value_label,
    get_cycle_varname,
    get_value_label,
)


CATEGORIES = {
    "GEN_005": {
        "mappings": {
            "2021": {"1": "Excellent", "9": "Not stated"},
        }
    }
}


def test_get_value_label_maps_known_code_to_label():
    assert get_value_label("GEN_005", 1, "2021", CATEGORIES) == "Excellent"


def test_get_value_label_handles_integer_valued_floats():
    # Parquet-loaded numeric codes commonly arrive as floats (e.g. 9.0).
    assert get_value_label("GEN_005", 9.0, "2021", CATEGORIES) == "Not stated"


def test_get_value_label_falls_back_to_raw_value_when_unmapped():
    assert get_value_label("GEN_005", 99, "2021", CATEGORIES) == "99"


def test_get_value_label_falls_back_when_variable_or_cycle_missing():
    assert get_value_label("UNKNOWN_VAR", 1, "2021", CATEGORIES) == "1"
    assert get_value_label("GEN_005", 1, "2099", CATEGORIES) == "1"


def test_get_cycle_value_label_reads_cycle_specific_json_structure():
    cycle_var_info = {
        "GEN_005": {"categories": {"1": "Excellent"}}
    }

    assert get_cycle_value_label("GEN_005", 1, cycle_var_info) == "Excellent"
    assert get_cycle_value_label("GEN_005", 2, cycle_var_info) == "2"
    assert get_cycle_value_label("MISSING_VAR", 1, cycle_var_info) == "1"


def test_get_cycle_varname_falls_back_to_harmonized_name_when_unmapped():
    crosswalk = {"GEN_005": {"2021": "GENDVHDI"}}

    assert get_cycle_varname("GEN_005", "2021", crosswalk) == "GENDVHDI"
    assert get_cycle_varname("GEN_005", "2099", crosswalk) == "GEN_005"


def test_get_available_harmonized_vars_checks_cycle_column_presence():
    crosswalk = {
        "GEN_005": {"2021": "GENDVHDI"},
        "MISSING_HERE": {"2021": "SOME_VAR"},
    }
    merged_data = pd.DataFrame({"GENDVHDI": [1, 2]})

    available = get_available_harmonized_vars(crosswalk, "2021", merged_data)

    assert available == ["GEN_005"]
