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
from src.data.loader import load_cycle_data, load_variable_descriptions, load_json_variable_descriptions, load_crosswalk, load_categories, merge_data
from src.data.processor import create_age_groups, apply_region_filter
from src.analysis.bootstrap import run_bootstrap_analysis_for_all_values
from src.ui.components import display_data_metrics, create_content_card
from src.ui.sidebar import (
    create_cycle_selector,
    create_variable_search_sidebar, 
    create_geographic_filters_sidebar, 
    create_apply_filters_section
)
from src.ui.results import display_results, display_crosstab_report
from src.utils.session import initialize_session_state, get_session_state, set_session_state
from src.utils.helpers import (
    validate_data_columns, 
    create_excel_download, 
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
        st.image("https://wdgpublichealth.ca/sites/all/themes/de_theme/logo.png", use_container_width=True)
    
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
    
    # NEW: Cycle selection at the top
    cycle = st.selectbox(
        "Select CCHS Cycle/Year",
        options=AVAILABLE_CYCLES,
        index=AVAILABLE_CYCLES.index(DEFAULT_CYCLE),
        help="Choose the survey cycle. Data and descriptions will load automatically based on this selection.",
        key="main_cycle_selector"  # Add unique key
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
    
    # Load harmonization data
    crosswalk = load_crosswalk()
    categories = load_categories()
    
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
        # If cycle changed in sidebar, update and rerun
        st.rerun()
    
    # Check if harmonized variables are available
    available_harmonized_vars = []
    use_harmonized = False
    if crosswalk and categories:
        # We'll check this after merging data
        pass
    
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
        # Get available harmonized variables for this cycle
        available_harmonized_vars = get_available_harmonized_vars(crosswalk, cycle, merged_data) if crosswalk else []
        
        st.markdown(create_content_card(
            "Variable Analysis",
            "Select variables for bootstrap prevalence analysis with multi-cycle harmonization support"
        ), unsafe_allow_html=True)
        
        # Enhanced variable selection with harmonization option
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**📋 Variable Selection**")
            
            # Toggle for harmonized variables
            if available_harmonized_vars:
                use_harmonized = st.checkbox(
                    "🔗 Use Harmonized Variables",
                    value=get_session_state('use_harmonized', False),
                    help="Use harmonized variable names that work across multiple cycles"
                )
                set_session_state('use_harmonized', use_harmonized)
                
                if use_harmonized:
                    st.info(f"📊 {len(available_harmonized_vars)} harmonized variables available for cycle {cycle}")
                    variable_options = available_harmonized_vars
                    variable_labels = {}
                    for var in variable_options:
                        if var in merged_desc_dict and merged_desc_dict[var]:
                            variable_labels[var] = f"{var}: {merged_desc_dict[var]}"
                        else:
                            variable_labels[var] = var
                else:
                    variable_options = [col for col in merged_data.columns if not col.startswith('BSW')]
                    variable_labels = {}
                    for var in variable_options:
                        if var in merged_desc_dict:
                            variable_labels[var] = f"{var}: {merged_desc_dict[var]}"
                        else:
                            variable_labels[var] = var
            else:
                use_harmonized = False
                variable_options = [col for col in merged_data.columns if not col.startswith('BSW')]
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
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, var(--light-bg) 0%, #E0F2F1 100%); 
                        padding: 1rem; border-radius: 12px; margin-top: 1rem; 
                        border-left: 4px solid var(--accent);">
                <h4 style="margin: 0 0 0.5rem 0; color: var(--primary); font-size: 0.9rem;">
                    📊 Analysis Summary
                </h4>
                <p style="margin: 0; font-size: 0.8rem; color: var(--text-light);">
                    <strong>Cycle:</strong> {cycle}<br>
                    <strong>Dataset:</strong> {len(merged_data):,} records<br>
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
                        # Get the actual variable name for this cycle if using harmonized variables
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
                        
                        # Display results for each variable
                        display_results(result_df, variable, use_labels=use_harmonized)
                        
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
                    if use_harmonized and available_harmonized_vars:
                        analysis_variables = available_harmonized_vars
                    else:
                        analysis_variables = [col for col in merged_data.columns 
                                            if col not in ['ONT_ID', 'WTS_S'] and not col.startswith('GEO') and not col.startswith('BSW')]
                    
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
                            # Get the actual variable name for this cycle if using harmonized variables
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
                        except Exception as e:
                            st.warning(f"⚠️ Skipped {variable}: {str(e)}")
                    
                    if combined_results:
                        combined_df = pd.concat(combined_results, ignore_index=True)
                        set_session_state('combined_results', combined_df)
                        
                        st.success(f"✅ Batch analysis complete! Processed {len(combined_results)} variables.")
                        
                        # Download option
                        excel_data = create_excel_download(combined_df, f"CCHS_{cycle}_Analysis_Results")
                        st.download_button(
                            label="📊 Download Results as Excel",
                            data=excel_data,
                            file_name=f"cchs_{cycle}_analysis_results.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                    progress_bar.empty()
                    status_text.empty()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Enhanced crosstab report section with cycle information
    combined_results = get_session_state('combined_results')
    if combined_results is not None:
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
        st.markdown(f"""
        <div class="content-card">
            <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
                <div style="width: 4px; height: 40px; background: var(--gradient-primary); 
                            border-radius: 2px; margin-right: 1rem;"></div>
                <div style="flex: 1;">
                    <h2 style="margin: 0; color: var(--primary); font-size: 1.8rem; font-weight: 700;">
                        📈 Analysis Results Dashboard - Cycle {cycle}
                    </h2>
                    <p style="margin: 4px 0 0 0; color: var(--text-light); font-weight: 500;">
                        Comprehensive bootstrap analysis results with {'harmonized ' if use_harmonized else ''}variable labels
                    </p>
                </div>
                <div style="background: var(--gradient-accent); color: white; padding: 8px 16px; 
                           border-radius: 20px; font-weight: 600; font-size: 0.9rem;">
                    ✅ Cycle {cycle} Complete
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Enhanced tabs with cycle-specific features
        tab1, tab2, tab3 = st.tabs([
            "📊 Crosstab Report", 
            "👥 Age Group Analysis", 
            "💾 Data Export"
        ])
        
        with tab1:
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
                st.download_button(
                    label=f"📥 Download Cycle {cycle} Results (CSV)",
                    data=csv,
                    file_name=f"cchs_{cycle}_analysis_results.csv",
                    mime="text/csv",
                    help=f"Download the complete {cycle} analysis results as a CSV file",
                    use_container_width=True
                )
            
            with col2:
                st.markdown("**📊 Excel Export**")
                excel_data = create_excel_download(combined_results, f"CCHS_{cycle}_Analysis")
                st.download_button(
                    label=f"📊 Download Cycle {cycle} Results (Excel)",
                    data=excel_data,
                    file_name=f"cchs_{cycle}_analysis_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help=f"Download {cycle} results as an Excel file with metadata",
                    use_container_width=True
                )
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Footer with cycle information
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: var(--text-light); padding: 1rem;">
        <p>🏥 Wellington-Dufferin-Guelph Public Health | CCHS Analysis Tool</p>
        <p style="font-size: 0.8rem;">Cycle {cycle} | Powered by Streamlit & Bootstrap Analysis | {'Harmonization Enabled' if use_harmonized else 'Standard Mode'}</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()