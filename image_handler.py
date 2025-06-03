# Fixed image_handler.py - Enhanced for better weighment flow

import tkinter as tk
from tkinter import messagebox
import os
import datetime
import cv2
import config
from camera import add_watermark

class ImageHandler:
    """Enhanced image handler with improved weighment flow logic"""
    
    def __init__(self, main_form):
        """Initialize image handler
        
        Args:
            main_form: Reference to the main form instance
        """
        self.main_form = main_form
        print("ImageHandler initialized")
    
    def determine_current_image_weighment(self):
        """FIXED: Determine which weighment images should be saved for based on actual weighment completion
        
        Logic:
        - If no weights captured yet -> first weighment images
        - If first weight captured but no second weight -> first weighment images  
        - If both weights captured -> second weighment images
        - If only second weight captured (edge case) -> second weighment images
        
        Returns:
            str: "first" or "second"
        """
        try:
            # Check what weighments are actually completed
            first_weight = self.main_form.first_weight_var.get().strip()
            first_timestamp = self.main_form.first_timestamp_var.get().strip()
            second_weight = self.main_form.second_weight_var.get().strip()
            second_timestamp = self.main_form.second_timestamp_var.get().strip()
            
            first_complete = bool(first_weight and first_timestamp)
            second_complete = bool(second_weight and second_timestamp)
            
            print(f"Weighment status - First: {first_complete}, Second: {second_complete}")
            
            # Decision logic for image weighment
            if not first_complete and not second_complete:
                # No weighments yet - images go to first
                image_weighment = "first"
                print("No weighments completed - images for FIRST weighment")
            elif first_complete and not second_complete:
                # First weighment done, second not done - images still go to first (until second weight is captured)
                image_weighment = "first"
                print("First weighment completed, second not done - images for FIRST weighment")
            elif first_complete and second_complete:
                # Both weighments done - images go to second
                image_weighment = "second"  
                print("Both weighments completed - images for SECOND weighment")
            elif not first_complete and second_complete:
                # Edge case: only second weighment (unusual) - images go to second
                image_weighment = "second"
                print("Only second weighment completed - images for SECOND weighment")
            else:
                # Default fallback
                image_weighment = "first"
                print("Default fallback - images for FIRST weighment")
            
            return image_weighment
            
        except Exception as e:
            print(f"Error determining image weighment: {e}")
            return "first"  # Safe fallback
    
    def load_images_from_record(self, record):
        """Load images from a record into the form"""
        print(f"Loading images from record for ticket: {record.get('ticket_no', 'unknown')}")
        
        # First weighment images
        first_front_image = record.get('first_front_image', '')
        first_back_image = record.get('first_back_image', '')
        
        # Second weighment images  
        second_front_image = record.get('second_front_image', '')
        second_back_image = record.get('second_back_image', '')
        
        # Store all image paths
        self.main_form.first_front_image_path = os.path.join(config.IMAGES_FOLDER, first_front_image) if first_front_image else None
        self.main_form.first_back_image_path = os.path.join(config.IMAGES_FOLDER, first_back_image) if first_back_image else None
        self.main_form.second_front_image_path = os.path.join(config.IMAGES_FOLDER, second_front_image) if second_front_image else None
        self.main_form.second_back_image_path = os.path.join(config.IMAGES_FOLDER, second_back_image) if second_back_image else None
        
        print(f"Loaded image paths:")
        print(f"  First front: {self.main_form.first_front_image_path}")
        print(f"  First back: {self.main_form.first_back_image_path}")
        print(f"  Second front: {self.main_form.second_front_image_path}")
        print(f"  Second back: {self.main_form.second_back_image_path}")
        
        # Update status
        self.update_image_status()
    
    def reset_images(self):
        """Reset image paths and status"""
        print("Resetting all image paths")
        self.main_form.first_front_image_path = None
        self.main_form.first_back_image_path = None
        self.main_form.second_front_image_path = None
        self.main_form.second_back_image_path = None
        
        # Update status display
        self.update_image_status()
    
    def update_image_status(self):
        """Update image status indicators with enhanced feedback"""
        try:
            # Count first weighment images
            first_count = 0
            if self.main_form.first_front_image_path and os.path.exists(self.main_form.first_front_image_path):
                first_count += 1
            if self.main_form.first_back_image_path and os.path.exists(self.main_form.first_back_image_path):
                first_count += 1
            
            # Count second weighment images
            second_count = 0
            if self.main_form.second_front_image_path and os.path.exists(self.main_form.second_front_image_path):
                second_count += 1
            if self.main_form.second_back_image_path and os.path.exists(self.main_form.second_back_image_path):
                second_count += 1
            
            print(f"Image status update: 1st={first_count}/2, 2nd={second_count}/2")
            
            # Update status variables if they exist
            if hasattr(self.main_form, 'first_image_status_var'):
                self.main_form.first_image_status_var.set(f"1st: {first_count}/2")
                if hasattr(self.main_form, 'first_image_status'):
                    self.main_form.first_image_status.config(
                        foreground="green" if first_count == 2 else "orange" if first_count == 1 else "red"
                    )
            
            if hasattr(self.main_form, 'second_image_status_var'):
                self.main_form.second_image_status_var.set(f"2nd: {second_count}/2")
                if hasattr(self.main_form, 'second_image_status'):
                    self.main_form.second_image_status.config(
                        foreground="green" if second_count == 2 else "orange" if second_count == 1 else "red"
                    )
            
            # Update total image count
            total_count = first_count + second_count
            if hasattr(self.main_form, 'total_image_status_var'):
                self.main_form.total_image_status_var.set(f"Total: {total_count}/4")
            
            # Try to update the camera UI status as well
            if hasattr(self.main_form, 'update_image_status_display'):
                self.main_form.update_image_status_display()
                
        except Exception as e:
            print(f"Error updating image status: {e}")
    
    def save_front_image(self, captured_image=None):
        """FIXED: Save front view camera image based on ACTUAL weighment completion status"""
        print("=== SAVE FRONT IMAGE CALLED ===")
        print(f"Captured image provided: {captured_image is not None}")
        
        # Validate vehicle number first
        if not self.main_form.form_validator.validate_vehicle_number():
            print("Vehicle number validation failed")
            return False
        
        # FIXED: Determine which weighment these images are for based on actual completion
        image_weighment = self.determine_current_image_weighment()
        weighment_label = "1st" if image_weighment == "first" else "2nd"
        print(f"FIXED: Saving {weighment_label} weighment front image (based on actual weighment status)")
        
        # Use captured image if provided, otherwise try to get from camera
        image = captured_image
        if image is None:
            print("No captured image provided, trying to get from front camera")
            if hasattr(self.main_form, 'front_camera') and hasattr(self.main_form.front_camera, 'current_frame'):
                image = self.main_form.front_camera.current_frame
                print(f"Got image from front camera current_frame: {image is not None}")
            else:
                print("No front camera or current_frame available")
        
        if image is None:
            print("ERROR: No image available to save")
            messagebox.showerror("Error", "No image available to save. Please ensure camera is active and capture a frame first.")
            return False
        
        print(f"Image shape: {image.shape}")
        
        try:
            # Generate filename with new format
            site_name = self.main_form.site_var.get().replace(" ", "_")
            vehicle_no = self.main_form.vehicle_var.get().replace(" ", "_")
            ticket_id = self.main_form.rst_var.get().strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # New naming format: {site}_{vehicle}_{timestamp}_{weighment}_front.jpg
            filename = f"{site_name}_{vehicle_no}_{timestamp}_{weighment_label}_front.jpg"
            print(f"Generated filename: {filename}")
            
            # Main watermark text
            watermark_text = f"{site_name} - {vehicle_no} - {timestamp} - {weighment_label.upper()} FRONT"
            
            # Add watermark with ticket ID
            print("Adding watermark...")
            watermarked_image = add_watermark(image, watermark_text, ticket_id)
            
            # Ensure images folder exists
            os.makedirs(config.IMAGES_FOLDER, exist_ok=True)
            
            # Save file path
            filepath = os.path.join(config.IMAGES_FOLDER, filename)
            print(f"Saving to: {filepath}")
            
            # Save the image
            success = cv2.imwrite(filepath, watermarked_image)
            print(f"cv2.imwrite returned: {success}")
            
            if not success:
                print("ERROR: cv2.imwrite failed")
                messagebox.showerror("Error", "Failed to save image file")
                return False
            
            # Verify file was created
            if not os.path.exists(filepath):
                print("ERROR: File was not created")
                messagebox.showerror("Error", "Image file was not created")
                return False
            
            file_size = os.path.getsize(filepath)
            print(f"File created successfully, size: {file_size} bytes")
            
            # FIXED: Update the appropriate image path based on ACTUAL weighment determination
            if image_weighment == "first":
                self.main_form.first_front_image_path = filepath
                print(f"Set first_front_image_path: {filepath}")
            else:
                self.main_form.second_front_image_path = filepath
                print(f"Set second_front_image_path: {filepath}")
            
            # Update status
            self.update_image_status()
            
            print(f"✅ {weighment_label} weighment front image saved successfully: {filename}")
            
            # Show success message
            messagebox.showinfo("Success", f"{weighment_label} weighment front image saved successfully!")
            
            return True
            
        except Exception as e:
            error_msg = f"Error saving front image: {str(e)}"
            print(f"ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", error_msg)
            return False
    
    def save_back_image(self, captured_image=None):
        """FIXED: Save back view camera image based on ACTUAL weighment completion status"""
        print("=== SAVE BACK IMAGE CALLED ===")
        print(f"Captured image provided: {captured_image is not None}")
        
        # Validate vehicle number first
        if not self.main_form.form_validator.validate_vehicle_number():
            print("Vehicle number validation failed")
            return False
        
        # FIXED: Determine which weighment these images are for based on actual completion
        image_weighment = self.determine_current_image_weighment()
        weighment_label = "1st" if image_weighment == "first" else "2nd"
        print(f"FIXED: Saving {weighment_label} weighment back image (based on actual weighment status)")
        
        # Use captured image if provided, otherwise try to get from camera
        image = captured_image
        if image is None:
            print("No captured image provided, trying to get from back camera")
            if hasattr(self.main_form, 'back_camera') and hasattr(self.main_form.back_camera, 'current_frame'):
                image = self.main_form.back_camera.current_frame
                print(f"Got image from back camera current_frame: {image is not None}")
            else:
                print("No back camera or current_frame available")
        
        if image is None:
            print("ERROR: No image available to save")
            messagebox.showerror("Error", "No image available to save. Please ensure camera is active and capture a frame first.")
            return False
        
        print(f"Image shape: {image.shape}")
        
        try:
            # Generate filename with new format
            site_name = self.main_form.site_var.get().replace(" ", "_")
            vehicle_no = self.main_form.vehicle_var.get().replace(" ", "_")
            ticket_id = self.main_form.rst_var.get().strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # New naming format: {site}_{vehicle}_{timestamp}_{weighment}_back.jpg
            filename = f"{site_name}_{vehicle_no}_{timestamp}_{weighment_label}_back.jpg"
            print(f"Generated filename: {filename}")
            
            # Main watermark text
            watermark_text = f"{site_name} - {vehicle_no} - {timestamp} - {weighment_label.upper()} BACK"
            
            # Add watermark with ticket ID
            print("Adding watermark...")
            watermarked_image = add_watermark(image, watermark_text, ticket_id)
            
            # Ensure images folder exists
            os.makedirs(config.IMAGES_FOLDER, exist_ok=True)
            
            # Save file path
            filepath = os.path.join(config.IMAGES_FOLDER, filename)
            print(f"Saving to: {filepath}")
            
            # Save the image
            success = cv2.imwrite(filepath, watermarked_image)
            print(f"cv2.imwrite returned: {success}")
            
            if not success:
                print("ERROR: cv2.imwrite failed")
                messagebox.showerror("Error", "Failed to save image file")
                return False
            
            # Verify file was created
            if not os.path.exists(filepath):
                print("ERROR: File was not created")
                messagebox.showerror("Error", "Image file was not created")
                return False
            
            file_size = os.path.getsize(filepath)
            print(f"File created successfully, size: {file_size} bytes")
            
            # FIXED: Update the appropriate image path based on ACTUAL weighment determination
            if image_weighment == "first":
                self.main_form.first_back_image_path = filepath
                print(f"Set first_back_image_path: {filepath}")
            else:
                self.main_form.second_back_image_path = filepath
                print(f"Set second_back_image_path: {filepath}")
            
            # Update status
            self.update_image_status()
            
            print(f"✅ {weighment_label} weighment back image saved successfully: {filename}")
            
            # Show success message
            messagebox.showinfo("Success", f"{weighment_label} weighment back image saved successfully!")
            
            return True
            
        except Exception as e:
            error_msg = f"Error saving back image: {str(e)}"
            print(f"ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", error_msg)
            return False
    
    def save_first_front_image(self, captured_image):
        """Save image specifically for first weighment front - used by continuous camera system"""
        print("=== SAVE FIRST FRONT IMAGE (SPECIFIC) ===")
        
        # Validate vehicle number first
        if not self.main_form.form_validator.validate_vehicle_number():
            print("Vehicle number validation failed")
            return False
        
        if captured_image is None:
            print("ERROR: No captured image provided")
            return False
        
        try:
            # Generate filename
            site_name = self.main_form.site_var.get().replace(" ", "_")
            vehicle_no = self.main_form.vehicle_var.get().replace(" ", "_")
            ticket_id = self.main_form.rst_var.get().strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"{site_name}_{vehicle_no}_{timestamp}_1st_front.jpg"
            watermark_text = f"{site_name} - {vehicle_no} - {timestamp} - 1ST FRONT"
            
            # Add watermark
            watermarked_image = add_watermark(captured_image, watermark_text, ticket_id)
            
            # Save image
            os.makedirs(config.IMAGES_FOLDER, exist_ok=True)
            filepath = os.path.join(config.IMAGES_FOLDER, filename)
            
            success = cv2.imwrite(filepath, watermarked_image)
            if success and os.path.exists(filepath):
                self.main_form.first_front_image_path = filepath
                self.update_image_status()
                print(f"✅ First front image saved: {filename}")
                return True
            else:
                print("ERROR: Failed to save first front image")
                return False
                
        except Exception as e:
            print(f"Error saving first front image: {e}")
            return False
    
    def save_first_back_image(self, captured_image):
        """Save image specifically for first weighment back - used by continuous camera system"""
        print("=== SAVE FIRST BACK IMAGE (SPECIFIC) ===")
        
        # Validate vehicle number first
        if not self.main_form.form_validator.validate_vehicle_number():
            print("Vehicle number validation failed")
            return False
        
        if captured_image is None:
            print("ERROR: No captured image provided")
            return False
        
        try:
            # Generate filename
            site_name = self.main_form.site_var.get().replace(" ", "_")
            vehicle_no = self.main_form.vehicle_var.get().replace(" ", "_")
            ticket_id = self.main_form.rst_var.get().strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"{site_name}_{vehicle_no}_{timestamp}_1st_back.jpg"
            watermark_text = f"{site_name} - {vehicle_no} - {timestamp} - 1ST BACK"
            
            # Add watermark
            watermarked_image = add_watermark(captured_image, watermark_text, ticket_id)
            
            # Save image
            os.makedirs(config.IMAGES_FOLDER, exist_ok=True)
            filepath = os.path.join(config.IMAGES_FOLDER, filename)
            
            success = cv2.imwrite(filepath, watermarked_image)
            if success and os.path.exists(filepath):
                self.main_form.first_back_image_path = filepath
                self.update_image_status()
                print(f"✅ First back image saved: {filename}")
                return True
            else:
                print("ERROR: Failed to save first back image")
                return False
                
        except Exception as e:
            print(f"Error saving first back image: {e}")
            return False
    
    def save_second_front_image(self, captured_image):
        """Save image specifically for second weighment front - used by continuous camera system"""
        print("=== SAVE SECOND FRONT IMAGE (SPECIFIC) ===")
        
        # Validate vehicle number first
        if not self.main_form.form_validator.validate_vehicle_number():
            print("Vehicle number validation failed")
            return False
        
        if captured_image is None:
            print("ERROR: No captured image provided")
            return False
        
        try:
            # Generate filename
            site_name = self.main_form.site_var.get().replace(" ", "_")
            vehicle_no = self.main_form.vehicle_var.get().replace(" ", "_")
            ticket_id = self.main_form.rst_var.get().strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"{site_name}_{vehicle_no}_{timestamp}_2nd_front.jpg"
            watermark_text = f"{site_name} - {vehicle_no} - {timestamp} - 2ND FRONT"
            
            # Add watermark
            watermarked_image = add_watermark(captured_image, watermark_text, ticket_id)
            
            # Save image
            os.makedirs(config.IMAGES_FOLDER, exist_ok=True)
            filepath = os.path.join(config.IMAGES_FOLDER, filename)
            
            success = cv2.imwrite(filepath, watermarked_image)
            if success and os.path.exists(filepath):
                self.main_form.second_front_image_path = filepath
                self.update_image_status()
                print(f"✅ Second front image saved: {filename}")
                return True
            else:
                print("ERROR: Failed to save second front image")
                return False
                
        except Exception as e:
            print(f"Error saving second front image: {e}")
            return False
    
    def save_second_back_image(self, captured_image):
        """Save image specifically for second weighment back - used by continuous camera system"""
        print("=== SAVE SECOND BACK IMAGE (SPECIFIC) ===")
        
        # Validate vehicle number first
        if not self.main_form.form_validator.validate_vehicle_number():
            print("Vehicle number validation failed")
            return False
        
        if captured_image is None:
            print("ERROR: No captured image provided")
            return False
        
        try:
            # Generate filename
            site_name = self.main_form.site_var.get().replace(" ", "_")
            vehicle_no = self.main_form.vehicle_var.get().replace(" ", "_")
            ticket_id = self.main_form.rst_var.get().strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"{site_name}_{vehicle_no}_{timestamp}_2nd_back.jpg"
            watermark_text = f"{site_name} - {vehicle_no} - {timestamp} - 2ND BACK"
            
            # Add watermark
            watermarked_image = add_watermark(captured_image, watermark_text, ticket_id)
            
            # Save image
            os.makedirs(config.IMAGES_FOLDER, exist_ok=True)
            filepath = os.path.join(config.IMAGES_FOLDER, filename)
            
            success = cv2.imwrite(filepath, watermarked_image)
            if success and os.path.exists(filepath):
                self.main_form.second_back_image_path = filepath
                self.update_image_status()
                print(f"✅ Second back image saved: {filename}")
                return True
            else:
                print("ERROR: Failed to save second back image")
                return False
                
        except Exception as e:
            print(f"Error saving second back image: {e}")
            return False
    
    def get_all_image_filenames(self):
        """Get all image filenames for database storage
        
        Returns:
            dict: Dictionary with all 4 image filenames
        """
        result = {
            'first_front_image': os.path.basename(self.main_form.first_front_image_path) if self.main_form.first_front_image_path else "",
            'first_back_image': os.path.basename(self.main_form.first_back_image_path) if self.main_form.first_back_image_path else "",
            'second_front_image': os.path.basename(self.main_form.second_front_image_path) if self.main_form.second_front_image_path else "",
            'second_back_image': os.path.basename(self.main_form.second_back_image_path) if self.main_form.second_back_image_path else ""
        }
        print(f"Get all image filenames returning: {result}")
        return result
    
    def get_current_weighment_images(self):
        """Get images for current weighment state based on actual completion
        
        Returns:
            dict: Front and back image paths for current weighment
        """
        image_weighment = self.determine_current_image_weighment()
        
        if image_weighment == "first":
            return {
                'front_image': self.main_form.first_front_image_path,
                'back_image': self.main_form.first_back_image_path
            }
        else:
            return {
                'front_image': self.main_form.second_front_image_path,
                'back_image': self.main_form.second_back_image_path
            }
    
    def are_current_weighment_images_complete(self):
        """Check if current weighment has both images captured
        
        Returns:
            bool: True if both front and back images are captured for current weighment
        """
        current_images = self.get_current_weighment_images()
        
        front_exists = current_images['front_image'] and os.path.exists(current_images['front_image'])
        back_exists = current_images['back_image'] and os.path.exists(current_images['back_image'])
        
        result = front_exists and back_exists
        print(f"Current weighment images complete: {result} (front: {front_exists}, back: {back_exists})")
        return result
    
    def get_total_image_count(self):
        """Get total count of captured images across both weighments
        
        Returns:
            int: Total number of images captured (0-4)
        """
        count = 0
        
        # First weighment images
        if self.main_form.first_front_image_path and os.path.exists(self.main_form.first_front_image_path):
            count += 1
        if self.main_form.first_back_image_path and os.path.exists(self.main_form.first_back_image_path):
            count += 1
        
        # Second weighment images
        if self.main_form.second_front_image_path and os.path.exists(self.main_form.second_front_image_path):
            count += 1
        if self.main_form.second_back_image_path and os.path.exists(self.main_form.second_back_image_path):
            count += 1
        
        print(f"Total image count: {count}/4")
        return count