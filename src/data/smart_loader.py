"""Smart data loader that uses precomputed data when available, falls back to real-time."""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from src.data.precompute import (
    load_precomputed_data,
    load_precomputed_bootstrap,
    load_precomputed_metadata,
    check_precompute_status,
    get_common_variables,
    PRECOMPUTE_DIR
)


def smart_load_cycle(
    cycle: str,
    crosswalk: Dict = None,
    categories: Dict = None,
    use_precompute: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict, bool]:
    """
    Smart loader that uses precomputed data when available, falls back to real-time.
    
    Args:
        cycle: Cycle name (e.g., "2021")
        crosswalk: Crosswalk dictionary (needed for real-time harmonization)
        categories: Categories dictionary (needed for real-time harmonization)
        use_precompute: Whether to attempt using precomputed data
    
    Returns:
        Tuple of (harmonized_data, bootstrap_data, metadata, is_precomputed)
    """
    is_precomputed = False
    
    # Try precomputed first if enabled
    if use_precompute:
        try:
            status = check_precompute_status([cycle])
            if status.get(cycle, False):
                data = load_precomputed_data(cycle)
                bootstrap = load_precomputed_bootstrap(cycle)
                metadata = load_precomputed_metadata(cycle)
                is_precomputed = True
                return data, bootstrap, metadata, is_precomputed
        except Exception as e:
            print(f"⚠️ Failed to load precomputed data for {cycle}: {e}")
            print("Falling back to real-time processing...")
    
    # Fall back to real-time processing
    if crosswalk is None:
        raise ValueError("Crosswalk required for real-time processing")
    
    # Import here to avoid circular dependency
    from src.data.loader import load_cycle_data
    
    # Load raw data
    raw_data, bootstrap_data = load_cycle_data(cycle)
    
    # Create harmonization mapping
    rename_dict = {}
    available_vars = []
    
    for harmonized_var, cycle_mapping in crosswalk.items():
        cycle_specific_var = cycle_mapping.get(cycle)
        
        if cycle_specific_var and cycle_specific_var != "Not Available":
            if cycle_specific_var in raw_data.columns:
                rename_dict[cycle_specific_var] = harmonized_var
                available_vars.append(harmonized_var)
    
    # Apply harmonization
    harmonized_data = raw_data.rename(columns=rename_dict)
    
    # Add CYCLE column
    harmonized_data['CYCLE'] = cycle
    
    # Create metadata
    metadata = {
        'cycle': cycle,
        'available_vars': available_vars,
        'record_count': len(harmonized_data),
        'harmonization_mapping': rename_dict,
        'realtime': True
    }
    
    return harmonized_data, bootstrap_data, metadata, is_precomputed


def smart_load_multiple_cycles(
    cycles: List[str],
    crosswalk: Dict = None,
    categories: Dict = None,
    use_precompute: bool = True
) -> Dict[str, Dict]:
    """
    Load multiple cycles using smart loading.
    
    Args:
        cycles: List of cycle years to load
        crosswalk: Crosswalk dictionary (needed for real-time fallback)
        categories: Categories dictionary (needed for real-time fallback)
        use_precompute: Whether to attempt using precomputed data
    
    Returns:
        Dict mapping cycle -> {
            'data': DataFrame,
            'bootstrap': DataFrame,
            'metadata': Dict,
            'precomputed': bool
        }
    """
    results = {}
    
    for cycle in cycles:
        try:
            data, bootstrap, metadata, is_precomputed = smart_load_cycle(
                cycle, crosswalk, categories, use_precompute
            )
            results[cycle] = {
                'data': data,
                'bootstrap': bootstrap,
                'metadata': metadata,
                'precomputed': is_precomputed
            }
        except Exception as e:
            print(f"❌ Error loading {cycle}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return results


def get_common_vars_smart(
    cycles: List[str],
    crosswalk: Dict = None,
    categories: Dict = None,
    use_precompute: bool = True
) -> List[str]:
    """
    Get common variables across cycles using smart approach.
    Uses precomputed metadata when available for speed.
    
    Args:
        cycles: List of cycle years
        crosswalk: Crosswalk dictionary (needed for real-time fallback)
        categories: Categories dictionary
        use_precompute: Whether to attempt using precomputed data
    
    Returns:
        Sorted list of common harmonized variable names
    """
    # Check if all cycles are precomputed
    if use_precompute:
        status = check_precompute_status(cycles)
        all_precomputed = all(status.get(c, False) for c in cycles)
        
        if all_precomputed:
            # Fast path - use precomputed metadata
            try:
                return get_common_variables(cycles)
            except Exception as e:
                print(f"⚠️ Failed to get common vars from precomputed: {e}")
    
    # Slow path - load and check manually
    cycle_data = smart_load_multiple_cycles(cycles, crosswalk, categories, use_precompute)
    
    if not cycle_data:
        return []
    
    # Get intersection of available vars
    all_vars = [set(result['metadata']['available_vars']) for result in cycle_data.values()]
    common = set.intersection(*all_vars) if all_vars else set()
    return sorted(list(common))


def load_and_combine_cycles_smart(
    cycles: List[str],
    crosswalk: Dict = None,
    categories: Dict = None,
    use_precompute: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load multiple cycles and combine into single DataFrames.
    Smart loader that uses precomputed data when available.
    
    Args:
        cycles: List of cycle years to load and combine
        crosswalk: Crosswalk dictionary (needed for real-time fallback)
        categories: Categories dictionary
        use_precompute: Whether to attempt using precomputed data
    
    Returns:
        Tuple of (combined_data, combined_bootstrap)
    """
    # Load all cycles
    cycle_data = smart_load_multiple_cycles(cycles, crosswalk, categories, use_precompute)
    
    if not cycle_data:
        raise ValueError("No cycles were successfully loaded")
    
    # Combine data
    combined_data_list = []
    combined_bootstrap_list = []
    
    for cycle, result in cycle_data.items():
        combined_data_list.append(result['data'])
        combined_bootstrap_list.append(result['bootstrap'])
    
    # Concatenate
    combined_data = pd.concat(combined_data_list, ignore_index=True)
    combined_bootstrap = pd.concat(combined_bootstrap_list, ignore_index=True)
    
    return combined_data, combined_bootstrap


def get_precompute_summary(cycles: List[str]) -> Dict:
    """
    Get summary of precompute status for cycles.
    
    Args:
        cycles: List of cycle years to check
    
    Returns:
        Dictionary with summary information
    """
    status = check_precompute_status(cycles)
    
    precomputed = [c for c, s in status.items() if s]
    missing = [c for c, s in status.items() if not s]
    
    summary = {
        'total_cycles': len(cycles),
        'precomputed_cycles': precomputed,
        'missing_cycles': missing,
        'all_precomputed': len(missing) == 0,
        'none_precomputed': len(precomputed) == 0,
        'partial_precomputed': 0 < len(precomputed) < len(cycles)
    }
    
    # Try to get common variables if all precomputed
    if summary['all_precomputed']:
        try:
            common_vars = get_common_variables(cycles)
            summary['common_variables_count'] = len(common_vars)
        except Exception:
            summary['common_variables_count'] = None
    
    return summary
