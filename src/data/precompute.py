"""Precompute harmonized datasets for multi-cycle analysis."""

import pandas as pd
import numpy as np
from pathlib import Path
import pickle
import json
from typing import Dict, List, Tuple, Optional
import streamlit as st


# Default precompute directory
PRECOMPUTE_DIR = Path("data/precomputed")


def check_precompute_status(cycles: List[str], save_dir: Path = PRECOMPUTE_DIR) -> Dict[str, bool]:
    """
    Check which cycles have been precomputed.
    
    Args:
        cycles: List of cycle years (e.g., ["2021", "2022", "2023"])
        save_dir: Directory where precomputed data is stored
    
    Returns:
        Dictionary mapping cycle -> True/False (precomputed status)
    """
    status = {}
    
    for cycle in cycles:
        data_path = save_dir / f"harmonized_data_{cycle}.parquet"
        meta_path = save_dir / f"metadata_{cycle}.pkl"
        status[cycle] = data_path.exists() and meta_path.exists()
    
    return status


def load_precomputed_data(cycle: str, save_dir: Path = PRECOMPUTE_DIR) -> pd.DataFrame:
    """
    Load precomputed harmonized data for a cycle.
    
    Args:
        cycle: Cycle year (e.g., "2021")
        save_dir: Directory where precomputed data is stored
    
    Returns:
        DataFrame with harmonized variables
    
    Raises:
        FileNotFoundError: If precomputed data doesn't exist
    """
    path = save_dir / f"harmonized_data_{cycle}.parquet"
    
    if not path.exists():
        raise FileNotFoundError(f"Precomputed data not found: {path}")
    
    return pd.read_parquet(path)


def load_precomputed_bootstrap(cycle: str, save_dir: Path = PRECOMPUTE_DIR) -> pd.DataFrame:
    """
    Load precomputed bootstrap weights for a cycle.
    
    Args:
        cycle: Cycle year (e.g., "2021")
        save_dir: Directory where precomputed data is stored
    
    Returns:
        DataFrame with bootstrap weights (ONT_ID and BSW columns)
    
    Raises:
        FileNotFoundError: If precomputed data doesn't exist
    """
    path = save_dir / f"harmonized_bootstrap_{cycle}.parquet"
    
    if not path.exists():
        raise FileNotFoundError(f"Precomputed bootstrap data not found: {path}")
    
    return pd.read_parquet(path)


def load_precomputed_metadata(cycle: str, save_dir: Path = PRECOMPUTE_DIR) -> Dict:
    """
    Load metadata for precomputed cycle.
    
    Args:
        cycle: Cycle year (e.g., "2021")
        save_dir: Directory where precomputed data is stored
    
    Returns:
        Dictionary with metadata (available_vars, record_count, etc.)
    
    Raises:
        FileNotFoundError: If metadata doesn't exist
    """
    path = save_dir / f"metadata_{cycle}.pkl"
    
    if not path.exists():
        raise FileNotFoundError(f"Metadata not found: {path}")
    
    with open(path, 'rb') as f:
        return pickle.load(f)


def get_common_variables(cycles: List[str], save_dir: Path = PRECOMPUTE_DIR) -> List[str]:
    """
    Get variables available across all selected cycles using precomputed metadata.
    
    Args:
        cycles: List of cycle years
        save_dir: Directory where precomputed data is stored
    
    Returns:
        Sorted list of common harmonized variable names
    """
    if not cycles:
        return []
    
    # Load metadata for each cycle
    all_vars = []
    for cycle in cycles:
        try:
            meta = load_precomputed_metadata(cycle, save_dir)
            all_vars.append(set(meta['available_vars']))
        except FileNotFoundError:
            return []  # Missing precomputed data
    
    # Find intersection
    common = set.intersection(*all_vars) if all_vars else set()
    return sorted(list(common))


@st.cache_data
def precompute_cycle_data(
    cycle: str,
    crosswalk: Dict,
    categories: Dict,
    data_path: str = "data",
    save_dir: Path = PRECOMPUTE_DIR
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """
    Precompute harmonized data for a single cycle.
    
    Creates:
    - harmonized_data_{cycle}.parquet: Harmonized survey data
    - harmonized_bootstrap_{cycle}.parquet: Bootstrap weights with ONT_ID
    - metadata_{cycle}.pkl: Variable metadata and availability
    
    Args:
        cycle: Cycle year (e.g., "2021")
        crosswalk: Crosswalk dictionary for variable harmonization
        categories: Categories dictionary for value label harmonization
        data_path: Path to raw data files
        save_dir: Directory to save precomputed files
    
    Returns:
        Tuple of (harmonized_data, harmonized_bootstrap, metadata)
    """
    import os
    print(f"Precomputing {cycle}...")
    
    # Create output directory if needed
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Load raw data
    data_file = os.path.join(data_path, f"hs{cycle}_on_distr.parquet")
    bootstrap_file = os.path.join(data_path, f"hs{cycle}_on_bootwt.parquet")
    
    if not os.path.exists(data_file) or not os.path.exists(bootstrap_file):
        raise FileNotFoundError(f"Raw data files not found for cycle {cycle}")
    
    data = pd.read_parquet(data_file)
    bootstrap_data = pd.read_parquet(bootstrap_file)
    
    # Create harmonization mapping for this cycle
    rename_dict = {}
    available_vars = []
    
    for harmonized_var, cycle_mapping in crosswalk.items():
        cycle_specific_var = cycle_mapping.get(cycle)
        
        if cycle_specific_var and cycle_specific_var != "Not Available":
            if cycle_specific_var in data.columns:
                rename_dict[cycle_specific_var] = harmonized_var
                available_vars.append(harmonized_var)
    
    # Apply harmonization (rename columns)
    harmonized_data = data.rename(columns=rename_dict)
    
    # Handle duplicate columns (keep first occurrence only)
    # This can happen when multiple cycle-specific variables map to same harmonized name
    if harmonized_data.columns.duplicated().any():
        duplicate_cols = harmonized_data.columns[harmonized_data.columns.duplicated()].unique().tolist()
        print(f"   ⚠️  Warning: Removing {len(duplicate_cols)} duplicate columns: {duplicate_cols[:10]}{'...' if len(duplicate_cols) > 10 else ''}")
        harmonized_data = harmonized_data.loc[:, ~harmonized_data.columns.duplicated(keep='first')]
    
    # Add CYCLE column for multi-cycle identification
    harmonized_data['CYCLE'] = cycle
    
    # Keep only harmonized columns plus core variables
    core_vars = ['ONT_ID', 'WTS_S', 'GEODVHR4', 'GEODVCSD']
    # Add age column (varies by cycle)
    if 'DHH_AGE' in harmonized_data.columns:
        core_vars.append('DHH_AGE')
    if 'AWCAGE' in harmonized_data.columns:
        core_vars.append('AWCAGE')
    
    # Keep harmonized vars + core vars that exist
    cols_to_keep = list(set(available_vars + core_vars + ['CYCLE']) & set(harmonized_data.columns))
    harmonized_data = harmonized_data[cols_to_keep]
    
    # Bootstrap data doesn't need harmonization (just ONT_ID and BSW columns)
    harmonized_bootstrap = bootstrap_data.copy()
    
    # Save harmonized data
    output_path = save_dir / f"harmonized_data_{cycle}.parquet"
    harmonized_data.to_parquet(output_path, index=False)
    
    # Save harmonized bootstrap
    bootstrap_output_path = save_dir / f"harmonized_bootstrap_{cycle}.parquet"
    harmonized_bootstrap.to_parquet(bootstrap_output_path, index=False)
    
    # Save metadata
    metadata = {
        'cycle': cycle,
        'available_vars': available_vars,
        'record_count': len(harmonized_data),
        'core_vars': core_vars,
        'precompute_date': pd.Timestamp.now().isoformat(),
        'harmonization_mapping': rename_dict
    }
    
    metadata_path = save_dir / f"metadata_{cycle}.pkl"
    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata, f)
    
    print(f"✅ {cycle}: {len(available_vars)} variables, {len(harmonized_data):,} records")
    print(f"   Saved to: {output_path}")
    
    return harmonized_data, harmonized_bootstrap, metadata


def precompute_all_cycles(
    cycles: List[str],
    crosswalk: Dict,
    categories: Dict,
    data_path: str = "data",
    save_dir: Path = PRECOMPUTE_DIR
) -> Dict[str, Dict]:
    """
    Precompute data for all specified cycles.
    
    Args:
        cycles: List of cycle years to precompute
        crosswalk: Crosswalk dictionary
        categories: Categories dictionary
        data_path: Path to raw data files
        save_dir: Directory to save precomputed files
    
    Returns:
        Dictionary mapping cycle -> {'data': DataFrame, 'bootstrap': DataFrame, 'metadata': Dict}
    """
    results = {}
    
    for cycle in cycles:
        try:
            data, bootstrap, meta = precompute_cycle_data(
                cycle, crosswalk, categories, data_path, save_dir
            )
            results[cycle] = {
                'data': data,
                'bootstrap': bootstrap,
                'metadata': meta
            }
        except Exception as e:
            print(f"❌ Failed to precompute {cycle}: {e}")
            import traceback
            traceback.print_exc()
    
    return results


def load_variable_availability_index(save_dir: Path = PRECOMPUTE_DIR) -> Dict[str, List[str]]:
    """
    Load the variable availability index (which variables exist in which cycles).
    
    Args:
        save_dir: Directory where precomputed data is stored
    
    Returns:
        Dictionary mapping variable_name -> [list of cycles where it exists]
    """
    index_path = save_dir / "variable_availability.json"
    
    if not index_path.exists():
        raise FileNotFoundError(f"Variable availability index not found: {index_path}")
    
    with open(index_path, 'r') as f:
        return json.load(f)


def create_variable_availability_index(
    cycles: List[str],
    save_dir: Path = PRECOMPUTE_DIR
) -> Dict[str, List[str]]:
    """
    Create a variable availability index from precomputed metadata.
    
    Args:
        cycles: List of cycles to include in index
        save_dir: Directory where precomputed data is stored
    
    Returns:
        Dictionary mapping variable_name -> [list of cycles where it exists]
    """
    availability_index = {}
    
    for cycle in cycles:
        try:
            meta = load_precomputed_metadata(cycle, save_dir)
            for var in meta['available_vars']:
                if var not in availability_index:
                    availability_index[var] = []
                availability_index[var].append(cycle)
        except FileNotFoundError:
            print(f"⚠️ Metadata not found for {cycle}, skipping...")
            continue
    
    # Save index
    index_path = save_dir / "variable_availability.json"
    with open(index_path, 'w') as f:
        json.dump(availability_index, f, indent=2)
    
    print(f"✅ Variable availability index created: {len(availability_index)} variables")
    print(f"   Saved to: {index_path}")
    
    return availability_index


def validate_precomputed_data(cycles: List[str], save_dir: Path = PRECOMPUTE_DIR) -> Dict[str, bool]:
    """
    Validate that precomputed data exists and is loadable for specified cycles.
    
    Args:
        cycles: List of cycles to validate
        save_dir: Directory where precomputed data is stored
    
    Returns:
        Dictionary mapping cycle -> True (valid) or False (invalid/missing)
    """
    validation = {}
    
    for cycle in cycles:
        try:
            # Try loading data
            data = load_precomputed_data(cycle, save_dir)
            bootstrap = load_precomputed_bootstrap(cycle, save_dir)
            metadata = load_precomputed_metadata(cycle, save_dir)
            
            # Basic validation checks
            checks = [
                len(data) > 0,
                'CYCLE' in data.columns,
                'ONT_ID' in data.columns,
                len(bootstrap) > 0,
                'ONT_ID' in bootstrap.columns,
                len(metadata.get('available_vars', [])) > 0,
                metadata.get('cycle') == cycle
            ]
            
            validation[cycle] = all(checks)
            
            if validation[cycle]:
                print(f"✅ {cycle}: Valid ({len(data):,} records, {len(metadata['available_vars'])} vars)")
            else:
                print(f"❌ {cycle}: Failed validation checks")
                
        except Exception as e:
            print(f"❌ {cycle}: {e}")
            validation[cycle] = False
    
    return validation
