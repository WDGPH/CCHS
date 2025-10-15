"""Reusable UI components for the CCHS application."""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


def create_metric_card(value: str, label: str) -> str:
    """Create a metric card HTML."""
    return f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """


def display_data_metrics(data: pd.DataFrame, weight_col: str = "WTS_S"):
    """Display data metrics in a row of cards."""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(create_metric_card(f"{len(data):,}", "Total Records"), 
                   unsafe_allow_html=True)
    
    with col2:
        st.markdown(create_metric_card(f"{len(data.columns)}", "Variables"), 
                   unsafe_allow_html=True)
    
    with col3:
        memory_mb = data.memory_usage(deep=True).sum() / 1024**2
        st.markdown(create_metric_card(f"{memory_mb:.1f}", "MB Memory"), 
                   unsafe_allow_html=True)
    
    with col4:
        missing_count = data.isnull().sum().sum()
        st.markdown(create_metric_card(f"{missing_count:,}", "Missing Values"), 
                   unsafe_allow_html=True)
    
    with col5:
        weighted_pop = data[weight_col].sum() if weight_col in data.columns else 0
        st.markdown(create_metric_card(f"{weighted_pop:,.0f}", "Weighted Population"), 
                   unsafe_allow_html=True)


def create_content_card(title: str, description: str, gradient_class: str = "gradient-primary") -> str:
    """Create a content card header."""
    return f"""
    <div class="content-card">
        <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
            <div style="width: 4px; height: 40px; background: var(--{gradient_class}); 
                        border-radius: 2px; margin-right: 1rem;"></div>
            <div>
                <h3 style="margin: 0; color: var(--primary); font-size: 1.4rem; font-weight: 600;">
                    {title}
                </h3>
                <p style="margin: 4px 0 0 0; color: var(--text-light); font-weight: 500;">
                    {description}
                </p>
            </div>
        </div>
    """


def create_progress_display():
    """Create a progress display container."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        current_var = st.empty()
    with col2:
        time_elapsed = st.empty()
    with col3:
        eta = st.empty()
    
    return progress_bar, status_text, current_var, time_elapsed, eta


def create_enhanced_chart(result_df, variable_name):
    """Create an enhanced chart for displaying analysis results."""
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Extract data for plotting
    x_labels = result_df['Label'] if 'Label' in result_df.columns else result_df['Value'].astype(str)
    prevalence = result_df['Prevalence']
    ci_lower = result_df['CI Lower']
    ci_upper = result_df['CI Upper']
    
    # Plot bars
    x = range(len(x_labels))
    bars = ax.bar(x, prevalence, color='skyblue', alpha=0.7)
    
    # Add confidence interval error bars
    ax.errorbar(x, prevalence, yerr=[prevalence - ci_lower, ci_upper - prevalence],
                fmt='none', color='navy', capsize=5, capthick=1.5, elinewidth=1.5)
    
    # Customize the plot
    ax.set_title(f'Prevalence Distribution for {variable_name}', pad=20, fontsize=12)
    ax.set_xlabel('Categories', labelpad=10)
    ax.set_ylabel('Prevalence (%)', labelpad=10)
    
    # Set x-axis labels
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=45, ha='right')
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom')
    
    # Adjust layout to prevent label cutoff
    plt.tight_layout()
    
    return fig