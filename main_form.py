# Updated main_form.py - Complete integration with modular structure

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

# Import modular components
from form_validation import FormValidator
from weight_manager import WeightManager
from vehicle_autocomplete import VehicleAutocomplete
from image_handler import ImageHandler

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
        
        # Initialize form variables
        self.init_variables()
        
        # Initialize helper components
        self.weight_manager = WeightManager(self)
        self.form_validator = FormValidator(self)
        self.vehicle_autocomplete = VehicleAutocomplete(self)
        self.image_handler = ImageHandler(self)
        
        # Camera lock to prevent both cameras from being used simultaneously
        self.camera_lock = threading.Lock()
        
        # Create UI elements
        self.create_form(parent)
        self.create_cameras_panel(parent)
        
        # Initialize vehicle autocomplete
        self.vehicle_autocomplete.refresh_cache()

    def init_variables(self):
        """Initialize form variables"""
        # Create variables for form fields
        self.site_var = tk.StringVar(value="Guntur")
        self.agency_var = tk.StringVar()
        self.rst_var = tk.StringVar()
        self.vehicle_var = tk.StringVar()
        self.tpt_var = tk.StringVar()
        self.material_var = tk.StringVar()
        
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
        
        # Current weight display variable - NEW FEATURE
        self.current_weight_var = tk.StringVar(value="0.00 kg")
        
        # Material type tracking
        self.material_type_var = tk.StringVar(value="Inert")
        
        # Saved image paths
        self.front_image_path = None
        self.back_image_path = None
        
        # Weighment state
        self.current_weighment = "first"  # Can be "first" or "second"
        
        # Vehicle number autocomplete cache
        self.vehicle_numbers_cache = []
        
        # Bind the agency and site variables to update data context
        self.agency_var.trace_add("write", self.on_agency_change)
        self.site_var.trace_add("write", self.on_site_change)
        
        # Generate next ticket number if data manager is available
        if hasattr(self, 'data_manager') and self.data_manager:
            self.generate_next_ticket_number()

    # Import methods from modular files
    from form_ui import create_form
    from camera_ui import create_cameras_panel, load_camera_settings, get_settings_storage, update_camera_settings

    def find_main_app(self):
        """Find the main app instance to access data manager"""
        widget = self.parent
        while widget:
            if hasattr(widget, 'data_manager'):
                return widget
            if hasattr(widget, 'master'):
                widget = widget.master
            else:
                break
        return None

    def on_agency_change(self, *args):
        """Handle agency selection change to update data file context"""
        try:
            if hasattr(self, 'agency_var') and hasattr(self, 'site_var'):
                agency_name = self.agency_var.get()
                site_name = self.site_var.get()
                
                if agency_name and site_name:
                    if hasattr(self, 'data_manager') and self.data_manager:
                        self.data_manager.set_agency_site_context(agency_name, site_name)
                        print(f"Updated data context: {agency_name}_{site_name}")
                    elif hasattr(self, 'save_callback'):
                        app = self.find_main_app()
                        if app and hasattr(app, 'data_manager'):
                            app.data_manager.set_agency_site_context(agency_name, site_name)
                            print(f"Updated data context via app: {agency_name}_{site_name}")
        except Exception as e:
            print(f"Error updating data context: {e}")

    def on_site_change(self, *args):
        """Handle site selection change to update data file context"""
        self.on_agency_change()

    def generate_next_ticket_number(self):
        """Generate the next ticket number based on existing records"""
        if not hasattr(self, 'data_manager') or not self.data_manager:
            return
            
        records = self.data_manager.get_all_records()
        highest_num = 0
        prefix = "T"
        
        for record in records:
            ticket = record.get('ticket_no', '')
            if ticket and ticket.startswith(prefix) and len(ticket) > 1:
                try:
                    num = int(ticket[1:])
                    highest_num = max(highest_num, num)
                except ValueError:
                    pass
        
        next_num = highest_num + 1
        next_ticket = f"{prefix}{next_num:04d}"
        self.rst_var.set(next_ticket)

    def check_ticket_exists(self, event=None):
        """Check if the ticket number already exists in the database"""
        ticket_no = self.rst_var.get().strip()
        if not ticket_no:
            return
            
        if hasattr(self, 'data_manager') and self.data_manager:
            records = self.data_manager.get_filtered_records(ticket_no)
            for record in records:
                if record.get('ticket_no') == ticket_no:
                    if record.get('second_weight') and record.get('second_timestamp'):
                        # messagebox.showinfo("Completed Record", 
                        #                 "This ticket already has both weighments completed.")
                        self.load_record_data(record)
                        self.current_weighment = "second"
                        self.weighment_state_var.set("Weighment Complete")
                        return
                    elif record.get('first_weight') and record.get('first_timestamp'):
                        self.current_weighment = "second"
                        self.load_record_data(record)
                        self.weighment_state_var.set("Second Weighment")
                        # messagebox.showinfo("Existing Ticket", 
                        #                 "This ticket already has a first weighment. Proceed with second weighment.")
                        return
                        
        # New ticket - set for first weighment
        self.current_weighment = "first"
        self.weighment_state_var.set("First Weighment")
        
        # Clear weight fields for new entry
        self.first_weight_var.set("")
        self.first_timestamp_var.set("")
        self.second_weight_var.set("")
        self.second_timestamp_var.set("")
        self.net_weight_var.set("")

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
        
        # Handle images using image handler
        self.image_handler.load_images_from_record(record)

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
        
        # Reset images
        self.image_handler.reset_images()
        
        # Reset cameras
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

    def get_form_data(self):
        """Get form data as a dictionary"""
        now = datetime.datetime.now()
        
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
        for field in ['first_weight', 'second_weight', 'first_timestamp', 'second_timestamp', 'net_weight']:
            if not data[field]:
                data[field] = ''
                
        return data

    def validate_form(self):
        """Validate form fields using form validator"""
        return self.form_validator.validate_form()

    def set_agency(self, agency_name):
        """Set the agency name"""
        if agency_name and hasattr(self, 'agency_var'):
            self.agency_var.set(agency_name)

    def set_site_incharge(self, incharge_name):
        """Set the site incharge name"""
        if incharge_name and hasattr(self, 'site_incharge_var'):
            self.site_incharge_var.set(incharge_name)

    def set_site(self, site_name):
        """Set the site name"""
        if site_name and hasattr(self, 'site_var'):
            self.site_var.set(site_name)

    def set_user_info(self, username=None, site_incharge=None):
        """Set the user and site incharge information"""
        if username and hasattr(self, 'user_name_var'):
            self.user_name_var.set(username)
            
        if site_incharge and hasattr(self, 'site_incharge_var'):
            self.site_incharge_var.set(site_incharge)

    def load_sites_and_agencies(self, settings_storage):
        """Load sites, agencies and transfer parties from settings storage"""
        if not settings_storage:
            return
            
        sites_data = settings_storage.get_sites()
        
        # Update site combo
        sites = sites_data.get('sites', ['Guntur'])
        if hasattr(self, 'site_combo') and self.site_combo:
            self.site_combo['values'] = tuple(sites)
            if self.site_var.get() not in sites and sites:
                self.site_var.set(sites[0])
        
        # Update agency combo
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

    def on_closing(self):
        """Handle cleanup when closing"""
        if hasattr(self, 'front_camera'):
            self.front_camera.stop_camera()
        if hasattr(self, 'back_camera'):
            self.back_camera.stop_camera()

    # Legacy methods that delegate to component managers
    def handle_weighbridge_weight(self, weight):
        """Handle weight from weighbridge - delegates to weight manager"""
        return self.weight_manager.handle_weighbridge_weight(weight)
    
    def capture_weight(self):
        """Capture weight - delegates to weight manager"""
        return self.weight_manager.capture_weight()
    
    def save_front_image(self, captured_image=None):
        """Save front image - delegates to image handler"""
        return self.image_handler.save_front_image(captured_image)
    
    def save_back_image(self, captured_image=None):
        """Save back image - delegates to image handler"""
        return self.image_handler.save_back_image(captured_image)