import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import cv2
from PIL import Image, ImageTk
import os
import datetime

import config
from ui_components import HoverButton

class CameraView:
    """Camera view widget with simplified interface"""
    def __init__(self, parent, camera_index=0):
        self.parent = parent
        self.camera_index = camera_index
        self.is_running = False
        self.captured_image = None
        self.cap = None
        
        # Create frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        # Video display - compact size
        self.canvas = tk.Canvas(self.frame, bg="black", width=150, height=120)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Draw message on canvas
        self.canvas.create_text(75, 60, text="Click Capture", fill="white", justify=tk.CENTER)
        
        # Controls frame
        controls = ttk.Frame(self.frame)
        controls.pack(fill=tk.X, padx=2, pady=2)
        
        # Buttons - using grid for better organization
        self.capture_button = HoverButton(controls, text="Capture", 
                                        bg=config.COLORS["primary"], fg=config.COLORS["button_text"],
                                        padx=2, pady=1, width=6,
                                        command=self.toggle_camera)
        self.capture_button.grid(row=0, column=0, padx=1, pady=1, sticky="ew")
        
        self.save_button = HoverButton(controls, text="Save", 
                                     bg=config.COLORS["secondary"], fg=config.COLORS["button_text"],
                                     padx=2, pady=1, width=6,
                                     command=self.save_image,
                                     state=tk.DISABLED)
        self.save_button.grid(row=0, column=1, padx=1, pady=1, sticky="ew")
        
        # Configure grid columns to be equal
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self.frame, textvariable=self.status_var)
        self.status_label.pack(fill=tk.X, padx=2, pady=2)
        
        # Video thread
        self.video_thread = None
        
        # Save function reference - will be set by the main app
        self.save_function = None
        
    def toggle_camera(self):
        """Start or stop the camera"""
        if not self.is_running:
            self.start_camera()
            self.capture_button.config(text="Stop")
        else:
            self.stop_camera()
            self.capture_button.config(text="Capture")
    
    def start_camera(self):
        """Start the camera feed"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                messagebox.showerror("Camera Error", "Failed to open camera.")
                return
            
            # Set status
            self.status_var.set("Camera active")
            
            # Start video thread
            self.is_running = True
            self.video_thread = threading.Thread(target=self.update_frame)
            self.video_thread.daemon = True
            self.video_thread.start()
            
        except Exception as e:
            messagebox.showerror("Camera Error", f"Error starting camera: {str(e)}")
    
    def update_frame(self):
        """Update the video frame in a separate thread"""
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                if ret:
                    # Capture frame
                    self.captured_image = frame.copy()
                    
                    # Convert to RGB for tkinter
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    # Resize to fit smaller canvas
                    frame_resized = cv2.resize(frame_rgb, (150, 120))
                    # Convert to PhotoImage
                    img = Image.fromarray(frame_resized)
                    img_tk = ImageTk.PhotoImage(image=img)
                    
                    # Update canvas in main thread
                    if self.is_running:
                        self.parent.after_idle(lambda i=img_tk: self._update_canvas(i) if self.is_running else None)
                    
                    # Enable save button
                    if self.is_running:
                        self.parent.after_idle(self._enable_save)
                    
                    # Short delay
                    time.sleep(0.05)
                else:
                    # Camera disconnected
                    self.is_running = False
                    if self.parent.winfo_exists():
                        self.parent.after_idle(self._camera_error)
                    break
            except Exception as e:
                print(f"Camera error: {str(e)}")
                self.is_running = False
                if self.parent.winfo_exists():
                    self.parent.after_idle(self._camera_error)
                break
    
    def _enable_save(self):
        """Enable the save button from main thread"""
        if self.is_running:
            self.save_button.config(state=tk.NORMAL)
    
    def _update_canvas(self, img_tk):
        """Update canvas with new image (called from main thread)"""
        if self.is_running and self.parent.winfo_exists():
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
            self.canvas.image = img_tk  # Keep reference
    
    def _camera_error(self):
        """Handle camera errors (called from main thread)"""
        if self.parent.winfo_exists():
            self.status_var.set("Camera error - please try again")
            self.stop_camera()
            self.capture_button.config(text="Capture")
    
    def save_image(self):
        """Call the save function provided by main app"""
        if self.save_function and self.captured_image is not None:
            if self.save_function(self.captured_image):
                # Stop the camera after successful save
                self.stop_camera()
                self.capture_button.config(text="Capture")
                self.save_button.config(state=tk.DISABLED)
                # Clear canvas and show saved message
                self.canvas.delete("all")
                self.canvas.create_text(75, 60, text="Image Saved\nClick Capture for new", 
                                      fill="white", justify=tk.CENTER)
        else:
            self.status_var.set("Please capture an image first")
    
    def stop_camera(self):
        """Stop the camera feed"""
        self.is_running = False
        
        # Wait for thread to complete
        if self.video_thread and self.video_thread.is_alive():
            self.video_thread.join(0.5)
        
        # Release camera
        if self.cap:
            self.cap.release()
            self.cap = None
        
        # Update status
        self.status_var.set("Ready")
        self.save_button.config(state=tk.DISABLED)

def add_watermark(image, text):
    """Add a watermark to an image with sitename, vehicle number and timestamp"""
    # Create a copy of the image
    result = image.copy()
    
    # Get image dimensions
    height, width = result.shape[:2]
    
    # Set up watermark text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    color = (255, 255, 255)  # White color
    thickness = 2
    
    # Add semi-transparent overlay for better text visibility
    overlay = result.copy()
    cv2.rectangle(overlay, (0, height - 40), (width, height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, result, 0.5, 0, result)
    
    # Add text
    cv2.putText(result, text, (10, height - 15), font, font_scale, color, thickness)
    
    return result