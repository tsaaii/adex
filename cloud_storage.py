import os
import json
import datetime
from google.cloud import storage
from google.api_core.exceptions import Forbidden, NotFound

class CloudStorageService:
    """Service for Google Cloud Storage operations"""
    
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
            
        except Exception as e:
            print(f"Error initializing cloud storage: {e}")
            self.client = None
            self.bucket = None
    
    def is_connected(self):
        """Check if connected to cloud storage"""
        return self.client is not None and self.bucket is not None
    
    def save_json(self, data, filename):
        """Save data as JSON to cloud storage
        
        Args:
            data: Data to save
            filename: Filename to save as
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            return False
            
        try:
            # Create folder structure if filename includes folders
            if '/' in filename:
                folder = os.path.dirname(filename)
                if folder:
                    # Create an empty object with folder name ending with slash
                    folder_blob = self.bucket.blob(f"{folder}/")
                    if not folder_blob.exists():
                        folder_blob.upload_from_string('', content_type='application/x-directory')
            
            # Convert data to JSON
            json_data = json.dumps(data, indent=4)
            
            # Create or update blob
            blob = self.bucket.blob(filename)
            
            # Upload with appropriate content type
            blob.upload_from_string(json_data, content_type="application/json")
            
            print(f"Saved {filename} to cloud storage")
            return True
            
        except Exception as e:
            print(f"Error saving to cloud storage: {str(e)}")
            return False
    
    def upload_image(self, local_image_path, cloud_filename):
        """Upload an image file to cloud storage
        
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
            
            print(f"Uploaded image {local_image_path} to cloud storage as {cloud_filename}")
            return True
            
        except Exception as e:
            print(f"Error uploading image to cloud storage: {str(e)}")
            return False
    
    def upload_record_with_images(self, record_data, json_filename, images_folder_path):
        """Upload a complete record with JSON data and associated images
        
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
        
        # Check for front and back images
        front_image = record_data.get('front_image', '')
        back_image = record_data.get('back_image', '')
        
        for image_type, image_filename in [('front', front_image), ('back', back_image)]:
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
        """Get a summary of uploaded files
        
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