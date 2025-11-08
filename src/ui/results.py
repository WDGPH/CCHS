"""Results display functions for the CCHS application."""

import streamlit as st
import pandas as pd
from typing import Optional
from src.ui.components import create_enhanced_chart


def is_multi_cycle(results_df: pd.DataFrame) -> bool:
    """Check if results contain multi-cycle data."""
    return 'CYCLE' in results_df.columns


def display_results(result_df, variable, use_labels=False, variable_description: Optional[str] = None):
    """Display the analysis results as a modern styled table and enhanced chart."""
    import uuid
    
    # Generate a unique session ID for this result display
    result_id = str(uuid.uuid4())[:8]
    
    # Use variable description in header if available
    display_var = variable_description if variable_description else variable
    
    # Modern header with improved styling
    st.markdown(f"""
    <div class="content-card">
        <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
            <div style="width: 4px; height: 40px; background: var(--gradient-primary); 
                        border-radius: 2px; margin-right: 1rem;"></div>
            <div>
                <h3 style="margin: 0; color: var(--primary); font-size: 1.5rem; font-weight: 600;">
                    Bootstrap Analysis Results
                </h3>
                <p style="margin: 4px 0 0 0; color: var(--text-light); font-weight: 500;">
                    Variable: <span style="color: var(--secondary); font-weight: 600;">{display_var}</span>
                    {f'<br><small style="color: var(--text-light); font-size: 0.85rem;">Code: {variable}</small>' if variable_description else ''}
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Always use Label column for display in both table and plot if available
    if 'Label' in result_df.columns:
        display_df = result_df.copy()
        display_df = display_df.rename(columns={'Label': 'Value Label'})
        styled_df = display_df.style.background_gradient(
            subset=['Prevalence'], 
            cmap='viridis'
        ).format({
            'Prevalence': '{:.2f}%',
            'Weighted Population': '{:,.0f}',
            'Standard Deviation': '{:.3f}',
            'CI Lower': '{:.2f}',
            'CI Upper': '{:.2f}',
            'CV (%)': '{:.1f}%',
            'Error': '{:.3f}'
        }).set_properties(**{
            'text-align': 'center',
            'font-weight': '500'
        })
        st.dataframe(styled_df, use_container_width=True)
        x_labels = display_df['Value Label']
    else:
        styled_df = result_df.style.background_gradient(
            subset=['Prevalence'], 
            cmap='viridis'
        ).format({
            'Prevalence': '{:.2f}%',
            'Weighted Population': '{:,.0f}',
            'Standard Deviation': '{:.3f}',
            'CI Lower': '{:.2f}',
            'CI Upper': '{:.2f}',
            'CV (%)': '{:.1f}%',
            'Error': '{:.3f}'
        }).set_properties(**{
            'text-align': 'center',
            'font-weight': '500'
        })
        st.dataframe(styled_df, use_container_width=True)
        x_labels = result_df['Value'].astype(str)
    
    # Create and display enhanced chart
    chart_title_var = variable_description if variable_description else variable
    fig = create_enhanced_chart(result_df, chart_title_var)
    st.pyplot(fig)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Show weighted population with unique key
    show_weighted_pop = st.checkbox("Show weighted population", key=f"weighted_pop_{result_id}")
    if show_weighted_pop:
        st.write("#### Weighted Population Distribution")
        st.dataframe(result_df[['Weighted Population']])
    
    # Recode variable names with unique keys
    if st.checkbox("Recode variable names", key=f"recode_names_{result_id}"):
        variables_in_data = list(result_df.index)
        st.write("Enter display names for each variable below:")
        rename_dict = {}
        for var in variables_in_data:
            new_name = st.text_input(f"Display name for '{var}'", value=var, key=f"rename_{result_id}_{var}")
            rename_dict[var] = new_name


def display_multi_cycle_results(results_df: pd.DataFrame, variable: str, variable_description: Optional[str] = None):
    """Display multi-cycle analysis results with comparison visualizations."""
    from src.ui.comparisons import (
        plot_cycle_trends, 
        plot_cycle_comparison, 
        plot_cycle_ci_comparison,
        display_cycle_table
    )
    from src.analysis.comparison import compare_cycles, create_comparison_summary
    
    # Use variable description in header if available
    display_var = variable_description if variable_description else variable
    
    st.markdown(f"""
    <div class="content-card">
        <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
            <div style="width: 4px; height: 40px; background: var(--gradient-primary); 
                        border-radius: 2px; margin-right: 1rem;"></div>
            <div>
                <h3 style="margin: 0; color: var(--primary); font-size: 1.5rem; font-weight: 600;">
                    Multi-Cycle Analysis Results
                </h3>
                <p style="margin: 4px 0 0 0; color: var(--text-light); font-weight: 500;">
                    Variable: <span style="color: var(--secondary); font-weight: 600;">{display_var}</span>
                    {f'<br><small style="color: var(--text-light); font-size: 0.85rem;">Code: {variable}</small>' if variable_description else ''}
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    var_results = results_df[results_df['Variable'] == variable].copy()
    
    if var_results.empty:
        st.warning(f"No results found for variable {variable}")
        return
    
    cycles = sorted(var_results['CYCLE'].unique())
    st.info(f"📊 Comparing {len(cycles)} cycle(s): {', '.join(cycles)}")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Comparison Table", "📈 Trends", "📊 Bar Chart", "📉 Summary"])
    
    with tab1:
        st.subheader("Cycle Comparison Table")
        comparison_table = display_cycle_table(var_results, variable)
    
    with tab2:
        st.subheader("Prevalence Trends Over Cycles")
        fig_trends = plot_cycle_trends(var_results, variable, variable_description)
        if fig_trends:
            st.pyplot(fig_trends)
    
    with tab3:
        st.subheader("Cycle Comparison Bar Chart")
        fig_bars = plot_cycle_comparison(var_results, variable, variable_description)
        if fig_bars:
            st.pyplot(fig_bars)
    
    with tab4:
        st.subheader("Comparison Summary")
        summary_df = create_comparison_summary(var_results)
        if not summary_df.empty:
            st.dataframe(summary_df.style.background_gradient(
                subset=['Change (pp)', 'Change (%)'],
                cmap='RdYlGn'
            ).format({
                'First Prevalence': '{:.2f}%',
                'Last Prevalence': '{:.2f}%',
                'Change (pp)': '{:.2f}',
                'Change (%)': '{:.1f}%'
            }), use_container_width=True)
        else:
            st.info("Summary data not available")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.subheader("Detailed Results by Cycle")
    for cycle in cycles:
        with st.expander(f"Cycle {cycle} Results", expanded=False):
            cycle_results = var_results[var_results['CYCLE'] == cycle].copy()
            cycle_results = cycle_results.drop(columns=['CYCLE'])
            display_results(cycle_results, variable, use_labels='Label' in cycle_results.columns)


def display_crosstab_report(combined_df):
    """Display a crosstab (pivot) report of prevalence by variable and value."""
    import uuid
    
    is_multi = is_multi_cycle(combined_df)
    
    report_id = str(uuid.uuid4())[:8]
    
    if is_multi:
        st.write("### Multi-Cycle Crosstab Report (Prevalence)")
        st.info("📊 This report includes data from multiple cycles. Use filters below to focus on specific cycles.")
        
        cycles = sorted(combined_df['CYCLE'].unique())
        selected_cycles = st.multiselect(
            "Filter by cycles",
            options=cycles,
            default=cycles,
            key=f"crosstab_cycle_filter_{report_id}"
        )
        
        if selected_cycles:
            combined_df = combined_df[combined_df['CYCLE'].isin(selected_cycles)]
    else:
        st.write("### Combined Crosstab Report (Prevalence)")
    
    # Display options with unique keys using UUID
    show_weighted_pop = st.checkbox("Show weighted population in crosstab", key=f"crosstab_weighted_pop_{report_id}")
    show_percentages = st.checkbox("Show percentages", value=True, key=f"crosstab_percentages_{report_id}")
    show_confidence_intervals = st.checkbox("Show confidence intervals", value=True, key=f"crosstab_ci_{report_id}")
    
    # Always use Label if available for columns
    col_field = 'Label' if 'Label' in combined_df.columns else 'Value'
    
    if is_multi:
        pivot_index = ['Variable', 'CYCLE'] if 'CYCLE' in combined_df.columns else 'Variable'
        pivot_columns = col_field
        pivot_values = 'Prevalence'
        
        prevalence_crosstab = pd.pivot_table(
            combined_df,
            index=pivot_index,
            columns=pivot_columns,
            values=pivot_values
        )
        
        weighted_pop_crosstab = pd.pivot_table(
            combined_df,
            index=pivot_index,
            columns=pivot_columns,
            values='Weighted Population'
        ) if show_weighted_pop else None
    else:
        prevalence_crosstab = pd.pivot_table(
            combined_df,
            index='Variable',
            columns=col_field,
            values='Prevalence'
        )
        weighted_pop_crosstab = pd.pivot_table(
            combined_df,
            index='Variable',
            columns=col_field,
            values='Weighted Population'
        ) if show_weighted_pop else None
    
    if show_weighted_pop and weighted_pop_crosstab is not None:
        st.write("#### Weighted Population Crosstab")
        st.dataframe(weighted_pop_crosstab)
    
    # Let the user recode variable names (rows) for the crosstab display
    if st.checkbox("Recode variable names for crosstab display", key=f"recode_var_names_{report_id}"):
        variables_in_crosstab = list(prevalence_crosstab.index.get_level_values('Variable').unique()) if is_multi else list(prevalence_crosstab.index)
        st.write("Enter display names for each variable (row) below:")
        rename_dict = {}
        for var in variables_in_crosstab:
            new_name = st.text_input(f"Display name for '{var}'", value=var, key=f"rename_var_{report_id}_{var}")
            rename_dict[var] = new_name
        
        if is_multi:
            recoded_crosstab = prevalence_crosstab.copy()
            recoded_crosstab.index = recoded_crosstab.index.set_levels(
                [rename_dict.get(v, v) for v in recoded_crosstab.index.levels[0]], 
                level='Variable'
            )
        else:
            recoded_crosstab = prevalence_crosstab.rename(index=rename_dict)
        
        # Extra feature: recode column names if desired
        if st.checkbox("Recode column names for crosstab display", key=f"recode_cols_{report_id}"):
            columns_in_crosstab = list(recoded_crosstab.columns)
            st.write("Enter display names for each column below:")
            rename_columns_dict = {}
            for col in columns_in_crosstab:
                new_name = st.text_input(f"Display name for column '{col}'", value=col, key=f"rename_col_{report_id}_{col}")
                rename_columns_dict[col] = new_name
            
            recoded_crosstab = recoded_crosstab.rename(columns=rename_columns_dict)
        
        st.write("#### Recoded Crosstab")
        st.dataframe(recoded_crosstab)
        
        # Optionally, allow the user to download the recoded crosstab as CSV
        if st.checkbox("Download options", key=f"download_options_{report_id}"):
            csv_data = recoded_crosstab.to_csv().encode('utf-8')
            st.download_button(
                label="Download Recoded Crosstab as CSV",
                data=csv_data,
                file_name="recoded_crosstab.csv",
                mime="text/csv",
                key=f"download_recoded_crosstab_{report_id}"
            )
    else:
        st.dataframe(prevalence_crosstab)
        
        if st.checkbox("Download options", key=f"download_options_{report_id}"):
            csv_data = prevalence_crosstab.to_csv().encode('utf-8')
            st.download_button(
                label="Download Prevalence Crosstab",
                data=csv_data,
                file_name="prevalence_crosstab.csv",
                mime="text/csv",
                key=f"download_prevalence_crosstab_{report_id}"
            )
            
            if show_weighted_pop and weighted_pop_crosstab is not None:
                weighted_csv = weighted_pop_crosstab.to_csv().encode('utf-8')
                st.download_button(
                    label="Download Weighted Population Crosstab",
                    data=weighted_csv,
                    file_name="weighted_pop_crosstab.csv",
                    mime="text/csv",
                    key=f"download_weighted_crosstab_{report_id}"
                )
