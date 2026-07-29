"""Smoke coverage for the question-led Advanced Analysis workspace."""

from streamlit.testing.v1 import AppTest


APP = r'''
import numpy as np
import pandas as pd

from src.ui.advanced import render_advanced_analytics_tab

rng = np.random.default_rng(4)
n = 600
frame = pd.DataFrame({
    "OUTCOME": rng.binomial(1, 0.4, n),
    "DHH_SEX": np.tile([1, 2], n // 2),
    "EDDVR3": np.tile([1, 2, 3], n // 3),
    "WTS_S": np.ones(n),
})
for replicate in range(8):
    frame[f"BSW{replicate}"] = rng.uniform(0.85, 1.15, n)

render_advanced_analytics_tab(
    merged_data=frame,
    selected_variables=["OUTCOME"],
    local_label="Test PHU",
    variable_descriptions={"OUTCOME": "Synthetic indicator"},
    outcome_value_labels={"OUTCOME": {0: "No", 1: "Yes"}},
)
'''


def test_advanced_workspace_default_path_renders_without_exception():
    app = AppTest.from_string(APP).run(timeout=15)
    assert not app.exception
    assert app.radio[0].value == "Describe"
    assert app.selectbox[0].value == "OUTCOME"
    assert app.selectbox[1].value == "DHH_SEX"
    assert len(app.get("download_button")) == 1


def test_advanced_workspace_question_paths_render_independently():
    app = AppTest.from_string(APP).run(timeout=15)
    for path in ("Compare", "Equity", "Benchmark"):
        app.radio[0].set_value(path).run(timeout=15)
        assert not app.exception
        assert app.radio[0].value == path


def test_equity_path_guides_social_order_and_hides_technical_measures():
    app = AppTest.from_string(APP).run(timeout=15)
    app.selectbox[1].set_value("EDDVR3").run(timeout=15)
    app.radio[0].set_value("Equity").run(timeout=15)
    assert not app.exception
    assert app.selectbox[2].label == "Outcome value to assess"
    assert app.selectbox[3].label == "Reference end (more resources / advantage)"
    assert app.selectbox[4].label == "Priority end (fewer resources / disadvantage)"
    assert any(
        expander.label == "Across the whole gradient (technical measures)"
        for expander in app.expander
    )
