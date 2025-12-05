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
    Create multi-cycle selection component with precompute support.
    Falls back to real-time processing if precomputed data unavailable.
    
    Args:
        crosswalk: Optional crosswalk dictionary to show available harmonized variables
        data_dict: Optional dictionary mapping cycle -> DataFrame to check variable availability
    
    Returns:
        List of selected cycles
    """
    from src.data.smart_loader import get_precompute_summary
    from config.settings import ENABLE_PRECOMPUTING
    
    st.sidebar.markdown("""
    <div class="sidebar-card">
        <h3 style="margin: 0 0 1rem 0; color: var(--primary); display: flex; align-items: center;">
            📅 <span style="margin-left: 0.5rem;">Select Cycles</span>
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Check precompute status if enabled
    if ENABLE_PRECOMPUTING:
        summary = get_precompute_summary(AVAILABLE_CYCLES)
        
        if summary['all_precomputed']:
            st.sidebar.success("⚡ All cycles precomputed - fast analysis enabled!")
        elif summary['none_precomputed']:
            st.sidebar.info(
                "💡 Precomputed data not found. Multi-cycle analysis will use real-time processing.\n\n"
                "For faster analysis, run: `python scripts/precompute_cycles.py`"
            )
        elif summary['partial_precomputed']:
            st.sidebar.info(
                f"⚡ Precomputed: {', '.join(summary['precomputed_cycles'])}\n\n"
                f"⏱️ Real-time: {', '.join(summary['missing_cycles'])}\n\n"
                "Run `python scripts/precompute_cycles.py` to precompute all cycles."
            )
    
    selected_cycles = st.sidebar.multiselect(
        "Select CCHS Cycles/Years",
        options=AVAILABLE_CYCLES,
        default=[DEFAULT_CYCLE],
        help="Select one or more survey cycles to compare. Uses precomputed data when available, otherwise processes in real-time.",
        key="multi_cycle_selector"
    )
    
    if selected_cycles:
        # Show status for selected cycles
        if ENABLE_PRECOMPUTING:
            selected_summary = get_precompute_summary(selected_cycles)
            
            if selected_summary['all_precomputed']:
                # All precomputed - fast path
                common_var_count = selected_summary.get('common_variables_count', 0)
                st.sidebar.success(
                    f"✅ {len(selected_cycles)} cycle(s) selected: {', '.join(selected_cycles)}\n\n"
                    f"⚡ Fast mode enabled\n\n"
                    f"📊 {common_var_count} harmonized variables available"
                )
            elif selected_summary['none_precomputed']:
                # All real-time - legacy path
                st.sidebar.warning(
                    f"⏱️ {len(selected_cycles)} cycle(s): {', '.join(selected_cycles)}\n\n"
                    f"Processing in real-time (may be slower)\n\n"
                    "Consider running precompute script for better performance"
                )
                if crosswalk and data_dict:
                    from src.data.harmonizer import get_common_harmonized_vars
                    common_vars = get_common_harmonized_vars(selected_cycles, crosswalk, data_dict)
                    if common_vars:
                        st.sidebar.info(f"📊 {len(common_vars)} harmonized variables available")
            else:
                # Mixed - hybrid path
                st.sidebar.info(
                    f"🔄 Mixed mode for {len(selected_cycles)} cycle(s):\n\n"
                    f"⚡ Precomputed: {', '.join(selected_summary['precomputed_cycles'])}\n\n"
                    f"⏱️ Real-time: {', '.join(selected_summary['missing_cycles'])}"
                )
        else:
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
    """
    Legacy function kept for compatibility - no longer displays UI.
    Variable selection now handled in main area only.
    """
    return use_harmonized if harmonized_vars else False


def create_geographic_filters_sidebar(data=None):
    """
    Create the geographic filters sidebar section with optional preview.
    
    Args:
        data: Optional DataFrame to show record count preview
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div class="sidebar-card">
        <h3 style="margin: 0 0 1rem 0; color: var(--primary); display: flex; align-items: center;">
            Geographic Filters
        </h3>
        <p style="margin: 0 0 1rem 0; color: var(--text-light); font-size: 0.85rem;">
            Apply geographic boundaries to focus your analysis
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Enhanced filter options with better styling
    filter_by_district = st.sidebar.checkbox(
        "District-level GEODVCSD codes",
        help="Filter data by district-level geographic codes"
    )
    
    filter_by_municipality_dropdown = st.sidebar.checkbox(
        "Municipality-level codes",
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
                f"Selected: {', '.join(selected_municipalities)} "
                f"({len(district_codes)} areas)"
            )

    filter_by_health_region = st.sidebar.checkbox(
        "Health region-level GEODVHR4",
        help="Filter by health region boundaries"
    )
    
    # Show preview of record count if data is provided
    if data is not None and (filter_by_district or filter_by_municipality_dropdown or filter_by_health_region):
        from src.data.processor import apply_region_filter
        try:
            preview_data = apply_region_filter(data, filter_by_district, filter_by_health_region, district_codes)
            record_count = len(preview_data)
            original_count = len(data)
            pct = (record_count / original_count * 100) if original_count > 0 else 0
            
            if record_count < 100:
                st.sidebar.warning(f"Preview: {record_count:,} records ({pct:.1f}%) - Small sample size!")
            else:
                st.sidebar.info(f"Preview: {record_count:,} records ({pct:.1f}%)")
        except Exception:
            pass
    
    return filter_by_district, filter_by_municipality_dropdown, district_codes, filter_by_health_region


def create_inclusion_flag_filters_sidebar(data=None, desc_dict=None):
    """
    Create the inclusion flag filters sidebar section.
    Works for all cycles (2021, 2022, 2023).
    
    Args:
        data: Optional DataFrame to detect available inclusion flags
        desc_dict: Dictionary mapping variable names to descriptions (required for detection)
    
    Returns:
        Dictionary mapping flag_name -> True/False (whether to filter by it)
    """
    from src.utils.helpers import get_inclusion_flags
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div class="sidebar-card">
        <h3 style="margin: 0 0 1rem 0; color: var(--primary); display: flex; align-items: center;">
            🎯 <span style="margin-left: 0.5rem;">Data Quality Filters</span>
        </h3>
        <p style="margin: 0 0 1rem 0; color: var(--text-light); font-size: 0.85rem;">
            Filter by inclusion flags to ensure only eligible respondents are included
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    selected_flags = {}
    
    if data is not None and desc_dict is not None:
        # Detect available inclusion flags using description
        inclusion_flags = get_inclusion_flags(data, desc_dict)
        
        if inclusion_flags:
            st.sidebar.markdown("""
            <div style="background: var(--light-bg); padding: 0.75rem; border-radius: 8px; 
                       margin: 0.5rem 0; border-left: 3px solid var(--accent);">
                <strong style="color: var(--primary);">Select Inclusion Flags</strong>
                <p style="margin: 0.5rem 0 0 0; font-size: 0.8rem; color: var(--text-light);">
                    Only include respondents who were asked specific module questions
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Sort flags by variable name for consistency
            sorted_flags = sorted(inclusion_flags.items())
            
            # Show flags in checkboxes
            for flag, desc in sorted_flags:
                # Extract a short label from description (remove " - Inclusion Flag - (F)")
                short_desc = desc.replace(" - Inclusion Flag - (F)", "").strip()
                if not short_desc:
                    short_desc = flag
                
                selected_flags[flag] = st.sidebar.checkbox(
                    f"✅ {flag}: {short_desc}",
                    value=False,
                    help=desc,
                    key=f"inclusion_flag_{flag}"
                )
            
            # Show preview if any flags selected
            if any(selected_flags.values()):
                from src.data.processor import apply_inclusion_flag_filters
                try:
                    preview_data = apply_inclusion_flag_filters(data, selected_flags)
                    record_count = len(preview_data)
                    original_count = len(data)
                    pct = (record_count / original_count * 100) if original_count > 0 else 0
                    
                    if record_count < 100:
                        st.sidebar.warning(
                            f"📊 Preview: {record_count:,} records ({pct:.1f}%) "
                            f"- Small sample size!"
                        )
                    else:
                        st.sidebar.info(
                            f"📊 Preview: {record_count:,} records ({pct:.1f}%) "
                            f"after inclusion flag filters"
                        )
                except Exception as e:
                    st.sidebar.warning(f"Could not preview: {str(e)}")
        else:
            st.sidebar.info("ℹ️ No inclusion flags detected. Ensure variable descriptions are loaded.")
    else:
        if desc_dict is None:
            st.sidebar.info("ℹ️ Load data to see available inclusion flags")
        else:
            st.sidebar.info("ℹ️ Variable descriptions needed to detect inclusion flags")
    
    return selected_flags


def create_age_group_configuration():
    """
    Create age group configuration UI in sidebar.
    Returns a tuple of (age_bins, age_labels) to be used when creating age groups.
    """
    from config.settings import AGE_GROUP_PRESETS
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div class="sidebar-card">
        <h3 style="margin: 0 0 1rem 0; color: var(--primary); display: flex; align-items: center;">
            👥 <span style="margin-left: 0.5rem;">Age Group Configuration</span>
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    preset = st.sidebar.selectbox(
        "Select Age Group Preset",
        options=list(AGE_GROUP_PRESETS.keys()),
        index=0,
        help="Choose a predefined age grouping or create a custom one",
        key="age_group_preset"
    )
    
    if preset == "Custom":
        st.sidebar.markdown("**Define Custom Age Groups:**")
        st.sidebar.info("💡 Enter bin edges separated by commas (e.g., 0,18,30,50,65,120)")
        
        bins_input = st.sidebar.text_input(
            "Bin Edges (comma-separated)",
            value="0,15,25,45,65,120",
            help="Enter age boundaries. Must start with 0 and end with a high value (e.g., 120)",
            key="custom_age_bins"
        )
        
        labels_input = st.sidebar.text_input(
            "Labels (comma-separated)",
            value="0-14,15-24,25-44,45-64,65+",
            help="Enter labels for each age range. Number of labels = bins - 1",
            key="custom_age_labels"
        )
        
        try:
            bins = [int(x.strip()) for x in bins_input.split(',')]
            labels = [x.strip() for x in labels_input.split(',')]
            
            if len(labels) != len(bins) - 1:
                st.sidebar.error(f"❌ Error: {len(labels)} labels provided but need {len(bins)-1} (bins-1)")
                return None, None
            
            st.sidebar.success(f"✅ Custom age groups: {len(labels)} groups defined")
            
            # Show preview
            with st.sidebar.expander("👁️ Preview Age Groups", expanded=False):
                for i, label in enumerate(labels):
                    st.write(f"• {label}: {bins[i]} to {bins[i+1]-1}")
            
            return bins, labels
            
        except ValueError as e:
            st.sidebar.error(f"❌ Invalid format: {str(e)}")
            return None, None
    else:
        # Use preset
        config = AGE_GROUP_PRESETS[preset]
        bins = config["bins"]
        labels = config["labels"]
        
        st.sidebar.success(f"✅ Using preset: {len(labels)} age groups")
        
        # Show preview
        with st.sidebar.expander("👁️ Preview Age Groups", expanded=False):
            for i, label in enumerate(labels):
                st.write(f"• {label}: {bins[i]} to {bins[i+1]-1}")
        
        return bins, labels


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
        "🎯 Apply All Filters", 
        type="primary",
        help="Apply geographic and inclusion flag filters to the dataset",
        use_container_width=True
    )