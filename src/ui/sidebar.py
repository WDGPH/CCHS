"""Sidebar functionality for the CCHS application."""

import streamlit as st
from config.settings import MUNICIPALITY_OPTIONS, AVAILABLE_CYCLES, DEFAULT_CYCLE


def create_analysis_mode_selector():
    """Create analysis mode selector (Single Cycle vs Multi-Cycle)."""
    st.sidebar.markdown("""
    <div class="sidebar-card">
        <h3 style="margin: 0 0 1rem 0; color: var(--primary); display: flex; align-items: center;">
            📅 <span style="margin-left: 0.5rem;">Analysis Mode</span>
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    analysis_mode = st.sidebar.radio(
        "Select Analysis Mode",
        options=["Single Cycle", "Multi-Cycle"],
        index=0,
        help="Single Cycle: Analyze one survey year. Multi-Cycle: Compare across multiple years.",
        key="analysis_mode_selector"
    )
    
    return analysis_mode


def create_cycle_selector():
    """Create cycle selection component for single cycle mode."""
    st.markdown("""
    <div class="sidebar-card">
        <h3 style="margin: 0 0 1rem 0; color: var(--primary); display: flex; align-items: center;">
            📅 <span style="margin-left: 0.5rem;">Survey Cycle</span>
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    cycle = st.sidebar.selectbox(
        "Select CCHS Cycle/Year",
        options=AVAILABLE_CYCLES,
        index=AVAILABLE_CYCLES.index(DEFAULT_CYCLE),
        help="Choose the survey cycle. Data and descriptions will load automatically based on this selection.",
        key="sidebar_cycle_selector"
    )
    
    return cycle


def create_multi_cycle_selector(crosswalk=None, data_dict=None):
    """
    Create multi-cycle selection component.
    
    Args:
        crosswalk: Optional crosswalk dictionary to show available harmonized variables
        data_dict: Optional dictionary mapping cycle -> DataFrame to check variable availability
    
    Returns:
        List of selected cycles
    """
    st.sidebar.markdown("""
    <div class="sidebar-card">
        <h3 style="margin: 0 0 1rem 0; color: var(--primary); display: flex; align-items: center;">
            📅 <span style="margin-left: 0.5rem;">Select Cycles</span>
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    selected_cycles = st.sidebar.multiselect(
        "Select CCHS Cycles/Years",
        options=AVAILABLE_CYCLES,
        default=[DEFAULT_CYCLE],
        help="Select one or more survey cycles to compare. Data will be harmonized automatically.",
        key="multi_cycle_selector"
    )
    
    if selected_cycles:
        st.sidebar.success(f"✅ Selected {len(selected_cycles)} cycle(s): {', '.join(selected_cycles)}")
        
        if crosswalk and data_dict:
            from src.data.harmonizer import get_common_harmonized_vars
            common_vars = get_common_harmonized_vars(selected_cycles, crosswalk, data_dict)
            if common_vars:
                st.sidebar.info(f"📊 {len(common_vars)} harmonized variables available across all selected cycles")
            else:
                st.sidebar.warning("⚠️ No common harmonized variables found across selected cycles")
    else:
        st.sidebar.warning("⚠️ Please select at least one cycle")
    
    return selected_cycles


def create_variable_search_sidebar(desc_df, desc_dict, harmonized_vars=None, use_harmonized=False):
    """Create the variable search sidebar section with optional harmonized variable support."""
    st.sidebar.markdown("""
    <div class="sidebar-card">
        <h3 style="margin: 0 0 1rem 0; color: var(--primary); display: flex; align-items: center;">
            🔍 <span style="margin-left: 0.5rem;">CCHS Variable Search</span>
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Add harmonization toggle if harmonized variables are available
    if harmonized_vars:
        use_harmonized = st.sidebar.checkbox(
            "🔗 Use Harmonized Variables",
            value=use_harmonized,
            help="Use harmonized variable names that work across multiple cycles"
        )
    
    if use_harmonized and harmonized_vars:
        # Display harmonized variables
        st.sidebar.markdown("""
        <div style="background: var(--light-bg); padding: 0.75rem; border-radius: 8px; 
                   margin: 0.5rem 0; border-left: 3px solid var(--accent);">
            <strong style="color: var(--primary);">Harmonized Variables Available</strong>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.8rem; color: var(--text-light);">
                {len(harmonized_vars)} harmonized variables for this cycle
            </p>
        </div>
        """.format(len=len), unsafe_allow_html=True)
        
        # Search in harmonized variables
        search_term = st.sidebar.text_input(
            "🔤 Search harmonized variables", 
            placeholder="e.g., smoking, health",
            help="Search harmonized variable names"
        ).lower()
        
        if search_term:
            matches = [var for var in harmonized_vars if search_term in var.lower()]
            if matches:
                st.sidebar.success(f"✅ Found {len(matches)} harmonized match(es)")
                for match in matches[:10]:  # Show first 10 matches
                    st.sidebar.markdown(f"• **{match}**")
            else:
                st.sidebar.warning(f"⚠️ No harmonized variables found containing '{search_term}'")
    
    elif desc_df is not None:
        # Original variable search functionality
        search_option = st.sidebar.radio(
            "🎯 Search by:", 
            ["Variable Code", "Description"],
            help="Choose how to search the variable database"
        )
        
        if search_option == "Variable Code":
            search_term = st.sidebar.text_input(
                "🔤 Enter variable code", 
                placeholder="e.g., GEN_005",
                help="Search for specific variable codes"
            ).upper()
            if search_term:
                matches = desc_df[desc_df['Variable'].str.contains(search_term, case=False)]
                if not matches.empty:
                    st.sidebar.success(f"✅ Found {len(matches)} match(es)")
                    st.sidebar.dataframe(matches, use_container_width=True)
                else:
                    st.sidebar.warning(f"⚠️ No variables found containing '{search_term}'")
        else:
            search_term = st.sidebar.text_input(
                "📝 Enter description keyword", 
                placeholder="e.g., health, smoking",
                help="Search within variable descriptions"
            )
            if search_term:
                matches = desc_df[desc_df['Description'].str.contains(search_term, case=False)]
                if not matches.empty:
                    st.sidebar.success(f"✅ Found {len(matches)} match(es)")
                    st.sidebar.dataframe(matches, use_container_width=True)
                else:
                    st.sidebar.warning(f"⚠️ No descriptions found containing '{search_term}'")
        
        # Enhanced variable info display
        st.sidebar.markdown("---")
        st.sidebar.markdown("""
        <div class="sidebar-card">
            <h3 style="margin: 0 0 1rem 0; color: var(--primary); display: flex; align-items: center;">
                📋 <span style="margin-left: 0.5rem;">Selected Variables</span>
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.get('selected_variables', []):
            for i, var in enumerate(st.session_state['selected_variables']):
                if var in desc_dict:
                    st.sidebar.markdown(f"""
                    <div style="background: white; padding: 0.75rem; border-radius: 8px; 
                               margin-bottom: 0.5rem; border-left: 3px solid var(--secondary);">
                        <strong style="color: var(--primary);">{var}</strong><br>
                        <span style="color: var(--text-light); font-size: 0.85rem;">{desc_dict[var]}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.sidebar.info("💡 No variables selected yet")
    else:
        st.sidebar.error("❌ Variable descriptions file not found or couldn't be loaded")
    
    return use_harmonized if harmonized_vars else False


def create_geographic_filters_sidebar():
    """Create the geographic filters sidebar section."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div class="sidebar-card">
        <h3 style="margin: 0 0 1rem 0; color: var(--primary); display: flex; align-items: center;">
            🗺️ <span style="margin-left: 0.5rem;">Geographic Filters</span>
        </h3>
        <p style="margin: 0 0 1rem 0; color: var(--text-light); font-size: 0.85rem;">
            Apply geographic boundaries to focus your analysis
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Enhanced filter options with better styling
    filter_by_district = st.sidebar.checkbox(
        "🏛️ District-level GEODVCSD codes",
        help="Filter data by district-level geographic codes"
    )
    
    filter_by_municipality_dropdown = st.sidebar.checkbox(
        "🏘️ Municipality-level codes",
        help="Filter by specific municipality boundaries"
    )
    
    district_codes = None
    if filter_by_municipality_dropdown:
        st.sidebar.markdown("""
        <div style="background: var(--light-bg); padding: 0.75rem; border-radius: 8px; 
                   margin: 0.5rem 0; border-left: 3px solid var(--accent);">
            <strong style="color: var(--primary);">Select Municipality</strong>
        </div>
        """, unsafe_allow_html=True)
        
        selected_municipalities = st.sidebar.multiselect(
            "Choose area(s) of interest:",
            options=list(MUNICIPALITY_OPTIONS.keys()),
            help="Select one or more municipalities for analysis"
        )
        
        # Combine selected codes
        district_codes = {}
        for m in selected_municipalities:
            district_codes.update(MUNICIPALITY_OPTIONS[m])
        
        if selected_municipalities:
            st.sidebar.success(
                f"✅ Selected: {', '.join(selected_municipalities)} "
                f"({len(district_codes)} areas)"
            )

    filter_by_health_region = st.sidebar.checkbox(
        "🏥 Health region-level GEODVHR4",
        help="Filter by health region boundaries"
    )
    
    return filter_by_district, filter_by_municipality_dropdown, district_codes, filter_by_health_region


def create_apply_filters_section():
    """Create the apply filters section in sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style="background: white; padding: 1rem; border-radius: 12px; 
               margin: 1rem 0; text-align: center; border: 2px solid var(--border);">
        <h4 style="margin: 0 0 0.5rem 0; color: var(--primary);">Ready to Apply Filters?</h4>
        <p style="margin: 0; color: var(--text-light); font-size: 0.85rem;">
            Click below to filter your dataset based on the selected criteria
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    return st.sidebar.button(
        "🎯 Apply Geographic Filters", 
        type="primary",
        help="Apply all selected geographic filters to the dataset",
        use_container_width=True
    )