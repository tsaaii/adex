import os
import csv
import pandas as pd
import datetime
import logging
from tkinter import messagebox, filedialog
import config
import json
from cloud_storage import CloudStorageService
import shutil

# Import PDF generation capabilities
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import cv2
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ReportLab not available - PDF auto-generation will be disabled")

# Set up logging
def setup_logging():
    """Set up logging directory and configuration"""
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create log filename with current date
    log_filename = os.path.join(logs_dir, f"weighbridge_{datetime.datetime.now().strftime('%Y-%m-%d')}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    return logging.getLogger('DataManager')

class DataManager:
    """Class for managing data operations with enhanced logging and debugging"""
    
    def __init__(self):
        """Initialize data manager with logging"""
        # Set up logging first
        self.logger = setup_logging()
        self.logger.info("DataManager initialized")
        
        self.data_file = config.DATA_FILE
        self.initialize_new_csv_structure()
        
        # Create daily PDF folder structure
        self.setup_daily_pdf_folders()
        
        # Load address config for PDF generation
        self.address_config = self.load_address_config()
        
        self.logger.info(f"Data file: {self.data_file}")
    
    def setup_daily_pdf_folders(self):
        """Set up daily folder structure for PDF generation"""
        try:
            # Create base PDF reports folder
            self.pdf_reports_folder = os.path.join(config.DATA_FOLDER, 'daily_reports')
            os.makedirs(self.pdf_reports_folder, exist_ok=True)
            
            # Create today's folder
            today = datetime.datetime.now()
            self.today_folder_name = today.strftime("%d-%m")  # Format: 28-05
            self.today_pdf_folder = os.path.join(self.pdf_reports_folder, self.today_folder_name)
            os.makedirs(self.today_pdf_folder, exist_ok=True)
            
            self.logger.info(f"Daily PDF folder ready: {self.today_pdf_folder}")
            
        except Exception as e:
            self.logger.error(f"Error setting up daily PDF folders: {e}")
            self.today_pdf_folder = config.DATA_FOLDER  # Fallback
    
    def load_address_config(self):
        """Load address configuration for PDF generation"""
        try:
            config_file = os.path.join(config.DATA_FOLDER, 'address_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return json.load(f)
            else:
                # Create default config for PDF generation
                default_config = {
                    "agencies": {
                        "Default Agency": {
                            "name": "Default Agency",
                            "address": "123 Main Street\nCity, State - 123456",
                            "contact": "+91-1234567890",
                            "email": "info@agency.com"
                        },
                        "Tharuni": {
                            "name": "Tharuni Environmental Services",
                            "address": "Environmental Complex\nGuntur, Andhra Pradesh - 522001",
                            "contact": "+91-9876543210",
                            "email": "info@tharuni.com"
                        }
                    },
                    "sites": {
                        "Guntur": {
                            "name": "Guntur Processing Site",
                            "address": "Industrial Area, Guntur\nAndhra Pradesh - 522001",
                            "contact": "+91-9876543210"
                        }
                    }
                }
                
                # Save default config
                os.makedirs(config.DATA_FOLDER, exist_ok=True)
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=4)
                
                return default_config
        except Exception as e:
            self.logger.error(f"Error loading address config for PDF: {e}")
            return {"agencies": {}, "sites": {}}

    def get_current_data_file(self):
        """Get the current data file path based on context"""
        return config.get_current_data_file()
        
    def initialize_new_csv_structure(self):
        """Update CSV structure to include weighment fields if needed"""
        current_file = self.get_current_data_file()
        
        if not os.path.exists(current_file):
            # Create new file with updated header
            try:
                os.makedirs(os.path.dirname(current_file), exist_ok=True)
                with open(current_file, 'w', newline='', encoding='utf-8') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(config.CSV_HEADER)
                self.logger.info(f"Created new CSV file: {current_file}")
            except Exception as e:
                self.logger.error(f"Error creating CSV file: {e}")
            return
            
        try:
            # Check if existing file has the new structure
            with open(current_file, 'r', newline='', encoding='utf-8') as csv_file:
                reader = csv.reader(csv_file)
                header = next(reader, None)
                
                # Check if our new fields exist in the header
                if header and all(field in header for field in ['First Weight', 'First Timestamp', 'Second Weight', 'Second Timestamp']):
                    # Structure is already updated
                    self.logger.info("CSV structure is up to date")
                    return
                    
                # Need to migrate old data to new structure
                data = list(reader)  # Read all existing data
            
            # Create backup of old file
            backup_file = f"{current_file}.backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(current_file, backup_file)
            self.logger.info(f"Created backup: {backup_file}")
            
            # Create new file with updated structure
            with open(current_file, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                
                # Write new header
                writer.writerow(config.CSV_HEADER)
                
                # Migrate old data - map old fields to new structure
                for row in data:
                    if len(row) >= 12:  # Ensure we have minimum fields
                        new_row = [
                            row[0],  # Date
                            row[1],  # Time
                            row[2],  # Site Name
                            row[3],  # Agency Name
                            row[4],  # Material
                            row[5],  # Ticket No
                            row[6],  # Vehicle No
                            row[7],  # Transfer Party Name
                            row[8] if len(row) > 8 else "",  # Gross Weight -> First Weight
                            "",      # First Timestamp (new field)
                            row[9] if len(row) > 9 else "",  # Tare Weight -> Second Weight
                            "",      # Second Timestamp (new field)
                            row[10] if len(row) > 10 else "",  # Net Weight
                            row[11] if len(row) > 11 else "",  # Material Type
                            row[12] if len(row) > 12 else "",  # First Front Image
                            row[13] if len(row) > 13 else "",  # First Back Image
                            row[14] if len(row) > 14 else "",  # Second Front Image
                            row[15] if len(row) > 15 else "",  # Second Back Image
                            row[16] if len(row) > 16 else "",  # Site Incharge
                            row[17] if len(row) > 17 else ""   # User Name
                        ]
                        writer.writerow(new_row)
                        
            self.logger.info("Database structure updated successfully")
            if messagebox:
                messagebox.showinfo("Database Updated", 
                                 "The data structure has been updated to support the new weighment system.\n"
                                 f"A backup of your old data has been saved to {backup_file}")
                             
        except Exception as e:
            self.logger.error(f"Error updating database structure: {e}")
            if messagebox:
                messagebox.showerror("Database Update Error", 
                                  f"Error updating database structure: {e}\n"
                                  "The application may not function correctly.")

    def set_agency_site_context(self, agency_name, site_name):
        """Set the current agency and site context for file operations"""
        # Update the global context
        config.set_current_context(agency_name, site_name)
        
        # Update our local reference
        self.data_file = self.get_current_data_file()
        
        # Ensure the new file exists with proper structure
        self.initialize_new_csv_structure()
        
        self.logger.info(f"Data context set to: Agency='{agency_name}', Site='{site_name}'")
        self.logger.info(f"Data file: {self.data_file}")

    def save_record(self, data):
        """FIXED: Save record to CSV file with enhanced validation and logging"""
        try:
            self.logger.info("="*50)
            self.logger.info("STARTING RECORD SAVE OPERATION")
            self.logger.info(f"Input data keys: {list(data.keys())}")
            
            # Enhanced validation with detailed logging
            validation_result = self.validate_record_data(data)
            if not validation_result['valid']:
                self.logger.error(f"Validation failed: {validation_result['errors']}")
                if messagebox:
                    messagebox.showerror("Validation Error", f"Record validation failed:\n" + "\n".join(validation_result['errors']))
                return False
            
            # Use the current data file
            current_file = self.get_current_data_file()
            self.logger.info(f"Using data file: {current_file}")
            
            # Check if this is an update to an existing record
            ticket_no = data.get('ticket_no', '')
            is_update = False
            
            if ticket_no:
                # Check if record with this ticket number exists
                records = self.get_filtered_records(ticket_no)
                for record in records:
                    if record.get('ticket_no') == ticket_no:
                        is_update = True
                        self.logger.info(f"Updating existing record: {ticket_no}")
                        break
            
            if not is_update:
                self.logger.info(f"Adding new record: {ticket_no}")
            
            # PRIORITY 1: Save to CSV locally (this MUST work)
            csv_success = False
            try:
                if is_update:
                    # Update existing record
                    csv_success = self.update_record(data)
                else:
                    # Add new record
                    csv_success = self.add_new_record(data)
                
                if csv_success:
                    self.logger.info(f"✅ Record {ticket_no} saved to local CSV successfully")
                else:
                    self.logger.error(f"❌ Failed to save record {ticket_no} to local CSV")
                    return False
            except Exception as csv_error:
                self.logger.error(f"❌ Critical error saving to CSV: {csv_error}")
                return False
            
            # Check if this is a complete record (both weighments)
            first_weight = data.get('first_weight', '').strip()
            first_timestamp = data.get('first_timestamp', '').strip()
            second_weight = data.get('second_weight', '').strip()
            second_timestamp = data.get('second_timestamp', '').strip()
            
            is_complete_record = (first_weight and first_timestamp and 
                                second_weight and second_timestamp)
            
            self.logger.info(f"Record completion status: {is_complete_record}")
            self.logger.info(f"First weight: '{first_weight}', timestamp: '{first_timestamp}'")
            self.logger.info(f"Second weight: '{second_weight}', timestamp: '{second_timestamp}'")
            
            # PRIORITY 2: Auto-generate PDF for complete records (optional, don't fail if this fails)
            pdf_generated = False
            pdf_path = None
            if is_complete_record:
                self.logger.info(f"Complete record detected for ticket {ticket_no} - attempting PDF generation...")
                try:
                    pdf_generated, pdf_path = self.auto_generate_pdf_for_complete_record(data)
                    if pdf_generated:
                        self.logger.info(f"✅ PDF auto-generated: {pdf_path}")
                        # Show success message to user only if PDF was generated
                        try:
                            if messagebox:
                                messagebox.showinfo("PDF Generated", 
                                                f"Record saved and PDF generated!\n\n"
                                                f"PDF saved to: {os.path.basename(pdf_path)}\n"
                                                f"Location: {os.path.dirname(pdf_path)}")
                        except:
                            # Don't fail if messagebox fails
                            pass
                    else:
                        self.logger.warning("⚠️ PDF generation failed, but record was saved")
                except Exception as pdf_error:
                    self.logger.error(f"⚠️ PDF generation error (non-critical): {pdf_error}")
            
            # PRIORITY 3: Save to cloud storage (optional, don't fail if this fails)
            cloud_success = False
            images_uploaded = 0
            total_images = 0
            
            # Only attempt cloud storage if enabled AND record is complete AND we have internet
            if (hasattr(config, 'USE_CLOUD_STORAGE') and config.USE_CLOUD_STORAGE and 
                is_complete_record):
                try:
                    cloud_success, images_uploaded, total_images = self.save_to_cloud_with_images(data)
                    
                    if cloud_success:
                        self.logger.info(f"✅ Complete record {ticket_no} successfully saved to cloud")
                        if images_uploaded > 0:
                            self.logger.info(f"✅ Images uploaded: {images_uploaded}/{total_images}")
                    else:
                        self.logger.warning(f"⚠️ Warning: Complete record {ticket_no} could not be saved to cloud (working offline)")
                except Exception as cloud_error:
                    self.logger.error(f"⚠️ Cloud storage error (non-critical): {cloud_error}")
            elif not is_complete_record:
                self.logger.info(f"ℹ️ Record {ticket_no} saved locally only - incomplete weighments")
            else:
                self.logger.info(f"ℹ️ Record {ticket_no} saved locally only - cloud storage disabled or offline")
            
            self.logger.info("RECORD SAVE OPERATION COMPLETED SUCCESSFULLY")
            self.logger.info("="*50)
            
            # Return success if CSV save worked (the critical operation)
            return csv_success
                    
        except Exception as e:
            self.logger.error(f"❌ Critical error saving record: {e}")
            return False

    def validate_record_data(self, data):
        """Enhanced validation with detailed error reporting"""
        errors = []
        
        # Check required fields
        required_fields = {
            'ticket_no': 'Ticket Number',
            'vehicle_no': 'Vehicle Number',
            'agency_name': 'Agency Name'
        }
        
        for field, display_name in required_fields.items():
            value = data.get(field, '').strip()
            if not value:
                errors.append(f"{display_name} is required")
        
        # Check weighment data consistency
        first_weight = data.get('first_weight', '').strip()
        first_timestamp = data.get('first_timestamp', '').strip()
        second_weight = data.get('second_weight', '').strip()
        second_timestamp = data.get('second_timestamp', '').strip()
        
        # If first weight exists, timestamp should also exist
        if first_weight and not first_timestamp:
            errors.append("First weighment timestamp is missing")
        
        # If second weight exists, timestamp should also exist
        if second_weight and not second_timestamp:
            errors.append("Second weighment timestamp is missing")
        
        # At least first weighment should be present for new records
        if not first_weight and not first_timestamp:
            errors.append("At least first weighment is required")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def add_new_record(self, data):
        """FIXED: Add a new record to the CSV file with enhanced error handling and logging"""
        try:
            self.logger.info("Adding new record to CSV")
            
            # Ensure all required fields have values
            record = [
                data.get('date', datetime.datetime.now().strftime("%d-%m-%Y")),
                data.get('time', datetime.datetime.now().strftime("%H:%M:%S")),
                data.get('site_name', ''),
                data.get('agency_name', ''),
                data.get('material', ''),
                data.get('ticket_no', ''),
                data.get('vehicle_no', ''),
                data.get('transfer_party_name', ''),
                data.get('first_weight', ''),
                data.get('first_timestamp', ''),
                data.get('second_weight', ''),
                data.get('second_timestamp', ''),
                data.get('net_weight', ''),
                data.get('material_type', ''),
                data.get('first_front_image', ''),
                data.get('first_back_image', ''),
                data.get('second_front_image', ''),
                data.get('second_back_image', ''),
                data.get('site_incharge', ''),
                data.get('user_name', '')
            ]
            
            # Log the record being saved
            self.logger.info(f"Record data: {record}")
            
            # Use current data file
            current_file = self.get_current_data_file()
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(current_file), exist_ok=True)
            
            # Write to CSV
            with open(current_file, 'a', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(record)
            
            self.logger.info(f"✅ New record added to {current_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error adding new record: {e}")
            return False

    def update_record(self, data):
        """FIXED: Update an existing record in the CSV file with enhanced error handling and logging"""
        try:
            current_file = self.get_current_data_file()
            ticket_no = data.get('ticket_no', '')
            
            self.logger.info(f"Updating record {ticket_no} in {current_file}")
            
            if not os.path.exists(current_file):
                self.logger.warning(f"CSV file doesn't exist, creating new one: {current_file}")
                return self.add_new_record(data)
            
            # Read all records
            all_records = []
            header = None
            try:
                with open(current_file, 'r', newline='', encoding='utf-8') as csv_file:
                    reader = csv.reader(csv_file)
                    header = next(reader, None)  # Read header
                    all_records = list(reader)
                    
                self.logger.info(f"Read {len(all_records)} records from CSV")
            except Exception as read_error:
                self.logger.error(f"Error reading CSV file: {read_error}")
                return False
            
            # Find and update the record
            updated = False
            
            for i, row in enumerate(all_records):
                if len(row) >= 6 and row[5] == ticket_no:  # Ticket number is index 5
                    self.logger.info(f"Found record to update at index {i}")
                    
                    # Update the row with new data including all fields
                    updated_row = [
                        data.get('date', row[0] if len(row) > 0 else ''),
                        data.get('time', row[1] if len(row) > 1 else ''),
                        data.get('site_name', row[2] if len(row) > 2 else ''),
                        data.get('agency_name', row[3] if len(row) > 3 else ''),
                        data.get('material', row[4] if len(row) > 4 else ''),
                        data.get('ticket_no', row[5] if len(row) > 5 else ''),
                        data.get('vehicle_no', row[6] if len(row) > 6 else ''),
                        data.get('transfer_party_name', row[7] if len(row) > 7 else ''),
                        data.get('first_weight', row[8] if len(row) > 8 else ''),
                        data.get('first_timestamp', row[9] if len(row) > 9 else ''),
                        data.get('second_weight', row[10] if len(row) > 10 else ''),
                        data.get('second_timestamp', row[11] if len(row) > 11 else ''),
                        data.get('net_weight', row[12] if len(row) > 12 else ''),
                        data.get('material_type', row[13] if len(row) > 13 else ''),
                        data.get('first_front_image', row[14] if len(row) > 14 else ''),
                        data.get('first_back_image', row[15] if len(row) > 15 else ''),
                        data.get('second_front_image', row[16] if len(row) > 16 else ''),
                        data.get('second_back_image', row[17] if len(row) > 17 else ''),
                        data.get('site_incharge', row[18] if len(row) > 18 else ''),
                        data.get('user_name', row[19] if len(row) > 19 else '')
                    ]
                    
                    all_records[i] = updated_row
                    updated = True
                    self.logger.info(f"Updated record data: {updated_row}")
                    break
            
            if not updated:
                self.logger.warning(f"Record with ticket {ticket_no} not found, adding as new record")
                return self.add_new_record(data)
                
            # Write all records back to the file
            try:
                # Create backup before updating
                backup_file = f"{current_file}.backup"
                if os.path.exists(current_file):
                    shutil.copy2(current_file, backup_file)
                
                with open(current_file, 'w', newline='', encoding='utf-8') as csv_file:
                    writer = csv.writer(csv_file)
                    if header:
                        writer.writerow(header)  # Write header
                    writer.writerows(all_records)  # Write all records
                
                # Remove backup if write was successful
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                    
                self.logger.info(f"✅ Record {ticket_no} updated in {current_file}")
                return True
            except Exception as write_error:
                self.logger.error(f"Error writing updated records: {write_error}")
                # Restore from backup if write failed
                backup_file = f"{current_file}.backup"
                if os.path.exists(backup_file):
                    shutil.copy2(backup_file, current_file)
                    os.remove(backup_file)
                    self.logger.info("Restored from backup due to write error")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error updating record: {e}")
            return False

    def get_all_records(self):
        """FIXED: Get all records from current CSV file with enhanced error handling"""
        records = []
        current_file = self.get_current_data_file()
        
        if not os.path.exists(current_file):
            self.logger.warning(f"CSV file does not exist: {current_file}")
            return records
            
        try:
            with open(current_file, 'r', newline='', encoding='utf-8') as csv_file:
                reader = csv.reader(csv_file)
                
                # Skip header
                header = next(reader, None)
                if not header:
                    self.logger.warning("CSV file has no header")
                    return records
                
                for row_num, row in enumerate(reader, 1):
                    try:
                        if len(row) >= 13:  # Minimum fields required
                            record = {
                                'date': row[0],
                                'time': row[1],
                                'site_name': row[2],
                                'agency_name': row[3],
                                'material': row[4],
                                'ticket_no': row[5],
                                'vehicle_no': row[6],
                                'transfer_party_name': row[7],
                                'first_weight': row[8] if len(row) > 8 else '',
                                'first_timestamp': row[9] if len(row) > 9 else '',
                                'second_weight': row[10] if len(row) > 10 else '',
                                'second_timestamp': row[11] if len(row) > 11 else '',
                                'net_weight': row[12] if len(row) > 12 else '',
                                'material_type': row[13] if len(row) > 13 else '',
                                'first_front_image': row[14] if len(row) > 14 else '',
                                'first_back_image': row[15] if len(row) > 15 else '',
                                'second_front_image': row[16] if len(row) > 16 else '',
                                'second_back_image': row[17] if len(row) > 17 else '',
                                'site_incharge': row[18] if len(row) > 18 else '',
                                'user_name': row[19] if len(row) > 19 else ''
                            }
                            records.append(record)
                        else:
                            self.logger.warning(f"Skipping row {row_num} - insufficient data: {len(row)} fields")
                    except Exception as row_error:
                        self.logger.error(f"Error processing row {row_num}: {row_error}")
                        
            self.logger.info(f"Successfully loaded {len(records)} records from {current_file}")
            return records
                
        except Exception as e:
            self.logger.error(f"Error reading records from {current_file}: {e}")
            return []

    def get_filtered_records(self, filter_text=""):
        """Get records filtered by text with logging"""
        try:
            all_records = self.get_all_records()
            
            if not filter_text:
                self.logger.info(f"Returning all {len(all_records)} records (no filter)")
                return all_records
                
            filter_text = filter_text.lower()
            filtered_records = []
            
            for record in all_records:
                # Check if filter text exists in any field
                if any(filter_text in str(value).lower() for value in record.values()):
                    filtered_records.append(record)
                    
            self.logger.info(f"Filtered {len(all_records)} records to {len(filtered_records)} using filter: '{filter_text}'")
            return filtered_records
        except Exception as e:
            self.logger.error(f"Error filtering records: {e}")
            return []

    # Include other methods from original file...
    # (keeping space for brevity, but include all other methods like save_to_cloud_with_images, 
    # auto_generate_pdf_for_complete_record, etc.)
    
    def save_to_cloud_with_images(self, data):
        """Save record with images to Google Cloud Storage only if both weighments are complete"""
        try:
            # Check if both weighments are complete before saving to cloud
            first_weight = data.get('first_weight', '').strip()
            first_timestamp = data.get('first_timestamp', '').strip()
            second_weight = data.get('second_weight', '').strip()
            second_timestamp = data.get('second_timestamp', '').strip()
            
            # Only save to cloud if both weighments are complete
            if not (first_weight and first_timestamp and second_weight and second_timestamp):
                self.logger.info(f"Skipping cloud save for ticket {data.get('ticket_no', 'unknown')} - incomplete weighments")
                return False, 0, 0
            
            # Check if cloud storage is enabled
            if not (hasattr(config, 'USE_CLOUD_STORAGE') and config.USE_CLOUD_STORAGE):
                self.logger.info("Cloud storage disabled - skipping")
                return False, 0, 0
            
            # Initialize cloud storage if not already initialized
            if not hasattr(self, 'cloud_storage') or self.cloud_storage is None:
                try:
                    from cloud_storage import CloudStorageService
                    self.cloud_storage = CloudStorageService(
                        config.CLOUD_BUCKET_NAME,
                        config.CLOUD_CREDENTIALS_PATH
                    )
                except ImportError:
                    self.logger.error("Cloud storage module not available")
                    return False, 0, 0
                except Exception as init_error:
                    self.logger.error(f"Failed to initialize cloud storage: {init_error}")
                    return False, 0, 0
            
            # Check if connected to cloud storage
            try:
                if not self.cloud_storage.is_connected():
                    self.logger.warning("Not connected to cloud storage (offline or configuration issue)")
                    return False, 0, 0
            except Exception as conn_error:
                self.logger.error(f"Cloud connection check failed: {conn_error}")
                return False, 0, 0
            
            # Get site name and ticket number for folder structure
            site_name = data.get('site_name', 'Unknown_Site').replace(' ', '_').replace('/', '_')
            agency_name = data.get('agency_name', 'Unknown_Agency').replace(' ', '_').replace('/', '_')
            ticket_no = data.get('ticket_no', 'unknown')
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create structured filename: agency_name/site_name/ticket_number/timestamp.json
            json_filename = f"{agency_name}/{site_name}/{ticket_no}/{timestamp}.json"
            
            # Add some additional metadata to the JSON
            enhanced_data = data.copy()
            enhanced_data['cloud_upload_timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            enhanced_data['record_status'] = 'complete'  # Mark as complete record
            enhanced_data['net_weight_calculated'] = self._calculate_net_weight_for_cloud(
                enhanced_data.get('first_weight', ''), 
                enhanced_data.get('second_weight', '')
            )
            
            # Upload record with images using the new method
            json_success, images_uploaded, total_images = self.cloud_storage.upload_record_with_images(
                enhanced_data, 
                json_filename, 
                config.IMAGES_FOLDER
            )
            
            if json_success:
                self.logger.info(f"Record {ticket_no} successfully saved to cloud at {json_filename}")
                if images_uploaded > 0:
                    self.logger.info(f"Uploaded {images_uploaded}/{total_images} images for ticket {ticket_no}")
                else:
                    self.logger.info(f"No images found to upload for ticket {ticket_no}")
            else:
                self.logger.error(f"Failed to save record {ticket_no} to cloud")
                
            return json_success, images_uploaded, total_images
            
        except Exception as e:
            self.logger.error(f"Error saving to cloud with images (non-critical): {str(e)}")
            return False, 0, 0

    def _calculate_net_weight_for_cloud(self, first_weight_str, second_weight_str):
        """Calculate net weight for cloud storage"""
        try:
            if first_weight_str and second_weight_str:
                first_weight = float(first_weight_str)
                second_weight = float(second_weight_str)
                return abs(first_weight - second_weight)
            return 0.0
        except (ValueError, TypeError):
            return 0.0

    def auto_generate_pdf_for_complete_record(self, record_data):
        """Automatically generate PDF for a complete record"""
        # Check if ReportLab is available
        try:
            global REPORTLAB_AVAILABLE
            if not REPORTLAB_AVAILABLE:
                self.logger.warning("ReportLab not available - skipping PDF generation")
                return False, None
        except:
            self.logger.warning("PDF generation not available")
            return False, None
        
        try:
            # Check if record is complete (both weighments)
            first_weight = record_data.get('first_weight', '').strip()
            first_timestamp = record_data.get('first_timestamp', '').strip()
            second_weight = record_data.get('second_weight', '').strip()
            second_timestamp = record_data.get('second_timestamp', '').strip()
            
            if not (first_weight and first_timestamp and second_weight and second_timestamp):
                self.logger.info("Record incomplete - skipping PDF generation")
                return False, None
            
            # Generate PDF filename
            ticket_no = record_data.get('ticket_no', 'Unknown').replace('/', '_')
            vehicle_no = record_data.get('vehicle_no', 'Unknown').replace('/', '_').replace(' ', '_')
            site_name = record_data.get('site_name', 'Unknown').replace(' ', '_').replace('/', '_')
            agency_name = record_data.get('agency_name', 'Unknown').replace(' ', '_').replace('/', '_')
            timestamp = datetime.datetime.now().strftime("%H%M%S")
            
            # PDF filename format: AgencyName_SiteName_TicketNo_VehicleNo_HHMMSS.pdf
            pdf_filename = f"{agency_name}_{site_name}_{ticket_no}_{vehicle_no}_{timestamp}.pdf"
            
            # Get today's folder
            daily_folder = self.get_daily_pdf_folder()
            pdf_path = os.path.join(daily_folder, pdf_filename)
            
            # Generate the PDF
            success = self.create_pdf_report([record_data], pdf_path)
            
            if success:
                self.logger.info(f"Auto-generated PDF: {pdf_path}")
                return True, pdf_path
            else:
                self.logger.error("Failed to generate PDF")
                return False, None
                
        except Exception as e:
            self.logger.error(f"Error in auto PDF generation (non-critical): {e}")
            return False, None

    def get_daily_pdf_folder(self):
        """Get or create today's PDF folder"""
        today = datetime.datetime.now()
        folder_name = today.strftime("%d-%m")  # Format: 28-05
        
        # Check if we need to create a new folder (date changed)
        if not hasattr(self, 'today_folder_name') or self.today_folder_name != folder_name:
            self.today_folder_name = folder_name
            self.today_pdf_folder = os.path.join(self.pdf_reports_folder, folder_name)
            os.makedirs(self.today_pdf_folder, exist_ok=True)
            self.logger.info(f"Created new daily folder: {self.today_pdf_folder}")
        
        return self.today_pdf_folder
    
    def create_pdf_report(self, records_data, save_path):
        """Create PDF report with 4-image grid for complete records (same as reports.py)
        
        Args:
            records_data: List of record dictionaries
            save_path: Path to save the PDF
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not REPORTLAB_AVAILABLE:
            return False
            
        try:
            doc = SimpleDocTemplate(save_path, pagesize=A4,
                                    rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
            
            styles = getSampleStyleSheet()
            elements = []

            # Ink-friendly styles with increased font sizes
            header_style = ParagraphStyle(
                name='HeaderStyle',
                fontSize=18,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                textColor=colors.black,
                spaceAfter=6,
                spaceBefore=6
            )
            
            subheader_style = ParagraphStyle(
                name='SubHeaderStyle',
                fontSize=12,
                alignment=TA_CENTER,
                fontName='Helvetica',
                textColor=colors.black,
                spaceAfter=12
            )
            
            section_header_style = ParagraphStyle(
                name='SectionHeader',
                fontSize=13,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                textColor=colors.black,
                spaceAfter=6,
                spaceBefore=6
            )

            label_style = ParagraphStyle(
                name='LabelStyle',
                fontSize=11,
                fontName='Helvetica-Bold',
                textColor=colors.black
            )

            value_style = ParagraphStyle(
                name='ValueStyle',
                fontSize=11,
                fontName='Helvetica',
                textColor=colors.black
            )

            for i, record in enumerate(records_data):
                if i > 0:
                    elements.append(PageBreak())

                # Get agency information from address config
                agency_name = record.get('agency_name', 'Unknown Agency')
                agency_info = self.address_config.get('agencies', {}).get(agency_name, {})
                
                # Header Section with Agency Info
                elements.append(Paragraph(agency_info.get('name', agency_name), header_style))
                
                if agency_info.get('address'):
                    address_text = agency_info.get('address', '').replace('\n', '<br/>')
                    elements.append(Paragraph(address_text, subheader_style))
                
                # Contact information
                contact_info = []
                if agency_info.get('contact'):
                    contact_info.append(f"Phone: {agency_info.get('contact')}")
                if agency_info.get('email'):
                    contact_info.append(f"Email: {agency_info.get('email')}")
                
                if contact_info:
                    elements.append(Paragraph(" | ".join(contact_info), subheader_style))
                
                elements.append(Spacer(1, 0.2*inch))

                # Print date and ticket information
                print_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                ticket_no = record.get('ticket_no', '000')
                
                elements.append(Paragraph(f"Print Date: {print_date}", value_style))
                elements.append(Paragraph(f"Ticket No: {ticket_no}", header_style))
                elements.append(Spacer(1, 0.15*inch))

                # Vehicle Information
                elements.append(Paragraph("VEHICLE INFORMATION", section_header_style))
                
                # Get material from material_type field if material is empty
                material_value = record.get('material', '') or record.get('material_type', '')
                user_name_value = record.get('user_name', '') or "Not specified"
                site_incharge_value = record.get('site_incharge', '') or "Not specified"
                
                vehicle_data = [
                    [Paragraph("<b>Vehicle No:</b>", label_style), Paragraph(record.get('vehicle_no', ''), value_style), 
                    Paragraph("<b>Date:</b>", label_style), Paragraph(record.get('date', ''), value_style), 
                    Paragraph("<b>Time:</b>", label_style), Paragraph(record.get('time', ''), value_style)],
                    [Paragraph("<b>Material:</b>", label_style), Paragraph(material_value, value_style), 
                    Paragraph("<b>Site Name:</b>", label_style), Paragraph(record.get('site_name', ''), value_style), 
                    Paragraph("<b>Transfer Party:</b>", label_style), Paragraph(record.get('transfer_party_name', ''), value_style)],
                    [Paragraph("<b>Agency Name:</b>", label_style), Paragraph(record.get('agency_name', ''), value_style), 
                    Paragraph("<b>User Name:</b>", label_style), Paragraph(user_name_value, value_style), 
                    Paragraph("<b>Site Incharge:</b>", label_style), Paragraph(site_incharge_value, value_style)]
                ]
                
                vehicle_inner_table = Table(vehicle_data, colWidths=[1.2*inch, 1.3*inch, 1.0*inch, 1.3*inch, 1.2*inch, 1.5*inch])
                vehicle_inner_table.setStyle(TableStyle([
                    ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                    ('FONTSIZE', (0,0), (-1,-1), 13),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('LEFTPADDING', (0,0), (-1,-1), 2),
                    ('RIGHTPADDING', (0,0), (-1,-1), 2),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ]))
                
                vehicle_table = Table([[vehicle_inner_table]], colWidths=[7.5*inch])
                vehicle_table.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                    ('LEFTPADDING', (0,0), (-1,-1), 12),
                    ('RIGHTPADDING', (0,0), (-1,-1), 12),
                    ('TOPPADDING', (0,0), (-1,-1), 8),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ]))
                elements.append(vehicle_table)
                elements.append(Spacer(1, 0.15*inch))

                # Weighment Information
                elements.append(Paragraph("WEIGHMENT DETAILS", section_header_style))
                
                # Weighment Information with proper net weight calculation
                first_weight_str = record.get('first_weight', '').strip()
                second_weight_str = record.get('second_weight', '').strip()
                net_weight_str = record.get('net_weight', '').strip()
                
                # If net weight is empty but we have both weights, calculate it
                if not net_weight_str and first_weight_str and second_weight_str:
                    try:
                        first_weight = float(first_weight_str)
                        second_weight = float(second_weight_str)
                        calculated_net = abs(first_weight - second_weight)
                        net_weight_str = f"{calculated_net:.2f}"
                    except (ValueError, TypeError):
                        net_weight_str = "Calculation Error"
                
                # If still empty, show as not available
                if not net_weight_str:
                    net_weight_str = "Not Available"
                
                weighment_data = [
                    [Paragraph("<b>First Weight:</b>", label_style), Paragraph(f"{first_weight_str} kg" if first_weight_str else "Not captured", value_style), 
                    Paragraph("<b>First Time:</b>", label_style), Paragraph(record.get('first_timestamp', '') or "Not captured", value_style)],
                    [Paragraph("<b>Second Weight:</b>", label_style), Paragraph(f"{second_weight_str} kg" if second_weight_str else "Not captured", value_style), 
                    Paragraph("<b>Second Time:</b>", label_style), Paragraph(record.get('second_timestamp', '') or "Not captured", value_style)],
                    ["", "", Paragraph("<b>Net Weight:</b>", label_style), Paragraph(f"{net_weight_str} Kgs", 
                                    ParagraphStyle(name='NetWeightCorner', fontSize=14, fontName='Helvetica-Bold', textColor=colors.black))]
                ]
                
                weighment_inner_table = Table(weighment_data, colWidths=[1.5*inch, 1.5*inch, 1.2*inch, 2.8*inch])
                weighment_inner_table.setStyle(TableStyle([
                    ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                    ('FONTSIZE', (0,0), (-1,-1), 14),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('LEFTPADDING', (0,0), (-1,-1), 2),
                    ('RIGHTPADDING', (0,0), (-1,-1), 2),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                    ('SPAN', (2,2), (3,2)),
                    ('ALIGN', (2,2), (3,2), 'RIGHT'),
                ]))
                
                weighment_table = Table([[weighment_inner_table]], colWidths=[7.5*inch])
                weighment_table.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                    ('LEFTPADDING', (0,0), (-1,-1), 12),
                    ('RIGHTPADDING', (0,0), (-1,-1), 12),
                    ('TOPPADDING', (0,0), (-1,-1), 8),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ]))
                elements.append(weighment_table)
                elements.append(Spacer(1, 0.15*inch))

                # 4-Image Grid Section
                elements.append(Paragraph("VEHICLE IMAGES (4-Image System)", section_header_style))
                
                # Get all 4 image paths
                first_front_img_path = os.path.join(config.IMAGES_FOLDER, record.get('first_front_image', ''))
                first_back_img_path = os.path.join(config.IMAGES_FOLDER, record.get('first_back_image', ''))
                second_front_img_path = os.path.join(config.IMAGES_FOLDER, record.get('second_front_image', ''))
                second_back_img_path = os.path.join(config.IMAGES_FOLDER, record.get('second_back_image', ''))

                # Create 2x2 image grid with headers
                img_data = [
                    ["1ST WEIGHMENT - FRONT", "1ST WEIGHMENT - BACK"],
                    [None, None],  # Will be filled with first weighment images
                    ["2ND WEIGHMENT - FRONT", "2ND WEIGHMENT - BACK"], 
                    [None, None]   # Will be filled with second weighment images
                ]

                # Process all 4 images
                images = [
                    (first_front_img_path, f"Ticket: {ticket_no} - 1st Front"),
                    (first_back_img_path, f"Ticket: {ticket_no} - 1st Back"),
                    (second_front_img_path, f"Ticket: {ticket_no} - 2nd Front"),
                    (second_back_img_path, f"Ticket: {ticket_no} - 2nd Back")
                ]
                
                processed_images = []
                for img_path, watermark_text in images:
                    if os.path.exists(img_path):
                        try:
                            temp_img = self.prepare_image_for_pdf(img_path, watermark_text)
                            if temp_img:
                                processed_img = RLImage(temp_img, width=3.5*inch, height=2.0*inch)
                                processed_images.append(processed_img)
                                # Clean up temp file
                                try:
                                    os.remove(temp_img)
                                except:
                                    pass
                            else:
                                processed_images.append("Image not available")
                        except Exception as e:
                            print(f"Error processing image {img_path}: {e}")
                            processed_images.append("Image error")
                    else:
                        processed_images.append("Image not available")

                # Fill the image grid
                img_data[1] = [processed_images[0], processed_images[1]]  # First weighment
                img_data[3] = [processed_images[2], processed_images[3]]  # Second weighment

                # Create images table with 2x2 grid
                img_table = Table(img_data, colWidths=[3.5*inch, 3.5*inch], 
                                 rowHeights=[0.3*inch, 2*inch, 0.3*inch, 2*inch])
                img_table.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                    ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (1,0), 10),  # Header row 1
                    ('FONTSIZE', (0,2), (1,2), 10),  # Header row 2
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('RIGHTPADDING', (0,0), (-1,-1), 6),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    # Header background
                    ('BACKGROUND', (0,0), (1,0), colors.lightgrey),
                    ('BACKGROUND', (0,2), (1,2), colors.lightgrey),
                ]))
                elements.append(img_table)
                
                # Add operator signature line at bottom right
                elements.append(Spacer(1, 0.3*inch))
                
                signature_table = Table([["", "Operator's Signature"]], colWidths=[5*inch, 2.5*inch])
                signature_table.setStyle(TableStyle([
                    ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                    ('FONTSIZE', (0,0), (-1,-1), 11),
                    ('ALIGN', (1,0), (1,0), 'RIGHT'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ]))
                elements.append(signature_table)

            # Build the PDF
            doc.build(elements)
            return True
            
        except Exception as e:
            print(f"Error creating PDF report: {e}")
            return False
    
    def prepare_image_for_pdf(self, image_path, watermark_text):
        """Prepare image for PDF by resizing and adding watermark"""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            # Resize image for PDF (maintain aspect ratio)
            height, width = img.shape[:2]
            max_width = 400
            max_height = 300
            
            # Calculate scaling factor
            scale_w = max_width / width
            scale_h = max_height / height
            scale = min(scale_w, scale_h)
            
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            img_resized = cv2.resize(img, (new_width, new_height))
            
            # Add watermark
            from camera import add_watermark  # Import the watermark function
            watermarked_img = add_watermark(img_resized, watermark_text)
            
            # Save temporary file
            temp_filename = f"temp_pdf_image_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
            temp_path = os.path.join(config.IMAGES_FOLDER, temp_filename)
            
            cv2.imwrite(temp_path, watermarked_img)
            return temp_path
            
        except Exception as e:
            print(f"Error preparing image for PDF: {e}")
            return None

    def save_to_cloud(self, data):
        """Legacy method - now calls the new save_to_cloud_with_images method
        
        Args:
            data: Record data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        success, _, _ = self.save_to_cloud_with_images(data)
        return success


    def get_record_by_vehicle(self, vehicle_no):
        """Get a specific record by vehicle number
        
        Args:
            vehicle_no: Vehicle number to search for
            
        Returns:
            dict: Record as dictionary or None if not found
        """
        current_file = self.get_current_data_file()
        
        if not os.path.exists(current_file):
            return None
            
        try:
            with open(current_file, 'r', newline='') as csv_file:
                reader = csv.reader(csv_file)
                
                # Skip header
                next(reader, None)
                
                for row in reader:
                    if len(row) >= 7 and row[6] == vehicle_no:  # Vehicle number is index 6
                        record = {
                            'date': row[0],
                            'time': row[1],
                            'site_name': row[2],
                            'agency_name': row[3],
                            'material': row[4],
                            'ticket_no': row[5],
                            'vehicle_no': row[6],
                            'transfer_party_name': row[7],
                            'first_weight': row[8] if len(row) > 8 else '',
                            'first_timestamp': row[9] if len(row) > 9 else '',
                            'second_weight': row[10] if len(row) > 10 else '',
                            'second_timestamp': row[11] if len(row) > 11 else '',
                            'net_weight': row[12] if len(row) > 12 else '',
                            'material_type': row[13] if len(row) > 13 else '',
                            'front_image': row[14] if len(row) > 14 else '',
                            'back_image': row[15] if len(row) > 15 else ''
                        }
                        return record
                        
            return None
                
        except Exception as e:
            print(f"Error finding record: {e}")
            return None
    


    def backup_complete_records_to_cloud_with_reports(self):
        """Enhanced backup: records, images, and daily reports with incremental backup
        
        Returns:
            dict: Comprehensive backup results
        """
        try:
            import config  # Import config at the beginning
            
            # Initialize cloud storage if not already initialized
            if not hasattr(self, 'cloud_storage') or self.cloud_storage is None:
                from cloud_storage import CloudStorageService
                self.cloud_storage = CloudStorageService(
                    config.CLOUD_BUCKET_NAME,
                    config.CLOUD_CREDENTIALS_PATH
                )
            
            # Check if connected to cloud storage
            if not self.cloud_storage.is_connected():
                return {
                    "success": False,
                    "error": "Not connected to cloud storage",
                    "records_uploaded": 0,
                    "total_records": 0,
                    "images_uploaded": 0,
                    "total_images": 0,
                    "reports_uploaded": 0,
                    "total_reports": 0
                }
            
            # Get all records and filter for complete ones
            all_records = self.get_all_records()
            complete_records = []
            
            for record in all_records:
                first_weight = record.get('first_weight', '').strip()
                first_timestamp = record.get('first_timestamp', '').strip()
                second_weight = record.get('second_weight', '').strip()
                second_timestamp = record.get('second_timestamp', '').strip()
                
                if (first_weight and first_timestamp and second_weight and second_timestamp):
                    complete_records.append(record)
            
            print(f"Found {len(complete_records)} complete records out of {len(all_records)} total records")
            
            # Use comprehensive backup method
            results = self.cloud_storage.comprehensive_backup(
                complete_records, 
                config.IMAGES_FOLDER,
                "data/daily_reports"  # Daily reports folder
            )
            
            print(f"Backup completed:")
            print(f"  Records: {results['records_uploaded']}/{results['total_records']}")
            print(f"  Images: {results['images_uploaded']}/{results['total_images']}")
            print(f"  Daily Reports: {results['reports_uploaded']}/{results['total_reports']}")
            if results['errors']:
                print(f"  Errors: {len(results['errors'])}")
            
            return results
            
        except Exception as e:
            error_msg = f"Error during comprehensive backup: {str(e)}"
            print(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "records_uploaded": 0,
                "total_records": 0,
                "images_uploaded": 0,
                "total_images": 0,
                "reports_uploaded": 0,
                "total_reports": 0
            }

    def get_daily_reports_info(self):
        """Get information about today's daily reports
        
        Returns:
            dict: Daily reports information
        """
        try:
            import datetime
            import os
            
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            reports_folder = "data/daily_reports"
            today_reports_folder = os.path.join(reports_folder, today_str)
            
            info = {
                "date": today_str,
                "folder_exists": os.path.exists(today_reports_folder),
                "total_files": 0,
                "total_size": 0,
                "file_types": {}
            }
            
            if info["folder_exists"]:
                # Count files and calculate size
                for root, dirs, files in os.walk(today_reports_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.exists(file_path):
                            info["total_files"] += 1
                            info["total_size"] += os.path.getsize(file_path)
                            
                            # Track file types
                            ext = os.path.splitext(file)[1].lower()
                            info["file_types"][ext] = info["file_types"].get(ext, 0) + 1
                
                # Format size
                size_bytes = info["total_size"]
                if size_bytes < 1024:
                    info["total_size_formatted"] = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    info["total_size_formatted"] = f"{size_bytes / 1024:.1f} KB"
                else:
                    info["total_size_formatted"] = f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                info["total_size_formatted"] = "0 B"
            
            return info
            
        except Exception as e:
            print(f"Error getting daily reports info: {e}")
            return {
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "folder_exists": False,
                "total_files": 0,
                "total_size": 0,
                "total_size_formatted": "0 B",
                "file_types": {},
                "error": str(e)
            }

    def get_enhanced_cloud_upload_summary(self):
        """Get enhanced summary including daily reports
        
        Returns:
            dict: Enhanced upload summary
        """
        try:
            import config  # Import config at the beginning
            
            if not hasattr(self, 'cloud_storage') or self.cloud_storage is None:
                from cloud_storage import CloudStorageService
                self.cloud_storage = CloudStorageService(
                    config.CLOUD_BUCKET_NAME,
                    config.CLOUD_CREDENTIALS_PATH
                )
            
            if not self.cloud_storage.is_connected():
                return {"error": "Not connected to cloud storage"}
            
            # Get current agency and site for filtering
            agency_name = config.CURRENT_AGENCY or "Unknown_Agency"
            site_name = config.CURRENT_SITE or "Unknown_Site"
            
            # Clean names for filtering
            clean_agency = agency_name.replace(' ', '_').replace('/', '_')
            clean_site = site_name.replace(' ', '_').replace('/', '_')
            
            # Get summary for current agency/site
            prefix = f"{clean_agency}/{clean_site}/"
            summary = self.cloud_storage.get_upload_summary(prefix)
            
            # Add daily reports summary (no prefix filter for reports)
            reports_summary = self.cloud_storage.get_upload_summary("daily_reports/")
            
            # Combine summaries
            if "error" not in summary and "error" not in reports_summary:
                summary["daily_report_files"] = reports_summary.get("total_files", 0)
                summary["daily_reports_size"] = reports_summary.get("total_size", "0 B")
            
            # Add context information
            summary["agency"] = agency_name
            summary["site"] = site_name
            summary["context"] = f"{agency_name} - {site_name}"
            
            # Add today's reports info
            daily_reports_info = self.get_daily_reports_info()
            summary["todays_reports"] = daily_reports_info
            
            return summary
            
        except Exception as e:
            return {"error": f"Error getting enhanced cloud summary: {str(e)}"}

    # Update the existing backup_complete_records_to_cloud method to use the new enhanced version
    def backup_complete_records_to_cloud(self):
        """Legacy method - now calls enhanced backup with reports
        
        Returns:
            tuple: (success_count, total_complete_records, images_uploaded, total_images) for backward compatibility
        """
        try:
            # Use the enhanced backup method
            results = self.backup_complete_records_to_cloud_with_reports()
            
            # Return in the old format for backward compatibility
            return (
                results.get("records_uploaded", 0),
                results.get("total_records", 0), 
                results.get("images_uploaded", 0),
                results.get("total_images", 0)
            )
            
        except Exception as e:
            print(f"Error in legacy backup method: {e}")
            return 0, 0, 0, 0



    def get_cloud_upload_summary(self):
        """Get summary of files uploaded to cloud storage
        
        Returns:
            dict: Upload summary with statistics
        """
        try:
            if not hasattr(self, 'cloud_storage') or self.cloud_storage is None:
                self.cloud_storage = CloudStorageService(
                    config.CLOUD_BUCKET_NAME,
                    config.CLOUD_CREDENTIALS_PATH
                )
            
            if not self.cloud_storage.is_connected():
                return {"error": "Not connected to cloud storage"}
            
            # Get current agency and site for filtering
            agency_name = config.CURRENT_AGENCY or "Unknown_Agency"
            site_name = config.CURRENT_SITE or "Unknown_Site"
            
            # Clean names for filtering
            clean_agency = agency_name.replace(' ', '_').replace('/', '_')
            clean_site = site_name.replace(' ', '_').replace('/', '_')
            
            # Get summary for current agency/site
            prefix = f"{clean_agency}/{clean_site}/"
            summary = self.cloud_storage.get_upload_summary(prefix)
            
            # Add context information
            summary["agency"] = agency_name
            summary["site"] = site_name
            summary["context"] = f"{agency_name} - {site_name}"
            
            return summary
            
        except Exception as e:
            return {"error": f"Error getting cloud summary: {str(e)}"}
    
    def validate_record(self, data):
        """Validate record data
        
        Args:
            data: Record data
            
        Returns:
            tuple: (is_valid, error_message)
        """
        required_fields = {
            "Ticket No": data.get('ticket_no', ''),
            "Vehicle No": data.get('vehicle_no', ''),
            "Agency Name": data.get('agency_name', '')
        }
        
        missing_fields = [field for field, value in required_fields.items() 
                         if not str(value).strip()]
        
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Check if we have at least the first weighment for a new entry
        if not data.get('first_weight', '').strip():
            return False, "First weighment is required"
            
        # Validate images if specified in validation
        front_image = data.get('front_image', '')
        back_image = data.get('back_image', '')
        
        if not front_image and not back_image:
            return False, "No images captured"
            
        return True, ""

    def cleanup_orphaned_images(self):
        """Clean up image files that are not referenced in any records
        
        Returns:
            tuple: (cleaned_files, total_size_freed)
        """
        try:
            # Get all records
            all_records = self.get_all_records()
            
            # Collect all referenced image filenames
            referenced_images = set()
            for record in all_records:
                front_image = record.get('front_image', '').strip()
                back_image = record.get('back_image', '').strip()
                
                if front_image:
                    referenced_images.add(front_image)
                if back_image:
                    referenced_images.add(back_image)
            
            # Get all image files in the images folder
            if not os.path.exists(config.IMAGES_FOLDER):
                return 0, 0
            
            all_image_files = [f for f in os.listdir(config.IMAGES_FOLDER) 
                             if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))]
            
            # Find orphaned images
            orphaned_images = []
            for image_file in all_image_files:
                if image_file not in referenced_images:
                    orphaned_images.append(image_file)
            
            # Clean up orphaned images
            cleaned_files = 0
            total_size_freed = 0
            
            for image_file in orphaned_images:
                image_path = os.path.join(config.IMAGES_FOLDER, image_file)
                if os.path.exists(image_path):
                    try:
                        # Get file size before deletion
                        file_size = os.path.getsize(image_path)
                        
                        # Delete the file
                        os.remove(image_path)
                        
                        cleaned_files += 1
                        total_size_freed += file_size
                        
                        print(f"Cleaned up orphaned image: {image_file}")
                        
                    except Exception as e:
                        print(f"Error cleaning up {image_file}: {e}")
            
            return cleaned_files, total_size_freed
            
        except Exception as e:
            print(f"Error during image cleanup: {e}")
            return 0, 0