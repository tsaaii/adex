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