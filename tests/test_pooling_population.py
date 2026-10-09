import pandas as pd
import pytest

from src.data.pooling import get_pooling_policy, prepare_pooling_population
from src.data import smart_loader
from tests.test_cycle_selection_state import synthetic_app, apply_filters, analyze


def population(cycles=("2022", "2023"), ages=(15, 18, 20, 30)):
    return pd.DataFrame({"CYCLE": [cycles[0]] * 2 + [cycles[1]] * 2, "AWCAGE": list(ages)})


def test_pooling_uses_the_common_adult_population_across_2023_age_change():
    data = population()
    prepared = prepare_pooling_population(data, ["2022", "2023"])
    assert prepared["AWCAGE"].tolist() == [18, 20, 30]
    assert data["AWCAGE"].tolist() == [15, 18, 20, 30]
    assert get_pooling_policy(["2022", "2023"])["minimum_age"] == 18


def test_older_cycles_can_use_the_common_twelve_plus_population_after_design_review():
    prepared = prepare_pooling_population(population(("2021", "2022")), ["2021", "2022"], reviewed=True)
    assert prepared["AWCAGE"].tolist() == [15, 18, 20, 30]
    assert get_pooling_policy(["2021", "2022"])["minimum_age"] == 12


@pytest.mark.parametrize("cycles,geography", [
    (["2021", "2022"], False),
    (["2022", "2023"], True),
])
def test_known_design_or_geography_breaks_require_review(cycles, geography):
    assert get_pooling_policy(cycles, geography)["review_reasons"]
    with pytest.raises(ValueError, match="compatibility review"):
        prepare_pooling_population(population(cycles), cycles, geography_filtered=geography)
    assert not prepare_pooling_population(
        population(cycles), cycles, reviewed=True, geography_filtered=geography
    ).empty


@pytest.mark.parametrize("ages", [(None, 18, 20, 30), (float("inf"), 18, 20, 30), ("unknown", 18, 20, 30)])
def test_pooling_rejects_unverifiable_age_populations(ages):
    with pytest.raises(ValueError, match="complete, finite numeric"):
        prepare_pooling_population(population(ages=ages), ["2022", "2023"])


def test_pooling_stops_when_age_restriction_removes_a_cycle():
    with pytest.raises(ValueError, match="common age population.*Missing: 2022"):
        prepare_pooling_population(population(ages=(12, 17, 20, 30)), ["2022", "2023"])


def test_new_cycles_require_an_explicit_population_policy():
    with pytest.raises(ValueError, match="unavailable.*2025"):
        get_pooling_policy(["2024", "2025"])


def test_app_requires_design_review_and_revoking_it_clears_results(synthetic_app):
    app = synthetic_app.run()
    app.radio(key="analysis_mode_selector").set_value("Cycle Pooling").run()
    app.multiselect(key="multi_cycle_selector").set_value(["2021", "2024"]).run()
    apply_filters(app)
    assert app.session_state["merged_data"] is None
    assert not app.exception

    review = next(cb for cb in app.checkbox if cb.label.startswith("I have reviewed survey-design"))
    review.check().run()
    apply_filters(app)
    analyze(app)
    result = app.session_state["combined_results"]
    assert set(result["Population Minimum Age"]) == {18}
    assert set(result["Compatibility Review"]) == {"Required analyst review completed"}

    next(cb for cb in app.checkbox if cb.label.startswith("I have reviewed survey-design")).uncheck().run()
    assert not app.exception
    assert app.session_state["merged_data"] is None
    assert app.session_state["combined_results"] is None


def test_app_applies_common_age_before_preparing_pooled_results(synthetic_app, monkeypatch):
    original_loader = smart_loader.smart_load_multiple_cycles

    def load_with_youth(*args, **kwargs):
        loaded = original_loader(*args, **kwargs)
        if "2022" in loaded:
            loaded["2022"]["data"].loc[0, "AWCAGE"] = 15
        return loaded

    monkeypatch.setattr(smart_loader, "smart_load_multiple_cycles", load_with_youth)
    app = synthetic_app.run()
    app.radio(key="analysis_mode_selector").set_value("Cycle Pooling").run()
    app.multiselect(key="multi_cycle_selector").set_value(["2022", "2023"]).run()
    apply_filters(app)
    assert len(app.session_state["merged_data"]) == 7
    assert app.session_state["merged_data"]["AWCAGE"].min() >= 18
    analyze(app)
    assert set(app.session_state["combined_results"]["Unweighted Denominator"]) == {7}
