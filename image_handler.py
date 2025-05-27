import tkinter as tk
from tkinter import messagebox
import os
import datetime
import cv2
import config
from camera import add_watermark

class ImageHandler:
    """Handles image capture and management functionality"""
    
    def __init__(self, main_form):
        """Initialize image handler
        
        Args:
            main_form: Reference to the main form instance
        """
        self.main_form = main_form
    
    def load_images_from_record(self, record):
        """Load images from a record into the form"""
        front_image = record.get('front_image', '')
        back_image = record.get('back_image', '')
        
        if front_image:
            self.main_form.front_image_path = os.path.join(config.IMAGES_FOLDER, front_image)
            self.main_form.front_image_status_var.set("Front: ✓")
            self.main_form.front_image_status.config(foreground="green")
        else:
            self.main_form.front_image_path = None
            self.main_form.front_image_status_var.set("Front: ✗")
            self.main_form.front_image_status.config(foreground="red")
            
        if back_image:
            self.main_form.back_image_path = os.path.join(config.IMAGES_FOLDER, back_image)
            self.main_form.back_image_status_var.set("Back: ✓")
            self.main_form.back_image_status.config(foreground="green")
        else:
            self.main_form.back_image_path = None
            self.main_form.back_image_status_var.set("Back: ✗")
            self.main_form.back_image_status.config(foreground="red")
    
    def reset_images(self):
        """Reset image paths and status"""
        self.main_form.front_image_path = None
        self.main_form.back_image_path = None
        self.main_form.front_image_status_var.set("Front: ✗")
        self.main_form.back_image_status_var.set("Back: ✗")
        self.main_form.front_image_status.config(foreground="red")
        self.main_form.back_image_status.config(foreground="red")
    
    def save_front_image(self, captured_image=None):
        """Save the front view camera image with watermark"""
        if not self.main_form.form_validator.validate_vehicle_number():
            return False
        
        # Use captured image or get from camera
        image = captured_image if captured_image is not None else self.main_form.front_camera.captured_image
        
        if image is not None:
            # Generate filename and watermark text
            site_name = self.main_form.site_var.get().replace(" ", "_")
            vehicle_no = self.main_form.vehicle_var.get().replace(" ", "_")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Watermark text
            watermark_text = f"{site_name} - {vehicle_no} - {timestamp}"
            
            # Add watermark
            watermarked_image = add_watermark(image, watermark_text)
            
            # Save file path
            filename = f"{site_name}_{vehicle_no}_{timestamp}_front.jpg"
            filepath = os.path.join(config.IMAGES_FOLDER, filename)
            
            # Save the image
            cv2.imwrite(filepath, watermarked_image)
            
            # Update status
            self.main_form.front_image_path = filepath
            self.main_form.front_image_status_var.set("Front: ✓")
            self.main_form.front_image_status.config(foreground="green")
            
            # messagebox.showinfo("Success", "Front image saved!")
            return True
            
        return False
    
    def save_back_image(self, captured_image=None):
        """Save the back view camera image with watermark"""
        if not self.main_form.form_validator.validate_vehicle_number():
            return False
        
        # Use captured image or get from camera
        image = captured_image if captured_image is not None else self.main_form.back_camera.captured_image
        
        if image is not None:
            # Generate filename and watermark text
            site_name = self.main_form.site_var.get().replace(" ", "_")
            vehicle_no = self.main_form.vehicle_var.get().replace(" ", "_")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Watermark text
            watermark_text = f"{site_name} - {vehicle_no} - {timestamp}"
            
            # Add watermark
            watermarked_image = add_watermark(image, watermark_text)
            
            # Save file path
            filename = f"{site_name}_{vehicle_no}_{timestamp}_back.jpg"
            filepath = os.path.join(config.IMAGES_FOLDER, filename)
            
            # Save the image
            cv2.imwrite(filepath, watermarked_image)
            
            # Update status
            self.main_form.back_image_path = filepath
            self.main_form.back_image_status_var.set("Back: ✓")
            self.main_form.back_image_status.config(foreground="green")
            
            # messagebox.showinfo("Success", "Back image saved!")
            return True
            
        return False