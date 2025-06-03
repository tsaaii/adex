import threading
import time
import subprocess
import platform
import os
import json
import datetime
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

class SimpleConnectivity:
    """Simple connectivity checker using ping"""
    
    def __init__(self, callback=None):
        self.callback = callback
        self.is_online = False
        self.running = True
        self.check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self.check_thread.start()
        print("🔍 Connectivity checker started")
    
    def _check_loop(self):
        """Check connectivity every 30 seconds"""
        while self.running:
            try:
                # Ping Google DNS with shorter timeout
                param = "-n" if platform.system().lower() == "windows" else "-c"
                result = subprocess.run(["ping", param, "1", "8.8.8.8"], 
                                      capture_output=True, timeout=3)
                new_status = result.returncode == 0
                
                # Only trigger callback if status actually changed
                if new_status != self.is_online:
                    self.is_online = new_status
                    status_text = "🌐 ONLINE" if new_status else "📴 OFFLINE"
                    print(f"🔄 Connectivity changed: {status_text}")
                    
                    if self.callback:
                        try:
                            self.callback(new_status)
                        except Exception as e:
                            print(f"❌ Error in connectivity callback: {e}")
                            
            except Exception as e:
                print(f"⚠️ Connectivity check error: {e}")
                # Assume offline if ping fails
                if self.is_online:
                    self.is_online = False
                    if self.callback:
                        try:
                            self.callback(False)
                        except Exception as e:
                            print(f"❌ Error in connectivity callback: {e}")
            
            # Wait 30 seconds before next check
            time.sleep(30)
    
    def stop(self):
        """Stop the connectivity checker"""
        print("🛑 Stopping connectivity checker")
        self.running = False

class SimpleQueue:
    """Simple offline queue with improved reliability"""
    
    def __init__(self):
        self.queue_file = "data/simple_queue.json"
        self.items = self._load_queue()
        print(f"📥 Queue initialized with {len(self.items)} items")
    
    def _load_queue(self):
        """Load queue from file with error handling"""
        try:
            if os.path.exists(self.queue_file):
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"📂 Loaded {len(data)} items from queue file")
                    return data
            else:
                print("📂 No existing queue file found, starting with empty queue")
                return []
        except Exception as e:
            print(f"❌ Error loading queue file: {e}")
            return []
    
    def _save_queue(self):
        """Save queue to file with error handling"""
        try:
            os.makedirs(os.path.dirname(self.queue_file), exist_ok=True)
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(self.items, f, indent=2, ensure_ascii=False)
            # Removed the print statement to reduce logging during fast operations
        except Exception as e:
            print(f"❌ Error saving queue file: {e}")
    
    def add(self, record_data, images=None, pdf_path=None):
        """Add item to queue"""
        try:
            item = {
                "id": datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'),
                "record": record_data,
                "images": images or [],
                "pdf": pdf_path,
                "timestamp": datetime.datetime.now().isoformat(),
                "attempts": 0,
                "last_attempt": None
            }
            self.items.append(item)
            self._save_queue()
            ticket_no = record_data.get('ticket_no', 'unknown')
            print(f"📥 Queued record: {ticket_no} (Queue size: {len(self.items)})")
            return True
        except Exception as e:
            print(f"❌ Error adding to queue: {e}")
            return False
    
    def count(self):
        """Get number of items in queue"""
        return len(self.items)
    
    def get_items(self):
        """Get copy of all queue items"""
        return self.items.copy()
    
    def remove_batch(self, item_ids):
        """Remove multiple items from queue by IDs - BATCH OPERATION"""
        try:
            initial_count = len(self.items)
            self.items = [item for item in self.items if item.get("id") not in item_ids]
            removed_count = initial_count - len(self.items)
            
            if removed_count > 0:
                self._save_queue()
                print(f"🗑️ Batch removed {removed_count} items from queue (Queue size: {len(self.items)})")
                return True
            else:
                print(f"⚠️ No items found to remove in batch")
                return False
        except Exception as e:
            print(f"❌ Error batch removing from queue: {e}")
            return False
    
    def remove(self, item_id):
        """Remove item from queue by ID"""
        try:
            initial_count = len(self.items)
            self.items = [item for item in self.items if item.get("id") != item_id]
            removed_count = initial_count - len(self.items)
            
            if removed_count > 0:
                self._save_queue()
                return True
            else:
                return False
        except Exception as e:
            print(f"❌ Error removing from queue: {e}")
            return False
    
    def clear(self):
        """Clear all items from queue"""
        try:
            self.items = []
            self._save_queue()
            print("🧹 Queue cleared")
            return True
        except Exception as e:
            print(f"❌ Error clearing queue: {e}")
            return False

class FastSync:
    """Ultra-fast parallel sync with optimizations"""
    
    def __init__(self, data_manager, queue):
        self.data_manager = data_manager
        self.queue = queue
        self.syncing = False
        self.last_sync_attempt = None
        self.max_workers = 5  # Parallel uploads
        print("🚀 Fast sync manager initialized with parallel processing")
    
    def start(self):
        """Start fast sync if not already running and there are items to sync"""
        if self.syncing:
            print("⏳ Sync already in progress, skipping")
            return False
            
        queue_count = self.queue.count()
        if queue_count == 0:
            print("📭 Queue is empty, nothing to sync")
            return False
        
        print(f"🚀 Starting FAST parallel sync for {queue_count} items")
        self.syncing = True
        sync_thread = threading.Thread(target=self._fast_sync, daemon=True)
        sync_thread.start()
        return True
    
    def _upload_single_record(self, item):
        """Upload a single record (for parallel processing)"""
        try:
            item_id = item.get("id")
            record_data = item.get("record", {})
            ticket_no = record_data.get('ticket_no', 'unknown')
            
            # Try to upload record to cloud (without excessive logging)
            success, images_uploaded, total_images = self.data_manager.save_to_cloud_with_images(record_data)
            
            return {
                "success": success,
                "item_id": item_id,
                "ticket_no": ticket_no,
                "images_uploaded": images_uploaded,
                "total_images": total_images,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "item_id": item.get("id"),
                "ticket_no": record_data.get('ticket_no', 'unknown'),
                "images_uploaded": 0,
                "total_images": 0,
                "error": str(e)
            }
    
    def _fast_sync(self):
        """Ultra-fast parallel sync with batch operations"""
        try:
            start_time = time.time()
            self.last_sync_attempt = datetime.datetime.now()
            items = self.queue.get_items()
            total_items = len(items)
            
            print(f"⚡ FAST SYNC: Processing {total_items} items with {self.max_workers} parallel workers...")
            
            # Pre-flight checks
            if not hasattr(self.data_manager, 'save_to_cloud_with_images'):
                print("❌ Data manager doesn't support cloud sync")
                return
            
            # Initialize cloud storage if needed
            if hasattr(self.data_manager, 'init_cloud_storage_if_needed'):
                if not self.data_manager.init_cloud_storage_if_needed():
                    print("❌ Failed to initialize cloud storage")
                    return
            
            # Check if cloud storage is connected
            if hasattr(self.data_manager, 'cloud_storage') and self.data_manager.cloud_storage:
                if not self.data_manager.cloud_storage.is_connected():
                    print("❌ Cloud storage not connected")
                    return
            
            # PARALLEL PROCESSING with ThreadPoolExecutor
            successful_ids = []
            failed_count = 0
            total_images_uploaded = 0
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_item = {executor.submit(self._upload_single_record, item): item for item in items}
                
                # Process completed tasks as they finish
                for i, future in enumerate(as_completed(future_to_item), 1):
                    try:
                        result = future.result()
                        
                        if result["success"]:
                            successful_ids.append(result["item_id"])
                            total_images_uploaded += result["images_uploaded"]
                            print(f"✅ {i}/{total_items}: {result['ticket_no']} ({result['images_uploaded']}/{result['total_images']} images)")
                        else:
                            failed_count += 1
                            error_msg = result.get("error", "Unknown error")
                            print(f"❌ {i}/{total_items}: {result['ticket_no']} - {error_msg}")
                            
                    except Exception as e:
                        failed_count += 1
                        print(f"❌ {i}/{total_items}: Future error - {e}")
            
            # BATCH REMOVE successful items from queue
            if successful_ids:
                print(f"🗑️ Batch removing {len(successful_ids)} successful items from queue...")
                self.queue.remove_batch(successful_ids)
            
            # Performance metrics
            end_time = time.time()
            duration = end_time - start_time
            synced_count = len(successful_ids)
            remaining_items = self.queue.count()
            
            # Final status with performance metrics
            print(f"⚡ FAST SYNC COMPLETED in {duration:.2f}s:")
            print(f"   ✅ Synced: {synced_count} records")
            print(f"   🖼️ Images: {total_images_uploaded}")
            print(f"   ❌ Failed: {failed_count}")
            print(f"   📋 Remaining: {remaining_items}")
            print(f"   📊 Speed: {synced_count/duration:.1f} records/sec")
            
            if synced_count > 0:
                print(f"🎉 Successfully synced {synced_count} records to cloud in {duration:.2f}s!")
            
            if remaining_items > 0:
                print(f"⚠️ {remaining_items} items remain in queue (will retry on next connectivity)")
            
        except Exception as e:
            print(f"❌ Critical error during fast sync: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.syncing = False
            print("🏁 Fast sync process completed")

class ConnectivityUI:
    """Enhanced connectivity UI with fast sync support"""
    
    def __init__(self, parent_frame, data_manager):
        self.parent_frame = parent_frame
        self.data_manager = data_manager
        
        # Create UI elements
        self.status_var = tk.StringVar(value="🔍 Checking...")
        self.queue_var = tk.StringVar(value="Queue: 0")
        
        # Status frame
        status_frame = tk.Frame(parent_frame, bg="#f0f0f0")
        status_frame.pack(side=tk.RIGHT, padx=5)
        
        # Status labels with better styling
        self.status_label = tk.Label(status_frame, textvariable=self.status_var, 
                                    font=("Segoe UI", 8), bg="#f0f0f0", fg="blue")
        self.status_label.pack(side=tk.LEFT, padx=2)
        
        self.queue_label = tk.Label(status_frame, textvariable=self.queue_var,
                                   font=("Segoe UI", 8), bg="#f0f0f0", fg="orange")
        self.queue_label.pack(side=tk.LEFT, padx=5)
        
        # Initialize components with fast sync
        self.queue = SimpleQueue()
        self.sync = FastSync(data_manager, self.queue)  # Use FastSync instead of SimpleSync
        self.connectivity = SimpleConnectivity(self._on_status_change)
        
        # Initial display update
        self._update_display()
        
        # Start periodic queue display updates
        self._schedule_display_update()
        
        print("🎛️ Enhanced connectivity UI initialized with fast sync")
    
    def _on_status_change(self, is_online):
        """Handle connectivity status change"""
        try:
            status_text = "🌐 Online" if is_online else "📴 Offline"
            self.status_var.set(status_text)
            
            print(f"🔄 Connectivity status changed: {status_text}")
            
            if is_online:
                print("🌐 Internet connection detected - starting FAST sync")
                # Small delay to ensure UI updates, then start fast sync
                self.parent_frame.after(1000, self._start_fast_sync_delayed)
            else:
                print("📴 Internet connection lost - will queue records offline")
                
            self._update_display()
            
        except Exception as e:
            print(f"❌ Error handling status change: {e}")
    
    def _start_fast_sync_delayed(self):
        """Start fast sync with a small delay"""
        try:
            if self.connectivity.is_online:
                sync_started = self.sync.start()
                if sync_started:
                    print("🚀 Fast sync started successfully")
                else:
                    print("ℹ️ Fast sync not started (already running or queue empty)")
        except Exception as e:
            print(f"❌ Error starting fast sync: {e}")
    
    def _update_display(self):
        """Update queue count display"""
        try:
            count = self.queue.count()
            if count > 0:
                self.queue_var.set(f"Queue: {count}")
                self.queue_label.config(fg="red" if count > 10 else "orange")
            else:
                self.queue_var.set("Queue: 0")
                self.queue_label.config(fg="green")
        except Exception as e:
            print(f"❌ Error updating display: {e}")
    
    def _schedule_display_update(self):
        """Schedule periodic display updates"""
        try:
            self._update_display()
            # Schedule next update in 3 seconds (faster updates during sync)
            self.parent_frame.after(3000, self._schedule_display_update)
        except Exception as e:
            print(f"❌ Error scheduling display update: {e}")
    
    def add_to_queue(self, record_data, images=None, pdf_path=None):
        """Add complete record to queue"""
        try:
            # Only queue complete records (both weighments)
            first_weight = record_data.get('first_weight', '').strip()
            first_timestamp = record_data.get('first_timestamp', '').strip()
            second_weight = record_data.get('second_weight', '').strip()
            second_timestamp = record_data.get('second_timestamp', '').strip()
            
            is_complete = (first_weight and first_timestamp and 
                          second_weight and second_timestamp)
            
            if not is_complete:
                print(f"⏭️ Skipping incomplete record: {record_data.get('ticket_no', 'unknown')}")
                return False
            
            # Collect existing image paths
            image_paths = []
            for field in ['first_front_image', 'first_back_image', 'second_front_image', 'second_back_image']:
                img_file = record_data.get(field, '').strip()
                if img_file:
                    img_path = os.path.join("data/images", img_file)
                    if os.path.exists(img_path):
                        image_paths.append(img_path)
            
            # Add to queue
            success = self.queue.add(record_data, image_paths, pdf_path)
            
            if success:
                self._update_display()
                ticket_no = record_data.get('ticket_no', 'unknown')
                print(f"📥 Added complete record to queue: {ticket_no}")
                
                # Try to sync immediately if online (using fast sync)
                if self.connectivity.is_online and not self.sync.syncing:
                    print("🌐 Online - attempting immediate FAST sync")
                    self.parent_frame.after(500, self._start_fast_sync_delayed)
                
                return True
            else:
                print(f"❌ Failed to add record to queue")
                return False
                
        except Exception as e:
            print(f"❌ Error adding to queue: {e}")
            return False
    
    def force_sync(self):
        """Force a fast sync attempt (for manual testing)"""
        try:
            if self.connectivity.is_online:
                print("🔄 Manual FAST sync requested")
                return self.sync.start()
            else:
                print("📴 Cannot sync - no internet connection")
                return False
        except Exception as e:
            print(f"❌ Error in force sync: {e}")
            return False
    
    def get_queue_status(self):
        """Get detailed queue status"""
        try:
            return {
                "count": self.queue.count(),
                "online": self.connectivity.is_online,
                "syncing": self.sync.syncing,
                "last_sync": self.sync.last_sync_attempt,
                "sync_type": "FastSync"
            }
        except Exception as e:
            print(f"❌ Error getting queue status: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            print("🧹 Cleaning up connectivity resources")
            if hasattr(self, 'connectivity'):
                self.connectivity.stop()
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")

# Integration functions for existing app
def add_connectivity_to_app(app_instance):
    """Add fast connectivity features to existing app"""
    try:
        # Find title_box in header
        if hasattr(app_instance, 'title_box'):
            app_instance.connectivity_ui = ConnectivityUI(app_instance.title_box, app_instance.data_manager)
            print("✅ Enhanced FAST connectivity added to app")
            return True
        else:
            print("❌ Could not find title_box in app")
            return False
    except Exception as e:
        print(f"⚠️ Could not add connectivity: {e}")
        return False

def add_to_queue_if_available(app_instance, record_data, pdf_path=None):
    """Add record to queue if connectivity features are available"""
    try:
        if hasattr(app_instance, 'connectivity_ui') and app_instance.connectivity_ui:
            return app_instance.connectivity_ui.add_to_queue(record_data, pdf_path=pdf_path)
        else:
            print("⚠️ Connectivity UI not available")
            return False
    except Exception as e:
        print(f"❌ Queue add error: {e}")
        return False

def cleanup_connectivity(app_instance):
    """Cleanup connectivity features"""
    try:
        if hasattr(app_instance, 'connectivity_ui') and app_instance.connectivity_ui:
            app_instance.connectivity_ui.cleanup()
            print("✅ Connectivity cleanup completed")
        else:
            print("ℹ️ No connectivity UI to cleanup")
    except Exception as e:
        print(f"❌ Cleanup error: {e}")

# Performance testing function
def test_fast_sync_performance():
    """Test fast sync performance"""
    print("🧪 Testing fast sync performance...")
    print("This would require actual data and cloud connection to test properly")
    print("Expected improvements:")
    print("  • 3-5x faster with parallel uploads")
    print("  • Batch queue operations")
    print("  • Reduced logging overhead")
    print("  • Concurrent image uploads")