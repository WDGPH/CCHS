from __future__ import annotations

import pytest

from src.data.harmonizer import auto_harmonize


@pytest.mark.parametrize(
    "label,expected",
    [
        ("Not stated", "Not stated"),
        ("NOT STATED", "Not stated"),
        ("Valid skip - Not applicable", "Valid skip"),
        ("Don't know", "Don't know"),
        ("Don’t know", "Don't know"),
        ("Female", "Female"),
        ("Male", "Male"),
        ("Yes", "Yes"),
        ("No", "No"),
        ("Excellent", "Excellent"),
    ],
)
def test_auto_harmonize_does_not_misclassify_substring_collisions(label, expected):
    # "Not stated", "Valid skip", "Don't know", and "Female" each contain "no"
    # or "male" as a substring (e.g. "**no**t stated", "fe**male**"), so a
    # naive substring check ordered "no"/"male" first would misclassify them.
    assert auto_harmonize(label) == expected
