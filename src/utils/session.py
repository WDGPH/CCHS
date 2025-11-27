"""Session state management functions for the CCHS application."""

import streamlit as st


def initialize_session_state():
    """Initialize all session state variables."""
    if 'filtered_data' not in st.session_state:
        st.session_state['filtered_data'] = None
    if 'merged_data' not in st.session_state:
        st.session_state['merged_data'] = None
    if 'combined_results' not in st.session_state:
        st.session_state['combined_results'] = None
    if 'selected_variables' not in st.session_state:
        st.session_state['selected_variables'] = []


def get_session_state(key, default=None):
    """Get a value from session state with a default."""
    return st.session_state.get(key, default)


def set_session_state(key, value):
    """Set a value in session state."""
    st.session_state[key] = value


def clear_session_state():
    """Clear all session state variables."""
    for key in ['filtered_data', 'merged_data', 'combined_results', 'selected_variables']:
        if key in st.session_state:
            del st.session_state[key]