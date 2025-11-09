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
    load_cycle_variable_info, load_crosswalk, load_categories, merge_data
)
from src.data.processor import create_age_groups, apply_region_filter
from src.analysis.bootstrap import run_bootstrap_analysis_for_all_values
from src.ui.components import (
    display_data_metrics, create_content_card, create_workflow_stepper,
    get_quality_badge, display_quality_legend
)
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
    get_cycle_value_label,
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
    
    # Handle mode switching with warning if user has active work
    previous_mode = get_session_state('analysis_mode')
    if previous_mode and previous_mode != analysis_mode:
        # Check if user has active work
        has_selections = get_session_state('selected_variables') and len(get_session_state('selected_variables')) > 0
        has_results = get_session_state('combined_results') is not None
        
        if has_selections or has_results:
            st.warning(f"⚠️ Switching from {previous_mode} to {analysis_mode} will clear your current selections and results.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Continue and Clear", type="primary"):
                    set_session_state('filtered_data', None)
                    set_session_state('merged_data', None)
                    set_session_state('combined_results', None)
                    set_session_state('selected_variables', [])
                    set_session_state('analysis_mode', analysis_mode)
                    st.rerun()
            with col2:
                if st.button("Cancel"):
                    st.rerun()
            st.stop()
        else:
            # No active work, safe to switch
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
        
        # Load multi-cycle harmonized data (load once, not twice!)
        with st.spinner("🔄 Loading and harmonizing multi-cycle data..."):
            data, bootstrap_data = load_multi_cycle_data(selected_cycles, crosswalk, categories)
        
        if data is None or bootstrap_data is None:
            st.error("❌ Failed to harmonize and combine multi-cycle data.")
            st.stop()
        
        # Get common harmonized variables from the already-harmonized data
        # No need to load raw data again - check which variables exist in all cycles
        available_harmonized_vars = []
        if crosswalk:
            for harmonized_var in crosswalk.keys():
                if harmonized_var in data.columns:
                    # Verify it exists in all selected cycles
                    has_data_in_all_cycles = True
                    for cycle_year in selected_cycles:
                        cycle_subset = data[data['CYCLE'] == cycle_year]
                        if cycle_subset.empty or harmonized_var not in cycle_subset.columns or cycle_subset[harmonized_var].isna().all():
                            has_data_in_all_cycles = False
                            break
                    if has_data_in_all_cycles:
                        available_harmonized_vars.append(harmonized_var)
        
        # Load variable descriptions (use first cycle as reference)
        desc_df, desc_dict = load_variable_descriptions(selected_cycles[0])
        json_desc_dict = load_json_variable_descriptions(selected_cycles[0])
        
        # Load cycle variable info for all selected cycles (for labels)
        cycle_var_info_dict = {cycle: load_cycle_variable_info(cycle) for cycle in selected_cycles}
        
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
        # Single cycle mode - use sidebar selector only
        cycle = create_cycle_selector()
        set_session_state('cycle', cycle)
        
        # Load data based on selected cycle
        data, bootstrap_data = load_cycle_data(cycle)
        if data is None or bootstrap_data is None:
            st.error("❌ Failed to load required data files. Please check your data directory.")
            return
        
        # Load variable descriptions for the selected cycle
        desc_df, desc_dict = load_variable_descriptions(cycle)
        json_desc_dict = load_json_variable_descriptions(cycle)
        cycle_var_info = load_cycle_variable_info(cycle)  # Load full info with categories
        merged_desc_dict = merge_descriptions(json_desc_dict, desc_dict)
        
        # Display data overview
        st.markdown(create_content_card(
            f"Dataset Overview - Cycle {cycle}",
            f"Summary statistics and metadata for the {cycle} CCHS dataset"
        ), unsafe_allow_html=True)
        
        display_data_metrics(data)
        st.markdown("</div>", unsafe_allow_html=True)
        
        available_harmonized_vars = []
        use_harmonized = False
    
    # Determine current workflow step
    current_step = 1
    if get_session_state('merged_data') is not None:
        if get_session_state('selected_variables') and len(get_session_state('selected_variables')) > 0:
            if get_session_state('combined_results') is not None:
                current_step = 4
            else:
                current_step = 3
        else:
            current_step = 2
    
    # Display workflow progress indicator
    create_workflow_stepper(current_step)
    
    # Geographic filters with data preview
    filter_by_district, filter_by_municipality_dropdown, district_codes, filter_by_health_region = create_geographic_filters_sidebar(data)
    
    # Apply filters button
    apply_filters = create_apply_filters_section()
    
    # Main content area - Auto-merge data after filtering
    if apply_filters:
        with st.spinner("🔄 Applying geographic filters and preparing data..."):
            filtered_data = apply_region_filter(
                data, filter_by_district, filter_by_health_region, district_codes
            )
            
            # Add age groups
            filtered_data = create_age_groups(filtered_data, 'DHH_AGE')
            
            # Automatically merge with bootstrap data (no manual step needed)
            merged_data = merge_data(filtered_data, bootstrap_data)
            
            # Store in session state
            set_session_state('filtered_data', filtered_data)
            set_session_state('merged_data', merged_data)
            
        st.success(f"✅ Filters applied and data prepared! Dataset now contains {len(filtered_data):,} records, ready for analysis.")
        
        # Display filtered data metrics
        st.markdown(create_content_card(
            "Filtered Dataset",
            "Statistics for the geographically filtered dataset"
        ), unsafe_allow_html=True)
        
        display_data_metrics(filtered_data)
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
            st.markdown("**Variable Selection**")
            
            # Toggle for harmonized variables (only show in single-cycle mode)
            if analysis_mode == "Single Cycle" and available_harmonized_vars:
                use_harmonized = st.checkbox(
                    "Use Harmonized Variables",
                    value=get_session_state('use_harmonized', False),
                    help="Use harmonized variable names that work across multiple cycles"
                )
                set_session_state('use_harmonized', use_harmonized)
            elif analysis_mode == "Multi-Cycle":
                use_harmonized = True
                st.info(f"Multi-cycle mode: Using {len(available_harmonized_vars)} harmonized variables available across all selected cycles")
            
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
            
            # Add search filter
            search_term = st.text_input(
                "Search variables by code or description:",
                placeholder="e.g., health, smoking, GEN_005",
                help="Filter the variable list by keyword"
            )
            
            # Filter options based on search
            if search_term:
                filtered_options = [
                    var for var in variable_options 
                    if search_term.lower() in var.lower() or 
                       search_term.lower() in variable_labels.get(var, '').lower()
                ]
                if filtered_options:
                    st.success(f"Found {len(filtered_options)} matching variable(s)")
                else:
                    st.warning("No variables match your search")
                    filtered_options = variable_options
            else:
                filtered_options = variable_options
            
            selected_variables = st.multiselect(
                "Select variables for analysis:",
                options=filtered_options,
                format_func=lambda x: variable_labels.get(x, x),
                help="Choose one or more variables to analyze",
                key="variable_multiselect"
            )
            
            # Store selected variables in session state
            set_session_state('selected_variables', selected_variables)
            
            if selected_variables:
                st.markdown(f"**{len(selected_variables)} variable(s) selected**")
                with st.expander("View Selected Variables", expanded=False):
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
                run_single = st.button("Analyze Selected Variables", type="primary")
            with col2:
                with st.expander("Batch Analysis (All Variables)"):
                    if analysis_mode == "Multi-Cycle":
                        total_vars = len(available_harmonized_vars) if available_harmonized_vars else 0
                    elif use_harmonized and available_harmonized_vars:
                        total_vars = len(available_harmonized_vars)
                    else:
                        total_vars = len([col for col in merged_data.columns 
                                        if col not in ['ONT_ID', 'WTS_S', 'CYCLE'] and not col.startswith('GEO') and not col.startswith('BSW')])
                    
                    st.warning(f"This will process all {total_vars} available variables. Estimated time: {total_vars * 2 // 60} minutes.")
                    confirm_batch = st.checkbox(f"I understand this will process {total_vars} variables")
                    run_batch = st.button("Run Batch Analysis", disabled=not confirm_batch, type="primary")
            
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
                                
                                # Add labels - try harmonized categories first, then fall back to cycle-specific
                                def get_label_with_fallback(row):
                                    # Try harmonized categories first
                                    if categories:
                                        label = get_value_label(variable, row['Value'], cycle_year, categories)
                                        if label != str(row['Value']):  # Found a label
                                            return label
                                    # Fallback to cycle-specific JSON
                                    cycle_info = cycle_var_info_dict.get(cycle_year, {})
                                    return get_cycle_value_label(variable, row['Value'], cycle_info)
                                
                                result_df['Label'] = result_df.apply(get_label_with_fallback, axis=1)
                                
                                cycle_results_list.append(result_df)
                            
                            if cycle_results_list:
                                combined_result_df = pd.concat(cycle_results_list, ignore_index=True)
                                combined_results.append(combined_result_df)
                                
                                # Display multi-cycle results immediately
                                var_desc = merged_desc_dict.get(variable, None)
                                display_multi_cycle_results(combined_result_df, variable, var_desc)
                        else:
                            # Single cycle analysis (existing behavior)
                            if use_harmonized and crosswalk:
                                actual_varname = get_cycle_varname(variable, cycle, crosswalk)
                            else:
                                actual_varname = variable
                            
                            result_df = run_bootstrap_analysis_for_all_values(merged_data, actual_varname, weight_col)
                            
                            # Add value labels from cycle-specific JSON (ALWAYS, not just for harmonized)
                            result_df['Label'] = result_df['Value'].apply(
                                lambda v: get_cycle_value_label(actual_varname, v, cycle_var_info)
                            )
                            
                            result_df['Variable'] = variable
                            combined_results.append(result_df)
                            
                            # Display results immediately (like main.py does)
                            var_desc = merged_desc_dict.get(variable, variable)
                            display_results(result_df, variable, use_labels='Label' in result_df.columns, variable_description=var_desc)
                        
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
                        st.warning(f"Skipped {variable}: {str(e)}")
                
                if combined_results:
                    combined_df = pd.concat(combined_results, ignore_index=True)
                    set_session_state('combined_results', combined_df)
                    
                    st.success(f"Batch analysis complete! Processed {len(combined_results)} variables.")
                
                progress_bar.empty()
                status_text.empty()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Consolidated results dashboard (removed duplicate crosstab section)
    combined_results = get_session_state('combined_results')
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
        
        # Simplified tabs - Results & Export only
        if analysis_mode == "Multi-Cycle":
            tab1, tab2 = st.tabs([
                "Results & Visualizations", 
                "Export Data"
            ])
        else:
            tab1, tab2 = st.tabs([
                "Results & Visualizations", 
                "Export Data"
            ])
        
        with tab1:
            # Show visualizations and detailed results
            if analysis_mode == "Multi-Cycle" and get_session_state('selected_variables'):
                # Multi-cycle: show cycle comparison visualizations
                st.subheader("Cycle Comparison Visualizations")
                for variable in get_session_state('selected_variables'):
                    var_desc = merged_desc_dict.get(variable, None)
                    display_multi_cycle_results(combined_results, variable, var_desc)
                
                st.markdown("---")
            elif analysis_mode == "Single Cycle" and get_session_state('selected_variables'):
                # Single-cycle: show standard bar charts for each variable
                st.subheader("Variable Analysis Results")
                for variable in get_session_state('selected_variables'):
                    var_results = combined_results[combined_results['Variable'] == variable].copy()
                    if not var_results.empty:
                        var_desc = merged_desc_dict.get(variable, variable)
                        display_results(var_results, variable, use_labels='Label' in var_results.columns, variable_description=var_desc)
                
                st.markdown("---")
            
            # Display cross-tabulation summary
            st.subheader("Cross-Tabulation Summary")
            display_crosstab_report(combined_results)
        
        with tab2:
            # Consolidated export section
            st.subheader("Export Analysis Results")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**CSV Format**")
                csv = combined_results.to_csv().encode('utf-8')
                if analysis_mode == "Multi-Cycle":
                    cycles_str = '_'.join(selected_cycles)
                    file_name = f"cchs_multi_cycle_{cycles_str}_results.csv"
                else:
                    file_name = f"cchs_{cycle}_results.csv"
                
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=file_name,
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col2:
                st.markdown("**Excel Format**")
                if analysis_mode == "Multi-Cycle" and is_multi_cycle(combined_results):
                    excel_data = create_multi_cycle_excel(combined_results, selected_cycles)
                    cycles_str = '_'.join(selected_cycles)
                    file_name = f"cchs_multi_cycle_{cycles_str}_results.xlsx"
                else:
                    excel_data = create_excel_download(combined_results, f"CCHS_{cycle}_Analysis")
                    file_name = f"cchs_{cycle}_results.xlsx"
                
                st.download_button(
                    label="Download Excel",
                    data=excel_data,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
        <p> Wellington-Dufferin-Guelph Public Health | CCHS Analysis Tool</p>
        <p style="font-size: 0.8rem;">Mode: {analysis_mode} | Cycles: {cycles_str} | Powered by Streamlit & Bootstrap Analysis | Harmonization: {harmonization_status}</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()