import tkinter as tk
from tkinter import ttk
import config
from ui_components import HoverButton
from camera import CameraView

def create_cameras_panel(self, parent):
    """Create the cameras panel with cameras side by side and state-based image capture"""
    # Camera container with compact layout
    camera_frame = ttk.LabelFrame(parent, text="Camera Capture (Reuse for 1st & 2nd Weighment)")
    camera_frame.pack(fill=tk.X, padx=5, pady=5)
    
    # Container for both cameras side by side
    cameras_container = ttk.Frame(camera_frame, style="TFrame")
    cameras_container.pack(fill=tk.X, padx=5, pady=5)
    cameras_container.columnconfigure(0, weight=1)
    cameras_container.columnconfigure(1, weight=1)
    
    # Front camera
    front_panel = ttk.Frame(cameras_container, style="TFrame")
    front_panel.grid(row=0, column=0, padx=2, pady=2, sticky="nsew")
    
    # Front camera title
    ttk.Label(front_panel, text="Front Camera").pack(anchor=tk.W, pady=2)
    
    # Create front camera with RTSP support
    self.front_camera = CameraView(front_panel)
    self.front_camera.save_function = self.image_handler.save_front_image
    
    # Back camera
    back_panel = ttk.Frame(cameras_container, style="TFrame")
    back_panel.grid(row=0, column=1, padx=2, pady=2, sticky="nsew")
    
    # Back Camera title
    ttk.Label(back_panel, text="Back Camera").pack(anchor=tk.W, pady=2)
    
    # Create back camera with RTSP support
    self.back_camera = CameraView(back_panel)
    self.back_camera.save_function = self.image_handler.save_back_image
    
    # Load camera settings and configure cameras
    self.load_camera_settings()
    
    # Image status section
    status_frame = ttk.LabelFrame(camera_frame, text="Image Capture Status")
    status_frame.pack(fill=tk.X, padx=5, pady=5)
    
    # Current weighment indicator
    current_weighment_frame = ttk.Frame(status_frame)
    current_weighment_frame.pack(fill=tk.X, padx=5, pady=2)
    
    ttk.Label(current_weighment_frame, text="Current State:", 
             font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
    
    # This will show which weighment we're currently capturing images for
    weighment_status_label = ttk.Label(current_weighment_frame, 
                                      textvariable=self.weighment_state_var,
                                      font=("Segoe UI", 9, "bold"),
                                      foreground=config.COLORS["primary"])
    weighment_status_label.pack(side=tk.LEFT, padx=5)
    
    # Image count status
    image_status_frame = ttk.Frame(status_frame)
    image_status_frame.pack(fill=tk.X, padx=5, pady=2)
    
    ttk.Label(image_status_frame, text="Images Captured:").pack(side=tk.LEFT, padx=5)
    
    # First weighment image status
    self.first_image_status_var = tk.StringVar(value="1st: 0/2")
    self.first_image_status = ttk.Label(image_status_frame, 
                                       textvariable=self.first_image_status_var, 
                                       foreground="red",
                                       font=("Segoe UI", 8, "bold"))
    self.first_image_status.pack(side=tk.LEFT, padx=10)
    
    # Second weighment image status
    self.second_image_status_var = tk.StringVar(value="2nd: 0/2")
    self.second_image_status = ttk.Label(image_status_frame, 
                                        textvariable=self.second_image_status_var, 
                                        foreground="red",
                                        font=("Segoe UI", 8, "bold"))
    self.second_image_status.pack(side=tk.LEFT, padx=10)
    
    # Total image count
    self.total_image_status_var = tk.StringVar(value="Total: 0/4")
    total_image_status = ttk.Label(image_status_frame,
                                  textvariable=self.total_image_status_var,
                                  foreground="blue",
                                  font=("Segoe UI", 8, "bold"))
    total_image_status.pack(side=tk.LEFT, padx=10)
    
    # Instructions
    instruction_frame = ttk.Frame(status_frame)
    instruction_frame.pack(fill=tk.X, padx=5, pady=2)
    
    instruction_text = ("💡 Capture front & back images during 1st weighment, then again during 2nd weighment")
    instruction_label = ttk.Label(instruction_frame, text=instruction_text, 
                                 font=("Segoe UI", 8, "italic"), 
                                 foreground="green")
    instruction_label.pack(side=tk.LEFT, padx=5)
    
    # Add action buttons below the cameras
    action_buttons_frame = ttk.Frame(camera_frame, style="TFrame")
    action_buttons_frame.pack(fill=tk.X, padx=5, pady=(5, 8))
    
    # Create the buttons with callbacks to main application functions
    save_btn = HoverButton(action_buttons_frame, 
                        text="Save Record", 
                        font=("Segoe UI", 10, "bold"),
                        bg=config.COLORS["secondary"],
                        fg=config.COLORS["button_text"],
                        padx=8, pady=3,
                        command=self.save_callback if self.save_callback else lambda: None)
    save_btn.pack(side=tk.LEFT, padx=5)
    
    view_btn = HoverButton(action_buttons_frame, 
                        text="View Records", 
                        font=("Segoe UI", 10),
                        bg=config.COLORS["primary"],
                        fg=config.COLORS["button_text"],
                        padx=8, pady=3,
                        command=self.view_callback if self.view_callback else lambda: None)
    view_btn.pack(side=tk.LEFT, padx=5)
    
    clear_btn = HoverButton(action_buttons_frame, 
                        text="Clear", 
                        font=("Segoe UI", 10),
                        bg=config.COLORS["button_alt"],
                        fg=config.COLORS["button_text"],
                        padx=8, pady=3,
                        command=self.clear_callback if self.clear_callback else lambda: None)
    clear_btn.pack(side=tk.LEFT, padx=5)
    
    exit_btn = HoverButton(action_buttons_frame, 
                        text="Exit", 
                        font=("Segoe UI", 10),
                        bg=config.COLORS["error"],
                        fg=config.COLORS["button_text"],
                        padx=8, pady=3,
                        command=self.exit_callback if self.exit_callback else lambda: None)
    exit_btn.pack(side=tk.LEFT, padx=5)

def update_image_status_display(self):
    """Update the total image count display"""
    if hasattr(self, 'image_handler') and hasattr(self, 'total_image_status_var'):
        total_count = self.image_handler.get_total_image_count()
        self.total_image_status_var.set(f"Total: {total_count}/4")

def load_camera_settings(self):
    """Load camera settings from storage and configure cameras"""
    try:
        # Get settings storage instance
        settings_storage = self.get_settings_storage()
        if not settings_storage:
            return
            
        # Get camera settings
        camera_settings = settings_storage.get_camera_settings()
        
        if camera_settings:
            # Configure front camera
            front_type = camera_settings.get("front_camera_type", "USB")
            if front_type == "RTSP":
                rtsp_url = settings_storage.get_rtsp_url("front")
                if rtsp_url:
                    self.front_camera.set_rtsp_config(rtsp_url)
            else:
                # USB camera
                front_index = camera_settings.get("front_camera_index", 0)
                self.front_camera.camera_index = front_index
                self.front_camera.camera_type = "USB"
            
            # Configure back camera
            back_type = camera_settings.get("back_camera_type", "USB")
            if back_type == "RTSP":
                rtsp_url = settings_storage.get_rtsp_url("back")
                if rtsp_url:
                    self.back_camera.set_rtsp_config(rtsp_url)
            else:
                # USB camera
                back_index = camera_settings.get("back_camera_index", 1)
                self.back_camera.camera_index = back_index
                self.back_camera.camera_type = "USB"
                
    except Exception as e:
        print(f"Error loading camera settings: {e}")

def get_settings_storage(self):
    """Get settings storage instance from the main app"""
    # Try to traverse up widget hierarchy to find settings storage
    widget = self.parent
    while widget:
        if hasattr(widget, 'settings_storage'):
            return widget.settings_storage
        if hasattr(widget, 'master'):
            widget = widget.master
        else:
            break
    
    # If not found in hierarchy, create a new instance
    try:
        from settings_storage import SettingsStorage
        return SettingsStorage()
    except:
        return None

def update_camera_settings(self, settings):
    """Update camera settings when changed in settings panel
    
    Args:
        settings: Camera settings dictionary
    """
    try:
        # Update front camera
        front_type = settings.get("front_camera_type", "USB")
        if front_type == "RTSP":
            # Get RTSP URL from settings
            username = settings.get("front_rtsp_username", "")
            password = settings.get("front_rtsp_password", "")
            ip = settings.get("front_rtsp_ip", "")
            port = settings.get("front_rtsp_port", "554")
            endpoint = settings.get("front_rtsp_endpoint", "/stream1")
            
            if ip:
                if username and password:
                    rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}{endpoint}"
                else:
                    rtsp_url = f"rtsp://{ip}:{port}{endpoint}"
                self.front_camera.set_rtsp_config(rtsp_url)
        else:
            # USB camera
            self.front_camera.camera_type = "USB"
            self.front_camera.camera_index = settings.get("front_camera_index", 0)
            self.front_camera.rtsp_url = None
        
        # Update back camera
        back_type = settings.get("back_camera_type", "USB")
        if back_type == "RTSP":
            # Get RTSP URL from settings
            username = settings.get("back_rtsp_username", "")
            password = settings.get("back_rtsp_password", "")
            ip = settings.get("back_rtsp_ip", "")
            port = settings.get("back_rtsp_port", "554")
            endpoint = settings.get("back_rtsp_endpoint", "/stream1")
            
            if ip:
                if username and password:
                    rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}{endpoint}"
                else:
                    rtsp_url = f"rtsp://{ip}:{port}{endpoint}"
                self.back_camera.set_rtsp_config(rtsp_url)
            else:
                # USB camera
                self.back_camera.camera_type = "USB"
                self.back_camera.camera_index = settings.get("back_camera_index", 1)
                self.back_camera.rtsp_url = None
                
    except Exception as e:
        print(f"Error updating camera settings: {e}")