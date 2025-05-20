
from cloud_storage import CloudStorageService
import config
import datetime
    
    # Create test data
test_data = {
        'test': True,
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'message': "This is a test"
    }
    
    # Initialize cloud storage
cloud_storage = CloudStorageService(
        config.CLOUD_BUCKET_NAME,
        config.CLOUD_CREDENTIALS_PATH
    )
    
    # Save test data
success = cloud_storage.save_json(test_data, "test_data.json")
    
if success:
        print("Successfully saved test data to cloud storage")
else:
        print("Failed to save test data to cloud storage")