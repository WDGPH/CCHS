from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.data import loader, smart_loader


@pytest.fixture
def synthetic_app(monkeypatch):
    """Exercise the real app without local survey files or precomputed data."""
    cycles = ["2021", "2022", "2023", "2024"]
    crosswalk = {"OUTCOME": {cycle: "OUTCOME" for cycle in cycles}}

    def frames(cycle):
        survey = pd.DataFrame({
            "ONT_ID": [1, 2, 3, 4],
            "OUTCOME": [1, 0, 1, 0],
            "WTS_S": [1.0] * 4,
            "AWCAGE": [20, 30, 40, 50],
            "CYCLE": [cycle] * 4,
        })
        bootstrap = pd.DataFrame({
            "ONT_ID": [1, 2, 3, 4],
            "BSW1": [1.2, 0.8, 1.2, 0.8],
            "BSW2": [0.8, 1.2, 0.8, 1.2],
            "CYCLE": [cycle] * 4,
        })
        return survey, bootstrap

    def load_multiple(selected_cycles, *args, **kwargs):
        return {
            cycle: {
                "data": frames(cycle)[0],
                "bootstrap": frames(cycle)[1],
                "metadata": {"available_vars": ["OUTCOME"]},
                "precomputed": False,
            }
            for cycle in selected_cycles
        }

    monkeypatch.setattr(loader, "load_cycle_data", frames)
    monkeypatch.setattr(loader, "load_crosswalk", lambda: crosswalk)
    monkeypatch.setattr(loader, "load_categories", lambda: {})
    monkeypatch.setattr(loader, "load_variable_descriptions", lambda cycle: (None, {}))
    monkeypatch.setattr(loader, "load_json_variable_descriptions", lambda cycle: {})
    monkeypatch.setattr(loader, "load_cycle_variable_info", lambda cycle: {
        "OUTCOME": {"description": "Synthetic outcome", "categories": {}}
    })
    monkeypatch.setattr(smart_loader, "smart_load_multiple_cycles", load_multiple)
    monkeypatch.setattr(smart_loader, "get_common_vars_smart", lambda *args, **kwargs: ["OUTCOME"])
    monkeypatch.setattr(smart_loader, "get_precompute_summary", lambda selected: {
        "all_precomputed": False,
        "none_precomputed": True,
        "partial_precomputed": False,
        "precomputed_cycles": [],
        "missing_cycles": list(selected),
    })
    return AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)


def apply_filters(app):
    next(button for button in app.button if "Apply All Filters" in button.label).click().run()


def analyze(app):
    app.multiselect(key="variable_multiselect").set_value(["OUTCOME"]).run()
    next(button for button in app.button if button.label == "Analyze Selected Variables").click().run()
    assert not app.exception


@pytest.mark.parametrize("mode,new_cycles", [
    ("Cycle Pooling", ["2022", "2023"]),
    ("Multi-Cycle Trends", ["2022", "2023"]),
    ("Cycle Pooling", ["2023"]),
    ("Cycle Pooling", []),
])
def test_cycle_changes_discard_old_data_results_and_variable_selection(synthetic_app, mode, new_cycles):
    app = synthetic_app.run()
    app.radio(key="analysis_mode_selector").set_value(mode).run()
    app.multiselect(key="multi_cycle_selector").set_value(["2023", "2024"]).run()
    apply_filters(app)
    analyze(app)
    original_results = app.session_state["combined_results"].copy()

    # Reordering the same years should preserve the prepared analysis.
    app.multiselect(key="multi_cycle_selector").set_value(["2024", "2023"]).run()
    assert not app.exception
    pd.testing.assert_frame_equal(app.session_state["combined_results"], original_results)

    app.multiselect(key="multi_cycle_selector").set_value(new_cycles).run()
    assert not app.exception
    for key in ["filtered_data", "merged_data", "combined_results"]:
        assert app.session_state[key] is None
    assert app.session_state["selected_variables"] == []
    assert "variable_multiselect" not in app.session_state
    assert not any("Analysis Results - Cycles" in element.value for element in app.markdown)

    if len(new_cycles) >= 2:
        apply_filters(app)
        assert set(app.session_state["merged_data"]["CYCLE"]) == set(new_cycles)
        assert app.multiselect(key="variable_multiselect").value == []
        analyze(app)
        results = app.session_state["combined_results"]
        if mode == "Cycle Pooling":
            assert set(results["Pooled Cycles"]) == {", ".join(new_cycles)}
        else:
            assert set(results["CYCLE"]) == set(new_cycles)


def test_single_cycle_change_discards_previous_analysis(synthetic_app):
    app = synthetic_app.run()
    apply_filters(app)
    analyze(app)
    previous_cycle = app.selectbox(key="sidebar_cycle_selector").value
    new_cycle = "2023" if previous_cycle != "2023" else "2024"

    app.selectbox(key="sidebar_cycle_selector").set_value(new_cycle).run()
    assert not app.exception
    for key in ["filtered_data", "merged_data", "combined_results"]:
        assert app.session_state[key] is None
    assert app.session_state["selected_variables"] == []

    apply_filters(app)
    assert set(app.session_state["merged_data"]["CYCLE"]) == {new_cycle}
    assert app.multiselect(key="variable_multiselect").value == []
