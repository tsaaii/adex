import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports

import config
from ui_components import HoverButton
from weighbridge import WeighbridgeManager
from settings_storage import SettingsStorage



class SettingsPanel:
    """Settings panel for camera and weighbridge configuration"""
    
    def __init__(self, parent, weighbridge_callback=None, update_cameras_callback=None, 
            current_user=None, user_role=None):
        """Initialize settings panel
        
        Args:
            parent: Parent widget
            weighbridge_callback: Callback for weighbridge weight updates
            update_cameras_callback: Callback for camera updates
            current_user: Currently logged-in username
            user_role: User role (admin or user)
        """
        self.parent = parent
        self.weighbridge_callback = weighbridge_callback
        self.update_cameras_callback = update_cameras_callback
        self.current_user = current_user
        self.user_role = user_role
        
        # Initialize settings storage
        self.settings_storage = SettingsStorage()
        
        # Check authentication for settings access
        if not self.authenticate_settings_access():
            return
        
        # Continue with initialization
        self.init_variables()
        self.weighbridge = WeighbridgeManager(self.weighbridge_callback)
        self.create_panel()
        self.load_saved_settings()
    
    def authenticate_settings_access(self):
        """Authenticate for settings access"""
        # If we already have a current user with admin role, allow access
        if self.current_user and self.user_role == 'admin':
            return True
        
        # Otherwise, prompt for authentication
        auth_dialog = tk.Toplevel(self.parent)
        auth_dialog.title("Settings Authentication")
        auth_dialog.geometry("300x150")
        auth_dialog.resizable(False, False)
        auth_dialog.transient(self.parent)
        auth_dialog.grab_set()
        
        # Center dialog
        auth_dialog.update_idletasks()
        width = auth_dialog.winfo_width()
        height = auth_dialog.winfo_height()
        x = (self.parent.winfo_width() // 2) - (width // 2)
        y = (self.parent.winfo_height() // 2) - (height // 2)
        auth_dialog.geometry(f"+{x}+{y}")
        
        # Create form
        frame = ttk.Frame(auth_dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Enter admin credentials:").pack(pady=(0, 10))
        
        # Username
        username_frame = ttk.Frame(frame)
        username_frame.pack(fill=tk.X, pady=2)
        ttk.Label(username_frame, text="Username:").pack(side=tk.LEFT)
        username_var = tk.StringVar()
        ttk.Entry(username_frame, textvariable=username_var).pack(side=tk.RIGHT, padx=5)
        
        # Password
        password_frame = ttk.Frame(frame)
        password_frame.pack(fill=tk.X, pady=2)
        ttk.Label(password_frame, text="Password:").pack(side=tk.LEFT)
        password_var = tk.StringVar()
        ttk.Entry(password_frame, textvariable=password_var, show="*").pack(side=tk.RIGHT, padx=5)
        
        # Result
        authenticated = [False]  # Using list as mutable container
        
        # Buttons
        def on_ok():
            if self.settings_storage.isAuthenticated(username_var.get(), password_var.get()):
                authenticated[0] = True
                auth_dialog.destroy()
            else:
                messagebox.showerror("Authentication Failed", "Invalid username or password", parent=auth_dialog)
        
        def on_cancel():
            auth_dialog.destroy()
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=5)
        
        # Wait for dialog to close
        self.parent.wait_window(auth_dialog)
        
        # Return authentication result
        return authenticated[0]
    
    def init_variables(self):
        """Initialize settings variables"""
        # Weighbridge settings
        self.com_port_var = tk.StringVar()
        self.baud_rate_var = tk.IntVar(value=9600)
        self.data_bits_var = tk.IntVar(value=8)
        self.parity_var = tk.StringVar(value="None")
        self.stop_bits_var = tk.DoubleVar(value=1.0)
        self.wb_status_var = tk.StringVar(value="Status: Disconnected")
        self.current_weight_var = tk.StringVar(value="0 kg")
        
        # Camera settings
        self.front_cam_index_var = tk.IntVar(value=0)
        self.back_cam_index_var = tk.IntVar(value=1)
        self.cam_status_var = tk.StringVar()
        
        # User management variables
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.confirm_password_var = tk.StringVar()
        self.fullname_var = tk.StringVar()
        self.is_admin_var = tk.BooleanVar(value=False)
        
        # Site management variables
        self.site_name_var = tk.StringVar()
        self.incharge_name_var = tk.StringVar()
        self.transfer_party_var = tk.StringVar()
        self.agency_name_var = tk.StringVar()
        
        # Cloud backup status variable
        self.backup_status_var = tk.StringVar()
    
    def load_saved_settings(self):
        """Load settings from storage"""
        # Load weighbridge settings
        wb_settings = self.settings_storage.get_weighbridge_settings()
        if wb_settings:
            if "com_port" in wb_settings and wb_settings["com_port"] in self.com_port_combo['values']:
                self.com_port_var.set(wb_settings["com_port"])
            if "baud_rate" in wb_settings:
                self.baud_rate_var.set(wb_settings["baud_rate"])
            if "data_bits" in wb_settings:
                self.data_bits_var.set(wb_settings["data_bits"])
            if "parity" in wb_settings:
                self.parity_var.set(wb_settings["parity"])
            if "stop_bits" in wb_settings:
                self.stop_bits_var.set(wb_settings["stop_bits"])
        
        # Load camera settings
        camera_settings = self.settings_storage.get_camera_settings()
        if camera_settings:
            if "front_camera_index" in camera_settings:
                self.front_cam_index_var.set(camera_settings["front_camera_index"])
            if "back_camera_index" in camera_settings:
                self.back_cam_index_var.set(camera_settings["back_camera_index"])
    
    def create_panel(self):
        """Create settings panel with tabs"""
        # Create settings notebook
        self.settings_notebook = ttk.Notebook(self.parent)
        self.settings_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Weighbridge settings tab
        weighbridge_tab = ttk.Frame(self.settings_notebook, style="TFrame")
        self.settings_notebook.add(weighbridge_tab, text="Weighbridge")
        
        # Camera settings tab
        camera_tab = ttk.Frame(self.settings_notebook, style="TFrame")
        self.settings_notebook.add(camera_tab, text="Cameras")
        
        # User management tab (only visible to admin)
        users_tab = ttk.Frame(self.settings_notebook, style="TFrame")
        self.settings_notebook.add(users_tab, text="Users")
        
        # Site management tab (only visible to admin)
        sites_tab = ttk.Frame(self.settings_notebook, style="TFrame")
        self.settings_notebook.add(sites_tab, text="Sites")
        
        # Create tab contents
        self.create_weighbridge_settings(weighbridge_tab)
        self.create_camera_settings(camera_tab)
        self.create_user_management(users_tab)
        self.create_site_management(sites_tab)
    
    def create_weighbridge_settings(self, parent):
        """Create weighbridge configuration settings"""
        # Weighbridge settings frame
        wb_frame = ttk.LabelFrame(parent, text="Weighbridge Configuration", padding=10)
        wb_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # COM Port selection
        ttk.Label(wb_frame, text="COM Port:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.com_port_combo = ttk.Combobox(wb_frame, textvariable=self.com_port_var, state="readonly")
        self.com_port_combo.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=5)
        self.refresh_com_ports()
        
        # Refresh COM ports button
        refresh_btn = HoverButton(wb_frame, text="Refresh Ports", bg=config.COLORS["primary_light"], 
                                 fg=config.COLORS["text"], padx=5, pady=2,
                                 command=self.refresh_com_ports)
        refresh_btn.grid(row=0, column=2, padx=5, pady=2)
        
        # Baud rate
        ttk.Label(wb_frame, text="Baud Rate:").grid(row=1, column=0, sticky=tk.W, pady=2)
        baud_rates = [600, 1200, 2400, 4800, 9600, 14400, 19200, 57600, 115200]
        ttk.Combobox(wb_frame, textvariable=self.baud_rate_var, values=baud_rates, 
                    state="readonly").grid(row=1, column=1, sticky=tk.EW, pady=2, padx=5)
        
        # Data bits
        ttk.Label(wb_frame, text="Data Bits:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(wb_frame, textvariable=self.data_bits_var, values=[5, 6, 7, 8], 
                    state="readonly").grid(row=2, column=1, sticky=tk.EW, pady=2, padx=5)
        
        # Parity
        ttk.Label(wb_frame, text="Parity:").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(wb_frame, textvariable=self.parity_var, 
                    values=["None", "Odd", "Even", "Mark", "Space"], 
                    state="readonly").grid(row=3, column=1, sticky=tk.EW, pady=2, padx=5)
        
        # Stop bits
        ttk.Label(wb_frame, text="Stop Bits:").grid(row=4, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(wb_frame, textvariable=self.stop_bits_var, values=[1.0, 1.5, 2.0], 
                    state="readonly").grid(row=4, column=1, sticky=tk.EW, pady=2, padx=5)
        
        # Connection buttons
        btn_frame = ttk.Frame(wb_frame)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        self.connect_btn = HoverButton(btn_frame, text="Connect", bg=config.COLORS["secondary"], 
                                     fg=config.COLORS["button_text"], padx=10, pady=3,
                                     command=self.connect_weighbridge)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.disconnect_btn = HoverButton(btn_frame, text="Disconnect", bg=config.COLORS["error"], 
                                        fg=config.COLORS["button_text"], padx=10, pady=3,
                                        command=self.disconnect_weighbridge, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)
        
        # Save settings button
        save_settings_btn = HoverButton(btn_frame, text="Save Settings", bg=config.COLORS["primary"], 
                                      fg=config.COLORS["button_text"], padx=10, pady=3,
                                      command=self.save_weighbridge_settings)
        save_settings_btn.pack(side=tk.LEFT, padx=5)
        
        # Status indicator
        ttk.Label(wb_frame, textvariable=self.wb_status_var, 
                foreground="red").grid(row=6, column=0, columnspan=3, sticky=tk.W)
        
        # Test weight display
        ttk.Label(wb_frame, text="Current Weight:").grid(row=7, column=0, sticky=tk.W, pady=2)
        self.weight_label = ttk.Label(wb_frame, textvariable=self.current_weight_var, 
                                    font=("Segoe UI", 10, "bold"))
        self.weight_label.grid(row=7, column=1, sticky=tk.W, pady=2)
        
        # Check if cloud storage is enabled and add backup section
        if hasattr(config, 'USE_CLOUD_STORAGE') and config.USE_CLOUD_STORAGE:
            # Create a separator
            ttk.Separator(wb_frame, orient=tk.HORIZONTAL).grid(
                row=8, column=0, columnspan=3, sticky=tk.EW, pady=10)
            
            # Cloud backup section
            cloud_frame = ttk.Frame(wb_frame)
            cloud_frame.grid(row=9, column=0, columnspan=3, sticky=tk.EW, pady=5)
            
            ttk.Label(cloud_frame, text="Cloud Backup:").grid(row=0, column=0, sticky=tk.W)
            
            # Backup button
            self.backup_btn = HoverButton(cloud_frame, 
                                        text="Backup All Records to Cloud", 
                                        bg=config.COLORS["primary_light"], 
                                        fg=config.COLORS["text"], padx=5, pady=2,
                                        command=self.backup_to_cloud)
            self.backup_btn.grid(row=0, column=1, padx=5, pady=2)
            
            # Backup status
            ttk.Label(cloud_frame, textvariable=self.backup_status_var).grid(
                row=0, column=2, sticky=tk.W, padx=5)


    def backup_to_cloud(self):
        """Backup all records to cloud storage"""
        try:
            # Find data manager
            data_manager = self.find_data_manager()
            
            if not data_manager:
                self.backup_status_var.set("Error: Data manager not found")
                return
            
            # Check if data manager has backup_to_cloud method
            if not hasattr(data_manager, 'save_to_cloud'):
                # Try to import necessary modules for backup
                try:
                    from cloud_storage import CloudStorageService
                    import datetime
                    
                    # Initialize cloud storage
                    cloud_storage = CloudStorageService(
                        config.CLOUD_BUCKET_NAME,
                        config.CLOUD_CREDENTIALS_PATH
                    )
                    
                    if not cloud_storage.is_connected():
                        self.backup_status_var.set("Error: Cloud connection failed")
                        return
                    
                    # Get all records
                    records = data_manager.get_all_records()
                    
                    # Create backup filename with timestamp
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"backups/all_records_{timestamp}.json"
                    
                    # Save to cloud
                    self.backup_status_var.set("Backing up...")
                    success = cloud_storage.save_json(records, filename)
                    
                    # Update status
                    if success:
                        self.backup_status_var.set("Backup successful!")
                    else:
                        self.backup_status_var.set("Backup failed!")
                        
                except Exception as e:
                    print(f"Error during backup: {e}")
                    self.backup_status_var.set(f"Error: {str(e)}")
            else:
                # Use existing backup method
                self.backup_status_var.set("Backing up...")
                success = data_manager.save_to_cloud({})
                
                # Update status
                if success:
                    self.backup_status_var.set("Backup successful!")
                else:
                    self.backup_status_var.set("Backup failed!")
                
        except Exception as e:
            print(f"Error during backup: {e}")
            self.backup_status_var.set(f"Error: {str(e)}")

    def find_data_manager(self):
        """Find data manager from the application"""
        # Try to traverse widget hierarchy to find app instance
        widget = self.parent
        while widget:
            if hasattr(widget, 'data_manager'):
                return widget.data_manager
            if hasattr(widget, 'master'):
                widget = widget.master
            else:
                break
        return None
            
    
    def create_camera_settings(self, parent):
        """Create camera configuration settings"""
        # Camera settings frame
        cam_frame = ttk.LabelFrame(parent, text="Camera Configuration", padding=10)
        cam_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Front camera index
        ttk.Label(cam_frame, text="Front Camera Index:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(cam_frame, textvariable=self.front_cam_index_var, 
                    values=[0, 1, 2, 3], state="readonly").grid(row=0, column=1, sticky=tk.EW, pady=2, padx=5)
        
        # Back camera index
        ttk.Label(cam_frame, text="Back Camera Index:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(cam_frame, textvariable=self.back_cam_index_var, 
                    values=[0, 1, 2, 3], state="readonly").grid(row=1, column=1, sticky=tk.EW, pady=2, padx=5)
        
        # Button frame
        cam_btn_frame = ttk.Frame(cam_frame)
        cam_btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        # Apply button
        apply_btn = HoverButton(cam_btn_frame, text="Apply Settings", bg=config.COLORS["primary"], 
                               fg=config.COLORS["button_text"], padx=10, pady=3,
                               command=self.apply_camera_settings)
        apply_btn.pack(side=tk.LEFT, padx=5)
        
        # Save settings button
        save_cam_btn = HoverButton(cam_btn_frame, text="Save Settings", bg=config.COLORS["secondary"], 
                                 fg=config.COLORS["button_text"], padx=10, pady=3,
                                 command=self.save_camera_settings)
        save_cam_btn.pack(side=tk.LEFT, padx=5)
        
        # Status message
        ttk.Label(cam_frame, textvariable=self.cam_status_var, 
                foreground=config.COLORS["primary"]).grid(row=3, column=0, columnspan=2, sticky=tk.W)

    def create_user_management(self, parent):
        """Create user management tab"""
        # Main container
        main_frame = ttk.Frame(parent, style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Split into two sides - left for list, right for details
        left_frame = ttk.LabelFrame(main_frame, text="Users")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), pady=5)
            
        right_frame = ttk.LabelFrame(main_frame, text="User Details")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
            
            # User list (left side)
        self.create_user_list(left_frame)
            
            # User details (right side)
        self.create_user_form(right_frame)
    
    def create_user_list(self, parent):
        """Create user list with controls"""
            # List frame
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Create listbox for users
        columns = ("username", "name", "role")
        self.users_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
            
            # Define headings
        self.users_tree.heading("username", text="Username")
        self.users_tree.heading("name", text="Name")
        self.users_tree.heading("role", text="Role")
            
            # Define column widths
        self.users_tree.column("username", width=100)
        self.users_tree.column("name", width=150)
        self.users_tree.column("role", width=80)
            
            # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.users_tree.yview)
        self.users_tree.configure(yscroll=scrollbar.set)
            
            # Pack widgets
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.users_tree.pack(fill=tk.BOTH, expand=True)
            
            # Bind selection event
        self.users_tree.bind("<<TreeviewSelect>>", self.on_user_select)
            
            # Buttons frame
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Add buttons
        new_btn = HoverButton(buttons_frame, 
                                text="New User", 
                                bg=config.COLORS["primary"],
                                fg=config.COLORS["button_text"],
                                padx=5, pady=2,
                                command=self.new_user)
        new_btn.pack(side=tk.LEFT, padx=2)
            
        delete_btn = HoverButton(buttons_frame, 
                                text="Delete User",
                                bg=config.COLORS["error"],
                                fg=config.COLORS["button_text"],
                                padx=5, pady=2,
                                command=self.delete_user)
        delete_btn.pack(side=tk.LEFT, padx=2)
            
        refresh_btn = HoverButton(buttons_frame, 
                                    text="Refresh", 
                                    bg=config.COLORS["secondary"],
                                    fg=config.COLORS["button_text"],
                                    padx=5, pady=2,
                                    command=self.load_users)
        refresh_btn.pack(side=tk.RIGHT, padx=2)
            
            # Load users
        self.load_users()
    
    def create_user_form(self, parent):
        """Create user details form"""
        form_frame = ttk.Frame(parent)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
        #Username
        ttk.Label(form_frame, text="Username:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.username_entry = ttk.Entry(form_frame, textvariable=self.username_var, width=20)
        self.username_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
            
            # Full Name
        ttk.Label(form_frame, text="Full Name:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.fullname_var, width=30).grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
            
            # Password
        ttk.Label(form_frame, text="Password:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.password_var, show="*", width=20).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
            
            # Confirm Password
        ttk.Label(form_frame, text="Confirm Password:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.confirm_password_var, show="*", width=20).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
            
            # Admin checkbox
        ttk.Checkbutton(form_frame, text="Admin User", variable=self.is_admin_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
            
            # Buttons
        buttons_frame = ttk.Frame(form_frame)
        buttons_frame.grid(row=5, column=0, columnspan=2, pady=10)
            
        self.save_btn = HoverButton(buttons_frame, 
                                    text="Save User", 
                                    bg=config.COLORS["secondary"],
                                    fg=config.COLORS["button_text"],
                                    padx=5, pady=2,
                                    command=self.save_user)
        self.save_btn.pack(side=tk.LEFT, padx=5)
            
        self.cancel_btn = HoverButton(buttons_frame, 
                                        text="Cancel", 
                                        bg=config.COLORS["button_alt"],
                                        fg=config.COLORS["button_text"],
                                        padx=5, pady=2,
                                        command=self.clear_user_form)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
            
            # Status label
        self.user_status_var = tk.StringVar()
        status_label = ttk.Label(form_frame, textvariable=self.user_status_var, foreground="blue")
        status_label.grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
            
            # Initially disable username field (for editing existing user)
        self.username_entry.configure(state="disabled")
            
            # Set edit mode flag
        self.edit_mode = False
    
    def create_site_management(self, parent):
        """Create site management tab with 2x2 grid layout"""
        # Create main frame to hold all sections
        main_frame = ttk.Frame(parent, style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configure main_frame as a 2x2 grid
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # ========== TOP LEFT: Site Names Section ==========
        site_frame = ttk.LabelFrame(main_frame, text="Site Names")
        site_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Site list and entry
        site_list_frame = ttk.Frame(site_frame)
        site_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Site listbox
        columns = ("site",)
        self.site_tree = ttk.Treeview(site_list_frame, columns=columns, show="headings", height=5)
        self.site_tree.heading("site", text="Site Name")
        self.site_tree.column("site", width=150)  # Reduced width
        
        # Add scrollbar
        site_scrollbar = ttk.Scrollbar(site_list_frame, orient=tk.VERTICAL, command=self.site_tree.yview)
        self.site_tree.configure(yscroll=site_scrollbar.set)
        
        # Pack widgets
        site_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.site_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Site controls
        site_controls = ttk.Frame(site_frame)
        site_controls.pack(fill=tk.X, padx=5, pady=5)
        
        # New site entry
        ttk.Label(site_controls, text="New Site:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(site_controls, textvariable=self.site_name_var, width=15).pack(side=tk.LEFT, padx=5)
        
        # Add and Delete buttons
        add_site_btn = HoverButton(site_controls,
                                text="Add",
                                bg=config.COLORS["primary"],
                                fg=config.COLORS["button_text"],
                                padx=5, pady=2,
                                command=self.add_site)
        add_site_btn.pack(side=tk.LEFT, padx=2)
        
        delete_site_btn = HoverButton(site_controls,
                                    text="Delete",
                                    bg=config.COLORS["error"],
                                    fg=config.COLORS["button_text"],
                                    padx=5, pady=2,
                                    command=self.delete_site)
        delete_site_btn.pack(side=tk.LEFT, padx=2)
        
        # ========== TOP RIGHT: Site Incharges Section ==========
        incharge_frame = ttk.LabelFrame(main_frame, text="Site Incharges")
        incharge_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Incharge list and entry
        incharge_list_frame = ttk.Frame(incharge_frame)
        incharge_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Incharge listbox
        columns = ("incharge",)
        self.incharge_tree = ttk.Treeview(incharge_list_frame, columns=columns, show="headings", height=5)
        self.incharge_tree.heading("incharge", text="Incharge Name")
        self.incharge_tree.column("incharge", width=150)  # Reduced width
        
        # Add scrollbar
        incharge_scrollbar = ttk.Scrollbar(incharge_list_frame, orient=tk.VERTICAL, command=self.incharge_tree.yview)
        self.incharge_tree.configure(yscroll=incharge_scrollbar.set)
        
        # Pack widgets
        incharge_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.incharge_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Incharge controls
        incharge_controls = ttk.Frame(incharge_frame)
        incharge_controls.pack(fill=tk.X, padx=5, pady=5)
        
        # New incharge entry
        ttk.Label(incharge_controls, text="New Incharge:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(incharge_controls, textvariable=self.incharge_name_var, width=15).pack(side=tk.LEFT, padx=5)
        
        # Add and Delete buttons
        add_incharge_btn = HoverButton(incharge_controls,
                                    text="Add",
                                    bg=config.COLORS["primary"],
                                    fg=config.COLORS["button_text"],
                                    padx=5, pady=2,
                                    command=self.add_incharge)
        add_incharge_btn.pack(side=tk.LEFT, padx=2)
        
        delete_incharge_btn = HoverButton(incharge_controls,
                                        text="Delete",
                                        bg=config.COLORS["error"],
                                        fg=config.COLORS["button_text"],
                                        padx=5, pady=2,
                                        command=self.delete_incharge)
        delete_incharge_btn.pack(side=tk.LEFT, padx=2)
        
        # ========== BOTTOM LEFT: Transfer Parties Section ==========
        tp_frame = ttk.LabelFrame(main_frame, text="Transfer Parties")
        tp_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Transfer Party list and entry
        tp_list_frame = ttk.Frame(tp_frame)
        tp_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Transfer Party listbox
        columns = ("transfer_party",)
        self.tp_tree = ttk.Treeview(tp_list_frame, columns=columns, show="headings", height=5)
        self.tp_tree.heading("transfer_party", text="Transfer Party Name")
        self.tp_tree.column("transfer_party", width=150)
        
        # Add scrollbar
        tp_scrollbar = ttk.Scrollbar(tp_list_frame, orient=tk.VERTICAL, command=self.tp_tree.yview)
        self.tp_tree.configure(yscroll=tp_scrollbar.set)
        
        # Pack widgets
        tp_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tp_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Transfer Party controls
        tp_controls = ttk.Frame(tp_frame)
        tp_controls.pack(fill=tk.X, padx=5, pady=5)
        
        # New Transfer Party entry
        ttk.Label(tp_controls, text="New Transfer Party:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(tp_controls, textvariable=self.transfer_party_var, width=15).pack(side=tk.LEFT, padx=5)
        
        # Add and Delete buttons
        add_tp_btn = HoverButton(tp_controls,
                            text="Add",
                            bg=config.COLORS["primary"],
                            fg=config.COLORS["button_text"],
                            padx=5, pady=2,
                            command=self.add_transfer_party)
        add_tp_btn.pack(side=tk.LEFT, padx=2)
        
        delete_tp_btn = HoverButton(tp_controls,
                                text="Delete",
                                bg=config.COLORS["error"],
                                fg=config.COLORS["button_text"],
                                padx=5, pady=2,
                                command=self.delete_transfer_party)
        delete_tp_btn.pack(side=tk.LEFT, padx=2)
        
        # ========== BOTTOM RIGHT: Agency Names Section ==========
        agency_frame = ttk.LabelFrame(main_frame, text="Agency Names")
        agency_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        
        # Agency list and entry
        agency_list_frame = ttk.Frame(agency_frame)
        agency_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Agency listbox
        columns = ("agency",)
        self.agency_tree = ttk.Treeview(agency_list_frame, columns=columns, show="headings", height=5)
        self.agency_tree.heading("agency", text="Agency Name")
        self.agency_tree.column("agency", width=150)
        
        # Add scrollbar
        agency_scrollbar = ttk.Scrollbar(agency_list_frame, orient=tk.VERTICAL, command=self.agency_tree.yview)
        self.agency_tree.configure(yscroll=agency_scrollbar.set)
        
        # Pack widgets
        agency_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.agency_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Agency controls
        agency_controls = ttk.Frame(agency_frame)
        agency_controls.pack(fill=tk.X, padx=5, pady=5)
        
        # New Agency entry
        ttk.Label(agency_controls, text="New Agency:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(agency_controls, textvariable=self.agency_name_var, width=15).pack(side=tk.LEFT, padx=5)
        
        # Add and Delete buttons
        add_agency_btn = HoverButton(agency_controls,
                                text="Add",
                                bg=config.COLORS["primary"],
                                fg=config.COLORS["button_text"],
                                padx=5, pady=2,
                                command=self.add_agency)
        add_agency_btn.pack(side=tk.LEFT, padx=2)
        
        delete_agency_btn = HoverButton(agency_controls,
                                    text="Delete",
                                    bg=config.COLORS["error"],
                                    fg=config.COLORS["button_text"],
                                    padx=5, pady=2,
                                    command=self.delete_agency)
        delete_agency_btn.pack(side=tk.LEFT, padx=2)
        
        # Save Settings button at the bottom
        save_sites_frame = ttk.Frame(main_frame)
        save_sites_frame.grid(row=2, column=0, columnspan=2, sticky="e", padx=5, pady=10)
        
        save_sites_btn = HoverButton(save_sites_frame,
                                text="Save Settings",
                                bg=config.COLORS["secondary"],
                                fg=config.COLORS["button_text"],
                                padx=8, pady=3,
                                command=self.save_sites_settings)
        save_sites_btn.pack(side=tk.RIGHT, padx=5)
        
        # Load sites, incharges, transfer parties and agencies
        self.load_sites()
    
    def refresh_com_ports(self):
        """Refresh available COM ports"""
        ports = self.weighbridge.get_available_ports()
        self.com_port_combo['values'] = ports
        if ports:
            # Try to keep the current selected port
            current_port = self.com_port_var.get()
            if current_port in ports:
                self.com_port_var.set(current_port)
            else:
                self.com_port_combo.current(0)

    def add_agency(self):
        """Add a new agency"""
        agency_name = self.agency_name_var.get().strip()
        if not agency_name:
            messagebox.showerror("Error", "Agency name cannot be empty")
            return
            
        # Check if agency already exists
        for item in self.agency_tree.get_children():
            if self.agency_tree.item(item, 'values')[0] == agency_name:
                messagebox.showerror("Error", "Agency name already exists")
                return
                
        # Add to treeview
        self.agency_tree.insert("", tk.END, values=(agency_name,))
        
        # Apply alternating row colors
        self._apply_row_colors(self.agency_tree)
        
        # Clear entry
        self.agency_name_var.set("")

    def delete_agency(self):
        """Delete selected agency"""
        selected_items = self.agency_tree.selection()
        if not selected_items:
            messagebox.showinfo("Selection", "Please select an agency to delete")
            return
            
        # Delete selected agency
        for item in selected_items:
            self.agency_tree.delete(item)
            
        # Apply alternating row colors
        self._apply_row_colors(self.agency_tree)

    def add_transfer_party(self):
        """Add a new transfer party"""
        tp_name = self.transfer_party_var.get().strip()
        if not tp_name:
            messagebox.showerror("Error", "Transfer party name cannot be empty")
            return
            
        # Check if transfer party already exists
        for item in self.tp_tree.get_children():
            if self.tp_tree.item(item, 'values')[0] == tp_name:
                messagebox.showerror("Error", "Transfer party name already exists")
                return
                
        # Add to treeview
        self.tp_tree.insert("", tk.END, values=(tp_name,))
        
        # Apply alternating row colors
        self._apply_row_colors(self.tp_tree)
        
        # Clear entry
        self.transfer_party_var.set("")
    
    def delete_transfer_party(self):
        """Delete selected transfer party"""
        selected_items = self.tp_tree.selection()
        if not selected_items:
            messagebox.showinfo("Selection", "Please select a transfer party to delete")
            return
            
        # Delete selected transfer party
        for item in selected_items:
            self.tp_tree.delete(item)
            
        # Apply alternating row colors
        self._apply_row_colors(self.tp_tree)

    # Update to settings_panel.py to handle weighbridge connection errors better

    def connect_weighbridge(self):
        """Connect to weighbridge with current settings and improved error handling"""
        com_port = self.com_port_var.get()
        if not com_port:
            messagebox.showerror("Error", "Please select a COM port")
            return
        
        try:
            # Get connection parameters
            baud_rate = self.baud_rate_var.get()
            data_bits = self.data_bits_var.get()
            parity = self.parity_var.get()
            stop_bits = self.stop_bits_var.get()
            
            # Connect to weighbridge
            if self.weighbridge.connect(com_port, baud_rate, data_bits, parity, stop_bits):
                # Update UI
                self.wb_status_var.set("Status: Connected")
                self.weight_label.config(foreground="green")
                self.connect_btn.config(state=tk.DISABLED)
                self.disconnect_btn.config(state=tk.NORMAL)
                messagebox.showinfo("Success", "Weighbridge connected successfully!")
            
        except Exception as e:
            # Extract error message
            error_msg = str(e)
            
            # Check for device not functioning error
            if "device attached" in error_msg.lower() and "not functioning" in error_msg.lower():
                # Show a more helpful error message with recovery options
                response = messagebox.askretrycancel(
                    "Connection Error", 
                    "Failed to connect to weighbridge:\n\n"
                    f"{error_msg}\n\n"
                    "Would you like to try again after checking the connection?",
                    icon=messagebox.ERROR
                )
                
                # If user wants to retry
                if response:
                    # Small delay before retry
                    self.parent.after(1000, self.connect_weighbridge)
                    
            elif "permission error" in error_msg.lower() or "access is denied" in error_msg.lower():
                # Likely another app is using the port
                response = messagebox.askretrycancel(
                    "Port in Use", 
                    "The COM port is currently in use by another application.\n\n"
                    f"{error_msg}\n\n"
                    "Close any other applications that might be using the port and try again.",
                    icon=messagebox.WARNING
                )
                
                # If user wants to retry
                if response:
                    # Small delay before retry
                    self.parent.after(1000, self.connect_weighbridge)
                    
            else:
                # Generic error message for other issues
                messagebox.showerror("Connection Error", f"Failed to connect to weighbridge:\n\n{error_msg}")
                
                # Update the status text to show error
                self.wb_status_var.set(f"Status: Connection Failed")
                self.weight_label.config(foreground="red")

    def disconnect_weighbridge(self):
        """Disconnect from weighbridge"""
        if self.weighbridge.disconnect():
            # Update UI
            self.wb_status_var.set("Status: Disconnected")
            self.weight_label.config(foreground="red")
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.current_weight_var.set("0 kg")
    
    def update_weight_display(self, weight):
        """Update weight display (callback for weighbridge)
        
        Args:
            weight: Weight value to display
        """
        self.current_weight_var.set(f"{weight:.2f} kg")
        
        # Update weight label color based on connection status
        if self.wb_status_var.get() == "Status: Connected":
            self.weight_label.config(foreground="green")
        else:
            self.weight_label.config(foreground="red")
        
        # Propagate weight update to form if callback is set
        if self.weighbridge_callback:
            self.weighbridge_callback(weight)
    
    def apply_camera_settings(self):
        """Apply camera index settings"""
        front_index = self.front_cam_index_var.get()
        back_index = self.back_cam_index_var.get()
        
        # Update camera indices through callback
        if self.update_cameras_callback:
            self.update_cameras_callback(front_index, back_index)
        
        self.cam_status_var.set("Camera settings applied. Changes take effect on next capture.")
    
    def save_weighbridge_settings(self):
        """Save weighbridge settings to persistent storage"""
        settings = {
            "com_port": self.com_port_var.get(),
            "baud_rate": self.baud_rate_var.get(),
            "data_bits": self.data_bits_var.get(),
            "parity": self.parity_var.get(),
            "stop_bits": self.stop_bits_var.get()
        }
        
        if self.settings_storage.save_weighbridge_settings(settings):
            messagebox.showinfo("Success", "Weighbridge settings saved successfully!")
        else:
            messagebox.showerror("Error", "Failed to save weighbridge settings.")
    
    def save_camera_settings(self):
        """Save camera settings to persistent storage"""
        settings = {
            "front_camera_index": self.front_cam_index_var.get(),
            "back_camera_index": self.back_cam_index_var.get()
        }
        
        if self.settings_storage.save_camera_settings(settings):
            messagebox.showinfo("Success", "Camera settings saved successfully!")
        else:
            messagebox.showerror("Error", "Failed to save camera settings.")
    
    def load_users(self):
        """Load users into the tree view"""
        # Clear existing items
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
            
        try:
            # Get users from storage
            users = self.settings_storage.get_users()
            
            # Add to treeview
            for username, user_data in users.items():
                role = user_data.get('role', 'user')
                name = user_data.get('name', '')
                
                self.users_tree.insert("", tk.END, values=(
                    username,
                    name,
                    role
                ))
                
            # Apply alternating row colors
            self._apply_row_colors(self.users_tree)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load users: {str(e)}")
    
    def on_user_select(self, event):
        """Handle user selection in the treeview"""
        selected_items = self.users_tree.selection()
        if not selected_items:
            return
            
        # Get user data
        item = selected_items[0]
        username = self.users_tree.item(item, 'values')[0]
        
        try:
            # Get user details
            users = self.settings_storage.get_users()
            
            if username in users:
                user_data = users[username]
                
                # Set form fields
                self.username_var.set(username)
                self.fullname_var.set(user_data.get('name', ''))
                self.is_admin_var.set(user_data.get('role', 'user') == 'admin')
                
                # Clear password fields
                self.password_var.set("")
                self.confirm_password_var.set("")
                
                # Disable username field for editing
                self.username_entry.configure(state="disabled")
                
                # Set edit mode
                self.edit_mode = True
                
                # Set status
                self.user_status_var.set("Editing user: " + username)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load user details: {str(e)}")
    
    def new_user(self):
        """Set up form for a new user"""
        # Clear form
        self.clear_user_form()
        
        # Enable username field
        self.username_entry.configure(state="normal")
        
        # Set edit mode
        self.edit_mode = False
        
        # Set status
        self.user_status_var.set("Creating new user")
    
    def save_user(self):
        """Save user to storage"""
        # Get form data
        username = self.username_var.get().strip()
        fullname = self.fullname_var.get().strip()
        password = self.password_var.get()
        confirm_password = self.confirm_password_var.get()
        is_admin = self.is_admin_var.get()
        
        # Validate inputs
        if not username:
            messagebox.showerror("Validation Error", "Username is required")
            return
            
        if not fullname:
            messagebox.showerror("Validation Error", "Full name is required")
            return
            
        # Check username format (alphanumeric)
        if not username.isalnum():
            messagebox.showerror("Validation Error", "Username must be alphanumeric")
            return
            
        # Check if password is required (new user or password change)
        if not self.edit_mode or password:
            if not password:
                messagebox.showerror("Validation Error", "Password is required")
                return
                
            if password != confirm_password:
                messagebox.showerror("Validation Error", "Passwords do not match")
                return
                
            if len(password) < 4:
                messagebox.showerror("Validation Error", "Password must be at least 4 characters")
                return
        
        try:
            # Get existing users
            users = self.settings_storage.get_users()
            
            # Check if username exists (for new user)
            if not self.edit_mode and username in users:
                messagebox.showerror("Error", "Username already exists")
                return
                
            # Prepare user data
            user_data = {
                "name": fullname,
                "role": "admin" if is_admin else "user"
            }
            
            # Set password if provided
            if password:
                user_data["password"] = self.settings_storage.hash_password(password)
            elif self.edit_mode and username in users:
                # Keep existing password
                user_data["password"] = users[username]["password"]
            
            # Save user
            users[username] = user_data
            
            # Save to storage
            if self.settings_storage.save_users(users):
                # Refresh user list
                self.load_users()
                
                # Clear form
                self.clear_user_form()
                
                # Show success message
                messagebox.showinfo("Success", f"User '{username}' saved successfully")
            else:
                messagebox.showerror("Error", "Failed to save user")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save user: {str(e)}")
    
    def delete_user(self):
        """Delete selected user"""
        selected_items = self.users_tree.selection()
        if not selected_items:
            messagebox.showinfo("Selection", "Please select a user to delete")
            return
            
        # Get user data
        item = selected_items[0]
        username = self.users_tree.item(item, 'values')[0]
        
        # Prevent deleting the last admin user
        try:
            # Get users
            users = self.settings_storage.get_users()
            
            # Count admin users
            admin_count = sum(1 for u, data in users.items() if data.get('role', '') == 'admin')
            
            # Check if attempting to delete the last admin
            if users.get(username, {}).get('role', '') == 'admin' and admin_count <= 1:
                messagebox.showerror("Error", "Cannot delete the last admin user")
                return
                
            # Confirm deletion
            confirm = messagebox.askyesno("Confirm", f"Are you sure you want to delete user '{username}'?")
            if not confirm:
                return
                
            # Delete user
            if username in users:
                del users[username]
                
                # Save to storage
                if self.settings_storage.save_users(users):
                    # Refresh user list
                    self.load_users()
                    
                    # Clear form if deleted user was being edited
                    if self.username_var.get() == username:
                        self.clear_user_form()
                    
                    # Show success message
                    messagebox.showinfo("Success", f"User '{username}' deleted successfully")
                else:
                    messagebox.showerror("Error", "Failed to save changes")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete user: {str(e)}")
    
    def clear_user_form(self):
        """Clear user form"""
        # Clear variables
        self.username_var.set("")
        self.fullname_var.set("")
        self.password_var.set("")
        self.confirm_password_var.set("")
        self.is_admin_var.set(False)
        
        # Reset edit mode
        self.edit_mode = False
        
        # Enable username field for new user
        self.username_entry.configure(state="normal")
        
        # Clear status
        self.user_status_var.set("")
    

    
    def add_site(self):
        """Add a new site"""
        site_name = self.site_name_var.get().strip()
        if not site_name:
            messagebox.showerror("Error", "Site name cannot be empty")
            return
            
        # Check if site already exists
        for item in self.site_tree.get_children():
            if self.site_tree.item(item, 'values')[0] == site_name:
                messagebox.showerror("Error", "Site name already exists")
                return
                
        # Add to treeview
        self.site_tree.insert("", tk.END, values=(site_name,))
        
        # Apply alternating row colors
        self._apply_row_colors(self.site_tree)
        
        # Clear entry
        self.site_name_var.set("")
    
    def delete_site(self):
        """Delete selected site"""
        selected_items = self.site_tree.selection()
        if not selected_items:
            messagebox.showinfo("Selection", "Please select a site to delete")
            return
            
        # Prevent deleting the last site
        if len(self.site_tree.get_children()) <= 1:
            messagebox.showerror("Error", "Cannot delete the last site")
            return
            
        # Delete selected site
        for item in selected_items:
            self.site_tree.delete(item)
            
        # Apply alternating row colors
        self._apply_row_colors(self.site_tree)
    
    def add_incharge(self):
        """Add a new incharge"""
        incharge_name = self.incharge_name_var.get().strip()
        if not incharge_name:
            messagebox.showerror("Error", "Incharge name cannot be empty")
            return
            
        # Check if incharge already exists
        for item in self.incharge_tree.get_children():
            if self.incharge_tree.item(item, 'values')[0] == incharge_name:
                messagebox.showerror("Error", "Incharge name already exists")
                return
                
        # Add to treeview
        self.incharge_tree.insert("", tk.END, values=(incharge_name,))
        
        # Apply alternating row colors
        self._apply_row_colors(self.incharge_tree)
        
        # Clear entry
        self.incharge_name_var.set("")
    
    def delete_incharge(self):
        """Delete selected incharge"""
        selected_items = self.incharge_tree.selection()
        if not selected_items:
            messagebox.showinfo("Selection", "Please select an incharge to delete")
            return
            
        # Delete selected incharge
        for item in selected_items:
            self.incharge_tree.delete(item)
            
        # Apply alternating row colors
        self._apply_row_colors(self.incharge_tree)
    
    def load_sites(self):
        """Load sites, incharges, transfer parties and agencies into treeviews"""
        # Clear existing items
        for item in self.site_tree.get_children():
            self.site_tree.delete(item)
            
        for item in self.incharge_tree.get_children():
            self.incharge_tree.delete(item)
            
        for item in self.tp_tree.get_children():
            self.tp_tree.delete(item)
            
        for item in self.agency_tree.get_children():
            self.agency_tree.delete(item)
            
        try:
            # Get sites data
            sites_data = self.settings_storage.get_sites()
            
            # Add sites to treeview
            for site in sites_data.get('sites', []):
                self.site_tree.insert("", tk.END, values=(site,))
                
            # Add incharges to treeview
            for incharge in sites_data.get('incharges', []):
                self.incharge_tree.insert("", tk.END, values=(incharge,))
                
            # Add transfer parties to treeview
            for tp in sites_data.get('transfer_parties', ['Advitia Labs']):
                self.tp_tree.insert("", tk.END, values=(tp,))
                
            # Add agencies to treeview
            for agency in sites_data.get('agencies', []):
                self.agency_tree.insert("", tk.END, values=(agency,))
                
            # Apply alternating row colors
            self._apply_row_colors(self.site_tree)
            self._apply_row_colors(self.incharge_tree)
            self._apply_row_colors(self.tp_tree)
            self._apply_row_colors(self.agency_tree)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sites: {str(e)}")

    def save_sites_settings(self):
        """Save sites, incharges, transfer parties and agencies to storage"""
        try:
            # Get all sites
            sites = []
            for item in self.site_tree.get_children():
                sites.append(self.site_tree.item(item, 'values')[0])
                
            # Get all incharges
            incharges = []
            for item in self.incharge_tree.get_children():
                incharges.append(self.incharge_tree.item(item, 'values')[0])
                
            # Get all transfer parties
            transfer_parties = []
            for item in self.tp_tree.get_children():
                transfer_parties.append(self.tp_tree.item(item, 'values')[0])
                
            # Get all agencies
            agencies = []
            for item in self.agency_tree.get_children():
                agencies.append(self.agency_tree.item(item, 'values')[0])
                
            # Save to storage
            sites_data = {
                "sites": sites,
                "incharges": incharges,
                "transfer_parties": transfer_parties,
                "agencies": agencies
            }
            
            if self.settings_storage.save_sites(sites_data):
                messagebox.showinfo("Success", "Sites settings saved successfully!")
            else:
                messagebox.showerror("Error", "Failed to save sites settings")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save sites settings: {str(e)}")

    def _apply_row_colors(self, tree):
        """Apply alternating row colors to treeview"""
        for i, item in enumerate(tree.get_children()):
            if i % 2 == 0:
                tree.item(item, tags=("evenrow",))
            else:
                tree.item(item, tags=("oddrow",))
        
        tree.tag_configure("evenrow", background=config.COLORS["table_row_even"])
        tree.tag_configure("oddrow", background=config.COLORS["table_row_odd"])
    
    def on_closing(self):
        """Handle cleanup when closing"""
        if self.weighbridge:
            self.weighbridge.disconnect()