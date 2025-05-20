import os
from pathlib import Path

# Add to config.py
# Cloud Storage settings
USE_CLOUD_STORAGE = True
CLOUD_BUCKET_NAME = "advitia-weighbridge-data"  # Your bucket name
CLOUD_CREDENTIALS_PATH = "gcloud-credentials.json"  # Path to your service account key

# Add to config.py:

# Global weighbridge reference
GLOBAL_WEIGHBRIDGE_MANAGER = None
GLOBAL_WEIGHBRIDGE_WEIGHT_VAR = None
GLOBAL_WEIGHBRIDGE_STATUS_VAR = None

# Global constants
DATA_FOLDER = 'data'
DATA_FILE = os.path.join(DATA_FOLDER, 'tharuni_data.csv')
IMAGES_FOLDER = os.path.join(DATA_FOLDER, 'images')

# CSV Header definition
CSV_HEADER = ['Date', 'Time', 'Site Name', 'Agency Name', 'Material', 'Ticket No', 'Vehicle No', 
              'Transfer Party Name', 'First Weight', 'First Timestamp', 'Second Weight', 'Second Timestamp',
              'Net Weight', 'Material Type', 'Front Image', 'Back Image', 'Site Incharge', 'User Name']

# Updated color scheme - Light yellow, light orange, and pinkish red
# Optimized for visibility on sunny screens
COLORS = {
    "primary": "#FA541C",         # Volcano (orange-red)
    "primary_light": "#FFBB96",   # Light volcano
    "secondary": "#FA8C16",       # Orange
    "background": "#F0F2F5",      # Light gray background
    "text": "#262626",            # Dark gray text for contrast
    "white": "#FFFFFF",           # White
    "error": "#F5222D",           # Red
    "warning": "#FAAD14",         # Gold/amber
    "header_bg": "#873800",       # Dark brown (volcano-9)
    "button_hover": "#D4380D",    # Darker volcano (volcano-7)
    "button_text": "#FFFFFF",     # Button text (White)
    "form_bg": "#FFFFFF",         # Form background
    "section_bg": "#FFF7E6",      # Very light orange
    "button_alt": "#D46B08",      # Orange-7
    "button_alt_hover": "#AD4E00", # Orange-8
    "table_header_bg": "#FFF1E6",  # Light volcano background
    "table_row_even": "#FAFAFA",   # Light gray for even rows
    "table_row_odd": "#FFFFFF",    # White for odd rows
    "table_border": "#FFD8BF"      # Light volcano for borders
}

# Standard width for UI components - reduced for smaller windows
STD_WIDTH = 20

# Ensure data folder exists
def initialize_folders():
    Path(DATA_FOLDER).mkdir(exist_ok=True)
    Path(IMAGES_FOLDER).mkdir(exist_ok=True)

# Create CSV file with header if it doesn't exist
def initialize_csv():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', newline='') as csv_file:
            import csv
            writer = csv.writer(csv_file)
            writer.writerow(CSV_HEADER)

def setup():
    """Initialize the application data structures"""
    initialize_folders()
    initialize_csv()


def set_global_weighbridge(manager, weight_var, status_var):
    """Set global references to weighbridge components"""
    global GLOBAL_WEIGHBRIDGE_MANAGER, GLOBAL_WEIGHBRIDGE_WEIGHT_VAR, GLOBAL_WEIGHBRIDGE_STATUS_VAR
    GLOBAL_WEIGHBRIDGE_MANAGER = manager
    GLOBAL_WEIGHBRIDGE_WEIGHT_VAR = weight_var
    GLOBAL_WEIGHBRIDGE_STATUS_VAR = status_var

def get_global_weighbridge_info():
    """Get global weighbridge references"""
    return GLOBAL_WEIGHBRIDGE_MANAGER, GLOBAL_WEIGHBRIDGE_WEIGHT_VAR, GLOBAL_WEIGHBRIDGE_STATUS_VAR

