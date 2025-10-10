"""CSS styles for the CCHS analysis application."""

CSS_STYLES = """
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
"""