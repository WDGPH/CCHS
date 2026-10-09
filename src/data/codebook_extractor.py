"""Parsing logic for Statistics Canada CCHS Data Dictionary/Freqs PDF codebooks."""

import re
from typing import Iterable


CATEGORY_ROW = re.compile(r"^(.+?)\s+(\d{1,3})\s+\d[\d,]*\s+\d[\d,]*\s+[\d.]+")
SECTION_END = re.compile(r"^(Note:|Source:|Universe:|Total)")


def parse_codebook_lines(lines: Iterable[str]) -> dict:
    """
    Parse codebook text lines into a variable -> {description, categories} dict.

    Expects the Statistics Canada CCHS Data Dictionary/Freqs layout: each
    variable starts with a "Variable Name:" line, has a "Concept:" line for
    its description, and an "Answer Categories" section listing "label code
    frequency frequency%" rows until a blank line or a Note:/Source:/
    Universe:/Total line ends the section.

    Args:
        lines: An iterable of text lines, in document order (may span
            multiple PDF pages - state carries across page boundaries the
            same way it does across lines within a page).

    Returns:
        Dict mapping variable_name -> {"description": str, "categories": {code: label}}
    """
    variables = {}
    current_variable = None
    current_description = None
    codes = {}
    in_answer_categories = False

    for line in lines:
        if "Variable Name:" in line:
            if current_variable:
                variables[current_variable] = {
                    "description": current_description,
                    "categories": codes.copy() if codes else {}
                }
            current_variable = line.split(":")[1].strip().replace(" Length", "")
            current_description = None
            codes = {}
            in_answer_categories = False
        elif "Concept:" in line:
            current_description = line.split(":")[1].strip()
        elif "Answer Categories" in line:
            in_answer_categories = True
            continue
        elif in_answer_categories:
            match = CATEGORY_ROW.match(line)
            if match:
                meaning = match.group(1).strip()
                code = match.group(2).strip()
                codes[code] = meaning
            elif line.strip() == "" or SECTION_END.match(line):
                in_answer_categories = False
                continue
        elif "Note:" in line or "Source:" in line or "Universe:" in line:
            in_answer_categories = False
            continue

    if current_variable:
        variables[current_variable] = {
            "description": current_description,
            "categories": codes.copy() if codes else {}
        }

    return variables


def extract_variables_with_categories(pdf_path) -> dict:
    """Extract variable/category metadata from a CCHS codebook PDF."""
    from pypdf import PdfReader

    lines = []
    with open(pdf_path, "rb") as file:
        reader = PdfReader(file)
        for page in reader.pages:
            lines.extend(page.extract_text().splitlines())

    return parse_codebook_lines(lines)
