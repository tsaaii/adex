import os
from pathlib import Path

# Add to config.py
# Cloud Storage settings
USE_CLOUD_STORAGE = True
CLOUD_BUCKET_NAME = "advitia-weighbridge-data"  # Your bucket name
CLOUD_CREDENTIALS_PATH = "gcloud-credentials.json"  # Path to your service account key
# Global constants
DATA_FOLDER = 'data'
DATA_FILE = os.path.join(DATA_FOLDER, 'tharuni_data.csv')
IMAGES_FOLDER = os.path.join(DATA_FOLDER, 'images')
# In config.py, update the CSV_HEADER list:

CSV_HEADER = ['Date', 'Time', 'Site Name', 'Agency Name', 'Material', 'Ticket No', 'Vehicle No', 
              'Transfer Party Name', 'First Weight', 'First Timestamp', 'Second Weight', 'Second Timestamp',
              'Net Weight', 'Material Type', 'Front Image', 'Back Image', 'Site Incharge', 'User Name']

# Refreshed color scheme
COLORS = {
    "primary": "#1E88E5",         # Brighter Blue
    "primary_light": "#BBDEFB",   # Lighter Blue
    "secondary": "#00BFA5",       # Teal
    "background": "#F5F7FA",      # Light Gray
    "text": "#212529",            # Dark Gray
    "white": "#FFFFFF",           # White
    "error": "#F44336",           # Red
    "warning": "#FFA000",         # Amber
    "header_bg": "#0D47A1",       # Darker Blue
    "button_hover": "#1565C0",    # Hover Blue
    "button_text": "#FFFFFF",     # Button Text (White)
    "form_bg": "#FFFFFF",         # Form Background
    "section_bg": "#F9FAFB",      # Section Background
    "button_alt": "#546E7A",      # Alternative button color
    "button_alt_hover": "#455A64", # Alternative button hover color
    "table_header_bg": "#E3F2FD", # Table header background
    "table_row_even": "#F5F5F5",  # Even row background
    "table_row_odd": "#FFFFFF",   # Odd row background
    "table_border": "#E0E0E0"     # Table border color
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