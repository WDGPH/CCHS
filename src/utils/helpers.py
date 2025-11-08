"""Utility helper functions for the CCHS application."""

import pandas as pd
import streamlit as st
from io import BytesIO


def format_number(num, format_type="comma"):
    """Format numbers with different styles."""
    if format_type == "comma":
        return f"{num:,}"
    elif format_type == "percentage":
        return f"{num:.2f}%"
    elif format_type == "decimal":
        return f"{num:.3f}"
    else:
        return str(num)


def create_excel_download(data: pd.DataFrame, sheet_name: str = "Analysis Results") -> bytes:
    """Create Excel file in memory for download."""
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        data.to_excel(writer, sheet_name=sheet_name, index=False)
    return excel_buffer.getvalue()


def validate_data_columns(data: pd.DataFrame, required_columns: list) -> bool:
    """Validate that required columns exist in the dataset."""
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        st.error(f"Missing required columns: {', '.join(missing_columns)}")
        return False
    return True


def safe_division(numerator, denominator, default=0):
    """Safely divide two numbers, returning default if denominator is zero."""
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ZeroDivisionError):
        return default


def filter_dataframe_by_values(df, column, values):
    """Filter dataframe by specific values in a column."""
    if column in df.columns and values:
        return df[df[column].isin(values)]
    return df


def get_memory_usage_mb(df):
    """Get memory usage of dataframe in MB."""
    return df.memory_usage(deep=True).sum() / 1024**2


def get_cycle_varname(harmonized_var: str, cycle: str, crosswalk: dict) -> str:
    """Helper to get cycle-specific variable name from harmonization crosswalk."""
    mapping = crosswalk.get(harmonized_var, {})
    return mapping.get(cycle, harmonized_var)


def get_value_label(harmonized_var: str, value, cycle: str, categories: dict) -> str:
    """Helper to get value label for cycle from harmonization categories."""
    cat = categories.get(harmonized_var, {})
    mappings = cat.get("mappings", {})
    year_map = mappings.get(str(cycle), {})
    
    # Convert value to string, but if it's a float and is_integer, cast to int first
    if isinstance(value, float) and value.is_integer():
        value_str = str(int(value))
    else:
        value_str = str(value)
    
    label = year_map.get(value_str, None)
    if label is None:
        return value_str
    return label


def get_available_harmonized_vars(crosswalk: dict, cycle: str, merged_data: pd.DataFrame) -> list:
    """Helper to get available harmonized variables for the selected cycle and data."""
    available = []
    for harmonized_var, mapping in crosswalk.items():
        varname = mapping.get(cycle)
        if varname and varname in merged_data.columns:
            available.append(harmonized_var)
    return available


def merge_descriptions(json_desc_dict: dict, csv_desc_dict: dict) -> dict:
    """Merge CSV and JSON descriptions, preferring CSV if present."""
    return {**json_desc_dict, **csv_desc_dict}


def create_multi_cycle_excel(results_df: pd.DataFrame, cycles: list) -> bytes:
    """
    Create Excel file with multiple sheets for multi-cycle results.
    
    Args:
        results_df: DataFrame with multi-cycle results (must contain 'CYCLE' column)
        cycles: List of cycles included in the results
    
    Returns:
        Excel file as bytes
    """
    excel_buffer = BytesIO()
    
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        results_df.to_excel(writer, sheet_name="Combined Results", index=False)
        
        for cycle in cycles:
            cycle_data = results_df[results_df['CYCLE'] == cycle].copy()
            if not cycle_data.empty:
                cycle_data = cycle_data.drop(columns=['CYCLE'])
                cycle_data.to_excel(writer, sheet_name=f"Cycle {cycle}", index=False)
        
        from src.analysis.comparison import create_comparison_summary
        summary_df = create_comparison_summary(results_df)
        if not summary_df.empty:
            summary_df.to_excel(writer, sheet_name="Comparison Summary", index=False)
    
    return excel_buffer.getvalue()