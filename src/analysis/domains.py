"""Helpers for selecting response domains for survey analysis."""

import re
import unicodedata

import pandas as pd


_NONRESPONSE_PATTERN = re.compile(
    r"(?<!\w)(?:valid skip|skip|not stated|don['’]t know|do not know|"
    r"refusal|not applicable|refused|n/a|na|missing|dk|ns)(?!\w)",
    re.IGNORECASE,
)


def is_nonresponse_label(value):
    """Recognize missing/skip labels without matching inside valid words."""
    if pd.isna(value):
        return True
    return bool(_NONRESPONSE_PATTERN.search(unicodedata.normalize("NFKC", str(value))))
