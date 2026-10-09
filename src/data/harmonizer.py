"""Data harmonization functions for multi-cycle CCHS analysis."""

import difflib
import re
import unicodedata
from typing import Optional

import pandas as pd


POOLED_VALUE_COLUMN = "__POOLED_HARMONIZED_VALUE__"


def _category_key(value):
    if pd.isna(value):
        return None
    key = str(value).strip()
    # Survey files often store integer codes as floats while dictionaries use
    # zero-padded strings. Normalize both sides without rounding other codes.
    if re.fullmatch(r"[+-]?\d+(?:\.0+)?", key):
        return str(int(key.partition(".")[0]))
    return key


def _normalize_category_mapping(mapping, variable, cycle):
    normalized = {}
    for code, label in mapping.items():
        key = _category_key(code)
        if key is None:
            raise ValueError(f"Category mapping for {variable} in cycle {cycle} has a missing code.")
        if key in normalized and normalized[key] != label:
            raise ValueError(
                f"Category mapping for {variable} in cycle {cycle} has conflicting "
                f"labels for equivalent code {key}."
            )
        normalized[key] = label
    return normalized


def _normalize_metadata_text(value):
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


def _validated_category_mapping(mapping, variable, cycle):
    normalized = _normalize_category_mapping(mapping, variable, cycle)
    label_codes = {}
    for code, label in normalized.items():
        label_key = _normalize_metadata_text(label)
        if not isinstance(label, str) or not label_key:
            raise ValueError(
                f"Category mapping for {variable} in cycle {cycle} has an empty "
                f"or malformed label for code {code}."
            )
        if label_key in label_codes:
            raise ValueError(
                f"Category mapping for {variable} in cycle {cycle} has ambiguous "
                f"duplicate labels for codes {label_codes[label_key]} and {code}. "
                "Review the data dictionary before pooling."
            )
        label_codes[label_key] = code
    return normalized


def assess_harmonized_compatibility(
    variable: str,
    cycles: list,
    crosswalk: dict,
    cycle_variable_info: dict,
):
    """Return whether a crosswalk entry is safe to pool and the reason.

    Availability is not enough for pooling. This conservative check requires
    equivalent normalized descriptions and equivalent category-label sets in
    every selected cycle. Continuous variables are accepted when all cycles
    consistently have no categorical metadata.
    """
    variable_crosswalk = crosswalk.get(variable, {})
    metadata = []
    for cycle_value in cycles:
        cycle = str(cycle_value)
        cycle_variable = variable_crosswalk.get(cycle)
        if not cycle_variable:
            return False, f"No crosswalk variable for cycle {cycle}."
        variable_info = cycle_variable_info.get(cycle, {}).get(cycle_variable)
        if not variable_info:
            return False, f"No data-dictionary metadata for {cycle_variable} in {cycle}."
        description = _normalize_metadata_text(variable_info.get("description"))
        if not description:
            return False, f"No description for {cycle_variable} in cycle {cycle}."
        try:
            mapping = _validated_category_mapping(
                variable_info.get("categories", {}), variable, cycle
            )
        except ValueError as error:
            return False, str(error)
        category_labels = {_normalize_metadata_text(label) for label in mapping.values()}
        metadata.append((cycle, cycle_variable, description, category_labels))

    descriptions = {item[2] for item in metadata}
    if len(descriptions) != 1:
        details = "; ".join(
            f"{cycle} {cycle_variable}"
            for cycle, cycle_variable, _, _ in metadata
        )
        return False, f"Descriptions differ across mapped variables ({details})."

    category_sets = [item[3] for item in metadata]
    categorical_cycles = [
        metadata[index][0]
        for index, labels in enumerate(category_sets)
        if labels
    ]
    if categorical_cycles and len(categorical_cycles) != len(metadata):
        missing = [
            metadata[index][0]
            for index, labels in enumerate(category_sets)
            if not labels
        ]
        return False, (
            "Categorical metadata is missing for cycle(s): "
            + ", ".join(missing)
            + "."
        )
    if category_sets and any(labels != category_sets[0] for labels in category_sets[1:]):
        return False, "Response category labels differ across cycles."

    return True, "Descriptions and category structures match across cycles."


def filter_poolable_variables(
    variables: list,
    cycles: list,
    crosswalk: dict,
    cycle_variable_info: dict,
):
    """Split common columns into poolable variables and incompatibility reasons."""
    poolable = []
    issues = {}
    for variable in variables:
        compatible, reason = assess_harmonized_compatibility(
            variable, cycles, crosswalk, cycle_variable_info
        )
        if compatible:
            poolable.append(variable)
        else:
            issues[variable] = reason
    return poolable, issues


def prepare_pooled_variable(
    data: pd.DataFrame,
    variable: str,
    categories: dict,
    cycle_col: str = "CYCLE",
    cycle_variable_info: Optional[dict] = None,
    crosswalk: Optional[dict] = None,
):
    """Prepare comparable response values for cycle pooling.

    Cycle-specific data-dictionary categories are authoritative when supplied;
    the generated categories file is only a fallback. When category mappings
    exist, every observed cycle and non-null value must be mapped. This prevents
    unlike codes from being silently pooled. If no selected cycle has mappings,
    shared raw values are retained (for continuous variables and stable codes).

    Returns a copied frame, the analysis column name, and whether labels were
    harmonized.
    """
    if variable not in data.columns or cycle_col not in data.columns:
        raise ValueError(
            f"Pooling requires both {variable!r} and {cycle_col!r} columns."
        )

    cycles = data[cycle_col].dropna().astype(str).str.strip().unique().tolist()
    if cycle_variable_info is not None:
        mappings = {}
        variable_crosswalk = (crosswalk or {}).get(variable, {})
        for cycle in cycles:
            cycle_variable = variable_crosswalk.get(cycle) or variable
            variable_info = cycle_variable_info.get(cycle, {}).get(
                cycle_variable, {}
            )
            mappings[cycle] = variable_info.get("categories", {})
    else:
        mappings = (
            categories.get(variable, {}).get("mappings", {})
            if categories
            else {}
        )
    cycle_mappings = {
        cycle: _validated_category_mapping(mappings.get(cycle, {}), variable, cycle)
        for cycle in cycles
    }
    cycles_with_mappings = [cycle for cycle, mapping in cycle_mappings.items() if mapping]

    if not cycles_with_mappings:
        return data, variable, False
    if len(cycles_with_mappings) != len(cycles):
        missing = sorted(set(cycles) - set(cycles_with_mappings))
        raise ValueError(
            f"Category harmonization for {variable} is incomplete; no mapping "
            f"is available for cycle(s): {', '.join(missing)}."
        )

    # Use the same identity rule for compatibility checks and response grouping.
    # Choose stable display labels regardless of cycle selection order.
    canonical_labels = {}
    for cycle in sorted(cycle_mappings):
        for label in cycle_mappings[cycle].values():
            canonical_labels.setdefault(
                _normalize_metadata_text(label),
                " ".join(unicodedata.normalize("NFKC", label).split()),
            )

    result = data.copy()
    result[POOLED_VALUE_COLUMN] = pd.NA
    for cycle, mapping in cycle_mappings.items():
        mask = result[cycle_col].astype(str).str.strip().eq(cycle)
        values = result.loc[mask, variable]
        keys = values.map(_category_key)
        unmapped = sorted(set(keys.dropna()) - set(mapping))
        if unmapped:
            preview = ", ".join(unmapped[:5])
            suffix = " ..." if len(unmapped) > 5 else ""
            raise ValueError(
                f"Category harmonization for {variable} has unmapped value(s) "
                f"in cycle {cycle}: {preview}{suffix}."
            )
        canonical_mapping = {
            code: canonical_labels[_normalize_metadata_text(label)]
            for code, label in mapping.items()
        }
        result.loc[mask, POOLED_VALUE_COLUMN] = keys.map(canonical_mapping).to_numpy()

    return result, POOLED_VALUE_COLUMN, True


def build_crosswalk(cycles: list, descriptions: dict, cutoff: float = 0.6) -> dict:
    """
    Build a crosswalk mapping reference-cycle variable names to each cycle's
    matching variable name, by fuzzy-matching variable descriptions.

    The last entry in `cycles` is treated as the reference cycle: every
    other cycle's variable is matched against each reference variable's
    description via difflib.get_close_matches (single best match). This is
    a heuristic textual match, not an authoritative concordance - unmatched
    or ambiguous descriptions are recorded as None and should be reviewed.

    Args:
        cycles: Cycle years in order, with the reference cycle last
        descriptions: Dict mapping cycle -> {variable_name: description}
        cutoff: difflib similarity cutoff (0-1) for a match to count

    Returns:
        Dict mapping reference_var -> {cycle: cycle_specific_var_or_None}
    """
    reference_cycle = cycles[-1]
    reference_vars = descriptions[reference_cycle]

    crosswalk = {}
    for ref_var, ref_desc in reference_vars.items():
        crosswalk[ref_var] = {reference_cycle: ref_var}
        for cycle in cycles[:-1]:
            candidates = descriptions[cycle]
            best_match = difflib.get_close_matches(ref_desc, candidates.values(), n=1, cutoff=cutoff)
            if best_match:
                for var, desc in candidates.items():
                    if desc == best_match[0]:
                        crosswalk[ref_var][cycle] = var
                        break
            else:
                crosswalk[ref_var][cycle] = None

    return crosswalk


def auto_harmonize(label: str) -> str:
    """
    Normalize a raw codebook category label into a shared harmonized category.

    Order matters: "not stated", "valid skip", "don't know", and "female"
    each contain "no" or "male" as a substring (e.g. "**no**t stated",
    "fe**male**"), so the more specific phrases must be checked before the
    shorter "no"/"male" rules or they get misclassified.
    """
    l = label.lower()
    if "not stated" in l:
        return "Not stated"
    if "valid skip" in l:
        return "Valid skip"
    if "don’t know" in l or "don't know" in l:
        return "Don't know"
    if "female" in l:
        return "Female"
    if "male" in l:
        return "Male"
    if "yes" in l:
        return "Yes"
    if "no" in l:
        return "No"
    return label.strip()


def get_common_harmonized_vars(cycles: list, crosswalk: dict, data_dict: dict) -> list:
    """
    Get harmonized variables that exist in all specified cycles.
    
    Args:
        cycles: List of cycle years
        crosswalk: Crosswalk dictionary
        data_dict: Dictionary mapping cycle -> DataFrame (with cycle-specific column names)
    
    Returns:
        List of harmonized variable names available in all cycles
    """
    common_vars = []
    
    for harmonized_var, cycle_mapping in crosswalk.items():
        available_in_all = True
        for cycle in cycles:
            cycle_specific_var = cycle_mapping.get(cycle)
            if not cycle_specific_var or cycle_specific_var not in data_dict[cycle].columns:
                available_in_all = False
                break
        
        if available_in_all:
            common_vars.append(harmonized_var)
    
    return common_vars
