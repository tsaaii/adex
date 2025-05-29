import os
import json
import datetime
from google.cloud import storage
from google.api_core.exceptions import Forbidden, NotFound

class CloudStorageService:
    """Enhanced service for Google Cloud Storage operations with daily reports backup"""
    
    def __init__(self, bucket_name, credentials_path=None):
        """Initialize cloud storage service
        
        Args:
            bucket_name (str): Name of the Google Cloud Storage bucket
            credentials_path (str, optional): Path to the service account key file
        """
        try:
            # Set credentials path as environment variable if provided
            if credentials_path:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            
            # Initialize client
            self.client = storage.Client()
            
            # Get bucket - don't check if it exists to avoid permission issues
            self.bucket = self.client.bucket(bucket_name)
            
            # Test connection with a simple operation
            try:
                # Try to list blobs (limited to 1) to test permissions
                next(self.bucket.list_blobs(max_results=1), None)
                print(f"Successfully connected to GCS bucket: {bucket_name}")
            except Forbidden as e:
                print(f"Permission error: {e}")
                print(f"Make sure the service account has 'Storage Object Admin' role for bucket {bucket_name}")
                self.bucket = None
            except NotFound:
                # Bucket doesn't exist, try to create it
                try:
                    self.bucket = self.client.create_bucket(bucket_name)
                    print(f"Created new bucket: {bucket_name}")
                except Exception as create_err:
                    print(f"Cannot create bucket: {create_err}")
                    self.bucket = None
            
            # Initialize backup tracking file path
            self.backup_tracking_file = "data/backup_tracking.json"
            
        except Exception as e:
            print(f"Error initializing cloud storage: {e}")
            self.client = None
            self.bucket = None
    
    def is_connected(self):
        """Check if connected to cloud storage"""
        return self.client is not None and self.bucket is not None
    
    def get_backup_tracking_data(self):
        """Get backup tracking data from local file
        
        Returns:
            dict: Tracking data with last backup timestamps and file hashes
        """
        try:
            if os.path.exists(self.backup_tracking_file):
                with open(self.backup_tracking_file, 'r') as f:
                    return json.load(f)
            else:
                return {
                    "last_backup_date": "",
                    "backed_up_files": {},
                    "daily_reports_backed_up": {}
                }
        except Exception as e:
            print(f"Error reading backup tracking: {e}")
            return {
                "last_backup_date": "",
                "backed_up_files": {},
                "daily_reports_backed_up": {}
            }
    
    def save_backup_tracking_data(self, tracking_data):
        """Save backup tracking data to local file
        
        Args:
            tracking_data (dict): Tracking data to save
        """
        try:
            os.makedirs(os.path.dirname(self.backup_tracking_file), exist_ok=True)
            with open(self.backup_tracking_file, 'w') as f:
                json.dump(tracking_data, f, indent=4)
        except Exception as e:
            print(f"Error saving backup tracking: {e}")
    
    def get_file_hash(self, file_path):
        """Get hash of a file for change detection
        
        Args:
            file_path (str): Path to file
            
        Returns:
            str: File hash or empty string if error
        """
        try:
            import hashlib
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"Error getting file hash for {file_path}: {e}")
            return ""
    
    def backup_daily_reports(self, reports_folder="data/daily_reports"):
        """Backup today's daily reports folder with incremental backup
        
        Args:
            reports_folder (str): Path to daily reports folder
            
        Returns:
            tuple: (files_uploaded, total_files_found, errors)
        """
        if not self.is_connected():
            return 0, 0, ["Not connected to cloud storage"]
        
        try:
            # Get today's date folder
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            today_reports_folder = os.path.join(reports_folder, today_str)
            
            if not os.path.exists(today_reports_folder):
                print(f"No daily reports folder found for today: {today_reports_folder}")
                return 0, 0, [f"No reports folder for {today_str}"]
            
            # Get backup tracking data
            tracking_data = self.get_backup_tracking_data()
            daily_reports_tracking = tracking_data.get("daily_reports_backed_up", {})
            
            files_uploaded = 0
            total_files_found = 0
            errors = []
            
            # Walk through today's reports folder
            for root, dirs, files in os.walk(today_reports_folder):
                for file in files:
                    total_files_found += 1
                    local_file_path = os.path.join(root, file)
                    
                    # Create relative path for cloud storage
                    rel_path = os.path.relpath(local_file_path, reports_folder)
                    cloud_path = f"daily_reports/{rel_path.replace(os.sep, '/')}"
                    
                    # Check if file needs backup (new or changed)
                    current_hash = self.get_file_hash(local_file_path)
                    
                    # Check tracking data
                    if (cloud_path in daily_reports_tracking and 
                        daily_reports_tracking[cloud_path].get("hash") == current_hash):
                        print(f"Skipping unchanged file: {file}")
                        continue
                    
                    # Upload file
                    try:
                        blob = self.bucket.blob(cloud_path)
                        blob.upload_from_filename(local_file_path)
                        
                        # Update tracking
                        daily_reports_tracking[cloud_path] = {
                            "hash": current_hash,
                            "upload_date": datetime.datetime.now().isoformat(),
                            "local_path": local_file_path
                        }
                        
                        files_uploaded += 1
                        print(f"Uploaded daily report: {cloud_path}")
                        
                    except Exception as e:
                        error_msg = f"Error uploading {file}: {str(e)}"
                        errors.append(error_msg)
                        print(error_msg)
            
            # Save updated tracking data
            tracking_data["daily_reports_backed_up"] = daily_reports_tracking
            tracking_data["last_backup_date"] = datetime.datetime.now().isoformat()
            self.save_backup_tracking_data(tracking_data)
            
            return files_uploaded, total_files_found, errors
            
        except Exception as e:
            error_msg = f"Error backing up daily reports: {str(e)}"
            return 0, 0, [error_msg]
    
    def save_json(self, data, filename):
        """Save data as JSON to cloud storage with incremental backup
        
        Args:
            data: Data to save
            filename: Filename to save as
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            return False
            
        try:
            # Get backup tracking data
            tracking_data = self.get_backup_tracking_data()
            backed_up_files = tracking_data.get("backed_up_files", {})
            
            # Create temporary local file to get hash
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(data, temp_file, indent=4)
                temp_path = temp_file.name
            
            # Get file hash
            current_hash = self.get_file_hash(temp_path)
            
            # Check if file needs upload (new or changed)
            if (filename in backed_up_files and 
                backed_up_files[filename].get("hash") == current_hash):
                print(f"Skipping unchanged JSON: {filename}")
                os.unlink(temp_path)  # Clean up temp file
                return True
            
            # Create folder structure if filename includes folders
            if '/' in filename:
                folder = os.path.dirname(filename)
                if folder:
                    # Create an empty object with folder name ending with slash
                    folder_blob = self.bucket.blob(f"{folder}/")
                    if not folder_blob.exists():
                        folder_blob.upload_from_string('', content_type='application/x-directory')
            
            # Upload with appropriate content type
            blob = self.bucket.blob(filename)
            blob.upload_from_filename(temp_path, content_type="application/json")
            
            # Update tracking
            backed_up_files[filename] = {
                "hash": current_hash,
                "upload_date": datetime.datetime.now().isoformat(),
                "type": "json"
            }
            
            # Save tracking data
            tracking_data["backed_up_files"] = backed_up_files
            self.save_backup_tracking_data(tracking_data)
            
            # Clean up temp file
            os.unlink(temp_path)
            
            print(f"Saved {filename} to cloud storage")
            return True
            
        except Exception as e:
            print(f"Error saving to cloud storage: {str(e)}")
            return False
    
    def upload_image(self, local_image_path, cloud_filename):
        """Upload an image file to cloud storage with incremental backup
        
        Args:
            local_image_path (str): Local path to the image file
            cloud_filename (str): Filename/path to save in cloud storage
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            print("Not connected to cloud storage")
            return False
            
        if not os.path.exists(local_image_path):
            print(f"Local image file not found: {local_image_path}")
            return False
            
        try:
            # Get backup tracking data
            tracking_data = self.get_backup_tracking_data()
            backed_up_files = tracking_data.get("backed_up_files", {})
            
            # Get file hash
            current_hash = self.get_file_hash(local_image_path)
            
            # Check if file needs upload (new or changed)
            if (cloud_filename in backed_up_files and 
                backed_up_files[cloud_filename].get("hash") == current_hash):
                print(f"Skipping unchanged image: {cloud_filename}")
                return True
            
            # Create folder structure if filename includes folders
            if '/' in cloud_filename:
                folder = os.path.dirname(cloud_filename)
                if folder:
                    # Create an empty object with folder name ending with slash
                    folder_blob = self.bucket.blob(f"{folder}/")
                    if not folder_blob.exists():
                        folder_blob.upload_from_string('', content_type='application/x-directory')
            
            # Create blob for the image
            blob = self.bucket.blob(cloud_filename)
            
            # Determine content type based on file extension
            file_extension = os.path.splitext(local_image_path)[1].lower()
            content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.webp': 'image/webp'
            }
            content_type = content_type_map.get(file_extension, 'image/jpeg')
            
            # Upload the image file
            blob.upload_from_filename(local_image_path, content_type=content_type)
            
            # Update tracking
            backed_up_files[cloud_filename] = {
                "hash": current_hash,
                "upload_date": datetime.datetime.now().isoformat(),
                "type": "image",
                "local_path": local_image_path
            }
            
            # Save tracking data
            tracking_data["backed_up_files"] = backed_up_files
            self.save_backup_tracking_data(tracking_data)
            
            print(f"Uploaded image {local_image_path} to cloud storage as {cloud_filename}")
            return True
            
        except Exception as e:
            print(f"Error uploading image to cloud storage: {str(e)}")
            return False
    
    def upload_record_with_images(self, record_data, json_filename, images_folder_path):
        """Upload a complete record with JSON data and associated images using incremental backup
        
        Args:
            record_data (dict): Record data to save as JSON
            json_filename (str): Cloud path for JSON file
            images_folder_path (str): Local folder path containing images
            
        Returns:
            tuple: (json_success, images_uploaded, total_images)
        """
        if not self.is_connected():
            return False, 0, 0
            
        # First, upload the JSON data
        json_success = self.save_json(record_data, json_filename)
        
        if not json_success:
            print("Failed to upload JSON data, skipping images")
            return False, 0, 0
        
        # Extract the base folder from json filename for images
        json_folder = os.path.dirname(json_filename)
        
        # Upload associated images
        images_uploaded = 0
        total_images = 0
        
        # Check for all 4 image types
        image_types = [
            ('first_front', record_data.get('first_front_image', '')),
            ('first_back', record_data.get('first_back_image', '')),
            ('second_front', record_data.get('second_front_image', '')),
            ('second_back', record_data.get('second_back_image', ''))
        ]
        
        for image_type, image_filename in image_types:
            if image_filename:
                total_images += 1
                local_image_path = os.path.join(images_folder_path, image_filename)
                
                if os.path.exists(local_image_path):
                    # Create cloud path for image: same folder as JSON + images subfolder
                    cloud_image_path = f"{json_folder}/images/{image_filename}"
                    
                    if self.upload_image(local_image_path, cloud_image_path):
                        images_uploaded += 1
                        # Add cloud path to record data for reference
                        record_data[f'{image_type}_image_cloud_path'] = cloud_image_path
                    else:
                        print(f"Failed to upload {image_type} image: {image_filename}")
                else:
                    print(f"Local {image_type} image not found: {local_image_path}")
        
        # Update JSON with cloud image paths if any images were uploaded
        if images_uploaded > 0:
            # Re-upload JSON with updated cloud paths
            self.save_json(record_data, json_filename)
            print(f"Updated JSON with cloud image paths")
        
        return json_success, images_uploaded, total_images
    
    def comprehensive_backup(self, complete_records, images_folder, reports_folder="data/daily_reports"):
        """Perform comprehensive backup of records, images, and daily reports
        
        Args:
            complete_records (list): List of complete record data
            images_folder (str): Path to images folder
            reports_folder (str): Path to daily reports folder
            
        Returns:
            dict: Comprehensive backup results
        """
        if not self.is_connected():
            return {
                "success": False,
                "error": "Not connected to cloud storage",
                "records": 0,
                "images": 0,
                "reports": 0
            }
        
        results = {
            "success": True,
            "records_uploaded": 0,
            "total_records": len(complete_records),
            "images_uploaded": 0,
            "total_images": 0,
            "reports_uploaded": 0,
            "total_reports": 0,
            "errors": []
        }
        
        # 1. Backup complete records with images
        print("Starting backup of complete records...")
        for record in complete_records:
            try:
                agency_name = record.get('agency_name', 'Unknown_Agency').replace(' ', '_').replace('/', '_')
                site_name = record.get('site_name', 'Unknown_Site').replace(' ', '_').replace('/', '_')
                ticket_no = record.get('ticket_no', 'unknown')
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                json_filename = f"{agency_name}/{site_name}/{ticket_no}/{timestamp}.json"
                
                json_success, images_uploaded, total_images = self.upload_record_with_images(
                    record, json_filename, images_folder
                )
                
                if json_success:
                    results["records_uploaded"] += 1
                    results["images_uploaded"] += images_uploaded
                    results["total_images"] += total_images
                else:
                    results["errors"].append(f"Failed to upload record {ticket_no}")
                    
            except Exception as e:
                error_msg = f"Error uploading record {record.get('ticket_no', 'unknown')}: {str(e)}"
                results["errors"].append(error_msg)
                print(error_msg)
        
        # 2. Backup daily reports
        print("Starting backup of daily reports...")
        try:
            reports_uploaded, total_reports, report_errors = self.backup_daily_reports(reports_folder)
            results["reports_uploaded"] = reports_uploaded
            results["total_reports"] = total_reports
            results["errors"].extend(report_errors)
            
        except Exception as e:
            error_msg = f"Error during daily reports backup: {str(e)}"
            results["errors"].append(error_msg)
            print(error_msg)
        
        # 3. Final status
        if results["errors"]:
            results["success"] = len(results["errors"]) < (results["total_records"] + results["total_reports"])
        
        return results
    
    # ... (keep all existing methods like check_file_exists, list_files, get_upload_summary, delete_file unchanged)
    
    def check_file_exists(self, cloud_filename):
        """Check if a file exists in cloud storage
        
        Args:
            cloud_filename (str): Cloud storage filename to check
            
        Returns:
            bool: True if file exists, False otherwise
        """
        if not self.is_connected():
            return False
            
        try:
            blob = self.bucket.blob(cloud_filename)
            return blob.exists()
        except Exception as e:
            print(f"Error checking file existence: {str(e)}")
            return False
    
    def list_files(self, prefix=None):
        """List files in the bucket with optional prefix
        
        Args:
            prefix (str, optional): Prefix to filter files by
            
        Returns:
            list: List of filenames
        """
        if not self.is_connected():
            return []
            
        try:
            blobs = self.client.list_blobs(self.bucket, prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            print(f"Error listing files: {str(e)}")
            return []

    def get_upload_summary(self, prefix=None):
        """Get a summary of uploaded files with daily reports info
        
        Args:
            prefix (str, optional): Prefix to filter files by
            
        Returns:
            dict: Summary with file counts and sizes
        """
        if not self.is_connected():
            return {"error": "Not connected to cloud storage"}
            
        try:
            blobs = list(self.client.list_blobs(self.bucket, prefix=prefix))
            
            summary = {
                "total_files": len(blobs),
                "json_files": 0,
                "image_files": 0,
                "daily_report_files": 0,
                "total_size_bytes": 0,
                "last_upload": None
            }
            
            latest_time = None
            
            for blob in blobs:
                summary["total_size_bytes"] += blob.size or 0
                
                # Track latest upload time
                if blob.time_created:
                    if latest_time is None or blob.time_created > latest_time:
                        latest_time = blob.time_created
                
                # Categorize files
                if blob.name.endswith('.json'):
                    summary["json_files"] += 1
                elif any(blob.name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
                    summary["image_files"] += 1
                elif blob.name.startswith('daily_reports/'):
                    summary["daily_report_files"] += 1
            
            if latest_time:
                summary["last_upload"] = latest_time.strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Convert size to human readable format
            size_bytes = summary["total_size_bytes"]
            if size_bytes < 1024:
                summary["total_size"] = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                summary["total_size"] = f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                summary["total_size"] = f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                summary["total_size"] = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
            
            return summary
            
        except Exception as e:
            return {"error": f"Error getting upload summary: {str(e)}"}
    
    def delete_file(self, cloud_filename):
        """Delete a file from cloud storage
        
        Args:
            cloud_filename (str): Cloud storage filename to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            return False
            
        try:
            blob = self.bucket.blob(cloud_filename)
            if blob.exists():
                blob.delete()
                print(f"Deleted {cloud_filename} from cloud storage")
                return True
            else:
                print(f"File not found in cloud storage: {cloud_filename}")
                return False
        except Exception as e:
            print(f"Error deleting file from cloud storage: {str(e)}")
            return False