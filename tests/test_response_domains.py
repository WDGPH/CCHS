import pytest
import pandas as pd
from streamlit.testing.v1 import AppTest

from src.analysis.domains import is_nonresponse_label, recalculate_response_domain
from src.analysis.bootstrap import run_cycle_pooled_analysis


@pytest.mark.parametrize("label", [
    "Current occasional smoker", "Canadian", "No functional limitations", "Yes", "No",
])
def test_nonresponse_filter_keeps_valid_labels(label):
    assert not is_nonresponse_label(label)


@pytest.mark.parametrize("label", [
    "Valid skip", "Not stated", "Don't know", "Don’t know", "Refusal",
    "Not applicable", "N/A", "NA", "DK", "NS", None,
])
def test_nonresponse_filter_recognizes_missing_labels(label):
    assert is_nonresponse_label(label)


@pytest.mark.parametrize("pooling", [False, True])
def test_recalculated_display_recomputes_uncertainty_and_release_flags(pooling):
    source = f'''
from functools import partial
import pandas as pd
from src.analysis.bootstrap import run_bootstrap_analysis_for_all_values, run_cycle_pooled_analysis
from src.analysis.domains import recalculate_response_domain
from src.ui.results import display_results
rows = []
for cycle in {['2023', '2024'] if pooling else ['2024']!r}:
    for value, weight, b1, b2 in [('Yes', 1., 1., 1.), ('No', 1., 1., 1.), ('Valid skip', 2., 4., 1.)]:
        rows.append({{'CYCLE': cycle, 'X': value, 'WTS_S': weight, 'BSW1': b1, 'BSW2': b2}})
data = pd.DataFrame(rows)
analyze = run_cycle_pooled_analysis if {pooling!r} else run_bootstrap_analysis_for_all_values
original = analyze(data, 'X', standards_cycle='2024')
original['Label'] = original['Value']
callback = partial(recalculate_response_domain, data, 'X', original_results=original,
                   pooling={pooling!r}, standards_cycle='2024',
                   expected_cycles={['2023', '2024'] if pooling else None!r})
display_results(original, 'X', standards_cycle='2024', recalculate=callback)
'''
    app = AppTest.from_string(source).run()
    next(cb for cb in app.checkbox if cb.label == "🎯 Filter skip/missing").check()
    next(cb for cb in app.checkbox if cb.label == "🔄 Recalculate %").check()
    app.run()

    assert not app.exception
    table = app.dataframe[0].value.set_index("Value")
    assert set(table.index) == {"No", "Yes"}
    assert set(table["Prevalence"]) == {"50.00%"}
    assert set(table["Standard Deviation"]) == {"0.000"}
    assert set(table["CI Lower"]) == {"50.00"}
    assert set(table["CI Upper"]) == {"50.00"}
    assert set(table["CV (%)"]) == {"0.0%"}
    assert set(table["Release Reason"]) == {"Confidence interval has zero length"}
    assert set(table["Unweighted Denominator"]) == {4 if pooling else 2}


def test_response_domain_does_not_silently_drop_a_selected_cycle():
    data = pd.DataFrame({
        "CYCLE": ["2023", "2024"], "X": ["Yes", "Valid skip"],
        "WTS_S": [1., 1.], "BSW1": [1., 1.],
    })
    original = run_cycle_pooled_analysis(data, "X")
    with pytest.raises(ValueError, match="at least two"):
        recalculate_response_domain(
            data, "X", ["Yes"], original, pooling=True, expected_cycles=["2023", "2024"]
        )


def test_response_domain_uses_cycle_specific_harmonized_codes():
    data = pd.DataFrame({
        "CYCLE": ["2023", "2023", "2024", "2024"], "X": [1., 9., 7., 99.],
        "WTS_S": [1., 3., 2., 4.], "BSW1": [1., 3., 2., 4.],
    })
    categories = {"X": {"mappings": {
        "2023": {"01": "Yes", "09": "Valid skip"},
        "2024": {"07": "yes", "99": "Valid skip"},
    }}}
    original = pd.DataFrame({"Value": ["Yes"], "Prevalence": [30.], "Label": ["Yes"]})
    result = recalculate_response_domain(
        data, "X", ["Yes"], original, pooling=True, categories=categories,
        expected_cycles=["2023", "2024"],
    )
    assert result["Value"].tolist() == ["Yes"]
    assert result["Prevalence"].tolist() == [100.]
    assert result["Weighted Population"].tolist() == [1.5]
    assert result["Unweighted Denominator"].tolist() == [2]


def test_display_cannot_recalculate_without_respondent_data():
    source = '''
import pandas as pd
from src.analysis.bootstrap import run_cycle_pooled_analysis
from src.ui.results import display_results
data = pd.DataFrame({'CYCLE': ['2023', '2024'], 'X': [0, 1], 'WTS_S': [1., 1.], 'BSW1': [1., 1.]})
display_results(run_cycle_pooled_analysis(data, 'X'), 'X')
'''
    app = AppTest.from_string(source).run()
    assert not app.exception
    assert next(cb for cb in app.checkbox if cb.label == "🔄 Recalculate %").disabled
