import os
from pathlib import Path
import datetime

# OFFLINE-FIRST CONFIGURATION
# Cloud Storage settings - ONLY used when explicitly requested via backup
USE_CLOUD_STORAGE = True  # Enable cloud storage for backup functionality
CLOUD_BUCKET_NAME = "advitia-weighbridge-data"  # Your bucket name
CLOUD_CREDENTIALS_PATH = "gcloud-credentials.json"  # Path to your service account key

# NEW: Offline-first mode - prevents automatic cloud attempts during regular saves
OFFLINE_FIRST_MODE = True  # Set to True to save locally first, cloud only on backup
AUTO_CLOUD_SAVE = False   # Set to True to attempt cloud save on every record save (not recommended for poor internet)

# Global weighbridge reference
GLOBAL_WEIGHBRIDGE_MANAGER = None
GLOBAL_WEIGHBRIDGE_WEIGHT_VAR = None
GLOBAL_WEIGHBRIDGE_STATUS_VAR = None

# Global constants
DATA_FOLDER = 'data'
DAILY_REPORTS_FOLDER = os.path.join(DATA_FOLDER, 'daily_reports')

# Ticket Number Configuration
TICKET_PREFIX = "T"  # Prefix for ticket numbers (e.g., "T" for T0001, T0002, etc.)
TICKET_START_NUMBER = 1  # Starting ticket number (will be incremented from here)
TICKET_NUMBER_DIGITS = 4  # Number of digits in ticket number (e.g., 4 for T0001, T0002)

# UPDATED: Dynamic filename generation instead of hardcoded
def get_data_filename(agency_name=None, site_name=None):
    """Generate dynamic filename based on agency and site
    
    Args:
        agency_name: Name of the agency
        site_name: Name of the site
        
    Returns:
        str: Formatted filename
    """
    if agency_name and site_name:
        # Clean the names for filename (remove spaces and special characters)
        clean_agency = agency_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        clean_site = site_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        filename = f"{clean_agency}_{clean_site}_data.csv"
    else:
        # Fallback to default if no agency/site provided
        filename = "weighbridge_data.csv"
    
    return os.path.join(DATA_FOLDER, filename)

# Default data file (will be updated when agency/site is selected)
DATA_FILE = os.path.join(DATA_FOLDER, 'weighbridge_data.csv')
IMAGES_FOLDER = os.path.join(DATA_FOLDER, 'images')

# Global variables to store current agency and site
CURRENT_AGENCY = None
CURRENT_SITE = None

def set_current_context(agency_name, site_name):
    """Set the current agency and site context for filename generation
    
    Args:
        agency_name: Current agency name
        site_name: Current site name
    """
    global CURRENT_AGENCY, CURRENT_SITE, DATA_FILE
    CURRENT_AGENCY = agency_name
    CURRENT_SITE = site_name
    
    # Update the global DATA_FILE path
    DATA_FILE = get_data_filename(agency_name, site_name)
    
    # Ensure the file exists with proper header
    initialize_csv()

def get_current_data_file():
    """Get the current data file path based on context
    
    Returns:
        str: Current data file path
    """
    return get_data_filename(CURRENT_AGENCY, CURRENT_SITE)

def reserve_next_ticket_number():
    """Reserve (peek at) the next ticket number WITHOUT incrementing the counter
    
    Returns:
        str: Next ticket number (e.g., "T0001", "T0002")
    """
    from settings_storage import SettingsStorage
    
    try:
        settings_storage = SettingsStorage()
        
        # Get current ticket counter from settings (don't increment)
        current_number = settings_storage.get_ticket_counter()
        
        # Generate the ticket number without incrementing
        next_ticket = f"{TICKET_PREFIX}{current_number:0{TICKET_NUMBER_DIGITS}d}"
        
        print(f"Reserved ticket number: {next_ticket}")
        return next_ticket
        
    except Exception as e:
        print(f"Error reserving ticket number: {e}")
        # Fallback to default format if settings fail
        return f"{TICKET_PREFIX}{TICKET_START_NUMBER:0{TICKET_NUMBER_DIGITS}d}"

def commit_next_ticket_number():
    """Actually increment and commit the ticket counter (only after successful save)
    
    Returns:
        bool: True if successful, False otherwise
    """
    from settings_storage import SettingsStorage
    
    try:
        settings_storage = SettingsStorage()
        
        # Get current ticket counter from settings
        current_number = settings_storage.get_ticket_counter()
        
        # Increment and save the counter
        success = settings_storage.save_ticket_counter(current_number + 1)
        
        if success:
            print(f"Committed ticket number: T{current_number:0{TICKET_NUMBER_DIGITS}d}, next will be: T{(current_number + 1):0{TICKET_NUMBER_DIGITS}d}")
        
        return success
        
    except Exception as e:
        print(f"Error committing ticket number: {e}")
        return False

def get_next_ticket_number():
    """Get the next ticket number and increment the counter
    DEPRECATED: Use reserve_next_ticket_number() and commit_next_ticket_number() instead
    
    Returns:
        str: Next ticket number (e.g., "T0001", "T0002")
    """
    print("WARNING: get_next_ticket_number() is deprecated. Use reserve_next_ticket_number() and commit_next_ticket_number() instead.")
    return reserve_next_ticket_number()

def reset_ticket_counter(start_number=None):
    """Reset the ticket counter to a specific number
    
    Args:
        start_number: Number to reset to (if None, uses TICKET_START_NUMBER)
    """
    from settings_storage import SettingsStorage
    
    try:
        settings_storage = SettingsStorage()
        reset_to = start_number if start_number is not None else TICKET_START_NUMBER
        
        settings_storage.save_ticket_counter(reset_to)
        print(f"Ticket counter reset to: {reset_to}")
        return True
        
    except Exception as e:
        print(f"Error resetting ticket counter: {e}")
        return False

def get_current_ticket_number():
    """Get the current ticket number without incrementing
    
    Returns:
        str: Current ticket number that would be generated next
    """
    from settings_storage import SettingsStorage
    
    try:
        settings_storage = SettingsStorage()
        current_number = settings_storage.get_ticket_counter()
        return f"{TICKET_PREFIX}{current_number:0{TICKET_NUMBER_DIGITS}d}"
        
    except Exception as e:
        print(f"Error getting current ticket number: {e}")
        return f"{TICKET_PREFIX}{TICKET_START_NUMBER:0{TICKET_NUMBER_DIGITS}d}"

def set_ticket_format(prefix=None, digits=None):
    """Update ticket format settings
    
    Args:
        prefix: New prefix for tickets (e.g., "WB", "TKT")
        digits: Number of digits for ticket numbers
    """
    global TICKET_PREFIX, TICKET_NUMBER_DIGITS
    
    if prefix is not None:
        TICKET_PREFIX = prefix
    if digits is not None:
        TICKET_NUMBER_DIGITS = digits
    
    print(f"Ticket format updated: {TICKET_PREFIX}{0:0{TICKET_NUMBER_DIGITS}d}")

# CSV Header definition
CSV_HEADER = ['Date', 'Time', 'Site Name', 'Agency Name', 'Material', 'Ticket No', 'Vehicle No', 
              'Transfer Party Name', 'First Weight', 'First Timestamp', 'Second Weight', 'Second Timestamp',
              'Net Weight', 'Material Type', 'First Front Image', 'First Back Image', 
              'Second Front Image', 'Second Back Image', 'Site Incharge', 'User Name']

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
    current_file = get_current_data_file()
    if not os.path.exists(current_file):
        with open(current_file, 'w', newline='') as csv_file:
            import csv
            writer = csv.writer(csv_file)
            writer.writerow(CSV_HEADER)

def setup_daily_reports_folder():
    """Setup daily reports folder structure"""
    try:
        # Create main daily_reports folder
        os.makedirs(DAILY_REPORTS_FOLDER, exist_ok=True)
        
        # Create today's folder
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        today_folder = os.path.join(DAILY_REPORTS_FOLDER, today_str)
        os.makedirs(today_folder, exist_ok=True)
        
        # Create a README file in the main folder if it doesn't exist
        readme_path = os.path.join(DAILY_REPORTS_FOLDER, "README.txt")
        if not os.path.exists(readme_path):
            with open(readme_path, 'w') as f:
                f.write("""DAILY REPORTS FOLDER STRUCTURE
================================

This folder contains daily reports organized by date.

Structure:
daily_reports/
├── YYYY-MM-DD/          # Daily folder (e.g., 2024-01-15)
│   ├── report1.pdf      # Reports generated on that day
│   ├── summary.xlsx     # Excel summaries
│   └── data_export.csv  # CSV exports
├── YYYY-MM-DD/
│   └── [more reports...]
└── README.txt           # This file

OFFLINE-FIRST BEHAVIOR:
- Records and PDFs are saved locally first
- Cloud backup is only attempted when explicitly requested via Settings > Backup
- This prevents internet connection delays during normal operations

GENERATED BY: Swaccha Andhra Corporation Weighbridge System
""")
        
        print(f"Daily reports folder setup completed: {DAILY_REPORTS_FOLDER}")
        print(f"Today's folder: {today_folder}")
        
        return True
        
    except Exception as e:
        print(f"Error setting up daily reports folder: {e}")
        return False

def get_todays_reports_folder():
    """Get today's reports folder path
    
    Returns:
        str: Path to today's reports folder
    """
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    return os.path.join(DAILY_REPORTS_FOLDER, today_str)

def ensure_todays_reports_folder():
    """Ensure today's reports folder exists
    
    Returns:
        str: Path to today's reports folder
    """
    today_folder = get_todays_reports_folder()
    os.makedirs(today_folder, exist_ok=True)
    return today_folder

def setup():
    """Initialize the application data structures"""
    initialize_folders()
    initialize_csv()
    setup_daily_reports_folder()
    
    # Print offline-first mode status
    if OFFLINE_FIRST_MODE:
        print("🔒 OFFLINE-FIRST MODE ENABLED")
        print("   • Records and PDFs saved locally first")
        print("   • Cloud backup available via Settings > Backup")
        print("   • No internet connection delays during regular saves")
    else:
        print("🌐 Online mode - cloud attempts during saves")

def set_global_weighbridge(manager, weight_var, status_var):
    """Set global references to weighbridge components"""
    global GLOBAL_WEIGHBRIDGE_MANAGER, GLOBAL_WEIGHBRIDGE_WEIGHT_VAR, GLOBAL_WEIGHBRIDGE_STATUS_VAR
    GLOBAL_WEIGHBRIDGE_MANAGER = manager
    GLOBAL_WEIGHBRIDGE_WEIGHT_VAR = weight_var
    GLOBAL_WEIGHBRIDGE_STATUS_VAR = status_var

def get_global_weighbridge_info():
    """Get global weighbridge references"""
    return GLOBAL_WEIGHBRIDGE_MANAGER, GLOBAL_WEIGHBRIDGE_WEIGHT_VAR, GLOBAL_WEIGHBRIDGE_STATUS_VAR