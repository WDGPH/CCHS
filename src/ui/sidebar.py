"""Sidebar functionality for the CCHS application."""

import streamlit as st
from config.settings import (
    AVAILABLE_CYCLES,
    DEFAULT_CYCLE,
    KNOWN_DISTRICT_LABELS,
    KNOWN_HEALTH_REGION_LABELS,
    MUNICIPALITY_OPTIONS,
    PUBLIC_HEALTH_UNITS,
)
from src.data.loader import load_ontario_csd_lookup, load_ontario_official_municipalities


def create_analysis_mode_selector():
    """Create the single-cycle or cross-cycle trend mode selector."""
    st.sidebar.markdown("""
    <div class="sidebar-card">
        <h3 style="margin: 0 0 1rem 0; color: var(--primary); display: flex; align-items: center;">
            📅 <span style="margin-left: 0.5rem;">Analysis Mode</span>
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    analysis_mode = st.sidebar.radio(
        "Select Analysis Mode",
        options=["Single Cycle", "Multi-Cycle Trends", "Cycle Pooling"],
        index=0,
        help=(
            "Single Cycle analyzes one survey year. Multi-Cycle Trends "
            "calculates each selected year separately and compares estimates. "
            "Cycle Pooling combines two or more years into one average-period "
            "estimate with scaled survey and bootstrap weights."
        ),
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


def create_multi_cycle_selector(crosswalk=None, data_dict=None, pooling=False):
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
    from src.data.precompute import run_precompute_workflow
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
            if st.sidebar.button("Precompute now", key="precompute_all_cycles_button", type="primary"):
                if not crosswalk:
                    st.sidebar.error("Crosswalk data is required before precomputing.")
                else:
                    with st.spinner("Precomputing harmonized multi-cycle data..."):
                        result = run_precompute_workflow(
                            cycles=AVAILABLE_CYCLES,
                            crosswalk=crosswalk,
                            categories={},
                        )
                    if result["success"]:
                        st.cache_data.clear()
                        st.sidebar.success("Precompute complete. Reloading cached state...")
                        st.rerun()
                    else:
                        st.sidebar.error(result["message"])
        elif summary['partial_precomputed']:
            st.sidebar.info(
                f"⚡ Precomputed: {', '.join(summary['precomputed_cycles'])}\n\n"
                f"⏱️ Real-time: {', '.join(summary['missing_cycles'])}\n\n"
                "Run `python scripts/precompute_cycles.py` to precompute all cycles."
            )
            if st.sidebar.button("Precompute missing cycles", key="precompute_missing_cycles_button"):
                if not crosswalk:
                    st.sidebar.error("Crosswalk data is required before precomputing.")
                else:
                    with st.spinner("Precomputing missing harmonized data..."):
                        result = run_precompute_workflow(
                            cycles=summary['missing_cycles'],
                            crosswalk=crosswalk,
                            categories={},
                        )
                    if result["success"]:
                        st.cache_data.clear()
                        st.sidebar.success("Missing cycles precomputed. Reloading cached state...")
                        st.rerun()
                    else:
                        st.sidebar.error(result["message"])
    
    selected_cycles = st.sidebar.multiselect(
        "Select CCHS Cycles/Years",
        options=AVAILABLE_CYCLES,
        default=(AVAILABLE_CYCLES[-2:] if pooling else [DEFAULT_CYCLE]),
        help=(
            "Select at least two cycles to combine into one pooled estimate."
            if pooling else
            "Select survey cycles for separate, cycle-specific estimates and "
            "cross-year trends. Records are not pooled across cycles."
        ),
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
    
    filter_by_health_region = st.sidebar.checkbox(
        "Public health unit / health region",
        help="Filter by one or more GEODVHR4 health region codes"
    )

    selected_health_regions = []
    available_health_region_labels = {}
    if filter_by_health_region:
        available_health_regions = _get_available_health_region_codes(data)
        available_health_region_labels = {
            code: _get_health_region_label(code)
            for code in available_health_regions
        }

        selected_health_regions = st.sidebar.multiselect(
            "Choose public health unit(s):",
            options=available_health_regions,
            format_func=lambda code: f"{available_health_region_labels.get(code, f'Health Region {code}')} ({code})",
            help="Select one or more health region codes for analysis"
        )

        if not available_health_regions:
            st.sidebar.warning("No GEODVHR4 values found in the loaded dataset.")

    filter_by_municipality_dropdown = st.sidebar.checkbox(
        "Official Ontario municipalities",
        help="Filter by official Ontario municipalities matched to GEODVCSD codes"
    )

    filter_by_configured_groups = st.sidebar.checkbox(
        "Configured municipality groups",
        help="Filter using configured groupings such as Dufferin, Wellington, and Guelph"
    )

    municipality_codes = {}
    configured_group_codes = {}
    if filter_by_configured_groups:
        municipality_group_options = _get_municipality_group_options(selected_health_regions)

        st.sidebar.markdown("""
        <div style="background: var(--light-bg); padding: 0.75rem; border-radius: 8px; 
                   margin: 0.5rem 0; border-left: 3px solid var(--accent);">
            <strong style="color: var(--primary);">Select Configured Group</strong>
        </div>
        """, unsafe_allow_html=True)

        if municipality_group_options:
            selected_groups = st.sidebar.multiselect(
                "Choose group(s):",
                options=list(municipality_group_options.keys()),
                help="Select one or more configured municipality groups for analysis"
            )

            for group in selected_groups:
                configured_group_codes.update(municipality_group_options[group])

            if selected_groups:
                st.sidebar.success(
                    f"Selected group(s): {', '.join(selected_groups)} "
                    f"({len(configured_group_codes)} census subdivision(s))"
                )
        else:
            st.sidebar.warning("No configured municipality groups are available for the current selection.")

    if filter_by_municipality_dropdown:
        municipality_options = _get_available_official_municipality_codes(data)

        if selected_health_regions:
            filtered_preview_codes = _filter_district_codes_by_health_regions(
                data,
                municipality_options,
                selected_health_regions,
            )
            if filtered_preview_codes:
                municipality_options = filtered_preview_codes

        st.sidebar.markdown("""
        <div style="background: var(--light-bg); padding: 0.75rem; border-radius: 8px; 
                   margin: 0.5rem 0; border-left: 3px solid var(--accent);">
            <strong style="color: var(--primary);">Select Official Municipality</strong>
        </div>
        """, unsafe_allow_html=True)

        if municipality_options:
            selected_municipality_codes = st.sidebar.multiselect(
                "Choose municipality(s):",
                options=municipality_options,
                format_func=_format_official_municipality_label,
                help="Select one or more official Ontario municipalities for analysis"
            )

            if selected_municipality_codes:
                municipality_codes = {
                    int(code): _format_official_municipality_label(int(code))
                    for code in selected_municipality_codes
                }
                municipality_labels = [
                    _format_official_municipality_label(int(code))
                    for code in selected_municipality_codes
                ]
                st.sidebar.success(
                    f"Selected {len(municipality_codes)} municipality(s): {', '.join(municipality_labels)}"
                )
        else:
            st.sidebar.warning("No official municipality values are available for the current selection.")

    filter_by_district = st.sidebar.checkbox(
        "Municipality / census subdivision (GEODVCSD)",
        help="Filter by specific census subdivision codes using the full Ontario lookup"
    )

    manual_district_codes = {}
    if filter_by_district:
        available_district_codes = _get_available_district_codes(data)
        selected_district_codes = st.sidebar.multiselect(
            "Choose municipality / subdivision(s):",
            options=available_district_codes,
            format_func=_format_district_label,
            help="Select one or more GEODVCSD district codes for analysis"
        )

        if selected_district_codes:
            manual_district_codes = {
                int(code): _format_district_label(int(code))
                for code in selected_district_codes
            }
            district_labels = [
                _format_district_label(int(code))
                for code in selected_district_codes
            ]
            st.sidebar.success(
                f"Selected {len(manual_district_codes)} subdivision(s): {', '.join(district_labels)}"
            )
        elif not available_district_codes:
            st.sidebar.warning("No GEODVCSD values found in the loaded dataset.")

    combined_district_codes = {}
    if configured_group_codes:
        combined_district_codes.update(configured_group_codes)
    if municipality_codes:
        combined_district_codes.update(municipality_codes)
    if manual_district_codes:
        combined_district_codes.update(manual_district_codes)

    # Show preview of record count if data is provided
    if data is not None and (combined_district_codes or selected_health_regions):
        from src.data.processor import apply_region_filter
        try:
            preview_data = apply_region_filter(
                data,
                district_codes=combined_district_codes or None,
                health_region_codes=selected_health_regions or None
            )
            record_count = len(preview_data)
            original_count = len(data)
            pct = (record_count / original_count * 100) if original_count > 0 else 0
            
            if record_count < 100:
                st.sidebar.warning(f"Preview: {record_count:,} records ({pct:.1f}%) - Small sample size!")
            else:
                st.sidebar.info(f"Preview: {record_count:,} records ({pct:.1f}%)")
        except Exception:
            pass

    return {
        "district_codes": combined_district_codes or None,
        "health_region_codes": selected_health_regions or None,
    }


def _get_available_health_region_codes(data):
    """Get sorted health region codes available in the currently loaded dataset."""
    if data is None or 'GEODVHR4' not in data.columns:
        return []

    unique_codes = (
        data['GEODVHR4']
        .dropna()
        .map(lambda value: int(float(value)))
        .unique()
        .tolist()
    )
    return sorted(unique_codes)


def _get_available_district_codes(data):
    """Get sorted district codes available in the currently loaded dataset."""
    if data is None or 'GEODVCSD' not in data.columns:
        return []

    unique_codes = (
        data['GEODVCSD']
        .dropna()
        .map(lambda value: int(float(value)))
        .unique()
        .tolist()
    )
    return sorted(unique_codes)


def _get_available_official_municipality_codes(data):
    """Get sorted official municipality CSD codes available in the current dataset."""
    official_municipalities = load_ontario_official_municipalities()
    if not official_municipalities:
        return []

    if data is None or 'GEODVCSD' not in data.columns:
        return sorted(int(code) for code in official_municipalities.keys())

    available_codes = set(_get_available_district_codes(data))
    official_codes = {int(code) for code in official_municipalities.keys()}
    return sorted(available_codes & official_codes)


def _get_health_region_label(code):
    """Resolve a user-facing label for a health region code."""
    if code in KNOWN_HEALTH_REGION_LABELS:
        return KNOWN_HEALTH_REGION_LABELS[code]

    for phu_config in PUBLIC_HEALTH_UNITS.values():
        if code in phu_config.get("health_region_codes", []):
            return phu_config["label"]

    return f"Health Region {code}"


def _format_district_label(code):
    """Resolve a user-facing label for a district code."""
    district_lookup = load_ontario_csd_lookup()
    district_record = district_lookup.get(str(code))
    if district_record:
        return district_record.get("label", f"{district_record.get('name', 'District')} ({code})")
    if code in KNOWN_DISTRICT_LABELS:
        return f"{KNOWN_DISTRICT_LABELS[code]} ({code})"
    return f"District {code}"


def _format_official_municipality_label(code):
    """Resolve a user-facing label for an official Ontario municipality."""
    official_lookup = load_ontario_official_municipalities()
    record = official_lookup.get(str(code))
    if record:
        return record.get("label", f"{record.get('official_name', 'Municipality')} ({code})")
    return _format_district_label(code)


def _filter_district_codes_by_health_regions(data, district_codes, selected_health_regions):
    """Limit district options to those observed within the selected health regions."""
    if (
        data is None
        or 'GEODVCSD' not in data.columns
        or 'GEODVHR4' not in data.columns
        or not district_codes
        or not selected_health_regions
    ):
        return district_codes

    normalized_health_regions = data['GEODVHR4'].map(
        lambda value: int(float(value)) if value == value else None
    )
    region_filtered = data.loc[
        normalized_health_regions.isin({int(code) for code in selected_health_regions}),
        'GEODVCSD'
    ]
    available_codes = sorted(region_filtered.dropna().map(lambda value: int(float(value))).unique().tolist())
    return [code for code in district_codes if code in set(available_codes)]


def _get_municipality_group_options(selected_health_regions):
    """Get configured municipality groups, optionally scoped to selected PHUs."""
    if not selected_health_regions:
        municipality_options = {}
        for phu_config in PUBLIC_HEALTH_UNITS.values():
            municipality_options.update(phu_config.get("municipality_groups", {}))
        return municipality_options or MUNICIPALITY_OPTIONS

    selected_region_codes = set(selected_health_regions)
    municipality_options = {}
    for phu_config in PUBLIC_HEALTH_UNITS.values():
        region_codes = set(phu_config.get("health_region_codes", []))
        if selected_region_codes & region_codes:
            municipality_options.update(phu_config.get("municipality_groups", {}))

    return municipality_options


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

            flag_labels = {}
            for flag, desc in sorted_flags:
                short_desc = desc.replace(" - Inclusion Flag - (F)", "").strip()
                flag_labels[flag] = short_desc if short_desc else flag

            selected_flag_names = st.sidebar.multiselect(
                "Inclusion Flags",
                options=[flag for flag, _ in sorted_flags],
                default=[],
                format_func=lambda flag: f"{flag}: {flag_labels[flag]}",
                help="Choose one or more inclusion flags to restrict the dataset.",
                key="selected_inclusion_flag_names",
                placeholder="Select inclusion flags...",
            )

            selected_flags = {
                flag: flag in selected_flag_names
                for flag, _ in sorted_flags
            }

            if selected_flag_names:
                st.sidebar.caption(
                    f"Selected {len(selected_flag_names)} flag(s): {', '.join(selected_flag_names)}"
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
