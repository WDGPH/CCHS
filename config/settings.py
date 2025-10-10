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
AGE_BINS = [0, 18, 25, 45, 65, 120]
AGE_LABELS = ['0-17', '18-24', '25-44', '45-64', '65+']
AGE_COLUMN = 'DHH_AGE'