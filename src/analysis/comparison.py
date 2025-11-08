"""Comparative analysis functions for multi-cycle CCHS data."""

import pandas as pd
import numpy as np
from typing import Optional


def compare_cycles(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot results to show cycles side-by-side for comparison.
    
    Args:
        results_df: DataFrame with columns including 'Variable', 'Value', 'CYCLE', 'Prevalence', etc.
    
    Returns:
        Pivoted DataFrame with cycles as columns
    """
    if 'CYCLE' not in results_df.columns:
        return results_df
    
    pivot_df = results_df.pivot_table(
        index=['Variable', 'Value'],
        columns='CYCLE',
        values='Prevalence',
        aggfunc='first'
    ).reset_index()
    
    return pivot_df


def calculate_change(cycle1_val: float, cycle2_val: float) -> float:
    """
    Calculate percentage point change between two cycles.
    
    Args:
        cycle1_val: Prevalence value from first cycle
        cycle2_val: Prevalence value from second cycle
    
    Returns:
        Percentage point change (cycle2 - cycle1)
    """
    if pd.isna(cycle1_val) or pd.isna(cycle2_val):
        return np.nan
    return cycle2_val - cycle1_val


def calculate_percent_change(cycle1_val: float, cycle2_val: float) -> float:
    """
    Calculate percentage change between two cycles.
    
    Args:
        cycle1_val: Prevalence value from first cycle
        cycle2_val: Prevalence value from second cycle
    
    Returns:
        Percentage change ((cycle2 - cycle1) / cycle1 * 100)
    """
    if pd.isna(cycle1_val) or pd.isna(cycle2_val) or cycle1_val == 0:
        return np.nan
    return ((cycle2_val - cycle1_val) / cycle1_val) * 100


def calculate_trend(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate trend direction (increasing/decreasing/stable) across cycles.
    
    Args:
        results_df: DataFrame with 'CYCLE', 'Variable', 'Value', 'Prevalence' columns
    
    Returns:
        DataFrame with added 'Trend' column indicating direction
    """
    if 'CYCLE' not in results_df.columns:
        return results_df
    
    result_df = results_df.copy()
    result_df['Trend'] = None
    
    for (variable, value), group in result_df.groupby(['Variable', 'Value']):
        if len(group) < 2:
            continue
        
        sorted_group = group.sort_values('CYCLE')
        prevalences = sorted_group['Prevalence'].values
        
        if len(prevalences) == 2:
            if prevalences[1] > prevalences[0] * 1.05:
                trend = 'Increasing'
            elif prevalences[1] < prevalences[0] * 0.95:
                trend = 'Decreasing'
            else:
                trend = 'Stable'
        else:
            slope = np.polyfit(range(len(prevalences)), prevalences, 1)[0]
            if slope > 0.1:
                trend = 'Increasing'
            elif slope < -0.1:
                trend = 'Decreasing'
            else:
                trend = 'Stable'
        
        result_df.loc[group.index, 'Trend'] = trend
    
    return result_df


def test_significance(cycle1_results: pd.DataFrame, cycle2_results: pd.DataFrame, 
                      variable: str, value: Optional[str] = None) -> dict:
    """
    Test statistical significance of difference between two cycles.
    
    Uses overlapping confidence intervals as a simple test.
    More sophisticated tests could be added later.
    
    Args:
        cycle1_results: Results DataFrame for first cycle
        cycle2_results: Results DataFrame for second cycle
        variable: Variable name to test
        value: Optional specific value to test
    
    Returns:
        Dictionary with test results including 'significant' boolean
    """
    filter1 = cycle1_results['Variable'] == variable
    filter2 = cycle2_results['Variable'] == variable
    
    if value is not None:
        filter1 = filter1 & (cycle1_results['Value'] == value)
        filter2 = filter2 & (cycle2_results['Value'] == value)
    
    result1 = cycle1_results[filter1].iloc[0] if len(cycle1_results[filter1]) > 0 else None
    result2 = cycle2_results[filter2].iloc[0] if len(cycle2_results[filter2]) > 0 else None
    
    if result1 is None or result2 is None:
        return {'significant': False, 'reason': 'Missing data'}
    
    ci1_lower = result1.get('CI Lower', np.nan)
    ci1_upper = result1.get('CI Upper', np.nan)
    ci2_lower = result2.get('CI Lower', np.nan)
    ci2_upper = result2.get('CI Upper', np.nan)
    
    if pd.isna(ci1_lower) or pd.isna(ci1_upper) or pd.isna(ci2_lower) or pd.isna(ci2_upper):
        return {'significant': False, 'reason': 'Missing confidence intervals'}
    
    overlap = not (ci1_upper < ci2_lower or ci2_upper < ci1_lower)
    
    return {
        'significant': not overlap,
        'overlap': overlap,
        'cycle1_ci': (ci1_lower, ci1_upper),
        'cycle2_ci': (ci2_lower, ci2_upper),
        'cycle1_prevalence': result1.get('Prevalence', np.nan),
        'cycle2_prevalence': result2.get('Prevalence', np.nan)
    }


def create_comparison_summary(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a summary table comparing cycles.
    
    Args:
        results_df: DataFrame with cycle comparison results
    
    Returns:
        Summary DataFrame with comparison statistics
    """
    if 'CYCLE' not in results_df.columns:
        return pd.DataFrame()
    
    summary_data = []
    
    for (variable, value), group in results_df.groupby(['Variable', 'Value']):
        if len(group) < 2:
            continue
        
        sorted_group = group.sort_values('CYCLE')
        cycles = sorted_group['CYCLE'].tolist()
        prevalences = sorted_group['Prevalence'].tolist()
        
        first_cycle = cycles[0]
        last_cycle = cycles[-1]
        first_prev = prevalences[0]
        last_prev = prevalences[-1]
        
        change_pp = calculate_change(first_prev, last_prev)
        change_pct = calculate_percent_change(first_prev, last_prev)
        
        trend_df = calculate_trend(group)
        trend = trend_df['Trend'].iloc[0] if 'Trend' in trend_df.columns else None
        
        summary_data.append({
            'Variable': variable,
            'Value': value,
            'First Cycle': first_cycle,
            'Last Cycle': last_cycle,
            'First Prevalence': first_prev,
            'Last Prevalence': last_prev,
            'Change (pp)': change_pp,
            'Change (%)': change_pct,
            'Trend': trend
        })
    
    return pd.DataFrame(summary_data)

