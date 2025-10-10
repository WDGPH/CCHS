"""Data processing functions for CCHS analysis."""

import pandas as pd
import streamlit as st
from config.settings import AGE_BINS, AGE_LABELS, AGE_COLUMN, MUNICIPALITY_OPTIONS, HEALTH_REGION_CODE


def create_age_groups(df, age_col=AGE_COLUMN):
    """Create age groups from age column."""
    # Check if the age column exists
    if age_col not in df.columns:
        print(f"Warning: Column '{age_col}' not found. Skipping age group creation.")
        df['AgeGroup'] = None  # Optionally, add a placeholder column
        return df

    # Create age groups
    df['AgeGroup'] = pd.cut(df[age_col], bins=AGE_BINS, labels=AGE_LABELS, right=False)
    return df


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