import pytest

from src.analysis.domains import is_nonresponse_label


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
