"""Data processing functions for CCHS analysis."""

import pandas as pd
import streamlit as st
from config.settings import AGE_BINS, AGE_LABELS, AGE_COLUMN, MUNICIPALITY_OPTIONS, HEALTH_REGION_CODE


def create_age_groups(df, age_column='DHH_AGE'):
    """Create age groups from the specified age column."""
    if age_column not in df.columns:
        print(f"Warning: Column '{age_column}' not found. No age groups created.")
        return df
    
    # Create a new DataFrame instead of modifying a copy
    result_df = df.copy()
    
    # Create age groups using loc
    result_df.loc[:, 'AgeGroup'] = None
    result_df.loc[df[age_column].between(0, 14), 'AgeGroup'] = '0-14'
    result_df.loc[df[age_column].between(15, 24), 'AgeGroup'] = '15-24'
    result_df.loc[df[age_column].between(25, 44), 'AgeGroup'] = '25-44'
    result_df.loc[df[age_column].between(45, 64), 'AgeGroup'] = '45-64'
    result_df.loc[df[age_column] >= 65, 'AgeGroup'] = '65+'
    
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