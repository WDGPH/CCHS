"""Data processing functions for CCHS analysis."""

import pandas as pd
import streamlit as st
from config.settings import AGE_COLUMN, MUNICIPALITY_OPTIONS, HEALTH_REGION_CODE


def create_age_groups(df, age_column=None, age_bins=None, age_labels=None):
    """
    Create age groups from the age column with flexible bin configuration.
    Automatically detects the correct age column for each cycle:
    - 2021: DHH_AGE
    - 2022/2023: AWCAGE
    - Multi-cycle harmonized: AWCAGE
    
    Args:
        df: DataFrame containing age data
        age_column: Optional specific age column name. If None, auto-detects.
        age_bins: List of bin edges (e.g., [0, 15, 25, 45, 65, 120])
        age_labels: List of labels for bins (e.g., ['0-14', '15-24', '25-44', '45-64', '65+'])
    
    Returns:
        DataFrame with AgeGroup column added
    """
    # Use default bins/labels if not provided
    if age_bins is None:
        from config.settings import DEFAULT_AGE_BINS
        age_bins = DEFAULT_AGE_BINS
    
    if age_labels is None:
        from config.settings import DEFAULT_AGE_LABELS
        age_labels = DEFAULT_AGE_LABELS
    
    # Auto-detect age column if not specified
    if age_column is None:
        if 'AWCAGE' in df.columns:
            age_column = 'AWCAGE'
        elif 'DHH_AGE' in df.columns:
            age_column = 'DHH_AGE'
        else:
            print("Warning: No age column found (DHH_AGE or AWCAGE). No age groups created.")
            result_df = df.copy()
            result_df['AgeGroup'] = None
            return result_df
    
    # Check if specified column exists
    if age_column not in df.columns:
        print(f"Warning: Column '{age_column}' not found. No age groups created.")
        result_df = df.copy()
        result_df['AgeGroup'] = None
        return result_df
    
    # Validate bins and labels
    if len(age_labels) != len(age_bins) - 1:
        st.error(f"Error: Number of labels ({len(age_labels)}) must be one less than bins ({len(age_bins)})")
        result_df = df.copy()
        result_df['AgeGroup'] = None
        return result_df
    
    # Create a new DataFrame instead of modifying a copy
    result_df = df.copy()
    
    # Create age groups using pd.cut for flexible binning
    try:
        result_df['AgeGroup'] = pd.cut(
            result_df[age_column],
            bins=age_bins,
            labels=age_labels,
            right=False,
            include_lowest=True
        )
        
        print(f"Age groups created using column: {age_column}")
        print(f"Bins: {age_bins}")
        print(f"Labels: {age_labels}")
    except Exception as e:
        st.error(f"Error creating age groups: {str(e)}")
        result_df['AgeGroup'] = None
    
    return result_df


def apply_region_filter(data, filter_by_district, filter_by_health_region, district_codes, health_region_code=HEALTH_REGION_CODE):
    """
    Dynamically apply region filters based on user selection.
    """
    # Apply municipality or district filter if district_codes is set
    if district_codes:
        filtered = data[data['GEODVCSD'].astype(int).isin([int(k) for k in district_codes.keys()])]
        st.write(f"Filtering by GEODVCSD codes: {list(district_codes.values())}")
    elif filter_by_health_region and health_region_code:
        filtered = data[data['GEODVHR4'] == health_region_code]
        st.write(f"Filtering by health region-level GEODVHR4 code: {health_region_code}")
    else:
        filtered = data
        st.write("No region filter applied; using the entire dataset.")
    return filtered


def apply_inclusion_flag_filters(data: pd.DataFrame, selected_flags: dict) -> pd.DataFrame:
    """
    Apply inclusion flag filters to the dataset.
    Works for all cycles (2021, 2022, 2023).
    
    Args:
        data: DataFrame to filter
        selected_flags: Dictionary mapping flag_name -> True/False
    
    Returns:
        Filtered DataFrame
    """
    filtered = data.copy()
    applied_filters = []
    
    # Apply each selected inclusion flag filter
    for flag, should_filter in selected_flags.items():
        if should_filter and flag in filtered.columns:
            # Filter to only include rows where flag == 1
            initial_count = len(filtered)
            filtered = filtered[filtered[flag] == 1]
            final_count = len(filtered)
            applied_filters.append(f"{flag} ({initial_count:,} → {final_count:,} records)")
    
    if applied_filters:
        st.write(f"Applied inclusion flag filters: {', '.join(applied_filters)}")
    else:
        st.write("No inclusion flag filters applied")
    
    return filtered