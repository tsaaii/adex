import os
import csv
import pandas as pd
import datetime
from tkinter import messagebox, filedialog
import config
import json
from cloud_storage import CloudStorageService


class DataManager:
    """Class for managing data operations with the CSV file"""
    
    def __init__(self):
        """Initialize data manager"""
        self.data_file = config.DATA_FILE
        self.initialize_new_csv_structure()
        
    def initialize_new_csv_structure(self):
        """Update CSV structure to include weighment fields if needed"""
        if not os.path.exists(self.data_file):
            # Create new file with updated header
            with open(self.data_file, 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(config.CSV_HEADER)
            return
            
        try:
            # Check if existing file has the new structure
            with open(self.data_file, 'r', newline='') as csv_file:
                reader = csv.reader(csv_file)
                header = next(reader, None)
                
                # Check if our new fields exist in the header
                if header and all(field in header for field in ['First Weight', 'First Timestamp', 'Second Weight', 'Second Timestamp']):
                    # Structure is already updated
                    return
                    
                # Need to migrate old data to new structure
                data = list(reader)  # Read all existing data
            
            # Create backup of old file
            backup_file = f"{self.data_file}.backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(self.data_file, backup_file)
            
            # Create new file with updated structure
            with open(self.data_file, 'w', newline='') as csv_file:
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
                            row[12] if len(row) > 12 else "",  # Front Image
                            row[13] if len(row) > 13 else ""   # Back Image
                        ]
                        writer.writerow(new_row)
                        
            messagebox.showinfo("Database Updated", 
                             "The data structure has been updated to support the new weighment system.\n"
                             f"A backup of your old data has been saved to {backup_file}")
                             
        except Exception as e:
            messagebox.showerror("Database Update Error", 
                              f"Error updating database structure: {e}\n"
                              "The application may not function correctly.")
            

    def save_to_cloud(self, data):
        """Save record as JSON to Google Cloud Storage only if both weighments are complete
        
        Args:
            data: Record data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if both weighments are complete before saving to cloud
            first_weight = data.get('first_weight', '').strip()
            first_timestamp = data.get('first_timestamp', '').strip()
            second_weight = data.get('second_weight', '').strip()
            second_timestamp = data.get('second_timestamp', '').strip()
            
            # Only save to cloud if both weighments are complete
            if not (first_weight and first_timestamp and second_weight and second_timestamp):
                print(f"Skipping cloud save for ticket {data.get('ticket_no', 'unknown')} - incomplete weighments")
                return False
            
            # Initialize cloud storage if not already initialized
            if not hasattr(self, 'cloud_storage') or self.cloud_storage is None:
                self.cloud_storage = CloudStorageService(
                    config.CLOUD_BUCKET_NAME,
                    config.CLOUD_CREDENTIALS_PATH
                )
            
            # Check if connected to cloud storage
            if not self.cloud_storage.is_connected():
                print("Not connected to cloud storage")
                return False
            
            # Get site name and ticket number for folder structure
            site_name = data.get('site_name', 'Unknown_Site').replace(' ', '_').replace('/', '_')
            ticket_no = data.get('ticket_no', 'unknown')
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create structured filename: site_name/ticket_number/timestamp.json
            filename = f"{site_name}/{ticket_no}/{timestamp}.json"
            
            # Add some additional metadata to the JSON
            enhanced_data = data.copy()
            enhanced_data['cloud_upload_timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            enhanced_data['record_status'] = 'complete'  # Mark as complete record
            enhanced_data['net_weight_calculated'] = self._calculate_net_weight_for_cloud(
                enhanced_data.get('first_weight', ''), 
                enhanced_data.get('second_weight', '')
            )
            
            # Save to cloud storage
            success = self.cloud_storage.save_json(enhanced_data, filename)
            
            if success:
                print(f"Record {ticket_no} successfully saved to cloud at {filename}")
            else:
                print(f"Failed to save record {ticket_no} to cloud")
                
            return success
            
        except Exception as e:
            print(f"Error saving to cloud: {str(e)}")
            return False

    def _calculate_net_weight_for_cloud(self, first_weight_str, second_weight_str):
        """Calculate net weight for cloud storage
        
        Args:
            first_weight_str: First weight as string
            second_weight_str: Second weight as string
            
        Returns:
            float: Net weight or 0 if calculation fails
        """
        try:
            if first_weight_str and second_weight_str:
                first_weight = float(first_weight_str)
                second_weight = float(second_weight_str)
                return abs(first_weight - second_weight)
            return 0.0
        except (ValueError, TypeError):
            return 0.0

    def save_record(self, data):
        """Save record to CSV file and cloud storage (only for complete records)
        
        Args:
            data: Dictionary of data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if this is an update to an existing record
            ticket_no = data.get('ticket_no', '')
            is_update = False
            
            if ticket_no:
                # Check if record with this ticket number exists
                records = self.get_filtered_records(ticket_no)
                for record in records:
                    if record.get('ticket_no') == ticket_no:
                        is_update = True
                        break
            
            # Save to CSV as before
            csv_success = False
            if is_update:
                # Update existing record
                csv_success = self.update_record(data)
            else:
                # Add new record
                csv_success = self.add_new_record(data)
            
            # Check if this is a complete record (both weighments)
            first_weight = data.get('first_weight', '').strip()
            first_timestamp = data.get('first_timestamp', '').strip()
            second_weight = data.get('second_weight', '').strip()
            second_timestamp = data.get('second_timestamp', '').strip()
            
            is_complete_record = (first_weight and first_timestamp and 
                                second_weight and second_timestamp)
            
            # Only save to cloud storage if enabled AND record is complete
            cloud_success = False
            if (hasattr(config, 'USE_CLOUD_STORAGE') and config.USE_CLOUD_STORAGE and 
                is_complete_record):
                cloud_success = self.save_to_cloud(data)
                
                if cloud_success:
                    print(f"Complete record {ticket_no} successfully saved to cloud")
                else:
                    print(f"Warning: Complete record {ticket_no} could not be saved to cloud")
            elif not is_complete_record:
                print(f"Record {ticket_no} saved locally only - incomplete weighments")
            
            # Return overall success (CSV is the primary storage)
            return csv_success
                    
        except Exception as e:
            print(f"Error saving record: {e}")
            return False

    def backup_complete_records_to_cloud(self):
        """Backup all complete records to cloud storage organized by site
        
        Returns:
            tuple: (success_count, total_complete_records)
        """
        try:
            # Initialize cloud storage if not already initialized
            if not hasattr(self, 'cloud_storage') or self.cloud_storage is None:
                self.cloud_storage = CloudStorageService(
                    config.CLOUD_BUCKET_NAME,
                    config.CLOUD_CREDENTIALS_PATH
                )
            
            # Check if connected to cloud storage
            if not self.cloud_storage.is_connected():
                print("Not connected to cloud storage")
                return 0, 0
            
            # Get all records
            all_records = self.get_all_records()
            
            # Filter for complete records only
            complete_records = []
            for record in all_records:
                first_weight = record.get('first_weight', '').strip()
                first_timestamp = record.get('first_timestamp', '').strip()
                second_weight = record.get('second_weight', '').strip()
                second_timestamp = record.get('second_timestamp', '').strip()
                
                if (first_weight and first_timestamp and second_weight and second_timestamp):
                    complete_records.append(record)
            
            print(f"Found {len(complete_records)} complete records out of {len(all_records)} total records")
            
            # Upload complete records to cloud
            success_count = 0
            for record in complete_records:
                if self.save_to_cloud(record):
                    success_count += 1
            
            print(f"Successfully uploaded {success_count} out of {len(complete_records)} complete records to cloud")
            return success_count, len(complete_records)
            
        except Exception as e:
            print(f"Error during cloud backup: {str(e)}")
            return 0, 0    

    
    def add_new_record(self, data):
        """Add a new record to the CSV file
        
        Args:
            data: Dictionary of data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Format data as a row
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
                data.get('front_image', ''),
                data.get('back_image', ''),
                data.get('site_incharge', ''),  # New field
                data.get('user_name', '')       # New field
            ]
            
            # Write to CSV
            with open(self.data_file, 'a', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(record)
                
            return True
            
        except Exception as e:
            print(f"Error adding new record: {e}")
            return False

    def update_record(self, data):
        """Update an existing record in the CSV file
        
        Args:
            data: Dictionary of data to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Read all records
            all_records = []
            with open(self.data_file, 'r', newline='') as csv_file:
                reader = csv.reader(csv_file)
                header = next(reader)  # Skip header
                all_records = list(reader)
            
            # Find and update the record
            ticket_no = data.get('ticket_no', '')
            updated = False
            
            for i, row in enumerate(all_records):
                if len(row) >= 6 and row[5] == ticket_no:  # Ticket number is index 5
                    # Update the row with new data
                    # Keep original date/time if not provided
                    updated_row = [
                        data.get('date', row[0]),
                        data.get('time', row[1]),
                        data.get('site_name', row[2]),
                        data.get('agency_name', row[3]),
                        data.get('material', row[4]),
                        data.get('ticket_no', row[5]),
                        data.get('vehicle_no', row[6]),
                        data.get('transfer_party_name', row[7]),
                        data.get('first_weight', row[8] if len(row) > 8 else ''),
                        data.get('first_timestamp', row[9] if len(row) > 9 else ''),
                        data.get('second_weight', row[10] if len(row) > 10 else ''),
                        data.get('second_timestamp', row[11] if len(row) > 11 else ''),
                        data.get('net_weight', row[12] if len(row) > 12 else ''),
                        data.get('material_type', row[13] if len(row) > 13 else ''),
                        data.get('front_image', row[14] if len(row) > 14 else ''),
                        data.get('back_image', row[15] if len(row) > 15 else ''),
                        data.get('site_incharge', row[16] if len(row) > 16 else ''),  # New field
                        data.get('user_name', row[17] if len(row) > 17 else '')       # New field
                    ]
                    
                    # Handle shorter rows by extending them to the expected length
                    if len(updated_row) > len(row):
                        all_records[i] = updated_row
                    else:
                        all_records[i] = updated_row + [''] * (len(header) - len(updated_row))
                    
                    updated = True
                    break
            
            if not updated:
                return False
                
            # Write all records back to the file
            with open(self.data_file, 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(header)  # Write header
                writer.writerows(all_records)  # Write all records
                
            return True
                
        except Exception as e:
            print(f"Error updating record: {e}")
            return False

    def get_all_records(self):
        """Get all records from CSV file
        
        Returns:
            list: List of records as dictionaries
        """
        records = []
        
        if not os.path.exists(self.data_file):
            return records
            
        try:
            with open(self.data_file, 'r', newline='') as csv_file:
                reader = csv.reader(csv_file)
                
                # Skip header
                header = next(reader, None)
                
                for row in reader:
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
                            'front_image': row[14] if len(row) > 14 else '',
                            'back_image': row[15] if len(row) > 15 else '',
                            'site_incharge': row[16] if len(row) > 16 else '',  # New field
                            'user_name': row[17] if len(row) > 17 else ''       # New field
                        }
                        records.append(record)
                        
            return records
                
        except Exception as e:
            print(f"Error reading records: {e}")
            return []
    
    def get_record_by_vehicle(self, vehicle_no):
        """Get a specific record by vehicle number
        
        Args:
            vehicle_no: Vehicle number to search for
            
        Returns:
            dict: Record as dictionary or None if not found
        """
        if not os.path.exists(self.data_file):
            return None
            
        try:
            with open(self.data_file, 'r', newline='') as csv_file:
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
    
    def get_filtered_records(self, filter_text=""):
        """Get records filtered by text
        
        Args:
            filter_text: Text to filter records by
            
        Returns:
            list: Filtered records
        """
        all_records = self.get_all_records()
        
        if not filter_text:
            return all_records
            
        filter_text = filter_text.lower()
        filtered_records = []
        
        for record in all_records:
            # Check if filter text exists in any field
            if any(filter_text in str(value).lower() for value in record.values()):
                filtered_records.append(record)
                
        return filtered_records
    
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