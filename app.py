"""
Refactored CCHS Analysis Application
Main entry point using modular components with multi-cycle support
"""

import streamlit as st
import pandas as pd
import time

# Import all modules from the refactored structure
from config.settings import PAGE_CONFIG, DEFAULT_CYCLE, AVAILABLE_CYCLES
from config.styles import CSS_STYLES
from src.data.loader import (
    load_cycle_data, load_multi_cycle_data, 
    load_variable_descriptions, load_json_variable_descriptions, 
    load_crosswalk, load_categories, merge_data
)
from src.data.processor import create_age_groups, apply_region_filter
from src.analysis.bootstrap import run_bootstrap_analysis_for_all_values
from src.ui.components import display_data_metrics, create_content_card
from src.ui.sidebar import (
    create_analysis_mode_selector,
    create_cycle_selector,
    create_multi_cycle_selector,
    create_variable_search_sidebar, 
    create_geographic_filters_sidebar, 
    create_apply_filters_section
)
from src.ui.results import display_results, display_crosstab_report, display_multi_cycle_results, is_multi_cycle
from src.utils.session import initialize_session_state, get_session_state, set_session_state
from src.utils.helpers import (
    validate_data_columns, 
    create_excel_download, 
    create_multi_cycle_excel,
    get_cycle_varname, 
    get_value_label, 
    get_available_harmonized_vars, 
    merge_descriptions
)


def main():
    """Main application function with multi-cycle support."""
    # Configure page
    st.set_page_config(**PAGE_CONFIG)
    
    # Apply custom CSS styles
    st.markdown(CSS_STYLES, unsafe_allow_html=True)
    
    # Initialize session state
    initialize_session_state()
    
    # Header with logo
    logo_col, title_col = st.columns([1, 4])
    
    with logo_col:
        st.image("https://wdgpublichealth.ca/sites/all/themes/de_theme/logo.png")
    
    with title_col:
        st.markdown("""
        <div style="padding: 1rem 0;">
            <h1 style="margin: 0; font-size: 2.5rem; font-weight: 700; color: var(--primary);">
                🏥 CCHS Analysis Dashboard
            </h1>
            <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem; color: var(--text-light);">
                Canadian Community Health Survey Bootstrap Analysis Tool
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Load harmonization data (needed for both modes)
    crosswalk = load_crosswalk()
    categories = load_categories()
    
    # Analysis mode selection in sidebar
    analysis_mode = create_analysis_mode_selector()
    
    # Handle mode switching - clear session state if mode changed
    previous_mode = get_session_state('analysis_mode')
    if previous_mode and previous_mode != analysis_mode:
        set_session_state('filtered_data', None)
        set_session_state('merged_data', None)
        set_session_state('combined_results', None)
    set_session_state('analysis_mode', analysis_mode)
    
    # Route to appropriate data loading based on mode
    if analysis_mode == "Multi-Cycle":
        # Multi-cycle mode
        selected_cycles = create_multi_cycle_selector(crosswalk, {})
        
        if not selected_cycles:
            st.warning("⚠️ Please select at least one cycle to proceed.")
            st.stop()
        
        # Load data for all selected cycles
        data_dict = {}
        for cycle in selected_cycles:
            cycle_data, cycle_bootstrap = load_cycle_data(cycle)
            if cycle_data is not None and cycle_bootstrap is not None:
                data_dict[cycle] = cycle_data
        
        if not data_dict:
            st.error("❌ Failed to load data files for any selected cycle.")
            st.stop()
        
        # Load multi-cycle harmonized data
        with st.spinner("🔄 Loading and harmonizing multi-cycle data..."):
            data, bootstrap_data = load_multi_cycle_data(selected_cycles, crosswalk, categories)
        
        if data is None or bootstrap_data is None:
            st.error("❌ Failed to harmonize and combine multi-cycle data.")
            st.stop()
        
        # Get common harmonized variables
        from src.data.harmonizer import get_common_harmonized_vars
        available_harmonized_vars = get_common_harmonized_vars(selected_cycles, crosswalk, data_dict) if crosswalk else []
        
        # Load variable descriptions (use first cycle as reference)
        desc_df, desc_dict = load_variable_descriptions(selected_cycles[0])
        json_desc_dict = load_json_variable_descriptions(selected_cycles[0])
        merged_desc_dict = merge_descriptions(json_desc_dict, desc_dict)
        
        # Display data overview
        cycles_str = ', '.join(selected_cycles)
        st.markdown(create_content_card(
            f"Multi-Cycle Dataset Overview - Cycles {cycles_str}",
            f"Combined and harmonized data from {len(selected_cycles)} survey cycle(s)"
        ), unsafe_allow_html=True)
        
        display_data_metrics(data)
        st.info(f"📊 Data harmonized and combined from cycles: {cycles_str}")
        st.markdown("</div>", unsafe_allow_html=True)
        
        cycle = cycles_str
        use_harmonized = True
        
    else:
        # Single cycle mode (existing behavior)
        cycle = st.selectbox(
            "Select CCHS Cycle/Year",
            options=AVAILABLE_CYCLES,
            index=AVAILABLE_CYCLES.index(DEFAULT_CYCLE),
            help="Choose the survey cycle. Data and descriptions will load automatically based on this selection.",
            key="main_cycle_selector"
        )
        set_session_state('cycle', cycle)
        
        # Load data based on selected cycle
        data, bootstrap_data = load_cycle_data(cycle)
        if data is None or bootstrap_data is None:
            st.error("❌ Failed to load required data files. Please check your data directory.")
            return
        
        # Load variable descriptions for the selected cycle
        desc_df, desc_dict = load_variable_descriptions(cycle)
        json_desc_dict = load_json_variable_descriptions(cycle)
        merged_desc_dict = merge_descriptions(json_desc_dict, desc_dict)
        
        # Display data overview
        st.markdown(create_content_card(
            f"Dataset Overview - Cycle {cycle}",
            f"Summary statistics and metadata for the {cycle} CCHS dataset"
        ), unsafe_allow_html=True)
        
        display_data_metrics(data)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Sidebar components with cycle selector
        cycle_sidebar = create_cycle_selector()
        if cycle_sidebar != cycle:
            st.rerun()
        
        available_harmonized_vars = []
        use_harmonized = False
    
    # Variable search in sidebar
    use_harmonized = create_variable_search_sidebar(
        desc_df, merged_desc_dict, available_harmonized_vars, use_harmonized
    )
    
    # Geographic filters
    filter_by_district, filter_by_municipality_dropdown, district_codes, filter_by_health_region = create_geographic_filters_sidebar()
    
    # Apply filters button
    apply_filters = create_apply_filters_section()
    
    # Main content area
    if apply_filters:
        with st.spinner("🔄 Applying geographic filters..."):
            filtered_data = apply_region_filter(
                data, filter_by_district, filter_by_health_region, district_codes
            )
            
            # Add age groups
            filtered_data = create_age_groups(filtered_data, 'DHH_AGE')
            
            # Merge with bootstrap data
            merged_data = merge_data(filtered_data, bootstrap_data)
            
            # Store in session state
            set_session_state('filtered_data', filtered_data)
            set_session_state('merged_data', merged_data)
            
        st.success(f"✅ Filters applied! Dataset now contains {len(filtered_data):,} records.")
        
        # Display filtered data metrics
        st.markdown(create_content_card(
            "Filtered Dataset",
            "Statistics for the geographically filtered dataset"
        ), unsafe_allow_html=True)
        
        display_data_metrics(filtered_data)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Enhanced merge data section
    if get_session_state('filtered_data') is not None and get_session_state('merged_data') is None:
        st.markdown("---")
        st.markdown(create_content_card(
            "🔗 Data Merging",
            "Combine filtered data with bootstrap weights for statistical analysis"
        ), unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Merge Data with Bootstrap Weights", type="primary", key="merge_button"):
                with st.spinner('🔄 Merging data...'):
                    filtered_data = get_session_state('filtered_data')
                    merged_data = merge_data(filtered_data, bootstrap_data)
                    set_session_state('merged_data', merged_data)
                    st.success("✅ Data merged successfully!")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Variable analysis section with harmonization support
    merged_data = get_session_state('merged_data')
    if merged_data is not None:
        # Get available harmonized variables
        if analysis_mode == "Multi-Cycle":
            # For multi-cycle, use common harmonized variables
            if not available_harmonized_vars and crosswalk:
                from src.data.harmonizer import get_common_harmonized_vars
                data_dict_for_check = {}
                for cycle_year in selected_cycles:
                    cycle_data = merged_data[merged_data['CYCLE'] == cycle_year].copy()
                    if not cycle_data.empty:
                        data_dict_for_check[cycle_year] = cycle_data
                available_harmonized_vars = get_common_harmonized_vars(selected_cycles, crosswalk, data_dict_for_check) if crosswalk else []
            use_harmonized = True
        else:
            # For single cycle, check available harmonized variables
            if crosswalk:
                available_harmonized_vars = get_available_harmonized_vars(crosswalk, cycle, merged_data)
        
        st.markdown(create_content_card(
            "Variable Analysis",
            "Select variables for bootstrap prevalence analysis with multi-cycle harmonization support"
        ), unsafe_allow_html=True)
        
        # Enhanced variable selection with harmonization option
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**📋 Variable Selection**")
            
            # Toggle for harmonized variables (only show in single-cycle mode)
            if analysis_mode == "Single Cycle" and available_harmonized_vars:
                use_harmonized = st.checkbox(
                    "🔗 Use Harmonized Variables",
                    value=get_session_state('use_harmonized', False),
                    help="Use harmonized variable names that work across multiple cycles"
                )
                set_session_state('use_harmonized', use_harmonized)
            elif analysis_mode == "Multi-Cycle":
                use_harmonized = True
                st.info(f"📊 Multi-cycle mode: Using {len(available_harmonized_vars)} harmonized variables available across all selected cycles")
            
            if use_harmonized and available_harmonized_vars:
                variable_options = available_harmonized_vars
                variable_labels = {}
                for var in variable_options:
                    if var in merged_desc_dict and merged_desc_dict[var]:
                        variable_labels[var] = f"{var}: {merged_desc_dict[var]}"
                    else:
                        variable_labels[var] = var
            else:
                variable_options = [col for col in merged_data.columns if not col.startswith('BSW') and col != 'CYCLE']
                variable_labels = {}
                for var in variable_options:
                    if var in merged_desc_dict:
                        variable_labels[var] = f"{var}: {merged_desc_dict[var]}"
                    else:
                        variable_labels[var] = var
            
            selected_variables = st.multiselect(
                "🎯 Select variables for analysis:",
                options=variable_options,
                format_func=lambda x: variable_labels.get(x, x),
                help="Choose one or more variables to analyze",
                key="variable_multiselect"
            )
            
            # Store selected variables in session state
            set_session_state('selected_variables', selected_variables)
            
            if selected_variables:
                st.markdown(f"✅ **{len(selected_variables)} variable(s) selected**")
                with st.expander("📖 View Selected Variables", expanded=False):
                    for var in selected_variables:
                        desc = merged_desc_dict.get(var, "No description available")
                        st.markdown(f"• **{var}**: {desc}")
        
        with col2:
            st.markdown("**⚖️ Weight Configuration**")
            weight_col = st.selectbox(
                "Bootstrap weight column:",
                ["WTS_S"],
                index=0,
                disabled=True,
                help="Weight column is automatically set to WTS_S for CCHS analysis"
            )
            
            # Analysis summary card
            mode_display = f"{len(selected_cycles)} cycles" if analysis_mode == "Multi-Cycle" else f"Cycle {cycle}"
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, var(--light-bg) 0%, #E0F2F1 100%); 
                        padding: 1rem; border-radius: 12px; margin-top: 1rem; 
                        border-left: 4px solid var(--accent);">
                <h4 style="margin: 0 0 0.5rem 0; color: var(--primary); font-size: 0.9rem;">
                    📊 Analysis Summary
                </h4>
                <p style="margin: 0; font-size: 0.8rem; color: var(--text-light);">
                    <strong>Mode:</strong> {analysis_mode}<br>
                    <strong>Dataset:</strong> {mode_display}<br>
                    <strong>Records:</strong> {len(merged_data):,}<br>
                    <strong>Method:</strong> Bootstrap Analysis<br>
                    <strong>Harmonization:</strong> {'Enabled' if use_harmonized else 'Disabled'}
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        if selected_variables:
            # Analysis options
            col1, col2 = st.columns(2)
            with col1:
                run_single = st.button("🔍 Analyze Selected Variables", type="primary")
            with col2:
                run_batch = st.button("⚡ Batch Analysis (All Variables)")
            
            # Single variable analysis with harmonization support
            if run_single:
                combined_results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                start_time = time.time()
                
                for i, variable in enumerate(selected_variables):
                    progress = (i + 1) / len(selected_variables)
                    progress_bar.progress(progress)
                    
                    elapsed = time.time() - start_time
                    remaining = (elapsed / progress * (1 - progress)) if progress > 0 else 0
                    
                    status_text.markdown(f"""
                    <div style="background: var(--background-alt); padding: 1rem; border-radius: 8px; 
                               text-align: center; margin: 1rem 0;">
                        <strong>Processing Variable {i+1} of {len(selected_variables)}</strong><br>
                        <span style="color: var(--secondary); font-weight: 600;">{variable}</span><br>
                        <small>Time: {elapsed:.1f}s | ETA: {remaining:.1f}s</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    try:
                        if analysis_mode == "Multi-Cycle":
                            # Multi-cycle analysis: run analysis per cycle
                            cycle_results_list = []
                            for cycle_year in selected_cycles:
                                cycle_data = merged_data[merged_data['CYCLE'] == cycle_year].copy()
                                if cycle_data.empty:
                                    continue
                                
                                result_df = run_bootstrap_analysis_for_all_values(cycle_data, variable, weight_col)
                                result_df['CYCLE'] = cycle_year
                                result_df['Variable'] = variable
                                
                                # Add harmonized labels
                                if categories:
                                    result_df['Label'] = result_df.apply(
                                        lambda row: get_value_label(variable, row['Value'], cycle_year, categories),
                                        axis=1
                                    )
                                
                                cycle_results_list.append(result_df)
                            
                            if cycle_results_list:
                                combined_result_df = pd.concat(cycle_results_list, ignore_index=True)
                                combined_results.append(combined_result_df)
                                
                                # Display multi-cycle results with description
                                var_desc = merged_desc_dict.get(variable, None)
                                display_multi_cycle_results(combined_result_df, variable, var_desc)
                        else:
                            # Single cycle analysis (existing behavior)
                            if use_harmonized and crosswalk:
                                actual_varname = get_cycle_varname(variable, cycle, crosswalk)
                            else:
                                actual_varname = variable
                            
                            result_df = run_bootstrap_analysis_for_all_values(merged_data, actual_varname, weight_col)
                            
                            # Add value labels if using harmonized variables
                            if use_harmonized and categories:
                                result_df['Label'] = result_df['Value'].apply(
                                    lambda v: get_value_label(variable, v, cycle, categories)
                                )
                            
                            result_df['Variable'] = variable
                            combined_results.append(result_df)
                            
                            # Display results for each variable with description
                            var_desc = merged_desc_dict.get(variable, None)
                            display_results(result_df, variable, use_labels=use_harmonized, variable_description=var_desc)
                        
                    except Exception as e:
                        st.error(f"❌ Error analyzing {variable}: {str(e)}")
                
                # Store combined results
                if combined_results:
                    combined_df = pd.concat(combined_results, ignore_index=True)
                    set_session_state('combined_results', combined_df)
                    
                    st.success(f"✅ Analysis complete for {len(selected_variables)} variables!")
                
                progress_bar.empty()
                status_text.empty()
            
            # Batch analysis with harmonization support
            if run_batch:
                st.warning("⚠️ Batch analysis will process all variables. This may take several minutes.")
                if st.button("🚀 Confirm Batch Analysis"):
                    # Get all available variables based on harmonization setting
                    if analysis_mode == "Multi-Cycle":
                        analysis_variables = available_harmonized_vars if available_harmonized_vars else []
                    elif use_harmonized and available_harmonized_vars:
                        analysis_variables = available_harmonized_vars
                    else:
                        analysis_variables = [col for col in merged_data.columns 
                                            if col not in ['ONT_ID', 'WTS_S', 'CYCLE'] and not col.startswith('GEO') and not col.startswith('BSW')]
                    
                    combined_results = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    start_time = time.time()
                    
                    for i, variable in enumerate(analysis_variables):
                        elapsed_time = time.time() - start_time
                        remaining_vars = len(analysis_variables) - i
                        eta = (elapsed_time / (i + 1)) * remaining_vars if i > 0 else 0
                        
                        status_text.text(
                            f"Processing {i+1}/{len(analysis_variables)}: {variable} "
                            f"(ETA: {eta/60:.1f} min)"
                        )
                        progress_bar.progress((i + 1) / len(analysis_variables))
                        
                        try:
                            if analysis_mode == "Multi-Cycle":
                                # Multi-cycle batch analysis
                                cycle_results_list = []
                                for cycle_year in selected_cycles:
                                    cycle_data = merged_data[merged_data['CYCLE'] == cycle_year].copy()
                                    if cycle_data.empty:
                                        continue
                                    
                                    result_df = run_bootstrap_analysis_for_all_values(cycle_data, variable, weight_col)
                                    result_df['CYCLE'] = cycle_year
                                    result_df['Variable'] = variable
                                    
                                    if categories:
                                        result_df['Label'] = result_df.apply(
                                            lambda row: get_value_label(variable, row['Value'], cycle_year, categories),
                                            axis=1
                                        )
                                    
                                    cycle_results_list.append(result_df)
                                
                                if cycle_results_list:
                                    combined_result_df = pd.concat(cycle_results_list, ignore_index=True)
                                    combined_results.append(combined_result_df)
                            else:
                                # Single cycle batch analysis
                                if use_harmonized and crosswalk:
                                    actual_varname = get_cycle_varname(variable, cycle, crosswalk)
                                else:
                                    actual_varname = variable
                                
                                result_df = run_bootstrap_analysis_for_all_values(merged_data, actual_varname, weight_col)
                                
                                if use_harmonized and categories:
                                    result_df['Label'] = result_df['Value'].apply(
                                        lambda v: get_value_label(variable, v, cycle, categories)
                                    )
                                
                                result_df['Variable'] = variable
                                combined_results.append(result_df)
                        except Exception as e:
                            st.warning(f"⚠️ Skipped {variable}: {str(e)}")
                    
                    if combined_results:
                        combined_df = pd.concat(combined_results, ignore_index=True)
                        set_session_state('combined_results', combined_df)
                        
                        st.success(f"✅ Batch analysis complete! Processed {len(combined_results)} variables.")
                        
                        # Download option
                        if analysis_mode == "Multi-Cycle" and is_multi_cycle(combined_df):
                            excel_data = create_multi_cycle_excel(combined_df, selected_cycles)
                            cycles_str = '_'.join(selected_cycles)
                            file_name = f"cchs_multi_cycle_{cycles_str}_analysis_results.xlsx"
                        else:
                            excel_data = create_excel_download(combined_df, f"CCHS_{cycle}_Analysis_Results")
                            file_name = f"cchs_{cycle}_analysis_results.xlsx"
                        
                        st.download_button(
                            label="📊 Download Results as Excel",
                            data=excel_data,
                            file_name=file_name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                    progress_bar.empty()
                    status_text.empty()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Enhanced crosstab report section with cycle information
    combined_results = get_session_state('combined_results')
    if combined_results is not None:
        if analysis_mode == "Multi-Cycle":
            cycles_str = ', '.join(selected_cycles)
            st.markdown(create_content_card(
                f"Multi-Cycle Crosstab Analysis - Cycles {cycles_str}",
                "Cross-tabulation report comparing prevalence across cycles with harmonized labels"
            ), unsafe_allow_html=True)
        else:
            st.markdown(create_content_card(
                f"Crosstab Analysis - Cycle {cycle}",
                "Cross-tabulation report of prevalence by variable and value with harmonized labels"
            ), unsafe_allow_html=True)
        
        display_crosstab_report(combined_results)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Enhanced results dashboard
    if combined_results is not None:
        st.markdown("---")
        
        # Enhanced results header with cycle info
        if analysis_mode == "Multi-Cycle":
            cycles_str = ', '.join(selected_cycles)
            header_title = f"📈 Analysis Results Dashboard - Cycles {cycles_str}"
            header_subtitle = "Comprehensive multi-cycle bootstrap analysis results with harmonized variable labels"
            badge_text = f"✅ {len(selected_cycles)} Cycles Complete"
        else:
            header_title = f"📈 Analysis Results Dashboard - Cycle {cycle}"
            header_subtitle = f"Comprehensive bootstrap analysis results with {'harmonized ' if use_harmonized else ''}variable labels"
            badge_text = f"✅ Cycle {cycle} Complete"
        
        st.markdown(f"""
        <div class="content-card">
            <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
                <div style="width: 4px; height: 40px; background: var(--gradient-primary); 
                            border-radius: 2px; margin-right: 1rem;"></div>
                <div style="flex: 1;">
                    <h2 style="margin: 0; color: var(--primary); font-size: 1.8rem; font-weight: 700;">
                        {header_title}
                    </h2>
                    <p style="margin: 4px 0 0 0; color: var(--text-light); font-weight: 500;">
                        {header_subtitle}
                    </p>
                </div>
                <div style="background: var(--gradient-accent); color: white; padding: 8px 16px; 
                           border-radius: 20px; font-weight: 600; font-size: 0.9rem;">
                    {badge_text}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Enhanced tabs with cycle-specific features
        if analysis_mode == "Multi-Cycle":
            tab1, tab2, tab3 = st.tabs([
                "📊 Crosstab Report", 
                "📈 Cycle Comparisons", 
                "💾 Data Export"
            ])
        else:
            tab1, tab2, tab3 = st.tabs([
                "📊 Crosstab Report", 
                "👥 Age Group Analysis", 
                "💾 Data Export"
            ])
        
        with tab1:
            if analysis_mode == "Multi-Cycle":
                cycles_str = ', '.join(selected_cycles)
                st.markdown(f"""
                <div style="background: var(--background-alt); padding: 1.5rem; border-radius: 12px; 
                            margin-bottom: 1.5rem; border-left: 4px solid var(--primary);">
                    <h4 style="margin: 0 0 0.5rem 0; color: var(--primary);">
                        📋 Cross-Tabulation Summary (Cycles {cycles_str})
                    </h4>
                    <p style="margin: 0; color: var(--text-light); font-size: 0.9rem;">
                        Interactive pivot table showing prevalence rates with harmonized labels across cycles.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background: var(--background-alt); padding: 1.5rem; border-radius: 12px; 
                            margin-bottom: 1.5rem; border-left: 4px solid var(--primary);">
                    <h4 style="margin: 0 0 0.5rem 0; color: var(--primary);">
                        📋 Cross-Tabulation Summary (Cycle {cycle})
                    </h4>
                    <p style="margin: 0; color: var(--text-light); font-size: 0.9rem;">
                        Interactive pivot table showing prevalence rates with {'harmonized labels' if use_harmonized else 'raw variable values'}.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            display_crosstab_report(combined_results)
        
        with tab2:
            if analysis_mode == "Multi-Cycle":
                cycles_str = ', '.join(selected_cycles)
                st.markdown(f"""
                <div style="background: var(--background-alt); padding: 1.5rem; border-radius: 12px; 
                            margin-bottom: 1.5rem; border-left: 4px solid var(--secondary);">
                    <h4 style="margin: 0 0 0.5rem 0; color: var(--primary);">
                        📈 Cycle Comparison Analysis
                    </h4>
                    <p style="margin: 0; color: var(--text-light); font-size: 0.9rem;">
                        Compare prevalence rates across selected cycles with trend analysis.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                if get_session_state('selected_variables'):
                    for variable in get_session_state('selected_variables'):
                        var_desc = merged_desc_dict.get(variable, None)
                        display_multi_cycle_results(combined_results, variable, var_desc)
                else:
                    st.info("💡 Select variables and run analysis to see cycle comparisons here.")
            else:
                # Age group analysis with enhanced cycle support
                st.markdown(f"""
                <div style="background: var(--background-alt); padding: 1.5rem; border-radius: 12px; 
                            margin-bottom: 1.5rem; border-left: 4px solid var(--secondary);">
                    <h4 style="margin: 0 0 0.5rem 0; color: var(--primary);">
                        👥 Age-Stratified Analysis (Cycle {cycle})
                    </h4>
                    <p style="margin: 0; color: var(--text-light); font-size: 0.9rem;">
                        Breakdown of analysis results by age groups to identify demographic patterns.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                age_analysis_enabled = st.checkbox(
                    "🔍 Enable Age Group-Wise Analysis", 
                    help="Perform detailed analysis stratified by age groups"
                )
                
                if age_analysis_enabled and get_session_state('selected_variables'):
                    # Age group analysis implementation
                    st.info("Age group analysis functionality would be implemented here with cycle-specific considerations.")
        
        with tab3:
            # Enhanced export with cycle information
            if analysis_mode == "Multi-Cycle":
                cycles_str = ', '.join(selected_cycles)
                st.markdown(f"""
                <div style="background: var(--background-alt); padding: 1.5rem; border-radius: 12px; 
                            margin-bottom: 1.5rem; border-left: 4px solid var(--accent);">
                    <h4 style="margin: 0 0 0.5rem 0; color: var(--primary);">
                        💾 Export Multi-Cycle Analysis Results
                    </h4>
                    <p style="margin: 0; color: var(--text-light); font-size: 0.9rem;">
                        Download your complete multi-cycle analysis results with comparison metadata.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background: var(--background-alt); padding: 1.5rem; border-radius: 12px; 
                            margin-bottom: 1.5rem; border-left: 4px solid var(--accent);">
                    <h4 style="margin: 0 0 0.5rem 0; color: var(--primary);">
                        💾 Export Analysis Results (Cycle {cycle})
                    </h4>
                    <p style="margin: 0; color: var(--text-light); font-size: 0.9rem;">
                        Download your complete analysis results with cycle and harmonization metadata.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            # Enhanced download section with cycle info
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📄 CSV Export**")
                csv = combined_results.to_csv().encode('utf-8')
                if analysis_mode == "Multi-Cycle":
                    cycles_str = '_'.join(selected_cycles)
                    file_name = f"cchs_multi_cycle_{cycles_str}_analysis_results.csv"
                    label = f"📥 Download Multi-Cycle Results (CSV)"
                    help_text = f"Download the complete multi-cycle analysis results as a CSV file"
                else:
                    file_name = f"cchs_{cycle}_analysis_results.csv"
                    label = f"📥 Download Cycle {cycle} Results (CSV)"
                    help_text = f"Download the complete {cycle} analysis results as a CSV file"
                
                st.download_button(
                    label=label,
                    data=csv,
                    file_name=file_name,
                    mime="text/csv",
                    help=help_text,
                    use_container_width=True
                )
            
            with col2:
                st.markdown("**📊 Excel Export**")
                if analysis_mode == "Multi-Cycle" and is_multi_cycle(combined_results):
                    excel_data = create_multi_cycle_excel(combined_results, selected_cycles)
                    cycles_str = '_'.join(selected_cycles)
                    file_name = f"cchs_multi_cycle_{cycles_str}_analysis_results.xlsx"
                    label = f"📊 Download Multi-Cycle Results (Excel)"
                    help_text = f"Download multi-cycle results as an Excel file with separate sheets per cycle"
                else:
                    excel_data = create_excel_download(combined_results, f"CCHS_{cycle}_Analysis")
                    file_name = f"cchs_{cycle}_analysis_results.xlsx"
                    label = f"📊 Download Cycle {cycle} Results (Excel)"
                    help_text = f"Download {cycle} results as an Excel file with metadata"
                
                st.download_button(
                    label=label,
                    data=excel_data,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help=help_text,
                    use_container_width=True
                )
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Footer with cycle information
    st.markdown("---")
    if analysis_mode == "Multi-Cycle":
        cycles_str = ', '.join(selected_cycles)
        harmonization_status = 'Enabled (Required)'
    else:
        cycles_str = cycle
        harmonization_status = 'Enabled' if use_harmonized else 'Disabled'
    
    st.markdown(f"""
    <div style="text-align: center; color: var(--text-light); padding: 1rem;">
        <p>🏥 Wellington-Dufferin-Guelph Public Health | CCHS Analysis Tool</p>
        <p style="font-size: 0.8rem;">Mode: {analysis_mode} | Cycles: {cycles_str} | Powered by Streamlit & Bootstrap Analysis | Harmonization: {harmonization_status}</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()