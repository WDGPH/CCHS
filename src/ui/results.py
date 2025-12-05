"""Results display functions for the CCHS application."""

import streamlit as st
import pandas as pd
from typing import Optional
from src.ui.components import create_enhanced_chart, get_quality_badge, display_quality_legend


def is_multi_cycle(results_df: pd.DataFrame) -> bool:
    """Check if results contain multi-cycle data."""
    return 'CYCLE' in results_df.columns


def display_results(result_df, variable, use_labels=False, variable_description: Optional[str] = None, show_info_expander=True, cycle_suffix=None):
    """Display the analysis results as a modern styled table and enhanced chart."""
    import hashlib
    
    # Generate a stable ID based on variable name and optional cycle suffix
    id_base = f"{variable}_{cycle_suffix}" if cycle_suffix else variable
    result_id = hashlib.md5(id_base.encode()).hexdigest()[:8]
    
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
    
    # Add filtering options AFTER the header
    st.markdown("**Display Options:**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_skips = st.checkbox(
            "🎯 Filter skip/missing",
            value=False,
            key=f"filter_skips_{result_id}",
            help="Remove 'Valid skip', 'Not stated', 'Don't know', and similar categories"
        )
    
    with col2:
        recalculate_pct = st.checkbox(
            "🔄 Recalculate %",
            value=False,
            key=f"recalc_pct_{result_id}",
            help="Show % only among those who answered"
        )
    
    with col3:
        show_debug = st.checkbox(
            "🔍 Debug",
            value=False,
            key=f"debug_{result_id}",
            help="Show values for debugging"
        )
    
    # Apply filtering if requested
    display_df = result_df.copy()
    original_count = len(display_df)
    filtered_count = original_count
    
    # Show debug info if requested
    if show_debug:
        st.write("**Debug Info:**")
        if 'Label' in display_df.columns:
            st.write("Label values:", display_df['Label'].tolist())
        st.write("Value column:", display_df['Value'].tolist())
    
    if filter_skips:
        # Define skip/missing patterns to filter
        skip_patterns = [
            'valid skip', 'skip', 'not stated', 'not stated', 'don\'t know', 
            'refusal', 'not applicable', 'refused', 'n/a', 'na', 
            'missing', 'dk', 'ns'
        ]
        
        # Check which column to filter on
        filter_column = None
        if 'Label' in display_df.columns and display_df['Label'].notna().any():
            filter_column = 'Label'
            st.write(f"🔍 Filtering on: {filter_column} column")
        else:
            filter_column = 'Value'
            st.write(f"🔍 Filtering on: {filter_column} column")
        
        # Create mask - keep rows that DON'T contain any skip patterns
        def should_keep_row(val):
            if pd.isna(val):
                return True
            val_str = str(val).lower().strip()
            for pattern in skip_patterns:
                if pattern in val_str:
                    return False
            return True
        
        mask = display_df[filter_column].apply(should_keep_row)
        display_df = display_df[mask].copy()
        filtered_count = len(display_df)
        
        if filtered_count < original_count:
            st.info(f"ℹ️ Filtered: {original_count} → {filtered_count} rows ({original_count - filtered_count} removed)")
        else:
            st.warning("⚠️ No skip/missing categories detected")
    
    # Recalculate percentages if requested
    if recalculate_pct and not display_df.empty:
        total_valid = display_df['Weighted Population'].sum()
        if total_valid > 0:
            display_df = display_df.copy()
            display_df['Original Prevalence'] = display_df['Prevalence'].copy()
            display_df['Prevalence'] = (display_df['Weighted Population'] / total_valid) * 100
            
            # Recalculate confidence intervals proportionally
            # Avoid division by zero
            with pd.option_context('mode.chained_assignment', None):
                scale_factor = display_df['Prevalence'] / display_df['Original Prevalence'].replace(0, 1)
                display_df['CI Lower'] = display_df['Prevalence'] - (display_df['Error'] * scale_factor).fillna(0)
                display_df['CI Upper'] = display_df['Prevalence'] + (display_df['Error'] * scale_factor).fillna(0)
            
            st.success(f"✅ Recalculated among {filtered_count} response(s) (weighted pop: {total_valid:,.0f})")
        else:
            st.error("❌ Cannot recalculate: no valid weighted population")
    
    # Add info box explaining response categories with actual data examples (only if not nested)
    if show_info_expander:
        with st.expander("ℹ️ Understanding Response Categories", expanded=False):
            st.markdown("""
        **Common Response Categories:**
        
        - **Valid Response** (e.g., Yes, No): Person was asked and provided an answer
        - **Valid Skip**: Question didn't apply (e.g., non-smokers skipping smoking questions)
        - **Not stated/Refusal**: Person declined to answer
        - **Don't know**: Person was unsure
        
        **Interpreting Percentages:**
        
        - **Default view**: Shows % of the entire population (including skips)
        - **Filtered view**: Removes skip/missing categories from display
        - **Recalculated view**: Shows % only among those who answered
        """)
        
        # Show actual example from current data
        st.markdown("**Example from your current data:**")
        
        # Get label column if available
        label_col = 'Label' if 'Label' in display_df.columns else 'Value'
        
        # Show first few rows as example
        example_rows = display_df.head(min(5, len(display_df)))
        for idx, row in example_rows.iterrows():
            label = row[label_col] if label_col in row else row['Value']
            prev = row['Prevalence']
            st.write(f"• **{label}**: {prev:.2f}% → {prev:.2f}% of entire population")
        
        # Calculate what it would be if recalculated
        total = display_df['Prevalence'].sum()
        if total > 0:
            st.markdown(f"\n**If recalculated among valid responses only:**")
            for idx, row in example_rows.iterrows():
                label = row[label_col] if label_col in row else row['Value']
                prev = row['Prevalence']
                recalc = (prev / total) * 100
                st.write(f"• **{label}**: {recalc:.1f}% → {recalc:.1f}% of those who answered")
    
    # Display quality legend
    display_quality_legend()
    
    # Add quality indicators to the dataframe
    display_df['Quality'] = display_df['CV (%)'].apply(lambda cv: get_quality_badge(cv))
    
    # Always use Label column for display in both table and plot if available
    if 'Label' in display_df.columns:
        display_df = display_df.rename(columns={'Label': 'Value Label'})
        x_labels = display_df['Value Label']
    else:
        x_labels = display_df['Value'].astype(str)
    
    # Reorder columns to put Quality after CV
    cols = list(display_df.columns)
    if 'Quality' in cols:
        cols.remove('Quality')
        cv_idx = cols.index('CV (%)')
        cols.insert(cv_idx + 1, 'Quality')
        display_df = display_df[cols]
    
    # Format dictionary for styling
    format_dict = {
        'Prevalence': '{:.2f}%',
        'Weighted Population': '{:,.0f}',
        'Standard Deviation': '{:.3f}',
        'CI Lower': '{:.2f}',
        'CI Upper': '{:.2f}',
        'CV (%)': '{:.1f}%',
        'Error': '{:.3f}'
    }
    
    # Add original prevalence format if it exists
    if 'Original Prevalence' in display_df.columns:
        format_dict['Original Prevalence'] = '{:.2f}%'
    
    styled_df = display_df.style.background_gradient(
        subset=['Prevalence'], 
        cmap='viridis'
    ).format(format_dict).set_properties(**{
        'text-align': 'center',
        'font-weight': '500'
    })
    
    st.markdown(styled_df.to_html(escape=False), unsafe_allow_html=True)
    
    # Create and display enhanced chart using the filtered/recalculated display_df
    chart_title_var = variable_description if variable_description else variable
    
    # Add note to chart title if recalculated
    if recalculate_pct:
        chart_title_var += " (% of valid responses)"
    elif filter_skips:
        chart_title_var += " (filtered)"
    
    # Prepare chart data - need to restore 'Label' column if it was renamed
    chart_data = display_df.copy()
    if 'Value Label' in chart_data.columns and 'Label' not in chart_data.columns:
        chart_data['Label'] = chart_data['Value Label']
    
    fig = create_enhanced_chart(chart_data, chart_title_var)
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
            display_results(cycle_results, variable, use_labels='Label' in cycle_results.columns, show_info_expander=False, cycle_suffix=cycle)


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
