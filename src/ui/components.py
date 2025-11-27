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


def create_workflow_stepper(current_step):
    """Create a progress stepper showing the analysis workflow steps"""
    steps = [
        ("Upload Data", 1),
        ("Select Variables", 2),
        ("Run Analysis", 3),
        ("View Results", 4)
    ]
    
    # Create columns for visual layout
    cols = st.columns(len(steps))
    
    for i, (step_name, step_num) in enumerate(steps):
        with cols[i]:
            # Determine styling based on step status
            if step_num < current_step:
                # Completed step
                circle_bg = "#4CAF50"
                circle_content = "✓"
                text_color = "#4CAF50"
            elif step_num == current_step:
                # Active step
                circle_bg = "#2196F3"
                circle_content = str(step_num)
                text_color = "#2196F3"
            else:
                # Pending step
                circle_bg = "#E0E0E0"
                circle_content = str(step_num)
                text_color = "#999"
            
            # Create HTML for this step
            step_html = f"""
            <div style="text-align: center;">
                <div style="width: 50px; height: 50px; border-radius: 50%; 
                            background: {circle_bg}; border: 2px solid {circle_bg}; 
                            display: flex; align-items: center; justify-content: center;
                            font-size: 1.2rem; font-weight: 700; color: white; 
                            margin: 0 auto 0.5rem;">
                    {circle_content}
                </div>
                <div style="font-size: 0.9rem; font-weight: 600; color: {text_color}; 
                            text-align: center;">
                    {step_name}
                </div>
            </div>
            """
            st.markdown(step_html, unsafe_allow_html=True)


def get_quality_badge(cv_percent: float) -> str:
    """
    Get quality indicator badge based on CV percentage.
    
    Args:
        cv_percent: Coefficient of variation percentage
    
    Returns:
        HTML string for quality badge
    """
    if cv_percent < 16.6:
        color = "#4CAF50"
        text = "Good"
        label = "Acceptable precision"
    elif cv_percent < 33.3:
        color = "#FF9800"
        text = "Caution"
        label = "Use with caution"
    else:
        color = "#F44336"
        text = "Poor"
        label = "Unreliable"
    
    return f'''<span style="background: {color}; color: white; padding: 2px 8px; 
                border-radius: 12px; font-size: 0.75rem; font-weight: 600; 
                white-space: nowrap;" title="{label}">{text}</span>'''


def display_quality_legend():
    """Display legend explaining quality indicators."""
    st.markdown("""
    <div style="background: var(--light-bg); padding: 1rem; border-radius: 8px; margin: 1rem 0; 
                border-left: 3px solid var(--primary);">
        <strong style="color: var(--primary);">Data Quality Indicators:</strong><br>
        <div style="margin-top: 0.5rem; font-size: 0.9rem;">
            <span style="background: #4CAF50; color: white; padding: 2px 8px; border-radius: 12px; 
                        font-size: 0.75rem; font-weight: 600;">Good</span> 
            CV < 16.6% - Acceptable precision<br>
            <span style="background: #FF9800; color: white; padding: 2px 8px; border-radius: 12px; 
                        font-size: 0.75rem; font-weight: 600; margin-top: 0.3rem; display: inline-block;">Caution</span> 
            CV 16.6-33.3% - Use with caution<br>
            <span style="background: #F44336; color: white; padding: 2px 8px; border-radius: 12px; 
                        font-size: 0.75rem; font-weight: 600; margin-top: 0.3rem; display: inline-block;">Poor</span> 
            CV > 33.3% - Unreliable, consider suppressing
        </div>
    </div>
    """, unsafe_allow_html=True)