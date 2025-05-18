import tkinter as tk
from tkinter import ttk, messagebox
import os
import datetime
import cv2
from PIL import Image, ImageTk
import threading

import config
from ui_components import HoverButton
from camera import CameraView, add_watermark

class MainForm:
    """Main data entry form for vehicle information"""
    
    def __init__(self, parent, notebook=None, summary_update_callback=None, data_manager=None):
        """Initialize the main form
        
        Args:
            parent: Parent widget
            notebook: Notebook for tab switching
            summary_update_callback: Function to call to update summary view
            data_manager: Data manager instance for checking existing entries
        """
        self.parent = parent
        self.notebook = notebook
        self.summary_update_callback = summary_update_callback
        self.data_manager = data_manager
        
        # Create form variables
        self.init_variables()
        
        # Camera lock to prevent both cameras from being used simultaneously
        self.camera_lock = threading.Lock()
        
        # Create UI elements
        self.create_form(parent)
        self.create_cameras_panel(parent)
        
        # Bind space key to the parent window
        self.parent.bind("<space>", self.handle_space_key)
        
    def init_variables(self):
        """Initialize form variables"""
        # Create variables for form fields
        self.site_var = tk.StringVar(value="Guntur")
        self.agency_var = tk.StringVar()
        self.material_var = tk.StringVar(value="MSW")
        self.rst_var = tk.StringVar()
        self.vehicle_var = tk.StringVar()
        self.tpt_var = tk.StringVar(value="Advitia Labs")
        
        # New variables for first and second weighment
        self.first_weight_var = tk.StringVar()
        self.first_timestamp_var = tk.StringVar()
        self.second_weight_var = tk.StringVar()
        self.second_timestamp_var = tk.StringVar()
        self.net_weight_var = tk.StringVar()
        
        # Material type tracking
        self.material_type_var = tk.StringVar(value="Inert")
        
        # Saved image paths
        self.front_image_path = None
        self.back_image_path = None
        
        # Weighment state
        self.current_weighment = "first"  # Can be "first" or "second"
        
        # If data manager is available, generate the next ticket number
        if hasattr(self, 'data_manager') and self.data_manager:
            self.generate_next_ticket_number()
    
    def generate_next_ticket_number(self):
        """Generate the next ticket number based on existing records"""
        if not hasattr(self, 'data_manager') or not self.data_manager:
            return
            
        # Get all records
        records = self.data_manager.get_all_records()
        
        # Find the highest ticket number
        highest_num = 0
        prefix = "T"  # Default prefix for tickets
        
        for record in records:
            ticket = record.get('ticket_no', '')
            if ticket and ticket.startswith(prefix) and len(ticket) > 1:
                try:
                    num = int(ticket[1:])
                    highest_num = max(highest_num, num)
                except ValueError:
                    pass
        
        # Generate next ticket number
        next_num = highest_num + 1
        next_ticket = f"{prefix}{next_num:04d}"
        
        # Set the ticket number
        self.rst_var.set(next_ticket)
        
    def create_form(self, parent):
        """Create the main data entry form with 3x3 layout"""
        # Vehicle Information Frame
        form_frame = ttk.LabelFrame(parent, text="Vehicle Information")
        form_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Set background color for better visibility
        form_inner = ttk.Frame(form_frame, style="TFrame")
        form_inner.pack(fill=tk.BOTH, padx=5, pady=5)
        
        # Create 3x3 grid layout
        # Configure grid columns for better distribution
        for i in range(3):  # 3 columns
            form_inner.columnconfigure(i, weight=1)  # Equal weight
        
        # Row 0: First row of labels
        # Site Name - Column 0
        ttk.Label(form_inner, text="Site Name:").grid(row=0, column=0, sticky=tk.W, padx=3, pady=3)
        
        # Agency Name - Column 1
        ttk.Label(form_inner, text="Agency Name:").grid(row=0, column=1, sticky=tk.W, padx=3, pady=3)
        
        # Material - Column 2
        ttk.Label(form_inner, text="Input Material").grid(row=0, column=2, sticky=tk.W, padx=3, pady=3)
        
        # Row 1: First row of entries
        # Site Name Entry - Column 0
        self.site_combo = ttk.Combobox(form_inner, textvariable=self.site_var, state="readonly", width=config.STD_WIDTH)
        self.site_combo['values'] = ('Guntur',)
        self.site_combo.grid(row=1, column=0, sticky=tk.W, padx=3, pady=3)
        
        # Agency Name Entry - Column 1
        ttk.Entry(form_inner, textvariable=self.agency_var, width=config.STD_WIDTH).grid(row=1, column=1, sticky=tk.W, padx=3, pady=3)
        
        # Material Combo Box - Column 2
        material_combo = ttk.Combobox(form_inner, textvariable=self.material_var, state="readonly", width=config.STD_WIDTH)
        material_combo['values'] = ('MSW')
        material_combo.grid(row=1, column=2, sticky=tk.W, padx=3, pady=3)
        
        # Row 2: Second row of labels
        # Ticket No - Column 0
        ttk.Label(form_inner, text="Ticket No:").grid(row=2, column=0, sticky=tk.W, padx=3, pady=3)
        
        # Vehicle No - Column 1
        ttk.Label(form_inner, text="Vehicle No:").grid(row=2, column=1, sticky=tk.W, padx=3, pady=3)
        
        # Transfer Party Name - Column 2
        ttk.Label(form_inner, text="Transfer Party Name:").grid(row=2, column=2, sticky=tk.W, padx=3, pady=3)
        
        # Row 3: Second row of entries
        # Ticket No Entry - Column 0
        ticket_entry = ttk.Entry(form_inner, textvariable=self.rst_var, width=config.STD_WIDTH)
        ticket_entry.grid(row=3, column=0, sticky=tk.W, padx=3, pady=3)
        ticket_entry.bind("<FocusOut>", self.check_ticket_exists)
        
        # Auto-generate next ticket button
        auto_ticket_btn = HoverButton(form_inner, text="Auto", 
                                    bg=config.COLORS["primary_light"], 
                                    fg=config.COLORS["text"],
                                    padx=2, pady=1,
                                    command=self.generate_next_ticket_number)
        auto_ticket_btn.grid(row=3, column=0, sticky=tk.E, padx=(0, 5), pady=3)
        
        # Vehicle No Entry - Column 1
        vehicle_entry = ttk.Entry(form_inner, textvariable=self.vehicle_var, width=config.STD_WIDTH)
        vehicle_entry.grid(row=3, column=1, sticky=tk.W, padx=3, pady=3)
        
        # Transfer Party Name Entry - Column 2
        tpt_entry = ttk.Entry(form_inner, textvariable=self.tpt_var, width=config.STD_WIDTH)
        tpt_entry.grid(row=3, column=2, sticky=tk.W, padx=3, pady=3)
        tpt_entry.configure(state="readonly")
        
        # Row 4: Third row of labels
        # Material Type - Column 0
        ttk.Label(form_inner, text="Material Type:").grid(row=4, column=0, sticky=tk.W, padx=3, pady=3)
        
        # Row 5: Third row of entries
        # Material Type Combo - Column 0
        material_type_combo = ttk.Combobox(form_inner, 
                                         textvariable=self.material_type_var, 
                                         state="readonly", 
                                         width=config.STD_WIDTH)
        # Material type options
        material_type_combo['values'] = ('Inert', 'Soil', 'Construction and Demolition', 
                                       'RDF(REFUSE DERIVED FUEL)')
        material_type_combo.grid(row=5, column=0, sticky=tk.W, padx=3, pady=3)
        
        # Create weighment frame
        weighment_frame = ttk.LabelFrame(form_inner, text="Weighment Information")
        weighment_frame.grid(row=6, column=0, columnspan=3, sticky="ew", padx=3, pady=10)
        
        # First row - labels
        ttk.Label(weighment_frame, text="First Weighment:").grid(row=0, column=0, sticky=tk.W, padx=3, pady=3)
        ttk.Label(weighment_frame, text="Time:").grid(row=0, column=1, sticky=tk.W, padx=3, pady=3)
        
        # First row - entries
        self.first_weight_entry = ttk.Entry(weighment_frame, textvariable=self.first_weight_var, width=10, state="readonly")
        self.first_weight_entry.grid(row=0, column=2, sticky=tk.W, padx=3, pady=3)
        
        ttk.Label(weighment_frame, textvariable=self.first_timestamp_var).grid(row=0, column=3, sticky=tk.W, padx=3, pady=3)
        
        # First weighment button
        self.first_weighment_btn = HoverButton(weighment_frame, text="Capture First Weight", 
                                             bg=config.COLORS["primary"], fg=config.COLORS["button_text"],
                                             padx=5, pady=2, command=self.capture_first_weighment)
        self.first_weighment_btn.grid(row=0, column=4, padx=3, pady=3, sticky=tk.E)
        
        # Second row - labels
        ttk.Label(weighment_frame, text="Second Weighment:").grid(row=1, column=0, sticky=tk.W, padx=3, pady=3)
        ttk.Label(weighment_frame, text="Time:").grid(row=1, column=1, sticky=tk.W, padx=3, pady=3)
        
        # Second row - entries
        self.second_weight_entry = ttk.Entry(weighment_frame, textvariable=self.second_weight_var, width=10, state="readonly")
        self.second_weight_entry.grid(row=1, column=2, sticky=tk.W, padx=3, pady=3)
        
        ttk.Label(weighment_frame, textvariable=self.second_timestamp_var).grid(row=1, column=3, sticky=tk.W, padx=3, pady=3)
        
        # Second weighment button
        self.second_weighment_btn = HoverButton(weighment_frame, text="Capture Second Weight", 
                                              bg=config.COLORS["primary"], fg=config.COLORS["button_text"],
                                              padx=5, pady=2, command=self.capture_second_weighment)
        self.second_weighment_btn.grid(row=1, column=4, padx=3, pady=3, sticky=tk.E)
        self.second_weighment_btn.config(state=tk.DISABLED)  # Initially disabled
        
        # Third row - Net weight
        ttk.Label(weighment_frame, text="Net Weight:").grid(row=2, column=0, sticky=tk.W, padx=3, pady=3)
        
        net_weight_display = ttk.Entry(weighment_frame, textvariable=self.net_weight_var, 
                                     state="readonly", width=10)
        net_weight_display.grid(row=2, column=2, sticky=tk.W, padx=3, pady=3)
        
        # Spacebar help text
        spacebar_label = ttk.Label(weighment_frame, text="Press SPACEBAR to capture current weight", 
                                  font=("Segoe UI", 8, "italic"))
        spacebar_label.grid(row=3, column=0, columnspan=5, pady=(5, 0), sticky=tk.E)
        
        # Image status indicators
        image_status_frame = ttk.Frame(form_inner)
        image_status_frame.grid(row=7, column=0, columnspan=3, sticky=tk.W, padx=3, pady=3)
        
        ttk.Label(image_status_frame, text="Images:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.front_image_status_var = tk.StringVar(value="Front: ✗")
        self.front_image_status = ttk.Label(image_status_frame, textvariable=self.front_image_status_var, foreground="red")
        self.front_image_status.pack(side=tk.LEFT, padx=(0, 5))
        
        self.back_image_status_var = tk.StringVar(value="Back: ✗")
        self.back_image_status = ttk.Label(image_status_frame, textvariable=self.back_image_status_var, foreground="red")
        self.back_image_status.pack(side=tk.LEFT)
    
    def load_sites_and_agencies(self, settings_storage):
        """Load sites and agencies from settings storage"""
        if not settings_storage:
            return
            
        # Get sites and incharges data
        sites_data = settings_storage.get_sites()
        
        # Update site combo
        sites = sites_data.get('sites', ['Guntur'])
        if hasattr(self, 'site_combo') and self.site_combo:
            self.site_combo['values'] = tuple(sites)
            
            # If current value not in list, set to first site
            if self.site_var.get() not in sites and sites:
                self.site_var.set(sites[0])
        
        # Update agency combo if it exists
        agencies = sites_data.get('incharges', [])
        if agencies and hasattr(self, 'agency_var'):
            # Find the agency entry widget
            for child in self.parent.winfo_children():
                if isinstance(child, ttk.LabelFrame) and "Vehicle Information" in child.cget("text"):
                    form_frame = child
                    for sub_child in form_frame.winfo_children():
                        if isinstance(sub_child, ttk.Frame):
                            form_inner = sub_child
                            
                            # Look for agency entry in row 1, column 1
                            for widget in form_inner.grid_slaves(row=1, column=1):
                                if isinstance(widget, ttk.Entry):
                                    # Convert to combobox
                                    agency_combo = ttk.Combobox(
                                        form_inner, 
                                        textvariable=self.agency_var,
                                        values=tuple(agencies),
                                        width=config.STD_WIDTH
                                    )
                                    agency_combo.grid(row=1, column=1, sticky=tk.W, padx=3, pady=3)
                                    widget.destroy()
                                    self.agency_combo = agency_combo
                                    return
                                elif isinstance(widget, ttk.Combobox):
                                    # Update values
                                    widget['values'] = tuple(agencies)
                                    self.agency_combo = widget
                                    return
    
    def check_ticket_exists(self, event=None):
        """Check if the ticket number already exists in the database"""
        ticket_no = self.rst_var.get().strip()
        if not ticket_no:
            return
            
        if hasattr(self, 'data_manager') and self.data_manager:
            # Check if this ticket exists in the database
            records = self.data_manager.get_filtered_records(ticket_no)
            for record in records:
                if record.get('ticket_no') == ticket_no:
                    # Record exists, determine weighment state
                    if record.get('second_weight') and record.get('second_timestamp'):
                        # Both weighments already done
                        messagebox.showinfo("Completed Record", 
                                         "This ticket already has both weighments completed.")
                        self.load_record_data(record)
                        return
                    elif record.get('first_weight') and record.get('first_timestamp'):
                        # First weighment done, set up for second
                        self.current_weighment = "second"
                        self.load_record_data(record)
                        
                        # Enable second weighment button, disable first
                        self.first_weighment_btn.config(state=tk.DISABLED)
                        self.second_weighment_btn.config(state=tk.NORMAL)
                        
                        messagebox.showinfo("Existing Ticket", 
                                         "This ticket already has a first weighment. Proceed with second weighment.")
                        return
                    
        # If we get here, this is a new ticket - set for first weighment
        self.current_weighment = "first"
        self.first_weighment_btn.config(state=tk.NORMAL)
        self.second_weighment_btn.config(state=tk.DISABLED)
        
        # Clear weight fields for new entry
        self.first_weight_var.set("")
        self.first_timestamp_var.set("")
        self.second_weight_var.set("")
        self.second_timestamp_var.set("")
        self.net_weight_var.set("")
        
    def load_record_data(self, record):
        """Load record data into the form"""
        # Set basic fields
        self.vehicle_var.set(record.get('vehicle_no', ''))
        self.agency_var.set(record.get('agency_name', ''))
        self.material_var.set(record.get('material', ''))
        self.material_type_var.set(record.get('material_type', ''))
        self.tpt_var.set(record.get('transfer_party_name', ''))
        
        # Set weighment data
        self.first_weight_var.set(record.get('first_weight', ''))
        self.first_timestamp_var.set(record.get('first_timestamp', ''))
        self.second_weight_var.set(record.get('second_weight', ''))
        self.second_timestamp_var.set(record.get('second_timestamp', ''))
        self.net_weight_var.set(record.get('net_weight', ''))
    
    def handle_space_key(self, event=None):
        """Handle spacebar press to capture current weight"""
        # Check if a ticket number is entered
        if not self.rst_var.get().strip():
            messagebox.showerror("Error", "Please enter a Ticket Number first.")
            return
            
        # Determine which weighment we're capturing based on current state
        if self.current_weighment == "first" and self.first_weighment_btn["state"] != "disabled":
            self.capture_first_weighment()
        elif self.current_weighment == "second" and self.second_weighment_btn["state"] != "disabled":
            self.capture_second_weighment()
    
    def capture_first_weighment(self):
        """Capture the first weighment"""
        # Validate required fields
        if not self.validate_basic_fields():
            return
            
        # Get current weight from weighbridge
        current_weight = self.get_current_weighbridge_value()
        if current_weight is None:
            return
            
        # Set first weighment
        self.first_weight_var.set(str(current_weight))
        
        # Set timestamp
        now = datetime.datetime.now()
        timestamp = now.strftime("%d-%m-%Y %H:%M:%S")
        self.first_timestamp_var.set(timestamp)
        
        # Disable first weighment button, enable second
        self.first_weighment_btn.config(state=tk.DISABLED)
        self.second_weighment_btn.config(state=tk.NORMAL)
        
        # Update current weighment state
        self.current_weighment = "second"
        
        # Automatically save the record to add to the pending queue
        if hasattr(self, 'summary_update_callback'):
            # Try to find the main app to trigger save
            app = self.find_main_app()
            if app and hasattr(app, 'save_record'):
                app.save_record()
            else:
                # Show confirmation if auto-save not available
                messagebox.showinfo("First Weighment", 
                                  f"First weighment recorded: {current_weight} kg\n"
                                  f"Please save the record to add to the pending queue.")
    
    def capture_second_weighment(self):
        """Capture the second weighment"""
        # Validate first weighment exists
        if not self.first_weight_var.get():
            messagebox.showerror("Error", "Please record the first weighment first.")
            return
            
        # Get current weight from weighbridge
        current_weight = self.get_current_weighbridge_value()
        if current_weight is None:
            return
            
        # Set second weighment
        self.second_weight_var.set(str(current_weight))
        
        # Set timestamp
        now = datetime.datetime.now()
        timestamp = now.strftime("%d-%m-%Y %H:%M:%S")
        self.second_timestamp_var.set(timestamp)
        
        # Calculate net weight
        self.calculate_net_weight()
        
        # Automatically save the record to complete the process
        app = self.find_main_app()
        if app and hasattr(app, 'save_record'):
            app.save_record()
        else:
            # Show confirmation if auto-save not available
            messagebox.showinfo("Second Weighment", 
                          f"Second weighment recorded: {current_weight} kg\n"
                          f"Net weight: {self.net_weight_var.get()} kg\n"
                          f"Please save the record to complete the process.")
    
    def get_current_weighbridge_value(self):
        """Get the current value from the weighbridge"""
        try:
            # Try to find the main app instance to access weighbridge data
            app = self.find_main_app()
            if app and hasattr(app, 'settings_panel'):
                # Get weight from the weighbridge display
                weight_str = app.settings_panel.current_weight_var.get()
                
                # Check if weighbridge is connected
                is_connected = app.settings_panel.weighbridge and app.settings_panel.wb_status_var.get() == "Status: Connected"
                
                if not is_connected:
                    messagebox.showerror("Weighbridge Error", 
                                       "Weighbridge is not connected. Please connect the weighbridge in Settings tab.")
                    return None
                
                # Extract number from string like "123.45 kg"
                import re
                match = re.search(r'(\d+\.?\d*)', weight_str)
                if match:
                    return float(match.group(1))
                else:
                    messagebox.showerror("Error", "Could not read weight from weighbridge. Please check connection.")
                    return None
            else:
                messagebox.showerror("Application Error", 
                                   "Cannot access weighbridge settings. Please restart the application.")
                return None
                
        except Exception as e:
            messagebox.showerror("Weighbridge Error", f"Error reading weighbridge: {str(e)}")
            return None
    
    def find_main_app(self):
        """Find the main app instance to access weighbridge data"""
        # Try to traverse up widget hierarchy to find main app instance
        widget = self.parent
        while widget:
            if hasattr(widget, 'settings_panel'):
                return widget
            if hasattr(widget, 'master'):
                widget = widget.master
            else:
                break
        return None
    
    def calculate_net_weight(self):
        """Calculate net weight as the difference between weighments"""
        try:
            first_weight = float(self.first_weight_var.get() or 0)
            second_weight = float(self.second_weight_var.get() or 0)
            
            # Calculate the absolute difference for net weight
            net_weight = abs(first_weight - second_weight)
            
            self.net_weight_var.set(str(net_weight))
        except ValueError:
            # Handle non-numeric input
            self.net_weight_var.set("")
    
    def validate_basic_fields(self):
        """Validate that basic required fields are filled"""
        required_fields = {
            "Ticket No": self.rst_var.get(),
            "Vehicle No": self.vehicle_var.get(),
            "Agency Name": self.agency_var.get()
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value.strip()]
        
        if missing_fields:
            messagebox.showerror("Validation Error", 
                            f"Please fill in the following required fields: {', '.join(missing_fields)}")
            return False
            
        return True
    
    def create_cameras_panel(self, parent):
        """Create the cameras panel with cameras side by side"""
        # Camera container with compact layout
        camera_frame = ttk.LabelFrame(parent, text="Camera Capture")
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
        
        # Create front camera
        self.front_camera = CameraView(front_panel)
        self.front_camera.save_function = self.save_front_image
        
        # Back camera
        back_panel = ttk.Frame(cameras_container, style="TFrame")
        back_panel.grid(row=0, column=1, padx=2, pady=2, sticky="nsew")
        
        # Back Camera title
        ttk.Label(back_panel, text="Back Camera").pack(anchor=tk.W, pady=2)
        
        # Create back camera
        self.back_camera = CameraView(back_panel)
        self.back_camera.save_function = self.save_back_image
    
    def validate_vehicle_number(self):
        """Validate that vehicle number is entered before capturing images"""
        if not self.vehicle_var.get().strip():
            messagebox.showerror("Error", "Please enter a vehicle number before capturing images.")
            return False
        return True
    
    def save_front_image(self, captured_image=None):
        """Save the front view camera image with watermark"""
        if not self.validate_vehicle_number():
            return False
        
        # Use captured image or get from camera
        image = captured_image if captured_image is not None else self.front_camera.captured_image
        
        if image is not None:
            # Generate filename and watermark text
            site_name = self.site_var.get().replace(" ", "_")
            vehicle_no = self.vehicle_var.get().replace(" ", "_")
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
            self.front_image_path = filepath
            self.front_image_status_var.set("Front: ✓")
            self.front_image_status.config(foreground="green")
            
            messagebox.showinfo("Success", "Front image saved!")
            return True
            
        return False
    
    def save_back_image(self, captured_image=None):
        """Save the back view camera image with watermark"""
        if not self.validate_vehicle_number():
            return False
        
        # Use captured image or get from camera
        image = captured_image if captured_image is not None else self.back_camera.captured_image
        
        if image is not None:
            # Generate filename and watermark text
            site_name = self.site_var.get().replace(" ", "_")
            vehicle_no = self.vehicle_var.get().replace(" ", "_")
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
            self.back_image_path = filepath
            self.back_image_status_var.set("Back: ✓")
            self.back_image_status.config(foreground="green")
            
            messagebox.showinfo("Success", "Back image saved!")
            return True
            
        return False
    
    def get_form_data(self):
        """Get form data as a dictionary"""
        # Get current date and time
        now = datetime.datetime.now()
        
        # Prepare data dictionary
        data = {
            'date': now.strftime("%d-%m-%Y"),
            'time': now.strftime("%H:%M:%S"),
            'site_name': self.site_var.get(),
            'agency_name': self.agency_var.get(),
            'material': self.material_var.get(),
            'ticket_no': self.rst_var.get(),
            'vehicle_no': self.vehicle_var.get(),
            'transfer_party_name': self.tpt_var.get(),
            'first_weight': self.first_weight_var.get(),
            'first_timestamp': self.first_timestamp_var.get(),
            'second_weight': self.second_weight_var.get(),
            'second_timestamp': self.second_timestamp_var.get(),
            'net_weight': self.net_weight_var.get(),
            'material_type': self.material_type_var.get(),
            'front_image': os.path.basename(self.front_image_path) if self.front_image_path else "",
            'back_image': os.path.basename(self.back_image_path) if self.back_image_path else ""
        }
        
        return data
    
    def validate_form(self):
        """Validate form fields"""
        required_fields = {
            "Ticket No": self.rst_var.get(),
            "Vehicle No": self.vehicle_var.get(),
            "Agency Name": self.agency_var.get()
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value.strip()]
        
        if missing_fields:
            messagebox.showerror("Validation Error", 
                            f"Please fill in the following required fields: {', '.join(missing_fields)}")
            return False
        
        # For first time entry, we need first weighment
        if self.current_weighment == "first" and not self.first_weight_var.get():
            messagebox.showerror("Validation Error", "Please capture first weighment before saving.")
            return False
            
        # For second weighment entry, we need both first and second
        if self.current_weighment == "second":
            if not self.first_weight_var.get():
                messagebox.showerror("Validation Error", "First weighment is missing.")
                return False
            
            if not self.second_weight_var.get():
                messagebox.showerror("Validation Error", "Please capture second weighment before saving.")
                return False
        
        # Validate at least one image is captured
        if not self.front_image_path and not self.back_image_path:
            result = messagebox.askyesno("Missing Images", 
                                    "No images have been captured. Continue without images?")
            if not result:
                return False
            
        return True
    
    def clear_form(self):
        """Reset form fields except site and Transfer Party Name"""
        # Reset variables
        self.rst_var.set("")
        self.vehicle_var.set("")
        self.agency_var.set("")
        self.first_weight_var.set("")
        self.first_timestamp_var.set("")
        self.second_weight_var.set("")
        self.second_timestamp_var.set("")
        self.net_weight_var.set("")
        self.material_type_var.set("Inert")
        
        # Reset weighment state
        self.current_weighment = "first"
        self.first_weighment_btn.config(state=tk.NORMAL)
        self.second_weighment_btn.config(state=tk.DISABLED)
        
        # Reset image paths
        self.front_image_path = None
        self.back_image_path = None
        self.front_image_status_var.set("Front: ✗")
        self.back_image_status_var.set("Back: ✗")
        self.front_image_status.config(foreground="red")
        self.back_image_status.config(foreground="red")
        
        # Reset camera displays if they were used
        if hasattr(self, 'front_camera'):
            self.front_camera.stop_camera()
            self.front_camera.captured_image = None
            self.front_camera.canvas.delete("all")
            self.front_camera.canvas.create_text(75, 60, text="Click Capture", fill="white", justify=tk.CENTER)
            self.front_camera.capture_button.config(text="Capture")
            
        if hasattr(self, 'back_camera'):
            self.back_camera.stop_camera()
            self.back_camera.captured_image = None
            self.back_camera.canvas.delete("all")
            self.back_camera.canvas.create_text(75, 60, text="Click Capture", fill="white", justify=tk.CENTER)
            self.back_camera.capture_button.config(text="Capture")
    
    def set_site(self, site_name):
        """Set the site name (used when site is selected from login)"""
        if site_name and hasattr(self, 'site_var'):
            self.site_var.set(site_name)
    
    def on_closing(self):
        """Handle cleanup when closing"""
        if hasattr(self, 'front_camera'):
            self.front_camera.stop_camera()
        if hasattr(self, 'back_camera'):
            self.back_camera.stop_camera()