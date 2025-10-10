"""Results display functions for the CCHS application."""

import streamlit as st
import pandas as pd
from src.ui.components import create_enhanced_chart


def display_results(result_df, variable, use_labels=False):
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
    fig = create_enhanced_chart(result_df, variable, x_labels)
    st.pyplot(fig)
    st.markdown("</div>", unsafe_allow_html=True)


def display_crosstab_report(combined_df):
    """
    Display a crosstab (pivot) report of prevalence by variable and value.
    Allows the user to recode (rename) both variable (row) names and column names for display in the crosstab.
    """
    st.write("### Combined Crosstab Report (Prevalence)")
    
    # Always use Label if available for columns
    col_field = 'Label' if 'Label' in combined_df.columns else 'Value'
    
    # Build the pivot table with index=Variable and columns=Value/Label
    prevalence_crosstab = pd.pivot_table(
        combined_df,
        index='Variable',
        columns=col_field,
        values='Prevalence'
    )
    # Weighted population crosstab
    weighted_pop_crosstab = pd.pivot_table(
        combined_df,
        index='Variable',
        columns=col_field,
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