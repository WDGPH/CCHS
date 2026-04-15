"""Configuration settings for the CCHS analysis application."""

# Page configuration
PAGE_CONFIG = {
    "page_title": "Canadian Community Health Survey (CCHS) Analysis",
    "page_icon": "📊",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

APP_BRANDING = {
    "header_title": "CCHS Bootstrap Analysis Platform",
    "header_subtitle": "Canadian Community Health Survey Statistical Analysis Tool",
    "footer_org": "Configurable Public Health Analytics",
    "logo_url": None,
}

# Available cycles
AVAILABLE_CYCLES = ["2021", "2022", "2023", "2024"]
DEFAULT_CYCLE = "2024"

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

KNOWN_DISTRICT_LABELS = {}
for district_group in MUNICIPALITY_OPTIONS.values():
    KNOWN_DISTRICT_LABELS.update(district_group)

PUBLIC_HEALTH_UNITS = {
    "wdg": {
        "label": "Wellington-Dufferin-Guelph Public Health",
        "health_region_codes": [3566],
        "municipality_groups": MUNICIPALITY_OPTIONS,
    }
}

KNOWN_HEALTH_REGION_LABELS = {
    3526: "Algoma Public Health",
    3527: "Brant County Health Unit",
    3530: "Durham Region Health Department",
    3533: "Grey Bruce Public Health",
    3534: "Haldimand-Norfolk Health Unit",
    3535: "Haliburton, Kawartha, Pine Ridge District Health Unit",
    3536: "Halton Region Public Health",
    3537: "Hamilton Public Health Services",
    3538: "Hastings Prince Edward Public Health",
    3539: "Huron Perth Public Health",
    3540: "Chatham-Kent Public Health",
    3541: "Kingston, Frontenac and Lennox & Addington Public Health",
    3542: "Lambton Public Health",
    3543: "Leeds, Grenville and Lanark District Health Unit",
    3544: "Middlesex-London Health Unit",
    3546: "Niagara Region Public Health",
    3547: "North Bay Parry Sound District Health Unit",
    3549: "Northwestern Health Unit",
    3550: "Huron Perth Public Health",
    3551: "Ottawa Public Health",
    3553: "Peel Public Health",
    3554: "Perth District Health Unit",
    3555: "Peterborough Public Health",
    3556: "Porcupine Health Unit",
    3557: "Renfrew County and District Health Unit",
    3558: "Eastern Ontario Health Unit",
    3560: "Simcoe Muskoka District Health Unit",
    3561: "Public Health Sudbury & Districts",
    3562: "Thunder Bay District Health Unit",
    3563: "Timiskaming Health Unit",
    3565: "Region of Waterloo Public Health",
    3566: "Wellington-Dufferin-Guelph Public Health",
    3568: "Windsor-Essex County Health Unit",
    3570: "York Region Public Health",
    3575: "Southwestern Public Health",
    3595: "Toronto Public Health",
}

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
