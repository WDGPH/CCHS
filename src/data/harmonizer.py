"""Data harmonization functions for multi-cycle CCHS analysis."""

import re
import unicodedata

import pandas as pd
from typing import Optional


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


def harmonize_variable_names(df: pd.DataFrame, cycle: str, crosswalk: dict) -> pd.DataFrame:
    """
    Rename cycle-specific variable names to harmonized names using crosswalk.
    
    Args:
        df: DataFrame with cycle-specific column names
        cycle: Cycle year (e.g., "2021", "2022", "2023")
        crosswalk: Crosswalk dictionary mapping harmonized_var -> {cycle: cycle_specific_var}
    
    Returns:
        DataFrame with harmonized column names (original columns preserved if not in crosswalk)
    """
    result_df = df.copy()
    rename_dict = {}
    
    for harmonized_var, cycle_mapping in crosswalk.items():
        cycle_specific_var = cycle_mapping.get(cycle)
        if cycle_specific_var and cycle_specific_var in result_df.columns:
            rename_dict[cycle_specific_var] = harmonized_var
    
    result_df = result_df.rename(columns=rename_dict)
    return result_df


def harmonize_values(df: pd.DataFrame, cycle: str, categories: dict, harmonized_vars: Optional[list] = None) -> pd.DataFrame:
    """
    Add harmonized label columns for categorical variables while preserving original values.
    
    Args:
        df: DataFrame with harmonized variable names
        cycle: Cycle year (e.g., "2021", "2022", "2023")
        categories: Categories dictionary mapping harmonized_var -> {mappings: {cycle: {value: label}}}
        harmonized_vars: Optional list of harmonized variables to process. If None, processes all variables in categories.
    
    Returns:
        DataFrame with added {var}_label columns containing harmonized labels
    """
    result_df = df.copy()
    
    vars_to_process = harmonized_vars if harmonized_vars else list(categories.keys())
    
    for harmonized_var in vars_to_process:
        if harmonized_var not in result_df.columns:
            continue
        
        cat_info = categories.get(harmonized_var, {})
        mappings = cat_info.get("mappings", {})
        cycle_mapping = mappings.get(cycle, {})
        
        if not cycle_mapping:
            continue
        
        label_col = f"{harmonized_var}_label"
        
        def map_value(val):
            if pd.isna(val):
                return None
            val_str = str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
            return cycle_mapping.get(val_str, val_str)
        
        result_df[label_col] = result_df[harmonized_var].apply(map_value)
    
    return result_df


def apply_harmonization(df: pd.DataFrame, cycle: str, crosswalk: dict, categories: dict, harmonized_vars: Optional[list] = None) -> pd.DataFrame:
    """
    Apply both variable name and value harmonization to a DataFrame.
    
    Args:
        df: DataFrame with cycle-specific column names and values
        cycle: Cycle year (e.g., "2021", "2022", "2023")
        crosswalk: Crosswalk dictionary for variable name mapping
        categories: Categories dictionary for value label mapping
        harmonized_vars: Optional list of harmonized variables to process for value harmonization
    
    Returns:
        DataFrame with harmonized column names and added label columns
    """
    result_df = harmonize_variable_names(df, cycle, crosswalk)
    result_df = harmonize_values(result_df, cycle, categories, harmonized_vars)
    return result_df


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
