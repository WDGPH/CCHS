import os
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Set page configuration with custom theme
st.set_page_config(
    page_title="Canadian Community Health Survey (CCHS) Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add CSS styling
st.markdown("""
<style>
    :root {
        --primary: #005568;
        --secondary: #00928F;
        --accent: #78A22F;
        --background: #FFFFFF;
        --background-alt: #F8FAFC;
        --light-bg: #F1F5F9;
        --text: #1A202C;
        --text-light: #4A5568;
        --border: #E2E8F0;
        --shadow: rgba(0, 85, 104, 0.1);
        --gradient-primary: linear-gradient(135deg, #005568 0%, #00928F 100%);
        --gradient-secondary: linear-gradient(135deg, #00928F 0%, #78A22F 100%);
        --gradient-accent: linear-gradient(135deg, #78A22F 0%, #8fb944 100%);
    }
    
    .content-card {
        background: white;
        padding: 2rem;
        border-radius: 16px;
        margin: 1.5rem 0;
        box-shadow: 0 4px 20px var(--shadow);
        border: 1px solid var(--border);
    }
    
    .sidebar-card {
        background: var(--background-alt);
        padding: 1rem;
        border-radius: 12px;
        margin: 1rem 0;
        border-left: 4px solid var(--primary);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 2px 12px var(--shadow);
        border: 1px solid var(--border);
        margin: 0.5rem 0;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary);
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: var(--text-light);
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stSelectbox > div > div {
        background-color: white;
        border: 2px solid var(--border);
        border-radius: 8px;
    }
    
    .stMultiSelect > div > div {
        background-color: white;
        border: 2px solid var(--border);
        border-radius: 8px;
    }
    
    .stButton > button {
        background: var(--gradient-primary);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px var(--shadow);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'filtered_data' not in st.session_state:
    st.session_state['filtered_data'] = None
if 'merged_data' not in st.session_state:
    st.session_state['merged_data'] = None
if 'combined_results' not in st.session_state:
    st.session_state['combined_results'] = None
if 'selected_variables' not in st.session_state:
    st.session_state['selected_variables'] = []

# 1. Caching data load for better performance
@st.cache_data
def load_data():
    """
    Load the main data and bootstrap data from parquet files.
    Adjust file names/paths as needed.
    """
    data_file = "data/hs2021_on_distr.parquet"
    bootstrap_file = "data/hs2021_on_bootwt.parquet"
    if os.path.exists(data_file) and os.path.exists(bootstrap_file):
        data = pd.read_parquet(data_file)
        bootstrap_data = pd.read_parquet(bootstrap_file)
        return data, bootstrap_data
    else:
        st.error("One or both of the required parquet files are missing.")
        return None, None

# Add this function to load the variable descriptions
@st.cache_data
def load_variable_descriptions():
    """
    Load the variable descriptions from the CCHS_2021_Recoded_Variables.csv file.
    """
    try:
        desc_file = "data/CCHS_2021_Recoded_Variables.csv"
        if os.path.exists(desc_file):
            descriptions = pd.read_csv(desc_file)
            # Create a dictionary for quick lookup
            desc_dict = dict(zip(descriptions['Variable'], descriptions['Description']))
            return descriptions, desc_dict
        else:
            return None, {}
    except Exception as e:
        st.error(f"Error loading variable descriptions: {e}")
        return None, {}

# 2. Merging filtered data with bootstrap weights
@st.cache_data
def merge_data(filtered_data, bootstrap_data):
    """
    Merge filtered data with bootstrap weights on 'ONT_ID'.
    """
    merged = pd.merge(filtered_data, bootstrap_data, on='ONT_ID', how='left')
    return merged

# 3. Creating age groups
def create_age_groups(df, age_col):
    # Check if the age column exists
    if age_col not in df.columns:
        print(f"Warning: Column '{age_col}' not found. Skipping age group creation.")
        df['AgeGroup'] = None  # Optionally, add a placeholder column
        return df

    # Define age bins and labels
    bins = [0, 18, 25, 45, 65, 120]
    labels = ['0-17', '18-24', '25-44', '45-64', '65+']

    # Create age groups
    df['AgeGroup'] = pd.cut(df[age_col], bins=bins, labels=labels, right=False)
    return df

# 4. Applying region filters
def apply_region_filter(data, filter_by_district, filter_by_health_region, district_codes, health_region_code):
    """
    Dynamically apply region filters based on user selection.
    """
    # Apply municipality or district filter if district_codes is set
    if district_codes:
        filtered = data[data['GEODVCSD'].astype(int).isin([int(k) for k in district_codes.keys()])]
        st.write(f"Filtering by GEODVCSD codes: {list(district_codes.values())}")
    elif filter_by_health_region and health_region_code:
        filtered = data[data['GEODVHR4'] == health_region_code]
        st.write(f"Filtering by health region-level GEODVHR4 code: {health_region_code}")
    else:
        filtered = data
        st.write("No region filter applied; using the entire dataset.")
    return filtered

# 5. Running the bootstrap analysis
def run_bootstrap_analysis_for_all_values(merged_data, variable_col, weight_col):
    """
    Perform bootstrap analysis using vectorized groupby operations.
    Computes weighted prevalences and bootstrap variances.
    """
    # Identify bootstrap weight columns (those starting with 'BSW')
    bootstrap_cols = [col for col in merged_data.columns if col.startswith('BSW')]
    
    # Precompute total weights for base and bootstrap replicates
    total_weight_base = merged_data[weight_col].sum()
    total_weights_boot = {col: merged_data[col].sum() for col in bootstrap_cols}
    
    # Compute weighted sums for the base weight grouped by the selected variable
    base_numerators = merged_data.groupby(variable_col)[weight_col].sum()
    base_prevalence = (base_numerators / total_weight_base) * 100

    # Weighted population for each group (sum of weights)
    weighted_population = base_numerators

    # OPTIMIZED: Compute all bootstrap replicates at once using vectorized operations
    # Group by variable and sum all bootstrap columns simultaneously
    bootstrap_sums = merged_data.groupby(variable_col)[bootstrap_cols].sum()
    
    # Convert total weights to Series for vectorized division
    total_weights_series = pd.Series(total_weights_boot, name='total_weights')
    
    # Vectorized calculation: divide each bootstrap sum by its corresponding total weight
    replicate_prevalence_df = bootstrap_sums.div(total_weights_series, axis=1) * 100

    # Compute variance, standard deviation, confidence intervals, etc.
    variance = ((replicate_prevalence_df.sub(base_prevalence, axis=0))**2).mean(axis=1)
    std_dev = np.sqrt(variance)
    ci_lower = base_prevalence - 1.96 * std_dev
    ci_upper = base_prevalence + 1.96 * std_dev
    cv = (std_dev / base_prevalence) * 100

    result_df = pd.DataFrame({
        'Value': base_prevalence.index,
        'Prevalence': base_prevalence.values,
        'Weighted Population': weighted_population.values,
        'Variance': variance.values,
        'Standard Deviation': std_dev.values,
        'CI Lower': ci_lower.values,
        'CI Upper': ci_upper.values,
        'CV (%)': cv.values,
        'Error': 1.96 * std_dev.values  # for error bars in plots
    }).reset_index(drop=True)
    
    return result_df

# 6. Enhanced displaying individual variable analysis results
def display_results(result_df, variable):
    """
    Display the analysis results as a modern styled table and enhanced chart.
    """
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
                    Variable: <span style="color: var(--secondary); font-weight: 600;">{variable}</span>
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Enhanced dataframe styling with modern color scheme
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
    
    st.pyplot(fig)
    st.markdown("</div>", unsafe_allow_html=True)

# 7. Displaying a combined crosstab report, with optional variable recoding
def display_crosstab_report(combined_df):
    """
    Display a crosstab (pivot) report of prevalence by variable and value.
    Allows the user to recode (rename) both variable (row) names and column names for display in the crosstab.
    """
    st.write("### Combined Crosstab Report (Prevalence)")
    
    # Build the pivot table with index=Variable and columns=Value
    prevalence_crosstab = pd.pivot_table(
        combined_df,
        index='Variable',
        columns='Value',
        values='Prevalence'
    )
    # Weighted population crosstab
    weighted_pop_crosstab = pd.pivot_table(
        combined_df,
        index='Variable',
        columns='Value',
        values='Weighted Population'
    )
    
    show_weighted_pop = st.checkbox("Show weighted population in crosstab")
    if show_weighted_pop:
        st.write("#### Weighted Population Crosstab")
        st.dataframe(weighted_pop_crosstab)
    
    # Let the user recode variable names (rows) for the crosstab display
    if st.checkbox("Recode variable names for crosstab display"):
        variables_in_crosstab = list(prevalence_crosstab.index)
        st.write("Enter display names for each variable (row) below:")
        rename_dict = {}
        for var in variables_in_crosstab:
            new_name = st.text_input(f"Display name for '{var}'", value=var, key=f"rename_{var}")
            rename_dict[var] = new_name
        
        recoded_crosstab = prevalence_crosstab.rename(index=rename_dict)
        
        # Extra feature: recode column names if desired
        if st.checkbox("Recode column names for crosstab display"):
            columns_in_crosstab = list(recoded_crosstab.columns)
            st.write("Enter display names for each column below:")
            rename_columns_dict = {}
            for col in columns_in_crosstab:
                new_name = st.text_input(f"Display name for column '{col}'", value=col, key=f"rename_col_{col}")
                rename_columns_dict[col] = new_name
            recoded_crosstab = recoded_crosstab.rename(columns=rename_columns_dict)
        
        st.write("#### Recoded Crosstab")
        st.dataframe(recoded_crosstab)
        
        # Optionally, allow the user to download the recoded crosstab as CSV
        if st.button("Download Recoded Crosstab as CSV"):
            csv_data = recoded_crosstab.to_csv().encode('utf-8')
            st.download_button(
                label="Click to Download",
                data=csv_data,
                file_name="recoded_crosstab.csv",
                mime="text/csv"
            )
    else:
        # If not recoding, just display the original pivot table
        st.dataframe(prevalence_crosstab)

# 8. Main Streamlit application
def main():
    # Add main title
    st.title("Canadian Community Health Survey (CCHS) Analysis")
    
    # A. Load data
    data, bootstrap_data = load_data()
    if data is None or bootstrap_data is None:
        st.stop()
        
    # Load variable descriptions
    desc_df, desc_dict = load_variable_descriptions()
    
    # Enhanced sidebar variable search with modern design
    st.sidebar.markdown("""
    <div class="sidebar-card">
        <h3 style="margin: 0 0 1rem 0; color: var(--primary); display: flex; align-items: center;">
            🔍 <span style="margin-left: 0.5rem;">CCHS Variable Search</span>
        </h3>
    </div>
    """, unsafe_allow_html=True)
    
    if desc_df is not None:
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
        
        if st.session_state['selected_variables']:
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
    
    # Define region codes (adjust as needed)
    wellington_codes = {
        3523017: 'Erin',
        3523043: 'Minto',
        3523025: 'Centre Wellington',
        3523009: 'Duelph Eramosa',
        3523033: 'Mapleton',
        3523050: 'Wellington North',
        3523001: 'Puslinch'
    }
    guelph_codes = {3523008: 'Guelph'}
    dufferin_codes = {
        3522014: 'Orangeville',
        3522021: 'Shelburne',
        3522008: 'Amaranth',
        3522001: 'East Garafraxa',
        3522010: 'Grand Valley'
    }
    health_region_code = 3566  # example code
    
    # Enhanced sidebar data filtering with modern design
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
    municipality = None
    if filter_by_municipality_dropdown:
        st.sidebar.markdown("""
        <div style="background: var(--light-bg); padding: 0.75rem; border-radius: 8px; 
                   margin: 0.5rem 0; border-left: 3px solid var(--accent);">
            <strong style="color: var(--primary);">Select Municipality</strong>
        </div>
        """, unsafe_allow_html=True)
        
        municipality_options = {
            "Wellington": wellington_codes,
            "Guelph": guelph_codes,
            "Dufferin": dufferin_codes
        }
        selected_municipalities = st.sidebar.multiselect(
            "Choose area(s) of interest:",
            options=list(municipality_options.keys()),
            help="Select one or more municipalities for analysis"
        )
        
        # Combine selected codes
        district_codes = {}
        for m in selected_municipalities:
            district_codes.update(municipality_options[m])
        
        if selected_municipalities:
            st.sidebar.success(
                f"✅ Selected: {', '.join(selected_municipalities)} "
                f"({len(district_codes)} areas)"
            )

    filter_by_health_region = st.sidebar.checkbox(
        "🏥 Health region-level GEODVHR4",
        help="Filter by health region boundaries"
    )
    
    # Enhanced apply filters section
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
    
    # C. Step 1: Enhanced Apply Filters button
    apply_filters = st.sidebar.button(
        "🎯 Apply Geographic Filters", 
        type="primary",
        help="Apply all selected geographic filters to the dataset",
        use_container_width=True
    )
    
    if apply_filters:
        with st.sidebar:
            with st.spinner('🔄 Applying filters...'):
                filtered_data = apply_region_filter(
                    data,
                    filter_by_district,
                    filter_by_health_region,
                    district_codes,
                    health_region_code
                )
                filtered_data = create_age_groups(filtered_data, 'DHH_AGE')
                st.session_state['filtered_data'] = filtered_data
                st.success("✅ Filters applied successfully!")
                
        # Show filter summary
        if any([filter_by_district, filter_by_municipality_dropdown, filter_by_health_region]):
            st.sidebar.markdown("""
            <div style="background: var(--light-bg); padding: 0.75rem; border-radius: 8px; 
                       margin-top: 0.5rem; border-left: 3px solid var(--secondary);">
                <strong style="color: var(--primary);">Active Filters:</strong><br>
            """, unsafe_allow_html=True)
            
            if filter_by_district:
                st.sidebar.markdown("• District-level filtering")
            if filter_by_municipality_dropdown and municipality:
                st.sidebar.markdown(f"• Municipality: {municipality}")
            if filter_by_health_region:
                st.sidebar.markdown("• Health region filtering")
                
            st.sidebar.markdown("</div>", unsafe_allow_html=True)
    
    # Display a preview of filtered data with enhanced styling
    if st.session_state['filtered_data'] is not None:
        st.markdown("---")
        
        # Enhanced data preview section
        st.markdown("""
        <div class="content-card">
            <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
                <div style="width: 4px; height: 40px; background: var(--gradient-accent); 
                            border-radius: 2px; margin-right: 1rem;"></div>
                <div>
                    <h3 style="margin: 0; color: var(--primary); font-size: 1.4rem; font-weight: 600;">
                        📊 Filtered Data Preview
                    </h3>
                    <p style="margin: 4px 0 0 0; color: var(--text-light); font-weight: 500;">
                        Review your filtered dataset before analysis
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Data metrics row
        data_preview = st.session_state['filtered_data']
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(data_preview):,}</div>
                <div class="metric-label">Total Records</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{len(data_preview.columns)}</div>
                <div class="metric-label">Variables</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{data_preview.memory_usage(deep=True).sum() / 1024**2:.1f}</div>
                <div class="metric-label">MB Memory</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{data_preview.isnull().sum().sum():,}</div>
                <div class="metric-label">Missing Values</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Weighted population metric card
        with col5:
            weight_col = 'WTS_S' if 'WTS_S' in data_preview.columns else data_preview.columns[0]
            weighted_pop = data_preview[weight_col].sum() if weight_col in data_preview.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{weighted_pop:,.0f}</div>
                <div class="metric-label">Weighted Population</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Enhanced dataframe display
        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(
            st.session_state['filtered_data'].head(10), 
            use_container_width=True,
            height=350
        )
        st.markdown("</div>", unsafe_allow_html=True)
        
        # D. Step 2: Enhanced Merge Data section
        st.markdown("---")
        st.markdown("""
        <div class="content-card">
            <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
                <div style="width: 4px; height: 40px; background: var(--gradient-secondary); 
                            border-radius: 2px; margin-right: 1rem;"></div>
                <div>
                    <h3 style="margin: 0; color: var(--primary); font-size: 1.4rem; font-weight: 600;">
                        🔗 Data Merging
                    </h3>
                    <p style="margin: 4px 0 0 0; color: var(--text-light); font-weight: 500;">
                        Combine filtered data with bootstrap weights for statistical analysis
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Merge Data with Bootstrap Weights", type="primary", key="merge_button"):
                with st.spinner('🔄 Merging data...'):
                    merged_data = merge_data(st.session_state['filtered_data'], bootstrap_data)
                    st.session_state['merged_data'] = merged_data
                    st.success("✅ Data merged successfully!")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # E. Step 3: Enhanced Configure and run bootstrap analysis section
    if st.session_state['merged_data'] is not None:
        st.markdown("---")
        st.markdown("""
        <div class="content-card">
            <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
                <div style="width: 4px; height: 40px; background: var(--gradient-primary); 
                            border-radius: 2px; margin-right: 1rem;"></div>
                <div>
                    <h3 style="margin: 0; color: var(--primary); font-size: 1.4rem; font-weight: 600;">
                        ⚙️ Analysis Configuration
                    </h3>
                    <p style="margin: 4px 0 0 0; color: var(--text-light); font-weight: 500;">
                        Configure bootstrap analysis parameters and select variables
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        merged_data = st.session_state['merged_data']
        
        # Enhanced variable selection with better UI
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Enhanced variable selection with descriptions
            variable_options = list(merged_data.columns)
            variable_labels = {}
            for var in variable_options:
                if var in desc_dict:
                    variable_labels[var] = f"{var}: {desc_dict[var]}"
                else:
                    variable_labels[var] = var
            
            st.markdown("**📋 Variable Selection**")
            selected_variables = st.multiselect(
                "Choose variables for bootstrap analysis:",
                options=variable_options,
                format_func=lambda x: variable_labels.get(x, x),
                help="Select one or more variables to analyze. Descriptions are shown when available.",
                key="variable_selector"
            )
            
            # Update session state
            st.session_state['selected_variables'] = selected_variables
            
            if selected_variables:
                st.markdown(f"✅ **{len(selected_variables)} variable(s) selected**")
                with st.expander("📖 View Selected Variables", expanded=False):
                    for var in selected_variables:
                        desc = desc_dict.get(var, "No description available")
                        st.markdown(f"• **{var}**: {desc}")
        
        with col2:
            st.markdown("**⚖️ Weight Configuration**")
            weight_col = st.selectbox(
                "Bootstrap weight column:",
                merged_data.columns,
                index=merged_data.columns.get_loc("WTS_S") if "WTS_S" in merged_data.columns else 0,
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
                    <strong>Dataset:</strong> {len(merged_data):,} records<br>
                    <strong>Method:</strong> Bootstrap Analysis<br>
                    <strong>Confidence:</strong> 95% CI
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        # Enhanced Run Analysis section
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Center the run button with enhanced styling
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            run_analysis = st.button(
                "🚀 Run Bootstrap Analysis", 
                type="primary",
                disabled=len(selected_variables) == 0,
                help="Start the bootstrap analysis for selected variables" if selected_variables 
                     else "Please select at least one variable to analyze",
                key="run_analysis_button"
            )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Run the analysis with enhanced progress display
        if run_analysis and selected_variables:
            st.markdown("---")
            st.markdown("""
            <div class="content-card">
                <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
                    <div style="width: 4px; height: 40px; background: var(--gradient-accent); 
                                border-radius: 2px; margin-right: 1rem;"></div>
                    <div>
                        <h3 style="margin: 0; color: var(--primary); font-size: 1.4rem; font-weight: 600;">
                            🔬 Analysis in Progress
                        </h3>
                        <p style="margin: 4px 0 0 0; color: var(--text-light); font-weight: 500;">
                            Running bootstrap analysis for selected variables
                        </p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            combined_results = []
            
            # Enhanced progress tracking
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Analysis metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    current_var = st.empty()
                with col2:
                    time_elapsed = st.empty()
                with col3:
                    eta = st.empty()
            
            import time
            start_time = time.time()
            
            for i, variable in enumerate(selected_variables):
                progress = (i + 1) / len(selected_variables)
                progress_bar.progress(progress)
                
                elapsed = time.time() - start_time
                estimated_total = elapsed / progress if progress > 0 else 0
                remaining = max(0, estimated_total - elapsed)
                
                status_text.markdown(f"""
                <div style="background: var(--background-alt); padding: 1rem; border-radius: 8px; 
                           text-align: center; margin: 1rem 0;">
                    <strong>Processing Variable {i+1} of {len(selected_variables)}</strong><br>
                    <span style="color: var(--secondary); font-weight: 600;">{variable}</span>
                </div>
                """, unsafe_allow_html=True)
                
                current_var.metric("Current Variable", f"{i+1}/{len(selected_variables)}")
                time_elapsed.metric("Time Elapsed", f"{elapsed:.1f}s")
                eta.metric("ETA", f"{remaining:.1f}s" if remaining > 0 else "Almost done!")
                
                with st.spinner(f"Analyzing {variable}..."):
                    result_df = run_bootstrap_analysis_for_all_values(merged_data, variable, weight_col)
                result_df['Variable'] = variable
                combined_results.append(result_df)
                
                # Display results for each variable with enhanced styling
                display_results(result_df, variable)
            
            # Complete the progress display
            progress_bar.progress(1.0)
            status_text.success("✅ Analysis completed successfully!")
            time.sleep(1)  # Brief pause to show completion
            progress_container.empty()
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            if combined_results:
                combined_df = pd.concat(combined_results, ignore_index=True)
                st.session_state['combined_results'] = combined_df
                st.success("All analyses completed successfully!")
    
    # F. Step 4: Enhanced Analysis Results Display
    if st.session_state['combined_results'] is not None:
        st.markdown("---")
        
        # Enhanced results header
        st.markdown("""
        <div class="content-card">
            <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
                <div style="width: 4px; height: 40px; background: var(--gradient-primary); 
                            border-radius: 2px; margin-right: 1rem;"></div>
                <div style="flex: 1;">
                    <h2 style="margin: 0; color: var(--primary); font-size: 1.8rem; font-weight: 700;">
                        📈 Analysis Results Dashboard
                    </h2>
                    <p style="margin: 4px 0 0 0; color: var(--text-light); font-weight: 500;">
                        Comprehensive bootstrap analysis results with interactive visualizations
                    </p>
                </div>
                <div style="background: var(--gradient-accent); color: white; padding: 8px 16px; 
                           border-radius: 20px; font-weight: 600; font-size: 0.9rem;">
                    ✅ Analysis Complete
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Enhanced tabs with icons and descriptions
        tab1, tab2, tab3 = st.tabs([
            "📊 Crosstab Report", 
            "👥 Age Group Analysis", 
            "💾 Data Export"
        ])
        
        with tab1:
            st.markdown("""
            <div style="background: var(--background-alt); padding: 1.5rem; border-radius: 12px; 
                        margin-bottom: 1.5rem; border-left: 4px solid var(--primary);">
                <h4 style="margin: 0 0 0.5rem 0; color: var(--primary);">
                    📋 Cross-Tabulation Summary
                </h4>
                <p style="margin: 0; color: var(--text-light); font-size: 0.9rem;">
                    Interactive pivot table showing prevalence rates across all analyzed variables and values.
                </p>
            </div>
            """, unsafe_allow_html=True)
            display_crosstab_report(st.session_state['combined_results'])
        
        with tab2:
            st.markdown("""
            <div style="background: var(--background-alt); padding: 1.5rem; border-radius: 12px; 
                        margin-bottom: 1.5rem; border-left: 4px solid var(--secondary);">
                <h4 style="margin: 0 0 0.5rem 0; color: var(--primary);">
                    👥 Age-Stratified Analysis
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
            
            if age_analysis_enabled:
                age_group_results = []
                
                if st.session_state['merged_data'] is not None and len(st.session_state['selected_variables']) > 0:
                    main_var = st.session_state['selected_variables'][0]
                    
                    # Enhanced progress tracking for age group analysis
                    with st.container():
                        st.info(f"🔄 Analyzing variable '{main_var}' across different age groups...")
                        age_progress = st.progress(0)
                        age_status = st.empty()
                        
                        age_groups = list(st.session_state['merged_data']['AgeGroup'].dropna().unique())
                        
                        for i, age_group in enumerate(age_groups):
                            group_data = st.session_state['merged_data'][
                                st.session_state['merged_data']['AgeGroup'] == age_group
                            ]
                            
                            if not group_data.empty:
                                progress = (i + 1) / len(age_groups)
                                age_progress.progress(progress)
                                age_status.text(f"Processing age group {i+1}/{len(age_groups)}: {age_group}")
                                
                                with st.spinner(f"Analyzing age group: {age_group}..."):
                                    result_df = run_bootstrap_analysis_for_all_values(group_data, main_var, weight_col)
                                result_df['AgeGroup'] = age_group
                                age_group_results.append(result_df)
                        
                        age_progress.empty()
                        age_status.empty()
                    
                    if age_group_results:
                        age_group_df = pd.concat(age_group_results, ignore_index=True)
                        
                        # Enhanced age group results display
                        st.markdown("""
                        <div style="background: white; padding: 1.5rem; border-radius: 12px; 
                                    margin: 1rem 0; box-shadow: 0 4px 20px var(--shadow); 
                                    border-left: 4px solid var(--accent);">
                            <h4 style="margin: 0 0 1rem 0; color: var(--primary);">
                                📊 Age Group Cross-Tabulation Results
                            </h4>
                        """, unsafe_allow_html=True)
                        
                        age_crosstab = pd.pivot_table(
                            age_group_df,
                            index='AgeGroup',
                            columns='Value',
                            values='Prevalence'
                        )
                        
                        # Enhanced styling for age group results
                        styled_age_crosstab = age_crosstab.style.format('{:.2f}%').background_gradient(
                            cmap='RdYlBu_r', axis=None
                        )
                        
                        st.dataframe(styled_age_crosstab, use_container_width=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style="background: var(--background-alt); padding: 2rem; border-radius: 12px; 
                                    text-align: center; border: 2px dashed var(--border);">
                            <h4 style="color: var(--text-light); margin: 0;">📭 No Age Group Data Available</h4>
                            <p style="color: var(--text-light); margin: 0.5rem 0 0 0;">
                                Age group analysis requires data with valid age groupings.
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("⚠️ Please select at least one variable for age-group analysis.")
        
        with tab3:
            st.markdown("""
            <div style="background: var(--background-alt); padding: 1.5rem; border-radius: 12px; 
                        margin-bottom: 1.5rem; border-left: 4px solid var(--accent);">
                <h4 style="margin: 0 0 0.5rem 0; color: var(--primary);">
                    💾 Export Analysis Results
                </h4>
                <p style="margin: 0; color: var(--text-light); font-size: 0.9rem;">
                    Download your complete analysis results in various formats for further use.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Enhanced download section with multiple format options
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📄 CSV Export**")
                csv = st.session_state['combined_results'].to_csv().encode('utf-8')
                st.download_button(
                    label="📥 Download Full Results (CSV)",
                    data=csv,
                    file_name="cchs_analysis_results.csv",
                    mime="text/csv",
                    help="Download the complete analysis results as a CSV file",
                    use_container_width=True
                )
                
                # Summary statistics
                results_df = st.session_state['combined_results']
                st.markdown(f"""
                <div style="background: white; padding: 1rem; border-radius: 8px; 
                           margin-top: 1rem; border-left: 3px solid var(--primary);">
                    <h5 style="margin: 0 0 0.5rem 0; color: var(--primary);">📊 Export Summary</h5>
                    <ul style="margin: 0; padding-left: 1.2rem; color: var (--text-light);">
                        <li><strong>{len(results_df):,}</strong> analysis records</li>
                        <li><strong>{results_df['Variable'].nunique()}</strong> unique variables</li>
                        <li><strong>{results_df['Value'].nunique()}</strong> unique values</li>
                        <li>File size: <strong>~{len(csv)/1024:.1f} KB</strong></li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("**📊 Excel Export**")
                # Create Excel file in memory
                from io import BytesIO
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    st.session_state['combined_results'].to_excel(
                        writer, sheet_name='Analysis Results', index=False
                    )
                
                excel_data = excel_buffer.getvalue()
                
                st.download_button(
                    label="📊 Download Results (Excel)",
                    data=excel_data,
                    file_name="cchs_analysis_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Download results as an Excel file with multiple sheets",
                    use_container_width=True
                )
                
                # Additional export info
                st.markdown(f"""
                <div style="background: white; padding: 1rem; border-radius: 8px; 
                           margin-top: 1rem; border-left: 3px solid var(--secondary);">
                    <h5 style="margin: 0 0 0.5rem 0; color: var(--secondary);">📋 Excel Features</h5>
                    <ul style="margin: 0; padding-left: 1.2rem; color: var(--text-light);">
                        <li>Multiple worksheets</li>
                        <li>Formatted tables</li>
                        <li>Ready for pivot analysis</li>
                        <li>Compatible with all Excel versions</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    

# Run the Streamlit app
if __name__ == "__main__":
    main()
