from __future__ import annotations

from src.data.codebook_extractor import parse_codebook_lines


CODEBOOK_TEXT = """\
Variable Name: DHH_SEX Length
Concept: Sex
Answer Categories Code Frequency Weighted Frequency %
Male 1 5,123 3,105,000 50.1
Female 2 5,100 3,090,000 49.9
Note: This variable is derived.
Variable Name: GEN_005 Length
Concept: Perceived health
Answer Categories Code Frequency Weighted Frequency %
Excellent 1 1,000 610,000 10.0
Not stated 9 50 30,500 0.5
"""


def test_parse_codebook_lines_extracts_description_and_categories():
    result = parse_codebook_lines(CODEBOOK_TEXT.splitlines())

    assert result["DHH_SEX"] == {
        "description": "Sex",
        "categories": {"1": "Male", "2": "Female"},
    }
    assert result["GEN_005"] == {
        "description": "Perceived health",
        "categories": {"1": "Excellent", "9": "Not stated"},
    }


def test_parse_codebook_lines_stops_category_section_on_blank_line():
    lines = [
        "Variable Name: FOO Length",
        "Concept: Foo concept",
        "Answer Categories Code Frequency Weighted Frequency %",
        "Yes 1 10 6,000 50.0",
        "",
        "No 2 10 6,000 50.0",
    ]

    result = parse_codebook_lines(lines)

    # The row after the blank line is outside the Answer Categories section
    # and must not be captured as a category.
    assert result["FOO"]["categories"] == {"1": "Yes"}


def test_parse_codebook_lines_handles_last_variable_without_trailing_marker():
    lines = [
        "Variable Name: ONLYVAR Length",
        "Concept: Only concept",
        "Answer Categories Code Frequency Weighted Frequency %",
        "Yes 1 10 6,000 50.0",
    ]

    result = parse_codebook_lines(lines)

    assert result == {
        "ONLYVAR": {"description": "Only concept", "categories": {"1": "Yes"}}
    }
