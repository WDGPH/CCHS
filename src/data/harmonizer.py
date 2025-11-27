"""Data harmonization functions for multi-cycle CCHS analysis."""

import pandas as pd
from typing import Optional


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

