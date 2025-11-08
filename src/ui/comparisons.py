"""Comparative visualization functions for multi-cycle CCHS analysis."""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import Optional


def plot_cycle_trends(results_df: pd.DataFrame, variable: str, variable_description: Optional[str] = None):
    """
    Create a line chart showing prevalence trends over cycles.
    
    Args:
        results_df: DataFrame with 'CYCLE', 'Variable', 'Value', 'Prevalence', 'CI Lower', 'CI Upper', optionally 'Label'
        variable: Variable name to plot
        variable_description: Optional variable description to display in title
    """
    if 'CYCLE' not in results_df.columns:
        st.warning("No cycle information found in results.")
        return None
    
    var_data = results_df[results_df['Variable'] == variable].copy()
    if var_data.empty:
        st.warning(f"No data found for variable {variable}")
        return None
    
    var_data = var_data.sort_values(['CYCLE', 'Value'])
    
    # Use Label column if available, otherwise use Value
    use_labels = 'Label' in var_data.columns
    
    # Use variable description in title if available
    title_var = variable_description if variable_description else variable
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for value in var_data['Value'].unique():
        value_data = var_data[var_data['Value'] == value].sort_values('CYCLE')
        cycles = value_data['CYCLE'].tolist()
        prevalences = value_data['Prevalence'].tolist()
        ci_lower = value_data['CI Lower'].tolist()
        ci_upper = value_data['CI Upper'].tolist()
        
        # Use label if available, otherwise use value
        if use_labels:
            label_val = value_data['Label'].iloc[0]
            label = label_val if pd.notna(label_val) else str(value)
        else:
            label = str(value)
        
        ax.plot(cycles, prevalences, marker='o', label=label, linewidth=2, markersize=8)
        ax.fill_between(cycles, ci_lower, ci_upper, alpha=0.2)
    
    ax.set_xlabel('Cycle', fontsize=12, fontweight='bold')
    ax.set_ylabel('Prevalence (%)', fontsize=12, fontweight='bold')
    ax.set_title(f'Prevalence Trends: {title_var}', fontsize=14, fontweight='bold', pad=20)
    ax.legend(title='Category', bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(var_data['CYCLE'].unique())
    
    plt.tight_layout()
    return fig


def plot_cycle_comparison(results_df: pd.DataFrame, variable: str, variable_description: Optional[str] = None):
    """
    Create a grouped bar chart comparing prevalence across cycles.
    
    Args:
        results_df: DataFrame with 'CYCLE', 'Variable', 'Value', 'Prevalence', optionally 'Label'
        variable: Variable name to plot
        variable_description: Optional variable description to display in title
    """
    if 'CYCLE' not in results_df.columns:
        st.warning("No cycle information found in results.")
        return None
    
    var_data = results_df[results_df['Variable'] == variable].copy()
    if var_data.empty:
        st.warning(f"No data found for variable {variable}")
        return None
    
    # Use Label column if available for index, otherwise use Value
    use_labels = 'Label' in var_data.columns
    
    pivot_data = var_data.pivot_table(
        index='Value',
        columns='CYCLE',
        values='Prevalence',
        aggfunc='first'
    )
    
    # Create label mapping if available
    if use_labels:
        label_map = {}
        for value in pivot_data.index:
            label_row = var_data[var_data['Value'] == value].iloc[0]
            label = label_row['Label'] if pd.notna(label_row.get('Label')) else str(value)
            label_map[value] = label
        x_labels = [label_map.get(val, str(val)) for val in pivot_data.index]
    else:
        x_labels = [str(val) for val in pivot_data.index]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(pivot_data.index))
    width = 0.8 / len(pivot_data.columns)
    
    for i, cycle in enumerate(pivot_data.columns):
        offset = (i - len(pivot_data.columns) / 2 + 0.5) * width
        ax.bar(x + offset, pivot_data[cycle], width, label=str(cycle), alpha=0.8)
    
    # Use variable description in title if available
    title_var = variable_description if variable_description else variable
    
    ax.set_xlabel('Category', fontsize=12, fontweight='bold')
    ax.set_ylabel('Prevalence (%)', fontsize=12, fontweight='bold')
    ax.set_title(f'Cycle Comparison: {title_var}', fontsize=14, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=45, ha='right')
    ax.legend(title='Cycle', bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    return fig


def plot_cycle_ci_comparison(results_df: pd.DataFrame, variable: str, variable_description: Optional[str] = None):
    """
    Create an error bar chart comparing confidence intervals across cycles.
    
    Args:
        results_df: DataFrame with 'CYCLE', 'Variable', 'Value', 'Prevalence', 'CI Lower', 'CI Upper', optionally 'Label'
        variable: Variable name to plot
        variable_description: Optional variable description to display in title
    """
    if 'CYCLE' not in results_df.columns:
        st.warning("No cycle information found in results.")
        return None
    
    var_data = results_df[results_df['Variable'] == variable].copy()
    if var_data.empty:
        st.warning(f"No data found for variable {variable}")
        return None
    
    var_data = var_data.sort_values(['CYCLE', 'Value'])
    
    # Use Label column if available
    use_labels = 'Label' in var_data.columns
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    for value in var_data['Value'].unique():
        value_data = var_data[var_data['Value'] == value].sort_values('CYCLE')
        cycles = value_data['CYCLE'].tolist()
        prevalences = value_data['Prevalence'].tolist()
        ci_lower = value_data['CI Lower'].tolist()
        ci_upper = value_data['CI Upper'].tolist()
        
        errors_lower = [p - cl for p, cl in zip(prevalences, ci_lower)]
        errors_upper = [cu - p for p, cu in zip(prevalences, ci_upper)]
        
        # Use label if available, otherwise use value
        if use_labels:
            label = value_data['Label'].iloc[0] if pd.notna(value_data['Label'].iloc[0]) else str(value)
        else:
            label = str(value)
        
        ax.errorbar(cycles, prevalences, yerr=[errors_lower, errors_upper], 
                   marker='o', label=label, capsize=5, capthick=2, 
                   linewidth=2, markersize=8, elinewidth=1.5)
    
    # Use variable description in title if available
    title_var = variable_description if variable_description else variable
    
    ax.set_xlabel('Cycle', fontsize=12, fontweight='bold')
    ax.set_ylabel('Prevalence (%)', fontsize=12, fontweight='bold')
    ax.set_title(f'Prevalence with Confidence Intervals: {title_var}', 
                fontsize=14, fontweight='bold', pad=20)
    ax.legend(title='Category', bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(var_data['CYCLE'].unique())
    
    plt.tight_layout()
    return fig


def display_cycle_table(results_df: pd.DataFrame, variable: Optional[str] = None):
    """
    Display a pivot table with cycles as columns for easy comparison.
    
    Args:
        results_df: DataFrame with cycle comparison results
        variable: Optional variable to filter by
    """
    if 'CYCLE' not in results_df.columns:
        st.warning("No cycle information found in results.")
        return
    
    display_df = results_df.copy()
    
    if variable:
        display_df = display_df[display_df['Variable'] == variable]
    
    if display_df.empty:
        st.warning(f"No data found for variable {variable}")
        return
    
    # Use Label column if available for display
    use_labels = 'Label' in display_df.columns
    
    if use_labels:
        # Create a combined Value/Label column for display
        display_df['Value_Label'] = display_df.apply(
            lambda row: row['Label'] if pd.notna(row.get('Label')) else str(row['Value']),
            axis=1
        )
        pivot_index = ['Variable', 'Value_Label']
    else:
        pivot_index = ['Variable', 'Value']
    
    pivot_df = display_df.pivot_table(
        index=pivot_index,
        columns='CYCLE',
        values='Prevalence',
        aggfunc='first'
    ).reset_index()
    
    # Rename Value_Label to Category for display
    if use_labels:
        pivot_df = pivot_df.rename(columns={'Value_Label': 'Category'})
    
    st.dataframe(pivot_df.style.background_gradient(
        subset=[col for col in pivot_df.columns if col not in ['Variable', 'Value', 'Category', 'Value_Label']], 
        cmap='viridis'
    ).format('{:.2f}%'), use_container_width=True)
    
    return pivot_df

