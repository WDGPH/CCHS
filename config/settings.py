"""Configuration settings for the CCHS analysis application."""

# Page configuration
PAGE_CONFIG = {
    "page_title": "Canadian Community Health Survey (CCHS) Analysis",
    "page_icon": "https://wdgpublichealth.ca/sites/all/themes/de_theme/logo.png",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Available cycles
AVAILABLE_CYCLES = ["2021", "2022", "2023"]
DEFAULT_CYCLE = "2023"

# File paths
DATA_PATH = "data"
HARMONIZATION_PATH = "harmonization"
PRECOMPUTED_PATH = "data/precomputed"  # Path for precomputed harmonized data

# Precomputing settings
ENABLE_PRECOMPUTING = True  # Enable use of precomputed data when available

# Geographic codes
WELLINGTON_CODES = {
    3523017: 'Erin',
    3523043: 'Minto',
    3523025: 'Centre Wellington',
    3523009: 'Duelph Eramosa',
    3523033: 'Mapleton',
    3523050: 'Wellington North',
    3523001: 'Puslinch'
}

GUELPH_CODES = {3523008: 'Guelph'}

DUFFERIN_CODES = {
    3522014: 'Orangeville',
    3522021: 'Shelburne',
    3522008: 'Amaranth',
    3522001: 'East Garafraxa',
    3522010: 'Grand Valley'
}

MUNICIPALITY_OPTIONS = {
    "Wellington": WELLINGTON_CODES,
    "Guelph": GUELPH_CODES,
    "Dufferin": DUFFERIN_CODES
}

HEALTH_REGION_CODE = 3566

# Analysis settings
DEFAULT_WEIGHT_COLUMN = "WTS_S"
CONFIDENCE_LEVEL = 0.95
BOOTSTRAP_PREFIX = "BSW"

# Age group settings
# Default age group configurations (can be customized by user)
DEFAULT_AGE_BINS = [0, 15, 25, 45, 65, 120]
DEFAULT_AGE_LABELS = ['0-14', '15-24', '25-44', '45-64', '65+']

# Preset age group options
AGE_GROUP_PRESETS = {
    "Standard (5 groups)": {
        "bins": [0, 15, 25, 45, 65, 120],
        "labels": ['0-14', '15-24', '25-44', '45-64', '65+']
    },
    "Detailed (7 groups)": {
        "bins": [0, 18, 25, 35, 45, 55, 65, 120],
        "labels": ['0-17', '18-24', '25-34', '35-44', '45-54', '55-64', '65+']
    },
    "Youth Focus (6 groups)": {
        "bins": [0, 12, 18, 25, 35, 65, 120],
        "labels": ['0-11', '12-17', '18-24', '25-34', '35-64', '65+']
    },
    "Senior Focus (6 groups)": {
        "bins": [0, 45, 55, 65, 75, 85, 120],
        "labels": ['0-44', '45-54', '55-64', '65-74', '75-84', '85+']
    },
    "Simple (3 groups)": {
        "bins": [0, 18, 65, 120],
        "labels": ['0-17', '18-64', '65+']
    },
    "Custom": {
        "bins": None,  # User will define
        "labels": None
    }
}

AGE_COLUMN = 'DHH_AGE'