import tkinter as tk
from tkinter import messagebox
import os
import datetime
import cv2
import config
from camera import add_watermark

class ImageHandler:
    """Handles image capture and management functionality for 4-image system with state-based naming"""
    
    def __init__(self, main_form):
        """Initialize image handler
        
        Args:
            main_form: Reference to the main form instance
        """
        self.main_form = main_form
    
    def load_images_from_record(self, record):
        """Load images from a record into the form"""
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
        
        # Update status
        self.update_image_status()
    
    def reset_images(self):
        """Reset image paths and status"""
        self.main_form.first_front_image_path = None
        self.main_form.first_back_image_path = None
        self.main_form.second_front_image_path = None
        self.main_form.second_back_image_path = None
        
        # Update status display
        self.update_image_status()
    
    def update_image_status(self):
        """Update image status indicators"""
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
        
        # Update status variables
        if hasattr(self.main_form, 'first_image_status_var'):
            self.main_form.first_image_status_var.set(f"1st: {first_count}/2")
            self.main_form.first_image_status.config(
                foreground="green" if first_count == 2 else "red"
            )
        
        if hasattr(self.main_form, 'second_image_status_var'):
            self.main_form.second_image_status_var.set(f"2nd: {second_count}/2")
            self.main_form.second_image_status.config(
                foreground="green" if second_count == 2 else "red"
            )
    
    def save_front_image(self, captured_image=None):
        """Save front view camera image based on current weighment state"""
        if not self.main_form.form_validator.validate_vehicle_number():
            return False
        
        # Determine which weighment we're in
        current_weighment = self.main_form.current_weighment
        weighment_label = "1st" if current_weighment == "first" else "2nd"
        
        # Use captured image or get from camera
        image = captured_image if captured_image is not None else self.main_form.front_camera.captured_image
        
        if image is not None:
            # Generate filename with new format
            site_name = self.main_form.site_var.get().replace(" ", "_")
            vehicle_no = self.main_form.vehicle_var.get().replace(" ", "_")
            ticket_id = self.main_form.rst_var.get().strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # New naming format: {site}_{vehicle}_{timestamp}_{weighment}_front.jpg
            filename = f"{site_name}_{vehicle_no}_{timestamp}_{weighment_label}_front.jpg"
            
            # Main watermark text
            watermark_text = f"{site_name} - {vehicle_no} - {timestamp} - {weighment_label.upper()} FRONT"
            
            # Add watermark with ticket ID
            watermarked_image = add_watermark(image, watermark_text, ticket_id)
            
            # Save file path
            filepath = os.path.join(config.IMAGES_FOLDER, filename)
            
            # Save the image
            cv2.imwrite(filepath, watermarked_image)
            
            # Update the appropriate image path based on weighment
            if current_weighment == "first":
                self.main_form.first_front_image_path = filepath
            else:
                self.main_form.second_front_image_path = filepath
            
            # Update status
            self.update_image_status()
            
            print(f"{weighment_label} weighment front image saved: {filename}")
            return True
            
        return False
    
    def save_back_image(self, captured_image=None):
        """Save back view camera image based on current weighment state"""
        if not self.main_form.form_validator.validate_vehicle_number():
            return False
        
        # Determine which weighment we're in
        current_weighment = self.main_form.current_weighment
        weighment_label = "1st" if current_weighment == "first" else "2nd"
        
        # Use captured image or get from camera
        image = captured_image if captured_image is not None else self.main_form.back_camera.captured_image
        
        if image is not None:
            # Generate filename with new format
            site_name = self.main_form.site_var.get().replace(" ", "_")
            vehicle_no = self.main_form.vehicle_var.get().replace(" ", "_")
            ticket_id = self.main_form.rst_var.get().strip()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # New naming format: {site}_{vehicle}_{timestamp}_{weighment}_back.jpg
            filename = f"{site_name}_{vehicle_no}_{timestamp}_{weighment_label}_back.jpg"
            
            # Main watermark text
            watermark_text = f"{site_name} - {vehicle_no} - {timestamp} - {weighment_label.upper()} BACK"
            
            # Add watermark with ticket ID
            watermarked_image = add_watermark(image, watermark_text, ticket_id)
            
            # Save file path
            filepath = os.path.join(config.IMAGES_FOLDER, filename)
            
            # Save the image
            cv2.imwrite(filepath, watermarked_image)
            
            # Update the appropriate image path based on weighment
            if current_weighment == "first":
                self.main_form.first_back_image_path = filepath
            else:
                self.main_form.second_back_image_path = filepath
            
            # Update status
            self.update_image_status()
            
            print(f"{weighment_label} weighment back image saved: {filename}")
            return True
            
        return False
    
    def get_all_image_filenames(self):
        """Get all image filenames for database storage
        
        Returns:
            dict: Dictionary with all 4 image filenames
        """
        return {
            'first_front_image': os.path.basename(self.main_form.first_front_image_path) if self.main_form.first_front_image_path else "",
            'first_back_image': os.path.basename(self.main_form.first_back_image_path) if self.main_form.first_back_image_path else "",
            'second_front_image': os.path.basename(self.main_form.second_front_image_path) if self.main_form.second_front_image_path else "",
            'second_back_image': os.path.basename(self.main_form.second_back_image_path) if self.main_form.second_back_image_path else ""
        }
    
    def get_current_weighment_images(self):
        """Get images for current weighment state
        
        Returns:
            dict: Front and back image paths for current weighment
        """
        current_weighment = self.main_form.current_weighment
        
        if current_weighment == "first":
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
        
        return front_exists and back_exists
    
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
        
        return count