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


def create_enhanced_chart(result_df: pd.DataFrame, variable: str):
    """Create an enhanced bar chart for results."""
    # Create enhanced color palette with gradients
    colors = ['#005568', '#00928F', '#78A22F', '#1fb5b3', '#8fb944', '#5C6F7C', '#7A68AE']
    
    # Create an enhanced bar chart with modern styling
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('white')
    
    # Create bars with enhanced styling
    bars = ax.bar(
        result_df['Value'].astype(str),
        result_df['Prevalence'],
        yerr=result_df['Error'],
        capsize=6,
        color=[colors[i % len(colors)] for i in range(len(result_df))],
        edgecolor='white',
        linewidth=2,
        alpha=0.85
    )
    
    # Enhanced axis styling
    ax.set_xlabel("Value", fontsize=14, fontweight='600', color='#162732')
    ax.set_ylabel("Prevalence (%)", fontsize=14, fontweight='600', color='#162732')
    ax.set_title(f"Prevalence Distribution: {variable}", 
                fontsize=16, fontweight='700', color='#005568', pad=20)
    
    # Modern grid and spine styling
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#E2E8F0')
    ax.spines['bottom'].set_color('#E2E8F0')
    ax.grid(axis='y', linestyle='--', alpha=0.4, color='#CBD5E0')
    
    # Enhanced value annotations with better positioning
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.annotate(
            f'{height:.1f}%',
            xy=(bar.get_x() + bar.get_width() / 2, height + result_df.iloc[i]['Error'] + 0.5),
            xytext=(0, 5),
            textcoords="offset points",
            ha='center',
            va='bottom',
            fontsize=11,
            fontweight='600',
            color='#162732',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                     edgecolor=colors[i % len(colors)], alpha=0.8)
        )
    
    # Add subtle background pattern
    ax.set_facecolor('#FAFBFC')
    
    plt.xticks(rotation=45, ha='right', fontsize=11, fontweight='500')
    plt.yticks(fontsize=11, fontweight='500')
    plt.tight_layout()
    
    return fig