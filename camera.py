# Enhanced camera.py - Continuous RTSP feed implementation

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
import queue

import config
from ui_components import HoverButton

class ContinuousCameraView:
    """Enhanced camera view with continuous RTSP feed and optimized performance"""
    
    def __init__(self, parent, camera_index=0, camera_type="USB", auto_start=True):
        self.parent = parent
        self.camera_index = camera_index
        self.camera_type = camera_type
        self.rtsp_url = None
        self.http_url = None
        self.auto_start = auto_start
        
        # Continuous feed control
        self.is_running = False
        self.is_capturing_continuous = False
        self.video_thread = None
        self.connection_retry_count = 0
        self.max_retries = 3
        
        # Frame management
        self.current_frame = None
        self.captured_image = None
        self.frame_lock = threading.Lock()
        self.frame_queue = queue.Queue(maxsize=2)  # Small buffer to prevent memory issues
        
        # Performance optimization
        self.last_frame_time = 0
        self.target_fps = 15  # Reduced FPS for RTSP to save bandwidth
        self.frame_skip_count = 0
        self.max_frame_skip = 2  # Skip frames to improve performance
        
        # Connection state
        self.connection_stable = False
        self.connection_attempts = 0
        self.last_successful_frame = 0
        
        # Zoom functionality
        self.zoom_level = 1.0
        self.min_zoom = 1.0
        self.max_zoom = 5.0
        self.zoom_step = 0.2
        self.pan_x = 0
        self.pan_y = 0
        self.is_panning = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        
        # Create UI
        self.create_ui()
        
        # Auto-start continuous feed if enabled
        if self.auto_start:
            self.start_continuous_feed()
    
    def create_ui(self):
        """Create the camera UI with enhanced controls"""
        # Main frame
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
        
        # Video display canvas - larger for better viewing
        self.canvas = tk.Canvas(self.frame, bg="black", width=280, height=210)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Bind mouse events for zoom and pan
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.canvas.bind("<Double-Button-1>", self.reset_zoom)
        
        # Initial message
        self.show_status_message("Starting camera feed...")
        
        # Controls frame
        controls = ttk.Frame(self.frame)
        controls.pack(fill=tk.X, padx=2, pady=2)
        
        # Top row - main controls
        main_controls = ttk.Frame(controls)
        main_controls.pack(fill=tk.X, pady=1)
        
        # Start/Stop continuous feed button
        self.feed_button = HoverButton(main_controls, text="Stop Feed", 
                                      bg=config.COLORS["error"], fg=config.COLORS["button_text"],
                                      padx=2, pady=1, width=8,
                                      command=self.toggle_continuous_feed)
        self.feed_button.grid(row=0, column=0, padx=1, pady=1, sticky="ew")
        
        # Capture current frame button
        self.capture_button = HoverButton(main_controls, text="Capture", 
                                        bg=config.COLORS["primary"], fg=config.COLORS["button_text"],
                                        padx=2, pady=1, width=8,
                                        command=self.capture_current_frame)
        self.capture_button.grid(row=0, column=1, padx=1, pady=1, sticky="ew")
        
        # Save captured image button
        self.save_button = HoverButton(main_controls, text="Save", 
                                     bg=config.COLORS["secondary"], fg=config.COLORS["button_text"],
                                     padx=2, pady=1, width=8,
                                     command=self.save_image,
                                     state=tk.DISABLED)
        self.save_button.grid(row=0, column=2, padx=1, pady=1, sticky="ew")
        
        # Configure grid columns
        main_controls.columnconfigure(0, weight=1)
        main_controls.columnconfigure(1, weight=1)
        main_controls.columnconfigure(2, weight=1)
        
        # Zoom controls
        zoom_frame = ttk.Frame(controls)
        zoom_frame.pack(fill=tk.X, pady=1)
        
        self.zoom_out_btn = HoverButton(zoom_frame, text="−", 
                                       bg=config.COLORS["button_alt"], fg=config.COLORS["button_text"],
                                       padx=2, pady=1, width=3,
                                       command=self.zoom_out)
        self.zoom_out_btn.grid(row=0, column=0, padx=1, pady=1)
        
        self.zoom_var = tk.StringVar(value="1.0x")
        zoom_label = ttk.Label(zoom_frame, textvariable=self.zoom_var, width=6, 
                              font=("Segoe UI", 8), anchor="center")
        zoom_label.grid(row=0, column=1, padx=1, pady=1, sticky="ew")
        
        self.zoom_in_btn = HoverButton(zoom_frame, text="+", 
                                      bg=config.COLORS["button_alt"], fg=config.COLORS["button_text"],
                                      padx=2, pady=1, width=3,
                                      command=self.zoom_in)
        self.zoom_in_btn.grid(row=0, column=2, padx=1, pady=1)
        
        self.reset_btn = HoverButton(zoom_frame, text="Reset", 
                                    bg=config.COLORS["primary_light"], fg=config.COLORS["text"],
                                    padx=2, pady=1, width=6,
                                    command=self.reset_zoom)
        self.reset_btn.grid(row=0, column=3, padx=1, pady=1, sticky="ew")
        
        zoom_frame.columnconfigure(1, weight=1)
        zoom_frame.columnconfigure(3, weight=1)
        
        # Status labels
        status_frame = ttk.Frame(controls)
        status_frame.pack(fill=tk.X, pady=1)
        
        self.status_var = tk.StringVar(value="Initializing...")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                     font=("Segoe UI", 7), foreground="blue")
        self.status_label.pack(side=tk.LEFT, padx=2)
        
        # FPS indicator
        self.fps_var = tk.StringVar(value="FPS: --")
        self.fps_label = ttk.Label(status_frame, textvariable=self.fps_var, 
                                  font=("Segoe UI", 7), foreground="green")
        self.fps_label.pack(side=tk.RIGHT, padx=2)
        
        # Save function reference
        self.save_function = None
    
    def show_status_message(self, message):
        """Show a status message on the canvas"""
        self.canvas.delete("all")
        canvas_width = self.canvas.winfo_width() or 280
        canvas_height = self.canvas.winfo_height() or 210
        
        self.canvas.create_text(canvas_width//2, canvas_height//2, 
                               text=message, fill="white", 
                               font=("Segoe UI", 10), justify=tk.CENTER)
    
    def set_rtsp_config(self, rtsp_url):
        """Set RTSP URL for IP camera"""
        self.rtsp_url = rtsp_url
        self.camera_type = "RTSP"
        
        # Restart feed if it's running
        if self.is_capturing_continuous:
            self.restart_feed()
    
    def set_http_config(self, http_url):
        """Set HTTP URL for IP camera"""
        self.http_url = http_url
        self.camera_type = "HTTP"
        
        # Restart feed if it's running
        if self.is_capturing_continuous:
            self.restart_feed()
    
    def start_continuous_feed(self):
        """Start continuous video feed"""
        if self.is_capturing_continuous:
            return
        
        try:
            # Initialize camera connection
            success = self._initialize_camera_connection()
            
            if not success:
                self.show_status_message(f"Failed to connect to {self.camera_type} camera\nClick 'Start Feed' to retry")
                self.status_var.set("Connection failed")
                return
            
            # Start continuous capture
            self.is_capturing_continuous = True
            self.is_running = True
            
            # Start the video thread
            self.video_thread = threading.Thread(target=self._continuous_feed_loop, daemon=True)
            self.video_thread.start()
            
            # Start UI update thread
            self._start_ui_updater()
            
            # Update UI
            self.feed_button.config(text="Stop Feed", bg=config.COLORS["error"])
            self.status_var.set(f"{self.camera_type} feed active")
            
        except Exception as e:
            self.show_status_message(f"Error starting feed:\n{str(e)}")
            self.status_var.set("Startup error")
    
    def _initialize_camera_connection(self):
        """Initialize camera connection based on type"""
        try:
            if self.camera_type == "RTSP" and self.rtsp_url:
                self.cap = cv2.VideoCapture(self.rtsp_url)
                # Optimize RTSP settings
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
                self.cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
                # Set lower resolution for better performance
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                
            elif self.camera_type == "HTTP" and self.http_url:
                # HTTP will be handled differently in the loop
                self.cap = None
                return self._test_http_connection()
                
            else:  # USB camera
                self.cap = cv2.VideoCapture(self.camera_index)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            # Test connection for USB/RTSP
            if self.cap and self.cap.isOpened():
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    self.connection_stable = True
                    self.last_successful_frame = time.time()
                    return True
            
            return False
            
        except Exception as e:
            print(f"Camera initialization error: {e}")
            return False
    
    def _test_http_connection(self):
        """Test HTTP camera connection"""
        try:
            if not self.http_url:
                return False
            with urllib.request.urlopen(self.http_url, timeout=5) as response:
                return response.getcode() == 200
        except:
            return False
    
    def _continuous_feed_loop(self):
        """Main continuous feed loop running in separate thread"""
        last_fps_update = time.time()
        frame_count = 0
        
        while self.is_capturing_continuous and self.is_running:
            try:
                current_time = time.time()
                
                # Frame rate limiting
                if current_time - self.last_frame_time < (1.0 / self.target_fps):
                    time.sleep(0.01)
                    continue
                
                # Read frame based on camera type
                if self.camera_type == "HTTP":
                    ret, frame = self._read_http_frame()
                else:
                    ret, frame = self.cap.read() if self.cap else (False, None)
                
                if ret and frame is not None:
                    # Frame skip for performance (only for RTSP)
                    if self.camera_type == "RTSP":
                        self.frame_skip_count += 1
                        if self.frame_skip_count < self.max_frame_skip:
                            continue
                        self.frame_skip_count = 0
                    
                    # Apply zoom and pan
                    processed_frame = self.apply_zoom_and_pan(frame)
                    
                    # Thread-safe frame update
                    with self.frame_lock:
                        self.current_frame = processed_frame.copy()
                    
                    # Add to queue for UI update (non-blocking)
                    try:
                        self.frame_queue.put_nowait(processed_frame)
                    except queue.Full:
                        # Remove old frame and add new one
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put_nowait(processed_frame)
                        except queue.Empty:
                            pass
                    
                    # Update timing
                    self.last_frame_time = current_time
                    self.last_successful_frame = current_time
                    frame_count += 1
                    
                    # Reset connection retry count on successful read
                    self.connection_retry_count = 0
                    self.connection_stable = True
                    
                    # Update FPS counter
                    if current_time - last_fps_update >= 1.0:
                        actual_fps = frame_count / (current_time - last_fps_update)
                        self.parent.after_idle(lambda: self.fps_var.set(f"FPS: {actual_fps:.1f}"))
                        frame_count = 0
                        last_fps_update = current_time
                
                else:
                    # Handle connection issues
                    self._handle_connection_loss()
                
            except Exception as e:
                print(f"Feed loop error: {e}")
                self._handle_connection_loss()
    
    def _handle_connection_loss(self):
        """Handle connection loss and implement reconnection logic"""
        self.connection_stable = False
        current_time = time.time()
        
        # Check if we've been without frames for too long
        if current_time - self.last_successful_frame > 10:  # 10 seconds timeout
            if self.connection_retry_count < self.max_retries:
                self.connection_retry_count += 1
                self.parent.after_idle(lambda: self.status_var.set(f"Reconnecting... ({self.connection_retry_count}/{self.max_retries})"))
                
                # Attempt reconnection
                if self.cap:
                    self.cap.release()
                
                time.sleep(2)  # Wait before retry
                
                if self._initialize_camera_connection():
                    self.last_successful_frame = time.time()
                    self.parent.after_idle(lambda: self.status_var.set(f"{self.camera_type} reconnected"))
                else:
                    self.parent.after_idle(lambda: self.status_var.set(f"Reconnection {self.connection_retry_count} failed"))
            else:
                # Max retries reached
                self.parent.after_idle(self._stop_feed_due_to_error)
        
        time.sleep(0.1)  # Short delay before next attempt
    
    def _start_ui_updater(self):
        """Start UI update loop"""
        self._update_display()
    
    def _update_display(self):
        """Update the display with the latest frame"""
        if not self.is_capturing_continuous:
            return
        
        try:
            # Get frame from queue (non-blocking)
            try:
                frame = self.frame_queue.get_nowait()
            except queue.Empty:
                # No new frame, schedule next update
                self.parent.after(33, self._update_display)  # ~30 FPS UI update
                return
            
            # Convert to RGB for tkinter
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize to fit canvas
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                frame_resized = cv2.resize(frame_rgb, (canvas_width, canvas_height))
            else:
                frame_resized = cv2.resize(frame_rgb, (280, 210))
            
            # Convert to PhotoImage and display
            img = Image.fromarray(frame_resized)
            img_tk = ImageTk.PhotoImage(image=img)
            
            # Update canvas
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
            self.canvas.image = img_tk  # Keep reference
            
        except Exception as e:
            print(f"Display update error: {e}")
        
        # Schedule next update
        self.parent.after(33, self._update_display)  # ~30 FPS UI update
    
    def _read_http_frame(self):
        """Read frame from HTTP stream"""
        try:
            if not self.http_url:
                return False, None
            
            with urllib.request.urlopen(self.http_url, timeout=2) as response:
                bytes_data = b''
                while True:
                    chunk = response.read(1024)
                    if not chunk:
                        break
                    bytes_data += chunk
                    
                    start = bytes_data.find(b'\xff\xd8')
                    end = bytes_data.find(b'\xff\xd9')
                    
                    if start != -1 and end != -1 and end > start:
                        jpeg_data = bytes_data[start:end+2]
                        nparr = np.frombuffer(jpeg_data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            return True, frame
                        
                        bytes_data = bytes_data[end+2:]
                
                return False, None
                
        except Exception as e:
            return False, None
    
    def toggle_continuous_feed(self):
        """Toggle continuous feed on/off"""
        if self.is_capturing_continuous:
            self.stop_continuous_feed()
        else:
            self.start_continuous_feed()
    
    def stop_continuous_feed(self):
        """Stop continuous video feed"""
        self.is_capturing_continuous = False
        self.is_running = False
        
        # Wait for thread to complete
        if self.video_thread and self.video_thread.is_alive():
            self.video_thread.join(timeout=1.0)
        
        # Release camera
        if self.cap:
            self.cap.release()
            self.cap = None
        
        # Clear frame queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
        
        # Reset zoom and pan
        self.reset_zoom()
        
        # Update UI
        self.feed_button.config(text="Start Feed", bg=config.COLORS["primary"])
        self.status_var.set("Feed stopped")
        self.fps_var.set("FPS: --")
        
        # Show startup message
        self.show_status_message("Camera feed stopped\nClick 'Start Feed' to resume")
    
    def _stop_feed_due_to_error(self):
        """Stop feed due to error"""
        self.stop_continuous_feed()
        self.show_status_message("Connection lost\nClick 'Start Feed' to retry")
        self.status_var.set("Connection failed")
    
    def restart_feed(self):
        """Restart the feed (useful when settings change)"""
        if self.is_capturing_continuous:
            self.stop_continuous_feed()
            time.sleep(0.5)  # Brief pause
            self.start_continuous_feed()
    
    def capture_current_frame(self):
        """Capture the current frame for saving"""
        try:
            if self.current_frame is not None:
                with self.frame_lock:
                    self.captured_image = self.current_frame.copy()
                
                self.save_button.config(state=tk.NORMAL)
                self.status_var.set("Frame captured - click Save to store")
                print(f"Frame captured successfully, shape: {self.captured_image.shape}")
            else:
                self.status_var.set("No live frame available - start feed first")
                print("No current frame available for capture")
        except Exception as e:
            self.status_var.set(f"Capture error: {str(e)}")
            print(f"Error capturing frame: {e}")
    
    def save_image(self):
        """Save the captured image"""
        try:
            print(f"Save image called - captured_image exists: {self.captured_image is not None}")
            print(f"Save function exists: {self.save_function is not None}")
            
            if self.captured_image is None:
                self.status_var.set("No image captured - click Capture first")
                print("No captured image available")
                return
            
            if self.save_function is None:
                self.status_var.set("Save function not configured")
                print("Save function not set")
                return
            
            # Call the save function with the captured image
            print("Calling save function...")
            success = self.save_function(self.captured_image)
            print(f"Save function returned: {success}")
            
            if success:
                self.status_var.set("Image saved successfully!")
                self.save_button.config(state=tk.DISABLED)
                self.captured_image = None
                print("Image saved and cleared")
            else:
                self.status_var.set("Failed to save image")
                print("Save function returned False")
                
        except Exception as e:
            error_msg = f"Save error: {str(e)}"
            self.status_var.set(error_msg)
            print(f"Exception in save_image: {e}")
            import traceback
            traceback.print_exc()
    
    # Zoom and pan methods (same as before)
    def zoom_in(self):
        if self.zoom_level < self.max_zoom:
            self.zoom_level = min(self.zoom_level + self.zoom_step, self.max_zoom)
            self.update_zoom_display()
    
    def zoom_out(self):
        if self.zoom_level > self.min_zoom:
            self.zoom_level = max(self.zoom_level - self.zoom_step, self.min_zoom)
            self.update_zoom_display()
            if self.zoom_level == self.min_zoom:
                self.pan_x = 0
                self.pan_y = 0
    
    def reset_zoom(self, event=None):
        self.zoom_level = self.min_zoom
        self.pan_x = 0
        self.pan_y = 0
        self.update_zoom_display()
    
    def update_zoom_display(self):
        self.zoom_var.set(f"{self.zoom_level:.1f}x")
    
    def on_mouse_wheel(self, event):
        if not self.is_capturing_continuous:
            return
        if event.delta > 0 or event.num == 4:
            self.zoom_in()
        elif event.delta < 0 or event.num == 5:
            self.zoom_out()
    
    def on_mouse_press(self, event):
        if not self.is_capturing_continuous or self.zoom_level <= self.min_zoom:
            return
        self.is_panning = True
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
        self.canvas.configure(cursor="fleur")
    
    def on_mouse_drag(self, event):
        if not self.is_panning or not self.is_capturing_continuous:
            return
        dx = event.x - self.last_mouse_x
        dy = event.y - self.last_mouse_y
        self.pan_x += dx
        self.pan_y += dy
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        max_pan_x = canvas_width * (self.zoom_level - 1) / 2
        max_pan_y = canvas_height * (self.zoom_level - 1) / 2
        
        self.pan_x = max(-max_pan_x, min(max_pan_x, self.pan_x))
        self.pan_y = max(-max_pan_y, min(max_pan_y, self.pan_y))
        
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
    
    def on_mouse_release(self, event):
        self.is_panning = False
        self.canvas.configure(cursor="")
    
    def apply_zoom_and_pan(self, frame):
        """Apply zoom and pan transformations"""
        if self.zoom_level <= self.min_zoom:
            return frame
        
        height, width = frame.shape[:2]
        zoom_width = int(width / self.zoom_level)
        zoom_height = int(height / self.zoom_level)
        
        center_x = width // 2 + int(self.pan_x * self.zoom_level / 4)
        center_y = height // 2 + int(self.pan_y * self.zoom_level / 4)
        
        x1 = max(0, center_x - zoom_width // 2)
        y1 = max(0, center_y - zoom_height // 2)
        x2 = min(width, x1 + zoom_width)
        y2 = min(height, y1 + zoom_height)
        
        if x2 - x1 < zoom_width:
            x1 = max(0, x2 - zoom_width)
        if y2 - y1 < zoom_height:
            y1 = max(0, y2 - zoom_height)
        
        zoomed_frame = frame[y1:y2, x1:x2]
        
        if zoomed_frame.size > 0:
            return cv2.resize(zoomed_frame, (width, height))
        else:
            return frame

# Keep the original CameraView class for backward compatibility
CameraView = ContinuousCameraView

# Watermark function remains the same
def add_watermark(image, text, ticket_id=None):
    """Add a watermark to an image with sitename, vehicle number, timestamp, and ticket ID"""
    result = image.copy()
    height, width = result.shape[:2]
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    main_font_scale = 0.7
    ticket_font_scale = 0.8
    color = (255, 255, 255)
    main_thickness = 2
    ticket_thickness = 2
    
    if ticket_id:
        ticket_text = f"Ticket: {ticket_id}"
        (text_width, text_height), baseline = cv2.getTextSize(ticket_text, font, ticket_font_scale, ticket_thickness)
        
        overlay_ticket = result.copy()
        cv2.rectangle(overlay_ticket, (0, 0), (text_width + 20, text_height + 20), (0, 0, 0), -1)
        cv2.addWeighted(overlay_ticket, 0.6, result, 0.4, 0, result)
        
        cv2.putText(result, ticket_text, (10, text_height + 10), font, ticket_font_scale, color, ticket_thickness)
    
    if text:
        (main_text_width, main_text_height), main_baseline = cv2.getTextSize(text, font, main_font_scale, main_thickness)
        
        overlay_main = result.copy()
        cv2.rectangle(overlay_main, (0, height - main_text_height - 20), (width, height), (0, 0, 0), -1)
        cv2.addWeighted(overlay_main, 0.5, result, 0.5, 0, result)
        
        cv2.putText(result, text, (10, height - 10), font, main_font_scale, color, main_thickness)
    
    return result