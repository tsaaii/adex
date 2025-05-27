import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import cv2
from PIL import Image, ImageTk
import os
import datetime
import urllib.request
import numpy as np

import config
from ui_components import HoverButton

class CameraView:
    """Camera view widget with USB, RTSP, HTTP support and zoom functionality"""
    def __init__(self, parent, camera_index=0, camera_type="USB"):
        self.parent = parent
        self.camera_index = camera_index
        self.camera_type = camera_type  # "USB", "RTSP", or "HTTP"
        self.rtsp_url = None
        self.http_url = None
        self.is_running = False
        self.captured_image = None
        self.cap = None
        self.connection_retry_count = 0
        self.max_retries = 3
        
        # Zoom functionality variables
        self.zoom_level = 1.0  # 1.0 = no zoom, 2.0 = 2x zoom, etc.
        self.min_zoom = 1.0
        self.max_zoom = 5.0
        self.zoom_step = 0.2
        self.pan_x = 0  # Horizontal pan offset
        self.pan_y = 0  # Vertical pan offset
        self.is_panning = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        
        # Create frame
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        # Video display - larger size for better zoom experience
        self.canvas = tk.Canvas(self.frame, bg="black", width=200, height=150)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Bind mouse events for zoom and pan
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux scroll down
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.canvas.bind("<Double-Button-1>", self.reset_zoom)
        
        # Draw message on canvas
        self.canvas.create_text(100, 75, text="Click Capture\nMouse wheel: Zoom\nDrag: Pan\nDouble-click: Reset", 
                               fill="white", justify=tk.CENTER)
        
        # Controls frame
        controls = ttk.Frame(self.frame)
        controls.pack(fill=tk.X, padx=2, pady=2)
        
        # Top row of buttons
        top_buttons = ttk.Frame(controls)
        top_buttons.pack(fill=tk.X, pady=1)
        
        self.capture_button = HoverButton(top_buttons, text="Capture", 
                                        bg=config.COLORS["primary"], fg=config.COLORS["button_text"],
                                        padx=2, pady=1, width=8,
                                        command=self.toggle_camera)
        self.capture_button.grid(row=0, column=0, padx=1, pady=1, sticky="ew")
        
        self.save_button = HoverButton(top_buttons, text="Save", 
                                     bg=config.COLORS["secondary"], fg=config.COLORS["button_text"],
                                     padx=2, pady=1, width=8,
                                     command=self.save_image,
                                     state=tk.DISABLED)
        self.save_button.grid(row=0, column=1, padx=1, pady=1, sticky="ew")
        
        # Configure grid columns to be equal
        top_buttons.columnconfigure(0, weight=1)
        top_buttons.columnconfigure(1, weight=1)
        
        # Zoom controls frame
        zoom_frame = ttk.Frame(controls)
        zoom_frame.pack(fill=tk.X, pady=1)
        
        # Zoom out button
        self.zoom_out_btn = HoverButton(zoom_frame, text="−", 
                                       bg=config.COLORS["button_alt"], fg=config.COLORS["button_text"],
                                       padx=2, pady=1, width=3,
                                       command=self.zoom_out)
        self.zoom_out_btn.grid(row=0, column=0, padx=1, pady=1)
        
        # Zoom level display
        self.zoom_var = tk.StringVar(value="1.0x")
        zoom_label = ttk.Label(zoom_frame, textvariable=self.zoom_var, width=6, 
                              font=("Segoe UI", 8), anchor="center")
        zoom_label.grid(row=0, column=1, padx=1, pady=1, sticky="ew")
        
        # Zoom in button
        self.zoom_in_btn = HoverButton(zoom_frame, text="+", 
                                      bg=config.COLORS["button_alt"], fg=config.COLORS["button_text"],
                                      padx=2, pady=1, width=3,
                                      command=self.zoom_in)
        self.zoom_in_btn.grid(row=0, column=2, padx=1, pady=1)
        
        # Reset zoom button
        self.reset_btn = HoverButton(zoom_frame, text="Reset", 
                                    bg=config.COLORS["primary_light"], fg=config.COLORS["text"],
                                    padx=2, pady=1, width=6,
                                    command=self.reset_zoom)
        self.reset_btn.grid(row=0, column=3, padx=1, pady=1, sticky="ew")
        
        # Configure zoom frame grid
        zoom_frame.columnconfigure(1, weight=1)
        zoom_frame.columnconfigure(3, weight=1)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self.frame, textvariable=self.status_var, font=("Segoe UI", 8))
        self.status_label.pack(fill=tk.X, padx=2, pady=1)
        
        # Video thread
        self.video_thread = None
        
        # Save function reference - will be set by the main app
        self.save_function = None
        
    def zoom_in(self):
        """Zoom in the camera view"""
        if self.zoom_level < self.max_zoom:
            self.zoom_level = min(self.zoom_level + self.zoom_step, self.max_zoom)
            self.update_zoom_display()
    
    def zoom_out(self):
        """Zoom out the camera view"""
        if self.zoom_level > self.min_zoom:
            self.zoom_level = max(self.zoom_level - self.zoom_step, self.min_zoom)
            self.update_zoom_display()
            # Reset pan when zooming out to minimum
            if self.zoom_level == self.min_zoom:
                self.pan_x = 0
                self.pan_y = 0
    
    def reset_zoom(self, event=None):
        """Reset zoom and pan to default"""
        self.zoom_level = self.min_zoom
        self.pan_x = 0
        self.pan_y = 0
        self.update_zoom_display()
    
    def update_zoom_display(self):
        """Update the zoom level display"""
        self.zoom_var.set(f"{self.zoom_level:.1f}x")
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel zoom"""
        if not self.is_running:
            return
            
        # Determine zoom direction
        if event.delta > 0 or event.num == 4:  # Zoom in
            self.zoom_in()
        elif event.delta < 0 or event.num == 5:  # Zoom out
            self.zoom_out()
    
    def on_mouse_press(self, event):
        """Handle mouse press for panning"""
        if not self.is_running or self.zoom_level <= self.min_zoom:
            return
            
        self.is_panning = True
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
        self.canvas.configure(cursor="fleur")  # Change cursor to indicate panning
    
    def on_mouse_drag(self, event):
        """Handle mouse drag for panning"""
        if not self.is_panning or not self.is_running:
            return
            
        # Calculate pan delta
        dx = event.x - self.last_mouse_x
        dy = event.y - self.last_mouse_y
        
        # Update pan offset
        self.pan_x += dx
        self.pan_y += dy
        
        # Limit pan to reasonable bounds
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        max_pan_x = canvas_width * (self.zoom_level - 1) / 2
        max_pan_y = canvas_height * (self.zoom_level - 1) / 2
        
        self.pan_x = max(-max_pan_x, min(max_pan_x, self.pan_x))
        self.pan_y = max(-max_pan_y, min(max_pan_y, self.pan_y))
        
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
    
    def on_mouse_release(self, event):
        """Handle mouse release after panning"""
        self.is_panning = False
        self.canvas.configure(cursor="")  # Reset cursor
    
    def apply_zoom_and_pan(self, frame):
        """Apply zoom and pan transformations to the frame"""
        if self.zoom_level <= self.min_zoom:
            return frame
            
        height, width = frame.shape[:2]
        
        # Calculate zoom region
        zoom_width = int(width / self.zoom_level)
        zoom_height = int(height / self.zoom_level)
        
        # Calculate center point with pan offset
        center_x = width // 2 + int(self.pan_x * self.zoom_level / 4)
        center_y = height // 2 + int(self.pan_y * self.zoom_level / 4)
        
        # Ensure the zoom region stays within frame bounds
        x1 = max(0, center_x - zoom_width // 2)
        y1 = max(0, center_y - zoom_height // 2)
        x2 = min(width, x1 + zoom_width)
        y2 = min(height, y1 + zoom_height)
        
        # Adjust if region goes out of bounds
        if x2 - x1 < zoom_width:
            x1 = max(0, x2 - zoom_width)
        if y2 - y1 < zoom_height:
            y1 = max(0, y2 - zoom_height)
        
        # Crop the zoomed region
        zoomed_frame = frame[y1:y2, x1:x2]
        
        # Resize back to original display size
        if zoomed_frame.size > 0:
            return cv2.resize(zoomed_frame, (width, height))
        else:
            return frame
        
    def set_rtsp_config(self, rtsp_url):
        """Set RTSP URL for IP camera
        
        Args:
            rtsp_url: Complete RTSP URL (rtsp://username:password@ip:port/endpoint)
        """
        self.rtsp_url = rtsp_url
        self.camera_type = "RTSP"
        
    def set_http_config(self, http_url):
        """Set HTTP URL for IP camera
        
        Args:
            http_url: Complete HTTP URL (http://username:password@ip:port/endpoint)
        """
        self.http_url = http_url
        self.camera_type = "HTTP"
        
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
            # Initialize camera based on type
            if self.camera_type == "RTSP" and self.rtsp_url:
                self.status_var.set("Connecting to RTSP...")
                self.cap = cv2.VideoCapture(self.rtsp_url)
                # Set buffer size to reduce latency
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                # Set timeout for RTSP connection
                self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
                self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
            elif self.camera_type == "HTTP" and self.http_url:
                self.status_var.set("Connecting to HTTP...")
                # For HTTP streams, we'll handle this in the update thread
                self.cap = None  # We'll use a different approach for HTTP
            else:
                # USB camera
                self.cap = cv2.VideoCapture(self.camera_index)
            
            # Test connection based on camera type
            if self.camera_type == "HTTP":
                # Test HTTP connection
                if not self._test_http_connection():
                    return
            else:
                # Test USB/RTSP connection
                if not self.cap.isOpened():
                    error_msg = "Failed to connect to RTSP camera" if self.camera_type == "RTSP" else "Failed to open USB camera"
                    messagebox.showerror("Camera Error", f"{error_msg}. Please check connection settings.")
                    return
                
                # Test if we can read a frame
                ret, test_frame = self.cap.read()
                if not ret:
                    error_msg = "RTSP stream not responding" if self.camera_type == "RTSP" else "USB camera not responding"
                    messagebox.showerror("Camera Error", f"{error_msg}. Please check camera settings.")
                    if self.cap:
                        self.cap.release()
                    return
            
            # Set status
            if self.camera_type == "HTTP":
                status_msg = "HTTP camera active"
            elif self.camera_type == "RTSP":
                status_msg = "RTSP camera active"
            else:
                status_msg = "USB camera active"
            self.status_var.set(status_msg)
            
            # Reset retry count on successful connection
            self.connection_retry_count = 0
            
            # Start video thread
            self.is_running = True
            self.video_thread = threading.Thread(target=self.update_frame)
            self.video_thread.daemon = True
            self.video_thread.start()
            
            # Update instruction text
            self.canvas.delete("all")
            
        except Exception as e:
            error_msg = f"Error starting {self.camera_type} camera: {str(e)}"
            messagebox.showerror("Camera Error", error_msg)
            self.status_var.set("Connection failed")
    
    def _test_http_connection(self):
        """Test HTTP camera connection"""
        try:
            if not self.http_url:
                messagebox.showerror("Camera Error", "HTTP URL not configured")
                return False
                
            # Try to fetch a frame from HTTP stream
            with urllib.request.urlopen(self.http_url, timeout=5) as response:
                if response.getcode() == 200:
                    return True
                else:
                    messagebox.showerror("Camera Error", f"HTTP camera returned status code: {response.getcode()}")
                    return False
                    
        except Exception as e:
            messagebox.showerror("Camera Error", f"Failed to connect to HTTP camera: {str(e)}")
            return False
    
    def _read_http_frame(self):
        """Read a frame from HTTP stream (MJPEG)"""
        try:
            with urllib.request.urlopen(self.http_url, timeout=2) as response:
                # For MJPEG streams, read until we find a complete JPEG frame
                bytes_data = b''
                while True:
                    chunk = response.read(1024)
                    if not chunk:
                        break
                    bytes_data += chunk
                    
                    # Look for JPEG start and end markers
                    start = bytes_data.find(b'\xff\xd8')  # JPEG start
                    end = bytes_data.find(b'\xff\xd9')    # JPEG end
                    
                    if start != -1 and end != -1 and end > start:
                        # Extract the JPEG frame
                        jpeg_data = bytes_data[start:end+2]
                        
                        # Convert to numpy array and decode
                        nparr = np.frombuffer(jpeg_data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            return True, frame
                        
                        # Remove processed data and continue looking for next frame
                        bytes_data = bytes_data[end+2:]
                        
                return False, None
                
        except Exception as e:
            print(f"HTTP frame read error: {e}")
            return False, None
    
    def update_frame(self):
        """Update the video frame in a separate thread with zoom support"""
        while self.is_running:
            try:
                if self.camera_type == "HTTP":
                    # Handle HTTP stream
                    ret, frame = self._read_http_frame()
                else:
                    # Handle USB/RTSP stream
                    ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    # Reset connection retry count on successful read
                    self.connection_retry_count = 0
                    
                    # Apply zoom and pan to the original frame
                    processed_frame = self.apply_zoom_and_pan(frame)
                    
                    # Store the processed frame for capture
                    self.captured_image = processed_frame.copy()
                    
                    # Convert to RGB for tkinter
                    frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                    # Resize to fit canvas
                    canvas_width = self.canvas.winfo_width()
                    canvas_height = self.canvas.winfo_height()
                    if canvas_width > 1 and canvas_height > 1:
                        frame_resized = cv2.resize(frame_rgb, (canvas_width, canvas_height))
                    else:
                        frame_resized = cv2.resize(frame_rgb, (200, 150))
                    
                    # Convert to PhotoImage
                    img = Image.fromarray(frame_resized)
                    img_tk = ImageTk.PhotoImage(image=img)
                    
                    # Update canvas in main thread
                    if self.is_running:
                        self.parent.after_idle(lambda i=img_tk: self._update_canvas(i) if self.is_running else None)
                    
                    # Enable save button
                    if self.is_running:
                        self.parent.after_idle(self._enable_save)
                    
                    # Short delay based on camera type
                    if self.camera_type == "HTTP":
                        time.sleep(0.1)  # Slower for HTTP streams
                    else:
                        time.sleep(0.033)  # ~30 FPS for USB/RTSP
                else:
                    # Camera disconnected or stream interrupted
                    if (self.camera_type in ["RTSP", "HTTP"]) and self.connection_retry_count < self.max_retries:
                        # Try to reconnect for RTSP/HTTP cameras
                        self.connection_retry_count += 1
                        print(f"{self.camera_type} connection lost, retrying... ({self.connection_retry_count}/{self.max_retries})")
                        
                        if self.parent.winfo_exists():
                            self.parent.after_idle(lambda: self.status_var.set(f"Reconnecting... ({self.connection_retry_count}/{self.max_retries})"))
                        
                        # Release and reconnect for RTSP
                        if self.camera_type == "RTSP" and self.cap:
                            self.cap.release()
                            time.sleep(2)  # Wait before retry
                            
                            if self.is_running:  # Check if still supposed to be running
                                self.cap = cv2.VideoCapture(self.rtsp_url)
                                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                                self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
                                self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
                        elif self.camera_type == "HTTP":
                            # For HTTP, just wait and try again
                            time.sleep(2)
                        continue
                    else:
                        # Max retries reached or USB camera disconnected
                        self.is_running = False
                        if self.parent.winfo_exists():
                            self.parent.after_idle(self._camera_error)
                        break
                        
            except Exception as e:
                print(f"Camera error: {str(e)}")
                if self.camera_type in ["RTSP", "HTTP"] and self.connection_retry_count < self.max_retries:
                    self.connection_retry_count += 1
                    time.sleep(2)
                    continue
                else:
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
            if self.camera_type == "HTTP":
                error_msg = "HTTP connection failed"
            elif self.camera_type == "RTSP":
                error_msg = "RTSP connection failed"
            else:
                error_msg = "USB camera error"
            self.status_var.set(f"{error_msg} - please try again")
            self.stop_camera()
            self.capture_button.config(text="Capture")

    def save_image(self):
        """Call the save function provided by main app"""
        if not self.captured_image:
            self.status_var.set("Please capture an image first")
            return
            
        if self.save_function:
            # Check if user explicitly confirmed to save the image
            should_save = messagebox.askyesno("Confirm Save", 
                                            f"Do you want to save this image?\n(Zoom: {self.zoom_level:.1f}x)",
                                            default=messagebox.YES)
            if not should_save:
                return
                
            # Now proceed with saving
            if self.save_function(self.captured_image):
                # Stop the camera after successful save
                self.stop_camera()
                self.capture_button.config(text="Capture")
                self.save_button.config(state=tk.DISABLED)
                # Clear canvas and show saved message
                self.canvas.delete("all")
                self.canvas.create_text(100, 75, text="Image Saved\nClick Capture for new", 
                                    fill="white", justify=tk.CENTER)
            else:
                self.status_var.set("Error saving image")
        else:
            self.status_var.set("Save function not configured")
    
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
        
        # Reset zoom and pan
        self.reset_zoom()
        
        # Update status
        self.status_var.set("Ready")
        self.save_button.config(state=tk.DISABLED)
        self.connection_retry_count = 0
        
        # Show instruction text
        self.canvas.delete("all")
        self.canvas.create_text(100, 75, text="Click Capture\nMouse wheel: Zoom\nDrag: Pan\nDouble-click: Reset", 
                               fill="white", justify=tk.CENTER)

def add_watermark(image, text, ticket_id=None):
    """Add a watermark to an image with sitename, vehicle number, timestamp, and ticket ID
    
    Args:
        image: The image to add watermark to
        text: Main watermark text (site, vehicle, timestamp)
        ticket_id: Ticket ID to display in top left corner
    """
    # Create a copy of the image
    result = image.copy()
    
    # Get image dimensions
    height, width = result.shape[:2]
    
    # Set up watermark text properties
    font = cv2.FONT_HERSHEY_SIMPLEX
    main_font_scale = 0.7
    ticket_font_scale = 0.8
    color = (255, 255, 255)  # White color
    main_thickness = 2
    ticket_thickness = 2
    
    # Add ticket ID watermark in top left corner
    if ticket_id:
        ticket_text = f"Ticket: {ticket_id}"
        
        # Calculate text size for background rectangle
        (text_width, text_height), baseline = cv2.getTextSize(ticket_text, font, ticket_font_scale, ticket_thickness)
        
        # Add semi-transparent background for ticket ID (top left)
        overlay_ticket = result.copy()
        cv2.rectangle(overlay_ticket, (0, 0), (text_width + 20, text_height + 20), (0, 0, 0), -1)
        cv2.addWeighted(overlay_ticket, 0.6, result, 0.4, 0, result)
        
        # Add ticket ID text
        cv2.putText(result, ticket_text, (10, text_height + 10), font, ticket_font_scale, color, ticket_thickness)
    
    # Add main watermark in bottom area
    if text:
        # Calculate text size for main watermark
        (main_text_width, main_text_height), main_baseline = cv2.getTextSize(text, font, main_font_scale, main_thickness)
        
        # Add semi-transparent overlay for better text visibility (bottom)
        overlay_main = result.copy()
        cv2.rectangle(overlay_main, (0, height - main_text_height - 20), (width, height), (0, 0, 0), -1)
        cv2.addWeighted(overlay_main, 0.5, result, 0.5, 0, result)
        
        # Add main watermark text
        cv2.putText(result, text, (10, height - 10), font, main_font_scale, color, main_thickness)
    
    return result