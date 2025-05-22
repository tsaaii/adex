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
    
    def __init__(self, parent, notebook=None, summary_update_callback=None, data_manager=None, 
                save_callback=None, view_callback=None, clear_callback=None, exit_callback=None):
        """Initialize the main form
        
        Args:
            parent: Parent widget
            notebook: Notebook for tab switching
            summary_update_callback: Function to call to update summary view
            data_manager: Data manager instance for checking existing entries
            save_callback: Callback for save button
            view_callback: Callback for view records button
            clear_callback: Callback for clear button
            exit_callback: Callback for exit button
        """
        self.parent = parent
        self.notebook = notebook
        self.summary_update_callback = summary_update_callback
        self.data_manager = data_manager
        self.save_callback = save_callback
        self.view_callback = view_callback
        self.clear_callback = clear_callback
        self.exit_callback = exit_callback
        
        # Create form variables
        self.init_variables()
        
        # Camera lock to prevent both cameras from being used simultaneously
        self.camera_lock = threading.Lock()
        
        # Create UI elements
        self.create_form(parent)
        self.create_cameras_panel(parent)
        
        # Remove spacebar binding since we now have manual buttons
        # self.parent.bind("<space>", self.handle_space_key)
        self.refresh_vehicle_numbers_cache()

    def handle_weighbridge_weight(self, weight):
        """Handle weight from weighbridge based on current state
        
        Args:
            weight: Current weight from weighbridge
        """
        if not self.validate_basic_fields():
            return
            
        # Format weight to 2 decimal places
        formatted_weight = f"{weight:.2f}"
        
        # Set current timestamp
        now = datetime.datetime.now()
        timestamp = now.strftime("%d-%m-%Y %H:%M:%S")
        
        # Check if this is a first or second weighment
        if self.current_weighment == "first":
            # This is a new entry - set first weighment
            self.first_weight_var.set(formatted_weight)
            self.first_timestamp_var.set(timestamp)
            
            # Change current state to second weighment
            self.current_weighment = "second"
            self.weighment_state_var.set("Second Weighment")
            
            # Save the record to add it to the pending queue
            if self.save_callback:
                self.save_callback()
                
            # Display confirmation
            messagebox.showinfo("First Weighment", 
                            f"First weighment recorded: {formatted_weight} kg\n"
                            f"Record saved to pending queue")
                
        elif self.current_weighment == "second":
            # This is a pending entry - set second weighment
            self.second_weight_var.set(formatted_weight)
            self.second_timestamp_var.set(timestamp)
            
            # Calculate net weight
            self.calculate_net_weight()
            
            # Update state
            self.weighment_state_var.set("Weighment Complete")
            
            # Save the complete record
            if self.save_callback:
                self.save_callback()
                
            # Display confirmation
            messagebox.showinfo("Second Weighment", 
                            f"Second weighment recorded: {formatted_weight} kg\n"
                            f"Net weight: {self.net_weight_var.get()} kg\n"
                            f"Record completed")
            

    def get_current_weighbridge_value(self):
        """Get the current value from the weighbridge using global reference"""
        try:
            # Use the global weighbridge reference
            import config
            weighbridge, weight_var, status_var = config.get_global_weighbridge_info()
            
            if weighbridge is None or weight_var is None or status_var is None:
                messagebox.showerror("Application Error", 
                                "Cannot access weighbridge settings. Please restart the application.")
                return None
            
            # Get weight from the weighbridge display
            weight_str = weight_var.get()
            
            # Check if weighbridge is connected
            is_connected = (weighbridge is not None and 
                        status_var.get() == "Status: Connected")
            
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

    def capture_first_weighment(self):
        """Capture the first weighment"""
        # Validate required fields
        if not self.validate_basic_fields():
            return
            
        # Check if manual entry has a value
        manual_weight = self.first_weight_var.get().strip()
        
        if manual_weight:
            # Use the manually entered weight
            try:
                weight_value = float(manual_weight)
                # Format to 2 decimal places
                self.first_weight_var.set(f"{weight_value:.2f}")
            except ValueError:
                messagebox.showerror("Error", "Invalid weight value. Please enter a valid number.")
                return
        else:
            # Get current weight from weighbridge
            current_weight = self.get_current_weighbridge_value()
            if current_weight is None:
                return
                
            # Set first weighment
            self.first_weight_var.set(f"{current_weight:.2f}")
        
        # Set timestamp
        now = datetime.datetime.now()
        timestamp = now.strftime("%d-%m-%Y %H:%M:%S")
        self.first_timestamp_var.set(timestamp)
        
        # Update current weighment state
        self.current_weighment = "second"
        self.weighment_state_var.set("Second Weighment")
        
        # Display prompt to save the first weighment
        messagebox.showinfo("First Weighment", 
                            f"First weighment recorded: {self.first_weight_var.get()} kg\n"
                            f"Please save the record to add to the pending queue.")

    def capture_second_weighment(self):
        """Capture the second weighment"""
        # Validate first weighment exists
        if not self.first_weight_var.get():
            messagebox.showerror("Error", "Please record the first weighment first.")
            return
            
        # Check if manual entry has a value
        manual_weight = self.second_weight_var.get().strip()
        
        if manual_weight:
            # Use the manually entered weight
            try:
                weight_value = float(manual_weight)
                # Format to 2 decimal places
                self.second_weight_var.set(f"{weight_value:.2f}")
            except ValueError:
                messagebox.showerror("Error", "Invalid weight value. Please enter a valid number.")
                return
        else:
            # Get current weight from weighbridge
            current_weight = self.get_current_weighbridge_value()
            if current_weight is None:
                return
                
            # Set second weighment
            self.second_weight_var.set(f"{current_weight:.2f}")
        
        # Set timestamp
        now = datetime.datetime.now()
        timestamp = now.strftime("%d-%m-%Y %H:%M:%S")
        self.second_timestamp_var.set(timestamp)
        
        # Calculate net weight
        self.calculate_net_weight()
        
        # Update state
        self.weighment_state_var.set("Weighment Complete")
        
        # Display prompt to save and complete the record
        messagebox.showinfo("Second Weighment", 
                        f"Second weighment recorded: {self.second_weight_var.get()} kg\n"
                        f"Net weight: {self.net_weight_var.get()} kg\n"
                        f"Please save the record to complete the process.")

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
                        self.current_weighment = "second"  # Set to "second" even though completed
                        self.weighment_state_var.set("Weighment Complete")
                        return
                    elif record.get('first_weight') and record.get('first_timestamp'):
                        # First weighment done, set up for second
                        self.current_weighment = "second"
                        self.load_record_data(record)
                        self.weighment_state_var.set("Second Weighment")
                        
                        messagebox.showinfo("Existing Ticket", 
                                        "This ticket already has a first weighment. Proceed with second weighment.")
                        return
                        
        # If we get here, this is a new ticket - set for first weighment
        self.current_weighment = "first"
        self.weighment_state_var.set("First Weighment")
        
        # Clear weight fields for new entry
        self.first_weight_var.set("")
        self.first_timestamp_var.set("")
        self.second_weight_var.set("")
        self.second_timestamp_var.set("")
        self.net_weight_var.set("")

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
        self.weighment_state_var.set("First Weighment")
        
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
            
        # Generate new ticket number
        self.generate_next_ticket_number()

    def init_variables(self):
        """Initialize form variables"""
        # Create variables for form fields
        self.site_var = tk.StringVar(value="Guntur")
        self.agency_var = tk.StringVar()
        self.rst_var = tk.StringVar()
        self.vehicle_var = tk.StringVar()
        self.tpt_var = tk.StringVar()
        self.material_var = tk.StringVar()  # Added missing material variable
        
        # User and site incharge variables
        self.user_name_var = tk.StringVar()
        self.site_incharge_var = tk.StringVar()
        
        # Weighment related variables
        self.first_weight_var = tk.StringVar()
        self.first_timestamp_var = tk.StringVar()
        self.second_weight_var = tk.StringVar()
        self.second_timestamp_var = tk.StringVar()
        self.net_weight_var = tk.StringVar()
        self.weighment_state_var = tk.StringVar(value="First Weighment")
        
        # Material type tracking
        self.material_type_var = tk.StringVar(value="Inert")
        
        # Saved image paths
        self.front_image_path = None
        self.back_image_path = None
        
        # Weighment state
        self.current_weighment = "first"  # Can be "first" or "second"
        
        # Vehicle number autocomplete cache
        self.vehicle_numbers_cache = []
        
        # If data manager is available, generate the next ticket number
        if hasattr(self, 'data_manager') and self.data_manager:
            self.generate_next_ticket_number()

    def refresh_vehicle_numbers_cache(self):
        """Refresh the cache of vehicle numbers for autocomplete"""
        self.vehicle_numbers_cache = self.get_vehicle_numbers()
        if hasattr(self, 'vehicle_entry'):
            self.vehicle_entry['values'] = self.vehicle_numbers_cache

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

# In main_form.py, fix the capture_weight method

    def capture_weight(self):
        """Capture weight from weighbridge based on current state"""
        # Validate required fields
        if not self.validate_basic_fields():
            return
            
        # Get current weight from weighbridge
        current_weight = self.get_current_weighbridge_value()
        if current_weight is None:
            return
        
        # Get current timestamp
        now = datetime.datetime.now()
        timestamp = now.strftime("%d-%m-%Y %H:%M:%S")
        
        # Determine which weighment to capture based on current state
        if self.current_weighment == "first":
            # Capture first weighment
            self.first_weight_var.set(f"{current_weight:.2f}")
            
            # Set timestamp
            self.first_timestamp_var.set(timestamp)
            
            # Update current weighment state
            self.current_weighment = "second"
            self.weighment_state_var.set("Second Weighment")
            
            # Display prompt to save the first weighment - but don't auto-save
            messagebox.showinfo("First Weighment", 
                            f"First weighment recorded: {current_weight:.2f} kg\n"
                            f"Time: {timestamp}\n"
                            f"Click Save Record to add to the pending queue.")
            
            # REMOVED: Automatic save attempt
            # app = self.find_main_app()
            # if app and hasattr(app, 'save_record'):
            #     app.save_record()
                
        elif self.current_weighment == "second":
            # Capture second weighment
            self.second_weight_var.set(f"{current_weight:.2f}")
            
            # Set timestamp
            self.second_timestamp_var.set(timestamp)
            
            # Calculate net weight
            self.calculate_net_weight()
            
            # Update state
            self.weighment_state_var.set("Weighment Complete")
            
            # Display prompt to save and complete the record - but don't auto-save
            messagebox.showinfo("Second Weighment", 
                            f"Second weighment recorded: {current_weight:.2f} kg\n"
                            f"Time: {timestamp}\n"
                            f"Net weight: {self.net_weight_var.get()} kg\n"
                            f"Click Save Record to complete the process.")
        
        # REMOVED: Automatic save attempt
        # app = self.find_main_app()
        # if app and hasattr(app, 'save_record'):
        #     app.save_record()

    def calculate_net_weight(self):
        """Calculate net weight as the difference between weighments"""
        # Check if we have at least one weight
        first_weight_str = self.first_weight_var.get().strip()
        second_weight_str = self.second_weight_var.get().strip()
        
        try:
            if first_weight_str and second_weight_str:
                # Calculate difference if both weights are available
                first_weight = float(first_weight_str)
                second_weight = float(second_weight_str)
                
                # Calculate the absolute difference for net weight
                net_weight = abs(first_weight - second_weight)
                
                # Format to 2 decimal places
                self.net_weight_var.set(f"{net_weight:.2f}")
            elif first_weight_str:
                # If only first weight available, leave net weight empty
                self.net_weight_var.set("")
            else:
                # No weights available
                messagebox.showerror("Error", "Please enter at least one weight value")
                
        except ValueError:
            # Handle non-numeric input
            messagebox.showerror("Error", "Invalid weight values. Please enter valid numbers.")
            self.net_weight_var.set("")


    def create_form(self, parent):
        """Create the main data entry form with modified layout"""
        # Vehicle Information Frame
        form_frame = ttk.LabelFrame(parent, text="Vehicle Information")
        form_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Set background color for better visibility
        form_inner = ttk.Frame(form_frame, style="TFrame")
        form_inner.pack(fill=tk.BOTH, padx=5, pady=5)
        
        # Configure grid columns for better distribution
        for i in range(3):  # 3 columns
            form_inner.columnconfigure(i, weight=1)  # Equal weight
        
        # =================== ROW 0: First row of labels ===================
        # Ticket No - Column 0
        ttk.Label(form_inner, text="Ticket No:").grid(row=0, column=0, sticky=tk.W, padx=3, pady=3)
        
        # Site Name - Column 1
        ttk.Label(form_inner, text="Site Name:").grid(row=0, column=1, sticky=tk.W, padx=3, pady=3)
        
        # Agency Name - Column 2
        ttk.Label(form_inner, text="Agency Name:").grid(row=0, column=2, sticky=tk.W, padx=3, pady=3)
        
        # =================== ROW 1: First row of entries ===================
        # Ticket No Entry - Column 0
        ticket_entry = ttk.Entry(form_inner, textvariable=self.rst_var, width=config.STD_WIDTH)
        ticket_entry.grid(row=1, column=0, sticky=tk.W, padx=3, pady=3)
        ticket_entry.bind("<FocusOut>", self.check_ticket_exists)
        
        # Auto-generate next ticket button
        auto_ticket_btn = HoverButton(form_inner, text="Auto", 
                                    bg=config.COLORS["primary_light"], 
                                    fg=config.COLORS["text"],
                                    padx=2, pady=1,
                                    command=self.generate_next_ticket_number)
        auto_ticket_btn.grid(row=1, column=0, sticky=tk.E, padx=(0, 5), pady=3)
        
        # Site Name Entry - Column 1
        self.site_combo = ttk.Combobox(form_inner, textvariable=self.site_var, state="readonly", width=config.STD_WIDTH)
        self.site_combo['values'] = ('Guntur',)
        self.site_combo.grid(row=1, column=1, sticky=tk.W, padx=3, pady=3)
        
        # Agency Name Combobox - Column 2 (now a dropdown)
        self.agency_combo = ttk.Combobox(form_inner, textvariable=self.agency_var, state="readonly", width=config.STD_WIDTH)
        self.agency_combo['values'] = ('Default Agency',)  # Default value, will be updated from settings
        self.agency_combo.grid(row=1, column=2, sticky=tk.W, padx=3, pady=3)
        
        # =================== ROW 2: Second row of labels ===================
        # Vehicle No - Column 0
        ttk.Label(form_inner, text="Vehicle No:").grid(row=2, column=0, sticky=tk.W, padx=3, pady=3)
        
        # Transfer Party Name - Column 1
        ttk.Label(form_inner, text="Transfer Party Name:").grid(row=2, column=1, sticky=tk.W, padx=3, pady=3)
        
        # Material Type - Column 2 
        ttk.Label(form_inner, text="Material Type:").grid(row=2, column=2, sticky=tk.W, padx=3, pady=3)
        
        # =================== ROW 3: Second row of entries ===================
        # Vehicle No Entry - Column 0
        self.vehicle_entry = ttk.Combobox(form_inner, textvariable=self.vehicle_var, width=config.STD_WIDTH)
        self.vehicle_entry.grid(row=3, column=0, sticky=tk.W, padx=3, pady=3)
        # Load initial vehicle numbers
        self.vehicle_entry['values'] = self.get_vehicle_numbers()
        # Bind events for autocomplete
        self.vehicle_entry.bind('<KeyRelease>', self.update_vehicle_autocomplete)
        
        # Transfer Party Name Combobox - Column 1 (now a dropdown)
        self.tpt_combo = ttk.Combobox(form_inner, textvariable=self.tpt_var, state="readonly", width=config.STD_WIDTH)
        self.tpt_combo['values'] = ('Advitia Labs',)  # Default value, will be updated from settings
        self.tpt_combo.grid(row=3, column=1, sticky=tk.W, padx=3, pady=3)
        
        # Material Type Combo - Column 2
        material_type_combo = ttk.Combobox(form_inner, 
                                        textvariable=self.material_type_var, 
                                        state="readonly", 
                                        width=config.STD_WIDTH)
        material_type_combo['values'] = ('Inert', 'Soil', 'Construction and Demolition', 
                                    'RDF(REFUSE DERIVED FUEL)')
        material_type_combo.grid(row=3, column=2, sticky=tk.W, padx=3, pady=3)
        
        # =================== WEIGHMENT PANEL (UPDATED) ===================
        weighment_frame = ttk.LabelFrame(form_inner, text="Weighment Information")
        weighment_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=3, pady=10)

        # Configure grid columns for weighment panel
        weighment_frame.columnconfigure(0, weight=1)  # Description
        weighment_frame.columnconfigure(1, weight=1)  # Weight value
        weighment_frame.columnconfigure(2, weight=1)  # Timestamp
        weighment_frame.columnconfigure(3, weight=1)  # Button

        # First Row - First Weighment
        ttk.Label(weighment_frame, text="First Weighment:", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5)

        # First Weight Entry (read-only)
        self.first_weight_entry = ttk.Entry(weighment_frame, textvariable=self.first_weight_var, 
                                    width=12, style="Weight.TEntry", state="readonly")
        self.first_weight_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        # First Timestamp
        #ttk.Label(weighment_frame, text="Timestamp:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        first_timestamp_label = ttk.Label(weighment_frame, textvariable=self.first_timestamp_var, foreground="blue")
        first_timestamp_label.grid(row=0, column=2, sticky=tk.E, padx=5, pady=5)

        # Second Row - Second Weighment
        ttk.Label(weighment_frame, text="Second Weighment:", font=("Segoe UI", 9, "bold")).grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5)

        # Second Weight Entry (read-only)
        self.second_weight_entry = ttk.Entry(weighment_frame, textvariable=self.second_weight_var, 
                                        width=12, style="Weight.TEntry", state="readonly")
        self.second_weight_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # Second Timestamp
        #ttk.Label(weighment_frame, text="Timestamp:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        second_timestamp_label = ttk.Label(weighment_frame, textvariable=self.second_timestamp_var, foreground="blue")
        second_timestamp_label.grid(row=1, column=2, sticky=tk.E, padx=5, pady=5)

        # Third Row - Net Weight
        ttk.Label(weighment_frame, text="Net Weight:", font=("Segoe UI", 9, "bold")).grid(
            row=2, column=0, sticky=tk.W, padx=5, pady=5)

        # Net Weight Display (read-only)
        net_weight_display = ttk.Entry(weighment_frame, textvariable=self.net_weight_var, 
                                    width=12, state="readonly", style="Weight.TEntry")
        net_weight_display.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        # Single Capture Weight Button - replaces separate buttons
        self.capture_weight_btn = HoverButton(weighment_frame, text="Capture Weight", 
                                        bg=config.COLORS["primary"], 
                                        fg=config.COLORS["button_text"],
                                        padx=10, pady=3,
                                        command=self.capture_weight)
        self.capture_weight_btn.grid(row=0, column=3, rowspan=2, sticky="ns", padx=5, pady=5)

        # Current weighment state indicator
        state_frame = ttk.Frame(weighment_frame)
        state_frame.grid(row=3, column=0, columnspan=4, sticky=tk.EW, padx=5, pady=(10,5))

        state_label = ttk.Label(state_frame, text="Current State: ", font=("Segoe UI", 9))
        state_label.pack(side=tk.LEFT)

        state_value_label = ttk.Label(state_frame, textvariable=self.weighment_state_var, 
                                    font=("Segoe UI", 9, "bold"), foreground=config.COLORS["primary"])
        state_value_label.pack(side=tk.LEFT)

        # Note about automatic capture
        manual_note = ttk.Label(state_frame, 
                            text="Note: Weights are automatically captured from the weighbridge", 
                            font=("Segoe UI", 8, "italic"), 
                            foreground="gray")
        manual_note.pack(side=tk.RIGHT)
                
        # Image status indicators
        image_status_frame = ttk.Frame(form_inner)
        image_status_frame.grid(row=5, column=0, columnspan=3, sticky=tk.W, padx=3, pady=3)
        
        ttk.Label(image_status_frame, text="Images:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.front_image_status_var = tk.StringVar(value="Front: ✗")
        self.front_image_status = ttk.Label(image_status_frame, textvariable=self.front_image_status_var, foreground="red")
        self.front_image_status.pack(side=tk.LEFT, padx=(0, 5))
        
        self.back_image_status_var = tk.StringVar(value="Back: ✗")
        self.back_image_status = ttk.Label(image_status_frame, textvariable=self.back_image_status_var, foreground="red")
        self.back_image_status.pack(side=tk.LEFT)



    def update_vehicle_autocomplete(self, event=None):
        """Update vehicle number autocomplete options based on current input"""
        current_text = self.vehicle_var.get().strip().upper()
        if not current_text:
            return
            
        # Get all vehicle numbers
        all_vehicles = self.get_vehicle_numbers()
        
        # Filter based on matching - checking for partial matches
        matches = []
        for vehicle in all_vehicles:
            # Convert to uppercase for case-insensitive comparison
            vehicle_upper = vehicle.upper()
            
            # Check if the current text appears anywhere in the vehicle number
            if current_text in vehicle_upper:
                matches.append(vehicle)
            
            # Special focus on the last 4 characters - if the vehicle number has at least 4 characters
            if len(vehicle_upper) >= 4:
                last_four = vehicle_upper[-4:]
                # If the current text appears in the last 4 characters, add it with higher priority
                if current_text in last_four and vehicle not in matches:
                    matches.append(vehicle)
        
        # Update the dropdown values
        if matches:
            self.vehicle_entry['values'] = matches
            
            # Only drop down the list if we have a decent match and the user has typed at least 2 characters
            if len(current_text) >= 2 and len(matches) > 0:
                self.vehicle_entry.event_generate('<Down>')

    def load_sites_and_agencies(self, settings_storage):
        """Load sites, agencies and transfer parties from settings storage"""
        if not settings_storage:
            return
            
        # Get sites and data
        sites_data = settings_storage.get_sites()
        
        # Update site combo
        sites = sites_data.get('sites', ['Guntur'])
        if hasattr(self, 'site_combo') and self.site_combo:
            self.site_combo['values'] = tuple(sites)
            
            # If current value not in list, set to first site
            if self.site_var.get() not in sites and sites:
                self.site_var.set(sites[0])
        
        # Update agency combo - now using 'agencies' field
        agencies = sites_data.get('agencies', ['Default Agency'])
        if hasattr(self, 'agency_combo') and self.agency_combo:
            self.agency_combo['values'] = tuple(agencies)
            if not self.agency_var.get() and agencies:
                self.agency_var.set(agencies[0])
                
        # Update transfer party combo
        transfer_parties = sites_data.get('transfer_parties', ['Advitia Labs'])
        if hasattr(self, 'tpt_combo') and self.tpt_combo:
            self.tpt_combo['values'] = tuple(transfer_parties)
            if not self.tpt_var.get() and transfer_parties:
                self.tpt_var.set(transfer_parties[0])


    def set_agency(self, agency_name):
        """Set the agency name (used when agency is selected from login)"""
        if agency_name and hasattr(self, 'agency_var'):
            self.agency_var.set(agency_name)

        
    def load_record_data(self, record):
        """Load record data into the form"""
        # Set basic fields
        self.rst_var.set(record.get('ticket_no', ''))
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
        
        # Handle images if they exist
        front_image = record.get('front_image', '')
        back_image = record.get('back_image', '')
        
        if front_image:
            self.front_image_path = os.path.join(config.IMAGES_FOLDER, front_image)
            self.front_image_status_var.set("Front: ✓")
            self.front_image_status.config(foreground="green")
        else:
            self.front_image_path = None
            self.front_image_status_var.set("Front: ✗")
            self.front_image_status.config(foreground="red")
            
        if back_image:
            self.back_image_path = os.path.join(config.IMAGES_FOLDER, back_image)
            self.back_image_status_var.set("Back: ✓")
            self.back_image_status.config(foreground="green")
        else:
            self.back_image_path = None
            self.back_image_status_var.set("Back: ✗")
            self.back_image_status.config(foreground="red")
    

    
    def get_vehicle_numbers(self):
        """Get a list of unique vehicle numbers from the database"""
        vehicle_numbers = []
        if hasattr(self, 'data_manager') and self.data_manager:
            records = self.data_manager.get_all_records()
            # Extract unique vehicle numbers from records
            for record in records:
                vehicle_no = record.get('vehicle_no', '')
                if vehicle_no and vehicle_no not in vehicle_numbers:
                    vehicle_numbers.append(vehicle_no)
        return vehicle_numbers
    
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
        """Create the cameras panel with cameras side by side and action buttons"""
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
            'material': self.material_var.get() if hasattr(self, 'material_var') else "",
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
            'back_image': os.path.basename(self.back_image_path) if self.back_image_path else "",
            'site_incharge': self.site_incharge_var.get() if hasattr(self, 'site_incharge_var') else "",
            'user_name': self.user_name_var.get() if hasattr(self, 'user_name_var') else ""
        }
        
        # Ensure empty weight fields are saved as empty strings
        if not data['first_weight']:
            data['first_weight'] = ''
        if not data['second_weight']:
            data['second_weight'] = ''
        if not data['first_timestamp']:
            data['first_timestamp'] = ''
        if not data['second_timestamp']:
            data['second_timestamp'] = ''
        if not data['net_weight']:
            data['net_weight'] = ''
            
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
        
        # For first time entry, we need first weighment and timestamp
        if self.current_weighment == "first" and (not self.first_weight_var.get() or not self.first_timestamp_var.get()):
            messagebox.showerror("Validation Error", "Please capture first weighment before saving.")
            return False
            
        # If this is a second weighment being completed, check if the second weight and timestamp exist
        # This validation is only applied if we're trying to complete the second weighment
        if self.current_weighment == "second" and self.second_weight_var.get() and not self.second_timestamp_var.get():
            messagebox.showerror("Validation Error", "Second weighment timestamp is missing.")
            return False
        
        # Note: We are no longer requiring second weighment to save the record
        # This allows records with only first weighment to be saved to the pending panel
                
        # Validate at least one image is captured
        if not self.front_image_path and not self.back_image_path:
            result = messagebox.askyesno("Missing Images", 
                                    "No images have been captured. Continue without images?")
            if not result:
                return False
            
        return True

    def set_user_info(self, username=None, site_incharge=None):
        """Set the user and site incharge information
        
        Args:
            username: The logged-in username
            site_incharge: The site incharge name selected at login
        """
        if username and hasattr(self, 'user_name_var'):
            self.user_name_var.set(username)
            
        if site_incharge and hasattr(self, 'site_incharge_var'):
            self.site_incharge_var.set(site_incharge)

    
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