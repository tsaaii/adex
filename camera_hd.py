# Enhanced camera.py - Using exact UI structure with HD capture from test script
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
import psutil
import gc
import warnings
import sys

# Completely suppress all OpenCV/FFMPEG output (from test script)
cv2.setLogLevel(0)
warnings.filterwarnings("ignore")

# Redirect stderr to suppress codec errors (from test script)
class SuppressStderr:
    def __enter__(self):
        self.original_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr.close()
        sys.stderr = self.original_stderr

# Import the unified logging system (from existing code)
try:
    from unified_logging import setup_enhanced_logger
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False
    print("⚠️ Unified logging not available - falling back to print statements")

try:
    import config
    from ui_components import HoverButton
except ImportError:
    # Fallback config and button
    class config:
        COLORS = {
            'primary': '#1976D2',
            'secondary': '#00BCD4',
            'warning': '#FF9800',
            'button_text': 'white'
        }
        LOGS_FOLDER = "logs"
    
    class HoverButton(tk.Button):
        def __init__(self, parent, **kwargs):
            super().__init__(parent, **kwargs)

class OptimizedCameraView:
    """Camera view using exact UI structure with HD capture from test script"""
    
    def __init__(self, parent, camera_index=0, camera_type="USB", camera_name="Camera", auto_start=True):
        # Setup logging first
        self.camera_name = camera_name
        self.setup_logging()
        
        self.parent = parent
        self.camera_index = camera_index
        self.camera_type = camera_type
        self.rtsp_url = None
        self.http_url = None
        
        # HD settings from test script
        self.min_hd_width = 1280
        self.min_hd_height = 720
        self.jpeg_quality = 95
        self.buffer_size = 3
        self.target_fps = 25
        self.stable_frames_required = 3
        
        # Performance optimization settings (from existing code)
        self.max_fps = 15
        self.min_fps = 5
        self.adaptive_quality = True
        self.frame_skip_threshold = 80
        
        # Resource monitoring
        self.cpu_usage = 0
        self.memory_usage = 0
        self.last_resource_check = 0
        self.resource_check_interval = 2.0
        
        # Feed control with auto-restart capability
        self.is_running = False
        self.should_be_running = True
        self.video_thread = None
        self.cap = None
        self.camera_available = False
        self.auto_reconnect = True
        self.reconnect_delay = 5.0
        
        # Threading events (from existing code)
        self.stop_event = threading.Event()
        self.frame_ready_event = threading.Event()
        
        # Frame management with HD support
        self.current_frame = None
        self.captured_image = None
        self.frame_lock = threading.Lock()
        self.display_frame = None
        
        # Frame buffer (from existing code)
        self.frame_buffer = {
            'raw_frame': None,
            'processed_frame': None,
            'timestamp': 0,
            'buffer_lock': threading.Lock()
        }
        
        # Performance tracking
        self.last_frame_time = 0
        self.frame_count = 0
        self.fps_counter = 0
        self.fps_timer = time.time()
        self.dropped_frames = 0
        self.total_frames = 0
        self.frame_skip_counter = 0
        self.stable_frame_counter = 0  # HD stability tracking
        
        # Connection state
        self.connection_stable = False
        self.last_error_time = 0
        self.error_cooldown = 3
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.connection_attempts = 0
        self.last_successful_frame = None
        
        # Zoom functionality
        self.zoom_level = 1.0
        self.min_zoom = 1.0
        self.max_zoom = 3.0
        self.zoom_step = 0.1
        self.pan_x = 0
        self.pan_y = 0
        self.is_panning = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        
        # Create UI (exact structure from existing code)
        self.create_ui()
        
        # Start resource monitoring
        self.start_resource_monitoring()
        
        # Auto-start camera feed
        self.start_continuous_feed()
        
        # Start watchdog
        self.start_watchdog()
    
    def setup_logging(self):
        """Setup enhanced logging for camera operations"""
        try:
            if LOGGING_AVAILABLE:
                logger_name = f"camera_{self.camera_name.lower().replace(' ', '_')}"
                self.logger = setup_enhanced_logger(logger_name, config.LOGS_FOLDER)
                self.logger.info(f"Enhanced logging initialized for {self.camera_name} camera")
            else:
                self.logger = self._create_fallback_logger()
        except Exception as e:
            print(f"⚠️ Could not setup camera logging: {e}")
            self.logger = self._create_fallback_logger()
    
    def _create_fallback_logger(self):
        """Create a fallback logger that prints to console"""
        class FallbackLogger:
            def __init__(self, camera_name):
                self.camera_name = camera_name
            
            def info(self, msg): print(f"INFO: {self.camera_name} - {msg}")
            def warning(self, msg): print(f"WARNING: {self.camera_name} - {msg}")
            def error(self, msg): print(f"ERROR: {self.camera_name} - {msg}")
            def debug(self, msg): print(f"DEBUG: {self.camera_name} - {msg}")
            def critical(self, msg): print(f"CRITICAL: {self.camera_name} - {msg}")
            def print_info(self, msg): print(f"ℹ️ {self.camera_name} - {msg}")
            def print_success(self, msg): print(f"✅ {self.camera_name} - {msg}")
            def print_warning(self, msg): print(f"⚠️ {self.camera_name} - {msg}")
            def print_error(self, msg): print(f"❌ {self.camera_name} - {msg}")
            def print_debug(self, msg): print(f"🔍 {self.camera_name} - {msg}")
        
        return FallbackLogger(self.camera_name)
    
    def create_ui(self):
        """Create UI with exact structure from existing code"""
        try:
            # Main frame
            self.frame = ttk.Frame(self.parent)
            self.frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
            
            # Video display canvas - optimized size
            self.canvas = tk.Canvas(self.frame, bg="black", width=288, height=216)
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
            self.show_status_message("Initializing camera...")
            
            # Controls frame
            controls = ttk.Frame(self.frame)
            controls.pack(fill=tk.X, padx=2, pady=2)
            
            # Main controls
            main_controls = ttk.Frame(controls)
            main_controls.pack(fill=tk.X, pady=1)
            
            # Feed toggle button
            self.feed_button = HoverButton(main_controls, text="Starting...", 
                                          bg=config.COLORS["primary"], fg=config.COLORS["button_text"],
                                          padx=2, pady=1, width=10,
                                          command=self.toggle_continuous_feed)
            self.feed_button.grid(row=0, column=0, padx=1, pady=1, sticky="ew")
            
            # Capture button
            self.capture_button = HoverButton(main_controls, text="📷 Capture", 
                                            bg=config.COLORS["primary"], fg=config.COLORS["button_text"],
                                            padx=2, pady=1, width=10,
                                            command=self.capture_current_frame)
            self.capture_button.grid(row=0, column=1, padx=1, pady=1, sticky="ew")
            
            # Save button
            self.save_button = HoverButton(main_controls, text="💾 Save", 
                                         bg=config.COLORS["secondary"], fg=config.COLORS["button_text"],
                                         padx=2, pady=1, width=8,
                                         command=self.save_image,
                                         state=tk.DISABLED)
            self.save_button.grid(row=0, column=2, padx=1, pady=1, sticky="ew")
            
            # Configure grid columns
            main_controls.columnconfigure(0, weight=1)
            main_controls.columnconfigure(1, weight=1)
            main_controls.columnconfigure(2, weight=1)
            
            # Status and performance info
            status_frame = ttk.Frame(controls)
            status_frame.pack(fill=tk.X, pady=1)
            
            # Status
            self.status_var = tk.StringVar(value="Initializing...")
            self.status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                         font=("Segoe UI", 7), foreground="blue")
            self.status_label.pack(side=tk.LEFT, padx=2)
            
            # Performance indicators
            self.perf_var = tk.StringVar(value="FPS: -- | CPU: -- | Dropped: --")
            self.perf_label = ttk.Label(status_frame, textvariable=self.perf_var, 
                                       font=("Segoe UI", 7), foreground="green")
            self.perf_label.pack(side=tk.RIGHT, padx=2)
            
        except Exception as e:
            self.logger.print_error(f"Error creating camera UI: {e}")
            raise
    
    def show_status_message(self, message):
        """Show a status message on the canvas"""
        try:
            self.canvas.delete("all")
            canvas_width = self.canvas.winfo_width() or 320
            canvas_height = self.canvas.winfo_height() or 240
            
            self.canvas.create_text(canvas_width//2, canvas_height//2, 
                                   text=message, fill="white", 
                                   font=("Segoe UI", 10), justify=tk.CENTER)
        except Exception as e:
            self.logger.print_error(f"Error showing status message: {e}")
    
    def set_rtsp_config(self, rtsp_url):
        """Configure camera for RTSP stream with HD settings"""
        try:
            self.rtsp_url = rtsp_url
            self.http_url = None  # Clear HTTP URL
            self.camera_type = "RTSP"
            self.logger.print_info(f"RTSP URL configured: {rtsp_url}")
            self.restart_feed()
        except Exception as e:
            self.logger.print_error(f"Error setting RTSP config: {e}")
    
    def set_http_config(self, http_url):
        """Configure camera for HTTP stream"""
        try:
            self.http_url = http_url
            self.rtsp_url = None  # Clear RTSP URL
            self.camera_type = "HTTP"
            self.logger.print_info(f"HTTP URL configured: {http_url}")
            self.restart_feed()
        except Exception as e:
            self.logger.print_error(f"Error setting HTTP config: {e}")
    
    def start_resource_monitoring(self):
        """Start resource monitoring thread"""
        try:
            def monitor_resources():
                while not self.stop_event.is_set():
                    try:
                        current_time = time.time()
                        if current_time - self.last_resource_check >= self.resource_check_interval:
                            self.cpu_usage = psutil.cpu_percent()
                            self.memory_usage = psutil.virtual_memory().percent
                            self.last_resource_check = current_time
                            
                            if self.adaptive_quality:
                                self._adjust_performance_settings()
                        
                        self.stop_event.wait(1.0)
                    except Exception as e:
                        self.logger.print_error(f"Resource monitoring error: {e}")
                        self.stop_event.wait(5.0)
            
            resource_thread = threading.Thread(target=monitor_resources, daemon=True)
            resource_thread.start()
            self.logger.print_debug("Resource monitoring started")
        except Exception as e:
            self.logger.print_error(f"Failed to start resource monitoring: {e}")
    
    def _adjust_performance_settings(self):
        """Adjust performance settings based on system load"""
        try:
            if self.cpu_usage > 85:
                self.target_fps = max(self.min_fps, self.target_fps - 1)
                if self.cpu_usage > 90:
                    self.logger.print_warning(f"High CPU usage ({self.cpu_usage:.1f}%), reducing FPS to {self.target_fps}")
            elif self.cpu_usage < 50:
                self.target_fps = min(self.max_fps, self.target_fps + 0.5)
            
            if self.memory_usage > 85:
                self.logger.print_warning(f"High memory usage ({self.memory_usage:.1f}%), triggering garbage collection")
                gc.collect()
        except Exception as e:
            self.logger.print_error(f"Performance adjustment error: {e}")
    
    def start_watchdog(self):
        """Start watchdog thread for auto-recovery"""
        try:
            def watchdog():
                self.logger.print_debug("Camera watchdog started")
                while not self.stop_event.is_set():
                    try:
                        if self.should_be_running and not self.is_running:
                            self.start_continuous_feed()
                        
                        if self.last_successful_frame:
                            time_since_frame = datetime.datetime.now() - self.last_successful_frame
                            if time_since_frame.total_seconds() > 30:
                                self.restart_feed()
                        
                        self.stop_event.wait(self.reconnect_delay)
                    except Exception as e:
                        self.logger.print_error(f"Watchdog error: {e}")
                        self.stop_event.wait(10.0)
            
            watchdog_thread = threading.Thread(target=watchdog, daemon=True)
            watchdog_thread.start()
            self.logger.print_debug("Camera watchdog enabled")
        except Exception as e:
            self.logger.print_error(f"Failed to start watchdog: {e}")
    
    def start_continuous_feed(self):
        """Start continuous camera feed - Always starts, never exits"""
        try:
            if self.is_running:
                self.logger.print_debug("Camera feed already running")
                return
            
            self.connection_attempts += 1
            self.is_running = True
            self.consecutive_failures = 0
            self.stop_event.clear()
            
            # Update UI
            self._update_status("Starting camera...")
            self._update_feed_button("🟡 Starting", config.COLORS["warning"])
            
            # Always start the video thread - it will handle connection attempts
            self.video_thread = threading.Thread(target=self._hd_video_loop, daemon=True)
            self.video_thread.start()
            self.logger.print_debug("HD video thread started")
            
            # Start UI update loop
            self._schedule_ui_update()
            
            # Update feed button to show it's running
            self._update_feed_button("⏹️ Stop Feed", config.COLORS["secondary"])
            
        except Exception as e:
            self.logger.print_error(f"Error starting camera: {e}")
            self._update_status(f"Start error: {str(e)}")
            # Don't set is_running to False - keep trying
    
    def _hd_video_loop(self):
        """HD video loop using test script approach"""
        self.logger.print_info("HD video capture loop started")
        consecutive_failures = 0
        last_gc_time = time.time()
        initialization_attempts = 0
        max_init_attempts = 10  # Try harder before giving up
        
        while not self.stop_event.is_set() and self.is_running:
            try:
                # Initialize camera if needed
                if not self.cap or not self._test_camera_connection():
                    if not self._initialize_hd_camera():
                        consecutive_failures += 1
                        initialization_attempts += 1
                        
                        # Don't exit - keep trying with longer delays
                        if initialization_attempts < max_init_attempts:
                            self._update_status_safe(f"Connecting... (attempt {initialization_attempts}/{max_init_attempts})")
                            self.stop_event.wait(min(initialization_attempts * 2, 10))  # Progressive delay
                        else:
                            # After max attempts, show waiting status and keep trying with long delays
                            self._update_status_safe("Waiting for camera connection...")
                            self.stop_event.wait(self.reconnect_delay)
                            initialization_attempts = 0  # Reset counter
                        continue
                    else:
                        consecutive_failures = 0
                        initialization_attempts = 0
                
                # Frame timing control
                current_time = time.time()
                target_frame_time = 1.0 / self.target_fps
                if current_time - self.last_frame_time < target_frame_time:
                    self.stop_event.wait(0.01)
                    continue
                
                # Read frame with HD quality check (from test script)
                ret, frame = self._read_hd_frame()
                
                if ret and frame is not None and frame.size > 0:
                    h, w = frame.shape[:2]
                    
                    # Only accept HD quality frames (from test script)
                    if h >= self.min_hd_height and w >= self.min_hd_width:
                        self.stable_frame_counter += 1
                        self.total_frames += 1
                        
                        # Store HD frame for capture (from test script)
                        with self.frame_lock:
                            self.current_frame = frame.copy()
                        
                        # Update display after stable frames (from test script)
                        if self.stable_frame_counter >= self.stable_frames_required:
                            processed_frame = self._process_frame_optimized(frame)
                            
                            # Update frames using direct buffer
                            with self.frame_buffer['buffer_lock']:
                                self.frame_buffer['raw_frame'] = frame.copy()
                                self.frame_buffer['processed_frame'] = processed_frame
                                self.frame_buffer['timestamp'] = current_time
                            
                            # Signal that new frame is ready
                            self.frame_ready_event.set()
                            
                            # Update connection status
                            if not self.connection_stable:
                                self.connection_stable = True
                                self.camera_available = True
                                self._update_status_safe(f"HD Connected ({w}x{h})")
                                self.logger.print_success("HD camera connection stabilized")
                    else:
                        self.stable_frame_counter = 0
                    
                    self.last_frame_time = current_time
                    self.frame_count += 1
                    consecutive_failures = 0
                    self.last_successful_frame = datetime.datetime.now()
                    
                    # Update performance counters
                    self._update_performance_counters()
                
                else:
                    # Handle frame read failure
                    consecutive_failures += 1
                    self.dropped_frames += 1
                    self.stable_frame_counter = 0
                    
                    if consecutive_failures > self.max_consecutive_failures:
                        self._close_camera()
                        self.camera_available = False
                        self.connection_stable = False
                        consecutive_failures = 0
                        self.stop_event.wait(1.0)
                    else:
                        self.stop_event.wait(0.05)
                
                # Periodic garbage collection
                if current_time - last_gc_time > 60:
                    gc.collect()
                    last_gc_time = current_time
                
            except Exception as e:
                consecutive_failures += 1
                self._close_camera()
                self.camera_available = False
                self.connection_stable = False
                self.stop_event.wait(1.0)
        
        self.logger.print_info("HD video capture loop ending")
        self._close_camera()
    
    def _initialize_hd_camera(self):
        """Initialize camera with HD settings from test script - Non-blocking"""
        try:
            self.logger.print_debug(f"Attempting to initialize {self.camera_type} camera for HD")
            self._close_camera()
            
            if self.camera_type == "RTSP" and self.rtsp_url:
                return self._initialize_rtsp_hd()
            elif self.camera_type == "HTTP" and self.http_url:
                return self._initialize_http()
            elif self.camera_type == "USB":
                return self._initialize_usb_hd()
            else:
                # No valid configuration - show appropriate status but don't fail
                self._update_status_safe("No camera configured")
                return False
        except Exception as e:
            self.logger.print_error(f"HD camera initialization error: {e}")
            return False
    
    def _initialize_rtsp_hd(self):
        """Initialize RTSP camera with HD settings from test script - Non-blocking"""
        try:
            if not self.rtsp_url:
                self.logger.print_warning("No RTSP URL configured")
                return False
                
            self.logger.print_info(f"Attempting RTSP connection: {self.rtsp_url}")
            
            # Use test script approach for HD RTSP
            with SuppressStderr():
                self.cap = cv2.VideoCapture(self.rtsp_url)
                
                if not self.cap.isOpened():
                    self.logger.print_warning("RTSP stream failed to open")
                    self.cap = None
                    return False
                
                # Same settings that work in test script
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)
                self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                
                time.sleep(2)  # Wait for stabilization
                
                # Test HD quality connection (from test script) - but don't block forever
                for attempt in range(5):  # Reduced attempts to avoid blocking
                    ret, test_frame = self.cap.read()
                    if ret and test_frame is not None and test_frame.size > 0:
                        h, w = test_frame.shape[:2]
                        if h >= self.min_hd_height and w >= self.min_hd_width:
                            self.logger.print_success(f"HD RTSP connection established: {w}x{h}")
                            return True
                    time.sleep(0.2)
                
                # If no HD quality achieved, close and fail gracefully
                self.cap.release()
                self.cap = None
                self.logger.print_warning("RTSP connected but no HD quality frames received")
                return False
                
        except Exception as e:
            self.logger.print_warning(f"RTSP connection failed: {e}")
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
            return False
    
    def _initialize_usb_hd(self):
        """Initialize USB camera with HD settings - Non-blocking"""
        try:
            self.logger.print_info(f"Attempting USB camera connection at index {self.camera_index}")
            
            self.cap = cv2.VideoCapture(self.camera_index)
            
            if not self.cap or not self.cap.isOpened():
                self.logger.print_warning(f"USB camera {self.camera_index} not available")
                if self.cap:
                    self.cap.release()
                    self.cap = None
                return False
            
            # Set HD resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Test connection
            ret, test_frame = self.cap.read()
            if ret and test_frame is not None:
                h, w = test_frame.shape[:2]
                self.logger.print_success(f"USB camera HD initialized: {w}x{h}")
                return True
            else:
                self.logger.print_warning(f"USB camera {self.camera_index} opened but no frames received")
                self.cap.release()
                self.cap = None
                return False
            
        except Exception as e:
            self.logger.print_warning(f"USB camera initialization failed: {e}")
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
            return False
    
    def _initialize_http(self):
        """Initialize HTTP camera"""
        try:
            if not self.http_url:
                return False
            
            request = urllib.request.Request(self.http_url)
            with urllib.request.urlopen(request, timeout=5) as response:
                if response.getcode() == 200:
                    self.logger.print_info("HTTP camera connection established")
                    return True
            return False
        except Exception as e:
            self.logger.print_error(f"HTTP initialization error: {e}")
            return False
    
    def _test_camera_connection(self):
        """Test camera connection"""
        try:
            if self.camera_type == "HTTP":
                return True
            
            if self.cap and self.cap.isOpened():
                ret, test_frame = self.cap.read()
                return ret and test_frame is not None
            return False
        except Exception as e:
            return False
    
    def _read_hd_frame(self):
        """Read frame with HD quality check"""
        try:
            if self.camera_type == "HTTP" and self.http_url:
                return self._read_http_frame_optimized()
            elif self.camera_type == "RTSP" and self.rtsp_url:
                if self.cap and self.cap.isOpened():
                    with SuppressStderr():
                        return self.cap.read()
            elif self.camera_type == "USB":
                if self.cap and self.cap.isOpened():
                    return self.cap.read()
            
            return False, None
        except Exception as e:
            return False, None
    
    def _read_http_frame_optimized(self):
        """Optimized HTTP frame reading"""
        try:
            if not self.http_url:
                return False, None
            
            request = urllib.request.Request(self.http_url)
            with urllib.request.urlopen(request, timeout=2) as response:
                image_data = response.read()
                nparr = np.frombuffer(image_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                return frame is not None, frame
        except Exception as e:
            return False, None
    
    def _process_frame_optimized(self, frame):
        """Optimized frame processing"""
        try:
            if frame is None:
                return None
            
            # Apply zoom and pan only if needed
            if self.zoom_level > 1.0 or self.pan_x != 0 or self.pan_y != 0:
                frame = self.apply_zoom_and_pan(frame)
            
            return frame
        except Exception as e:
            return frame
    
    def _close_camera(self):
        """Close camera resources safely"""
        try:
            if self.cap:
                with SuppressStderr():
                    self.cap.release()
                self.cap = None
        except Exception as e:
            self.logger.print_error(f"Error closing camera: {e}")
    
    def _schedule_ui_update(self):
        """Schedule optimized UI updates"""
        if self.is_running and not self.stop_event.is_set():
            self._update_display_optimized()
            self.parent.after_idle(lambda: self.parent.after(66, self._schedule_ui_update))
    
    def _update_display_optimized(self):
        """Optimized display update using direct buffer"""
        try:
            if not self.frame_ready_event.is_set():
                return
            
            # Get frame from buffer
            with self.frame_buffer['buffer_lock']:
                current_frame = self.frame_buffer['raw_frame']
                display_frame = self.frame_buffer['processed_frame']
                self.frame_ready_event.clear()
            
            if display_frame is None:
                return
            
            # Convert and resize efficiently
            frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            
            # Get canvas dimensions
            canvas_width = max(self.canvas.winfo_width(), 320)
            canvas_height = max(self.canvas.winfo_height(), 240)
            
            # Resize with optimization
            frame_resized = cv2.resize(frame_rgb, (canvas_width, canvas_height), 
                                     interpolation=cv2.INTER_LINEAR)
            
            # Convert to PhotoImage
            img = Image.fromarray(frame_resized)
            img_tk = ImageTk.PhotoImage(image=img)
            
            # Update canvas efficiently
            self.canvas.delete("all")
            self.canvas.create_image(canvas_width//2, canvas_height//2, image=img_tk)
            self.canvas.image = img_tk
            
        except Exception as e:
            pass
    
    def _update_performance_counters(self):
        """Update performance counters"""
        try:
            current_time = time.time()
            if current_time - self.fps_timer >= 1.0:
                fps = self.frame_count / (current_time - self.fps_timer)
                drop_rate = (self.dropped_frames / max(self.total_frames, 1)) * 100
                skip_rate = (self.frame_skip_counter / max(self.total_frames, 1)) * 100
                
                perf_text = f"FPS: {fps:.1f} | CPU: {self.cpu_usage:.0f}% | Drop: {drop_rate:.1f}% | Skip: {skip_rate:.1f}%"
                self._update_perf_safe(perf_text)
                
                self.frame_count = 0
                self.fps_timer = current_time
                
                if self.total_frames > 1000:
                    self.total_frames = 100
                    self.dropped_frames = int(self.dropped_frames * 0.1)
                    self.frame_skip_counter = int(self.frame_skip_counter * 0.1)
        except Exception as e:
            self.logger.print_error(f"Performance counter error: {e}")
    
    def capture_current_frame(self):
        """Capture current HD frame"""
        try:
            self.logger.print_info("Capturing current HD frame")
            
            with self.frame_lock:
                if self.current_frame is not None:
                    self.captured_image = self.current_frame.copy()
                    self.save_button.config(state=tk.NORMAL)
                    self._update_status("HD frame captured - ready to save")
                    return True
                else:
                    self._update_status("No HD frame available")
                    return False
        except Exception as e:
            self._update_status(f"Capture error: {str(e)}")
            return False
    
    def save_image(self):
        """Save captured HD image using test script approach"""
        try:
            if self.captured_image is None:
                self._update_status("No image to save")
                return False
            
            # Check if save function is configured (from existing system)
            if hasattr(self, 'save_function') and self.save_function:
                success = self.save_function(self.captured_image)
                if success:
                    self._update_status("HD image saved successfully")
                    self.save_button.config(state=tk.DISABLED)
                    self.captured_image = None
                    return True
                else:
                    self._update_status("Save failed")
                    return False
            else:
                # Fallback - save directly using test script approach
                return self._save_hd_image_direct()
                
        except Exception as e:
            self._update_status(f"Save error: {str(e)}")
            return False
    
    def _save_hd_image_direct(self):
        """Save HD image directly using test script approach"""
        try:
            if self.captured_image is None:
                return False
            
            # Create directory
            os.makedirs("captured_images", exist_ok=True)
            
            # Generate filename (from test script)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            camera_name = self.camera_name.replace(' ', '_')
            filename = f"{camera_name}_{timestamp}.jpg"
            filepath = os.path.join("captured_images", filename)
            
            # Save HD image with high quality (from test script)
            cv2.imwrite(filepath, self.captured_image, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
            
            # Show success message (from test script)
            file_size = os.path.getsize(filepath) / 1024
            h, w = self.captured_image.shape[:2]
            
            messagebox.showinfo("Success", 
                              f"HD Image saved!\n\n"
                              f"File: {filename}\n"
                              f"Resolution: {w}x{h}\n"
                              f"Size: {file_size:.1f} KB")
            
            self._update_status(f"HD Captured: {filename}")
            self.save_button.config(state=tk.DISABLED)
            self.captured_image = None
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {str(e)}")
            return False
    
    def toggle_continuous_feed(self):
        """Toggle camera feed"""
        try:
            if self.is_running:
                self.should_be_running = False
                self.stop_continuous_feed()
            else:
                self.should_be_running = True
                self.start_continuous_feed()
        except Exception as e:
            self.logger.print_error(f"Error toggling feed: {e}")
    
    def stop_continuous_feed(self):
        """Stop camera feed with enhanced cleanup"""
        try:
            self.logger.print_info("Stopping camera feed")
            self.is_running = False
            self.stop_event.set()
            
            # Wait for video thread to finish
            if self.video_thread and self.video_thread.is_alive():
                self.video_thread.join(timeout=3)
            
            # Close camera resources
            self._close_camera()
            
            # Update UI
            self._update_status("Camera stopped")
            
            # Update feed button safely
            if self._widget_exists(self.feed_button):
                self._update_feed_button("▶️ Start Feed", config.COLORS["primary"])
            
        except Exception as e:
            self.logger.print_error(f"Error stopping camera: {e}")
    
    def restart_feed(self):
        """Restart camera feed"""
        try:
            self.logger.print_info("Restarting camera feed")
            if self.is_running:
                self.stop_continuous_feed()
                self.stop_event.wait(0.5)
            self.start_continuous_feed()
        except Exception as e:
            self.logger.print_error(f"Error restarting feed: {e}")
    
    def _update_feed_button(self, text, color):
        """Update feed button with error handling"""
        try:
            if (hasattr(self, 'feed_button') and 
                self.feed_button and 
                self.feed_button.winfo_exists()):
                self.feed_button.config(text=text, bg=color)
        except tk.TclError as e:
            if "invalid command name" not in str(e):
                self.logger.print_error(f"Feed button update error: {e}")
        except Exception as e:
            self.logger.print_error(f"Feed button update error: {e}")
    
    def _update_status_safe(self, status):
        """Thread-safe status update with error handling"""
        try:
            def update_status():
                try:
                    if (hasattr(self, 'status_var') and 
                        self.status_var and 
                        hasattr(self, 'parent') and 
                        self.parent.winfo_exists()):
                        self.status_var.set(status)
                except tk.TclError as e:
                    if "invalid command name" not in str(e):
                        self.logger.print_error(f"Status update error: {e}")
                except Exception as e:
                    self.logger.print_error(f"Status update error: {e}")
            
            if hasattr(self, 'parent') and self.parent:
                self.parent.after_idle(update_status)
        except Exception as e:
            self.logger.print_error(f"Safe status update error: {e}")
    
    def _update_perf_safe(self, perf_text):
        """Thread-safe performance update with error handling"""
        try:
            def update_perf():
                try:
                    if (hasattr(self, 'perf_var') and 
                        self.perf_var and 
                        hasattr(self, 'parent') and 
                        self.parent.winfo_exists()):
                        self.perf_var.set(perf_text)
                except tk.TclError as e:
                    if "invalid command name" not in str(e):
                        self.logger.print_error(f"Performance update error: {e}")
                except Exception as e:
                    self.logger.print_error(f"Performance update error: {e}")
            
            if hasattr(self, 'parent') and self.parent:
                self.parent.after_idle(update_perf)
        except Exception as e:
            self.logger.print_error(f"Performance update error: {e}")
    
    def _update_status(self, status):
        """Update status thread-safely"""
        try:
            self.status_var.set(status)
        except Exception as e:
            self.logger.print_error(f"Status update error: {e}")
    
    def _widget_exists(self, widget):
        """Check if a widget still exists and is valid"""
        try:
            return widget and hasattr(widget, 'winfo_exists') and widget.winfo_exists()
        except:
            return False
    
    def shutdown_camera(self):
        """Enhanced shutdown with proper cleanup"""
        try:
            self.logger.print_info("Starting camera shutdown...")
            
            # Stop the should_be_running flag first
            self.should_be_running = False
            self.auto_reconnect = False
            
            # Stop the continuous feed
            self.stop_continuous_feed()
            
            # Wait for threads to finish
            if hasattr(self, 'video_thread') and self.video_thread and self.video_thread.is_alive():
                self.video_thread.join(timeout=2)
            
            # Clear any pending UI updates
            if hasattr(self, 'parent') and self.parent:
                try:
                    self.parent.after_cancel("all")
                except:
                    pass
            
            self.logger.print_success("Camera shutdown completed")
            
        except Exception as e:
            self.logger.print_error(f"Error during camera shutdown: {e}")
    
    # Mouse event handlers (optimized)
    def on_mouse_wheel(self, event):
        """Handle mouse wheel zoom"""
        try:
            if event.delta > 0 or event.num == 4:
                self.zoom_level = min(self.max_zoom, self.zoom_level + self.zoom_step)
            else:
                self.zoom_level = max(self.min_zoom, self.zoom_level - self.zoom_step)
        except Exception as e:
            pass
    
    def on_mouse_press(self, event):
        """Handle mouse press for panning"""
        try:
            if self.zoom_level > self.min_zoom:
                self.is_panning = True
                self.last_mouse_x = event.x
                self.last_mouse_y = event.y
        except Exception as e:
            pass
    
    def on_mouse_drag(self, event):
        """Handle mouse drag for panning"""
        try:
            if self.is_panning:
                dx = event.x - self.last_mouse_x
                dy = event.y - self.last_mouse_y
                self.pan_x += dx
                self.pan_y += dy
                self.last_mouse_x = event.x
                self.last_mouse_y = event.y
        except Exception as e:
            pass
    
    def on_mouse_release(self, event):
        """Handle mouse release"""
        try:
            self.is_panning = False
        except Exception as e:
            pass
    
    def reset_zoom(self, event=None):
        """Reset zoom and pan"""
        try:
            self.zoom_level = 1.0
            self.pan_x = 0
            self.pan_y = 0
        except Exception as e:
            pass
    
    def apply_zoom_and_pan(self, frame):
        """Apply zoom and pan efficiently"""
        try:
            if self.zoom_level <= 1.0:
                return frame
            
            h, w = frame.shape[:2]
            zoom_w = int(w / self.zoom_level)
            zoom_h = int(h / self.zoom_level)
            
            center_x = w // 2 + int(self.pan_x)
            center_y = h // 2 + int(self.pan_y)
            
            x1 = max(0, center_x - zoom_w // 2)
            y1 = max(0, center_y - zoom_h // 2)
            x2 = min(w, x1 + zoom_w)
            y2 = min(h, y1 + zoom_h)
            
            cropped = frame[y1:y2, x1:x2]
            return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
            
        except Exception as e:
            return frame
    
    # Static method for camera detection (from existing code)
    @staticmethod
    def detect_available_cameras():
        """Static method to detect available USB cameras"""
        available_cameras = []
        try:
            print("Scanning for USB cameras...")
            for i in range(8):
                try:
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            available_cameras.append(i)
                            print(f"✅ Found camera at index {i}")
                        cap.release()
                    else:
                        cap.release()
                except:
                    pass
            
            if not available_cameras:
                print("❌ No USB cameras detected")
            else:
                print(f"📹 Available cameras: {available_cameras}")
                
        except Exception as e:
            print(f"Error detecting cameras: {e}")
        
        return available_cameras
    
    # Backward compatibility methods
    def stop_camera(self):
        """Backward compatibility"""
        self.stop_continuous_feed()
    
    def start_camera(self):
        """Backward compatibility"""
        self.start_continuous_feed()
    
    def capture_image(self):
        """Backward compatibility"""
        return self.capture_current_frame()
    
    def reset_display(self):
        """Reset camera display"""
        try:
            self.canvas.delete("all")
            self.canvas.create_text(
                self.canvas.winfo_width()//2, 
                self.canvas.winfo_height()//2, 
                text="Camera Feed", 
                fill="white"
            )
        except:
            pass
    
    def get_connection_status(self):
        """Get detailed connection status"""
        try:
            status = {
                'camera_name': self.camera_name,
                'camera_type': self.camera_type,
                'is_running': self.is_running,
                'camera_available': self.camera_available,
                'connection_stable': self.connection_stable,
                'target_fps': self.target_fps,
                'cpu_usage': self.cpu_usage,
                'memory_usage': self.memory_usage,
                'dropped_frames': self.dropped_frames,
                'total_frames': self.total_frames,
                'frame_skip_counter': self.frame_skip_counter,
                'stable_frame_counter': self.stable_frame_counter
            }
            return status
        except Exception as e:
            return {'error': str(e)}
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            if hasattr(self, 'logger'):
                self.logger.print_info(f"{self.camera_name} camera cleanup started")
            self.shutdown_camera()
            if hasattr(self, 'logger'):
                self.logger.print_success(f"{self.camera_name} camera cleanup completed")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.print_error(f"Cleanup error: {e}")

# Maintain backward compatibility
RobustCameraView = OptimizedCameraView
ContinuousCameraView = OptimizedCameraView
CameraView = OptimizedCameraView

# Add watermark function (keeping your original)
def add_watermark(image, text, ticket_id=None):
    """Add a watermark to an image with sitename, vehicle number, timestamp, and image description in 2 lines at top, and ticket at bottom"""
    result = image.copy()
    height, width = result.shape[:2]
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    color = (255, 255, 255)
    thickness = 2
    line_spacing = 8
    
    if text:
        parts = [part.strip() for part in text.split(' - ')]
        
        if len(parts) >= 4:
            site = parts[0]
            vehicle = parts[1] 
            timestamp = parts[2]
            description = parts[3]
        
        line1 = f"{site} - {vehicle}"
        line2 = f"{timestamp} - {description}"
        
        (line1_width, line1_height), line1_baseline = cv2.getTextSize(line1, font, font_scale, thickness)
        (line2_width, line2_height), line2_baseline = cv2.getTextSize(line2, font, font_scale, thickness)
        
        total_text_height = line1_height + line2_height + line_spacing
        max_text_width = max(line1_width, line2_width)
        
        overlay = result.copy()
        overlay_y_start = 0
        overlay_y_end = total_text_height + 20
        cv2.rectangle(overlay, (0, overlay_y_start), (max_text_width + 20, overlay_y_end), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, result, 0.4, 0, result)
        
        line1_y = line1_height + 10
        cv2.putText(result, line1, (10, line1_y), font, font_scale, color, thickness)
        
        line2_y = line1_height + line2_height + line_spacing + 10
        cv2.putText(result, line2, (10, line2_y), font, font_scale, color, thickness)
    
    if ticket_id:
        ticket_text = f"Ticket: {ticket_id}"
        (ticket_width, ticket_height), ticket_baseline = cv2.getTextSize(ticket_text, font, font_scale, thickness)
        
        overlay_ticket = result.copy()
        overlay_y_start = height - ticket_height - 20
        overlay_y_end = height
        cv2.rectangle(overlay_ticket, (0, overlay_y_start), (ticket_width + 20, overlay_y_end), (0, 0, 0), -1)
        cv2.addWeighted(overlay_ticket, 0.6, result, 0.4, 0, result)
        
        cv2.putText(result, ticket_text, (10, height - 10), font, font_scale, color, thickness)
    
    return result