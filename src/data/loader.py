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
            
            # Ensure all variables are included, even if description is missing
            for var_name in var_dict.keys():
                if var_name not in desc_dict:
                    descriptions_data.append({
                        'Variable': var_name,
                        'Description': "No description available"
                    })
                    desc_dict[var_name] = "No description available"
            
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


@st.cache_data
def load_multi_cycle_data(cycles: list, crosswalk: dict, categories: dict):
    """
    Load and harmonize data from multiple cycles using pre-computed crosswalk.
    This uses simple column renaming (no value transformation) for performance.
    
    Args:
        cycles: List of cycle years to load (e.g., ["2021", "2022", "2023"])
        crosswalk: Crosswalk dictionary mapping harmonized_var -> {cycle: cycle_specific_var}
        categories: Categories dictionary (not used, kept for compatibility)
    
    Returns:
        Tuple of (combined_data, combined_bootstrap_data) or (None, None) if error
    """
    if not cycles:
        st.error("No cycles specified for multi-cycle loading.")
        return None, None
    
    if not crosswalk:
        st.warning("No crosswalk provided. Loading cycles without harmonization.")
    
    combined_data_list = []
    combined_bootstrap_list = []
    
    for cycle in cycles:
        # Load raw data for this cycle
        data, bootstrap_data = load_cycle_data(cycle)
        if data is None or bootstrap_data is None:
            st.warning(f"Skipping cycle {cycle} due to missing data files.")
            continue
        
        # Build reverse mapping: cycle_specific_var -> harmonized_var for this cycle
        # This is fast O(n) operation on crosswalk dictionary
        rename_dict = {}
        if crosswalk:
            for harmonized_var, cycle_mapping in crosswalk.items():
                cycle_specific_var = cycle_mapping.get(cycle)
                if cycle_specific_var and cycle_specific_var in data.columns:
                    rename_dict[cycle_specific_var] = harmonized_var
        
        # Apply harmonization - just column rename, no value transformation (fast!)
        harmonized_data = data.rename(columns=rename_dict) if rename_dict else data.copy()
        harmonized_data['CYCLE'] = cycle
        
        combined_data_list.append(harmonized_data)
        combined_bootstrap_list.append(bootstrap_data)
    
    if not combined_data_list:
        st.error("No valid cycles could be loaded.")
        return None, None
    
    # Combine all cycles (fast concat operation)
    combined_data = pd.concat(combined_data_list, ignore_index=True)
    combined_bootstrap = pd.concat(combined_bootstrap_list, ignore_index=True)
    
    return combined_data, combined_bootstrap


# Legacy function for backward compatibility
@st.cache_data
def load_data():
    """Legacy function - loads 2021 data by default for backward compatibility."""
    return load_cycle_data("2021")