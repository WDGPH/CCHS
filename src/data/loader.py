"""Data loading functions for CCHS analysis."""

import os
import json
import pandas as pd
import streamlit as st
from config.settings import DATA_PATH, AVAILABLE_CYCLES


@st.cache_data
def load_cycle_data(cycle: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load main data and bootstrap data for a specific cycle."""
    data_file = os.path.join(DATA_PATH, f"hs{cycle}_on_distr.parquet")
    bootstrap_file = os.path.join(DATA_PATH, f"hs{cycle}_on_bootwt.parquet")
    
    if os.path.exists(data_file) and os.path.exists(bootstrap_file):
        data = pd.read_parquet(data_file)
        bootstrap_data = pd.read_parquet(bootstrap_file)
        return data, bootstrap_data
    else:
        st.error(f"Data files for cycle {cycle} are missing. Please check the 'data/' directory.")
        return None, None


@st.cache_data
def load_variable_descriptions(cycle: str) -> tuple[pd.DataFrame, dict]:
    """Load variable descriptions from harmonized JSON file for a specific cycle."""
    try:
        # Load from harmonized JSON file first
        json_file = os.path.join("harmonization", f"CCHS_{cycle}.json")
        if os.path.exists(json_file):
            with open(json_file, "r") as f:
                var_dict = json.load(f)
            
            # Extract descriptions from JSON structure
            descriptions_data = []
            desc_dict = {}
            
            for var_name, var_info in var_dict.items():
                description = var_info.get("description", "")
                if description:
                    descriptions_data.append({
                        'Variable': var_name,
                        'Description': description
                    })
                    desc_dict[var_name] = description
            
            # Create DataFrame from extracted data
            if descriptions_data:
                desc_df = pd.DataFrame(descriptions_data)
                return desc_df, desc_dict
        
        # Fallback to CSV file if JSON doesn't exist or is empty
        desc_file = os.path.join(DATA_PATH, f"CCHS_{cycle}_Recoded_Variables.csv")
        if os.path.exists(desc_file):
            descriptions = pd.read_csv(desc_file)
            desc_dict = dict(zip(descriptions['Variable'], descriptions['Description']))
            return descriptions, desc_dict
        
        # If neither exists, return empty
        return None, {}
        
    except Exception as e:
        st.error(f"Error loading variable descriptions for cycle {cycle}: {e}")
        return None, {}


@st.cache_data
def load_json_variable_descriptions(cycle: str) -> dict:
    """Load JSON variable descriptions for a specific cycle (legacy function for compatibility)."""
    json_file = os.path.join("harmonization", f"CCHS_{cycle}.json")
    if os.path.exists(json_file):
        with open(json_file, "r") as f:
            var_dict = json.load(f)
        return {k: v.get("description", "") for k, v in var_dict.items()}
    return {}


@st.cache_data
def load_crosswalk() -> dict:
    """Load harmonization crosswalk."""
    crosswalk_file = os.path.join("harmonization", "crosswalk.json")
    if os.path.exists(crosswalk_file):
        with open(crosswalk_file, "r") as f:
            return json.load(f)
    return {}


@st.cache_data
def load_categories() -> dict:
    """Load harmonization categories."""
    categories_file = os.path.join("harmonization", "categories.json")
    if os.path.exists(categories_file):
        with open(categories_file, "r") as f:
            return json.load(f)
    return {}


@st.cache_data
def merge_data(filtered_data, bootstrap_data):
    """Merge filtered data with bootstrap weights on 'ONT_ID'."""
    merged = pd.merge(filtered_data, bootstrap_data, on='ONT_ID', how='left')
    return merged


# Legacy function for backward compatibility
@st.cache_data
def load_data():
    """Legacy function - loads 2021 data by default for backward compatibility."""
    return load_cycle_data("2021")