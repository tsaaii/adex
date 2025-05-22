import tkinter as tk
import os
import datetime
import threading
from tkinter import ttk, messagebox
from pending_vehicles_panel import PendingVehiclesPanel
import config
from ui_components import HoverButton, create_styles
from camera import CameraView
from main_form import MainForm
from summary_panel import SummaryPanel
from settings_panel import SettingsPanel
from data_management import DataManager
from reports import export_to_excel, export_to_pdf
from settings_storage import SettingsStorage
from login_dialog import LoginDialog

class TharuniApp:
    """Main application class"""
    
    def __init__(self, root):
        """Initialize the application with authentication
        
        Args:
            root: Root Tkinter window
        """
        self.root = root
        self.root.title("Advitia Labs")
        self.root.geometry("900x580")
        self.root.minsize(900, 580)
        
        # Set up initial configuration
        config.setup()
        
        # Initialize data manager
        self.data_manager = DataManager()
        
        # Initialize settings storage
        self.settings_storage = SettingsStorage()
        
        # Initialize UI styles
        self.style = create_styles()
        
        # Show login dialog before creating UI
        self.logged_in_user = None
        self.user_role = None
        self.selected_site = None
        self.selected_incharge = None  # Added incharge selection
        self.authenticate_user()
        
        # Initialize UI components if login successful
        if self.logged_in_user:
            self.create_widgets()
            
            # Start time update
            self.update_datetime()
            
            # Start periodic refresh for pending vehicles
            self.periodic_refresh()
            
            # Add window close handler
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def authenticate_user(self):
        """Show login dialog and authenticate user"""
        login = LoginDialog(self.root, self.settings_storage, show_select=True)
        
        if login.result:
            self.logged_in_user = login.username
            self.user_role = login.role
            self.selected_site = login.site
            self.selected_incharge = login.incharge  # Store the selected incharge
        else:
            # Exit application if login failed or canceled
            self.root.quit()
    
    def create_main_panel(self, parent):
        """Create main panel with form and pending vehicles list"""
        # Main panel to hold everything with scrollable frame for small screens
        main_panel = ttk.Frame(parent, style="TFrame")
        main_panel.pack(fill=tk.BOTH, expand=True)
        
        # Configure main_panel for proper resizing
        main_panel.columnconfigure(0, weight=3)  # Left panel gets 3x the weight
        main_panel.columnconfigure(1, weight=1)  # Right panel gets 1x the weight
        main_panel.rowconfigure(0, weight=1)     # Single row gets all the weight
        
        # Split the main panel into two parts: form and pending vehicles
        # Use grid instead of pack for better resize control
        left_panel = ttk.Frame(main_panel, style="TFrame")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        right_panel = ttk.Frame(main_panel, style="TFrame")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Add a canvas with scrollbar for small screens on the left panel
        canvas = tk.Canvas(left_panel, bg=config.COLORS["background"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=canvas.yview)
        
        # Configure left_panel for proper resizing
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(0, weight=1)
        
        # Create a frame that will contain the form and cameras
        scrollable_frame = ttk.Frame(canvas, style="TFrame")
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Add the frame to the canvas
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create the main form - pass data manager for ticket lookup
        self.main_form = MainForm(
            scrollable_frame, 
            notebook=self.notebook,
            summary_update_callback=self.update_summary,
            data_manager=self.data_manager,
            save_callback=self.save_record,
            view_callback=self.view_records,
            clear_callback=self.clear_form,
            exit_callback=self.on_closing
        )

        # Load sites and agencies for dropdowns in the main form
        self.main_form.load_sites_and_agencies(self.settings_storage)

        # Set the site name based on login selection if available
        if self.selected_site:
            self.main_form.set_site(self.selected_site)

        # Set the agency/incharge name based on login selection if available
        if self.selected_incharge:
            self.main_form.set_agency(self.selected_incharge)
        
        # Set user information
        self.main_form.set_user_info(
            username=self.logged_in_user,
            site_incharge=self.selected_incharge
        )

        # Create the pending vehicles panel on the right
        self.pending_vehicles = PendingVehiclesPanel(
            right_panel,
            data_manager=self.data_manager,
            on_vehicle_select=self.load_pending_vehicle
        )
        
        # Configure scroll region after adding content
        scrollable_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    def create_widgets(self):
        """Create all widgets and layout for the application"""
        # Create main container frame
        main_container = ttk.Frame(self.root, padding="5", style="TFrame")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Title and header section with user and site info
        self.create_header(main_container)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Create tabs
        main_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(main_tab, text="Vehicle Entry")
        
        summary_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(summary_tab, text="Recent Entries")
        
        settings_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(settings_tab, text="Settings")
        
        # Main panel with scrollable frame for small screens
        self.create_main_panel(main_tab)
        
        # Create summary panel
        self.summary_panel = SummaryPanel(summary_tab, self.data_manager)
        
        # Create settings panel with user info and weighbridge callback
        self.settings_panel = SettingsPanel(
            settings_tab, 
            weighbridge_callback=self.update_weight_from_weighbridge,  # This is the key callback
            update_cameras_callback=self.update_camera_indices,
            current_user=self.logged_in_user,
            user_role=self.user_role
        )
        
        # Handle role-based access to settings tabs - with error handling
        try:
            if self.user_role != 'admin' and hasattr(self.settings_panel, 'settings_notebook'):
                # Hide user and site management tabs for non-admin users
                self.settings_panel.settings_notebook.tab(2, state=tk.HIDDEN)  # Users tab
                self.settings_panel.settings_notebook.tab(3, state=tk.HIDDEN)  # Sites tab
        except (AttributeError, tk.TclError) as e:
            print(f"Error setting tab visibility: {e}")
    
    def create_header(self, parent):
        """Create header with title, user info, site info, incharge info and date/time"""
        # Title with company logo effect
        header_frame = ttk.Frame(parent, style="TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Create a styled header with gradient-like background
        title_box = tk.Frame(header_frame, bg=config.COLORS["header_bg"], padx=10, pady=5)
        title_box.pack(fill=tk.X)
        
        title_label = tk.Label(title_box, 
                            text="Advitia Labs", 
                            font=("Segoe UI", 14, "bold"),
                            fg=config.COLORS["white"],
                            bg=config.COLORS["header_bg"])
        title_label.pack(side=tk.LEFT)
        
        # User and Site info
        info_frame = tk.Frame(title_box, bg=config.COLORS["header_bg"])
        info_frame.pack(side=tk.LEFT, padx=20)
        
        # Show user info
        user_label = tk.Label(info_frame, 
                        text=f"User: {self.logged_in_user}" + (" (Admin)" if self.user_role == 'admin' else ""),
                        font=("Segoe UI", 9, "italic"),
                        fg=config.COLORS["white"],
                        bg=config.COLORS["header_bg"])
        user_label.pack(side=tk.TOP, anchor=tk.W)
        
        # Show site info if available
        if self.selected_site:
            site_label = tk.Label(info_frame, 
                            text=f"Site: {self.selected_site}",
                            font=("Segoe UI", 9, "italic"),
                            fg=config.COLORS["white"],
                            bg=config.COLORS["header_bg"])
            site_label.pack(side=tk.TOP, anchor=tk.W)
        
        # Show incharge info if available
        if self.selected_incharge:
            incharge_label = tk.Label(info_frame, 
                                text=f"Incharge: {self.selected_incharge}",
                                font=("Segoe UI", 9, "italic"),
                                fg=config.COLORS["white"],
                                bg=config.COLORS["header_bg"])
            incharge_label.pack(side=tk.TOP, anchor=tk.W)
        
        # Add logout button
        logout_btn = HoverButton(title_box, 
                            text="Logout", 
                            font=("Segoe UI", 9),
                            bg=config.COLORS["button_alt"],
                            fg=config.COLORS["white"],
                            padx=5, pady=1,
                            command=self.logout)
        logout_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Date and time frame (right side of header)
        datetime_frame = tk.Frame(title_box, bg=config.COLORS["header_bg"])
        datetime_frame.pack(side=tk.RIGHT)
        
        # Date and time variables
        self.date_var = tk.StringVar()
        self.time_var = tk.StringVar()
        
        date_label_desc = tk.Label(datetime_frame, text="Date:", 
                                font=("Segoe UI", 9),
                                fg=config.COLORS["white"],
                                bg=config.COLORS["header_bg"])
        date_label_desc.grid(row=0, column=0, sticky="w", padx=(0, 2))
        
        date_label = tk.Label(datetime_frame, textvariable=self.date_var, 
                            font=("Segoe UI", 9, "bold"),
                            fg=config.COLORS["white"],
                            bg=config.COLORS["header_bg"])
        date_label.grid(row=0, column=1, sticky="w", padx=(0, 10))
        
        time_label_desc = tk.Label(datetime_frame, text="Time:", 
                                font=("Segoe UI", 9),
                                fg=config.COLORS["white"],
                                bg=config.COLORS["header_bg"])
        time_label_desc.grid(row=0, column=2, sticky="w", padx=(0, 2))
        
        time_label = tk.Label(datetime_frame, textvariable=self.time_var, 
                            font=("Segoe UI", 9, "bold"),
                            fg=config.COLORS["white"],
                            bg=config.COLORS["header_bg"])
        time_label.grid(row=0, column=3, sticky="w")
    
# In advitia_app.py, fix load_pending_vehicle method

    def load_pending_vehicle(self, ticket_no):
        """Load a pending vehicle when selected from the pending vehicles panel
        
        Args:
            ticket_no: Ticket number to load
        """
        if hasattr(self, 'main_form'):
            # Switch to main tab
            self.notebook.select(0)
            
            # Set the ticket number in the form
            self.main_form.rst_var.set(ticket_no)
            
            # Trigger the ticket existence check
            # This will load record data and set correct weighment state
            self.main_form.check_ticket_exists()
            
            # CHANGED: Don't automatically capture weight when selecting a pending vehicle
            # Instead, inform the user they need to capture weight manually
            if self.is_weighbridge_connected():
                messagebox.showinfo("Vehicle Selected", 
                                f"Ticket {ticket_no} loaded for second weighment.\n"
                                "Press 'Capture Weight' button when the vehicle is on the weighbridge.")
                
                # REMOVED: The auto-capture code
                # weight = self.get_current_weighbridge_weight()
                # if weight is not None:
                #     self.main_form.handle_weighbridge_weight(weight)
    
    def is_weighbridge_connected(self):
        """Check if weighbridge is connected"""
        if hasattr(self, 'settings_panel') and hasattr(self.settings_panel, 'wb_status_var'):
            return self.settings_panel.wb_status_var.get() == "Status: Connected"
        return False
    
    def get_current_weighbridge_weight(self):
        """Get the current weight from weighbridge"""
        if hasattr(self, 'settings_panel') and hasattr(self.settings_panel, 'current_weight_var'):
            weight_str = self.settings_panel.current_weight_var.get()
            import re
            match = re.search(r'(\d+\.?\d*)', weight_str)
            if match:
                return float(match.group(1))
        return None
    
    def update_datetime(self):
        """Update date and time display"""
        now = datetime.datetime.now()
        self.date_var.set(now.strftime("%d-%m-%Y"))
        self.time_var.set(now.strftime("%H:%M:%S"))
        self.root.after(1000, self.update_datetime)  # Update every second
    
    def periodic_refresh(self):
        """Periodically refresh data displays"""
        try:
            # Update pending vehicles list if it exists
            if hasattr(self, 'pending_vehicles') and self.pending_vehicles:
                self.update_pending_vehicles()
            
            # Schedule next refresh and store the job ID so we can cancel it if needed
            self._refresh_job = self.root.after(60000, self.periodic_refresh)  # Refresh every minute
        except Exception as e:
            print(f"Error in periodic refresh: {e}")
            # Try to reschedule even if there was an error
            self._refresh_job = self.root.after(60000, self.periodic_refresh)


    # Fix for TharuniApp.update_weight_from_weighbridge in advitia_app.py
    # Fix for TharuniApp.update_weight_from_weighbridge in advitia_app.py



    # Update main_form.py with a new validation method to avoid changing the signature of existing methods

    def validate_basic_fields(self):
        """Validate that basic required fields are filled"""
        return self._validate_basic_fields_internal(show_error=True)

    def _validate_basic_fields_internal(self, show_error=True):
        """Internal validation method with error display control
        
        Args:
            show_error: Whether to show error message boxes
        """
        required_fields = {
            "Ticket No": self.rst_var.get(),
            "Vehicle No": self.vehicle_var.get(),
            "Agency Name": self.agency_var.get()
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value.strip()]
        
        if missing_fields:
            if show_error:
                messagebox.showerror("Validation Error", 
                                f"Please fill in the following required fields: {', '.join(missing_fields)}")
            return False
            
        return True
    # In advitia_app.py, modify update_weight_from_weighbridge

    def update_weight_from_weighbridge(self, weight):
        """Update weight from weighbridge - this is the key callback function
        
        Args:
            weight: Weight value from weighbridge
        """
        # Guard against recursive calls
        if hasattr(self, '_processing_weight_update') and self._processing_weight_update:
            return
        
        try:
            # Set processing flag
            self._processing_weight_update = True
            
            # Make the weight available to the main form
            if hasattr(self, 'settings_panel'):
                self.settings_panel.current_weight_var.set(f"{weight} kg")
                
            # Remove callback to settings_panel to prevent circular reference
            # if hasattr(self, 'settings_panel'):
            #     self.settings_panel.update_weight_display(weight)
                
            # Only update UI, don't perform automatic actions
            # Just update the weight display in the UI
            if self.notebook.index("current") == 0 and hasattr(self, 'main_form'):
                # Update the weight display, but don't automatically capture or save
                if hasattr(self.main_form, 'current_weight_var'):
                    self.main_form.current_weight_var.set(f"{weight:.2f} kg")
                    
                # IMPORTANT: Only automatically capture weight when explicitly requested
                # by the user, not on every weighbridge update
                if hasattr(self, '_auto_capture_requested') and self._auto_capture_requested:
                    self._auto_capture_requested = False  # Reset the flag
                    if hasattr(self.main_form, 'handle_weighbridge_weight'):
                        self.main_form.handle_weighbridge_weight(weight)
        finally:
            # Clear processing flag
            self._processing_weight_update = False

        # Add a method to request auto capture when user explicitly asks for it
    def request_auto_capture(self):
        """Request that the next weighbridge update auto-captures the weight"""
        self._auto_capture_requested = True

    # In main_form.py, modify the handle_weighbridge_weight method
    def handle_weighbridge_weight(self, weight):
        """Handle weight from weighbridge based on current state
        
        Args:
            weight: Current weight from weighbridge
        """
        # Add a guard flag
        if hasattr(self, '_processing_weight') and self._processing_weight:
            return
            
        try:
            # Set processing flag
            self._processing_weight = True
            
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
                
                # DON'T auto-save unless user explicitly requested it
                user_requested_save = getattr(self, '_user_requested_save', False)
                if self.save_callback and user_requested_save:
                    self._user_requested_save = False  # Reset the flag
                    self.save_callback()
                    
                # Display confirmation
                messagebox.showinfo("First Weighment", 
                                f"First weighment recorded: {formatted_weight} kg\n"
                                f"Click Save Record to add to pending queue")
                    
            elif self.current_weighment == "second":
                # Similar changes for second weighment
                self.second_weight_var.set(formatted_weight)
                self.second_timestamp_var.set(timestamp)
                
                # Calculate net weight
                self.calculate_net_weight()
                
                # Update state
                self.weighment_state_var.set("Weighment Complete")
                
                # DON'T auto-save unless user explicitly requested it
                user_requested_save = getattr(self, '_user_requested_save', False)
                if self.save_callback and user_requested_save:
                    self._user_requested_save = False  # Reset the flag
                    self.save_callback()
                    
                # Display confirmation
                messagebox.showinfo("Second Weighment", 
                                f"Second weighment recorded: {formatted_weight} kg\n"
                                f"Net weight: {self.net_weight_var.get()} kg\n"
                                f"Click Save Record to complete the record")
        finally:
            # Clear processing flag
            self._processing_weight = False

    # Add a method to request user-initiated save
    def request_save(self):
        """Mark that the user has explicitly requested a save"""
        self._user_requested_save = True

        # Update settings_panel.py update_weight_display to avoid double callbacks

        def update_weight_display(self, weight):
            """Update weight display (callback for weighbridge)
            
            Args:
                weight: Weight value to display
            """
            # Guard against recursive callbacks
            if self.processing_callback:
                return
                
            try:
                self.processing_callback = True
                
                # Update the weight variable
                self.current_weight_var.set(f"{weight:.2f} kg")
                
                # Update weight label color based on connection status
                if hasattr(self, 'weight_label'):
                    if self.wb_status_var.get() == "Status: Connected":
                        self.weight_label.config(foreground="green")
                    else:
                        self.weight_label.config(foreground="red")
                
                # Only propagate the callback if this is a direct weighbridge update,
                # not if we're being called from TharuniApp.update_weight_from_weighbridge
                if self.weighbridge_callback and not hasattr(self, '_from_app_update'):
                    try:
                        # Set a flag so we know this is from TharuniApp
                        self._from_app_update = True
                        self.weighbridge_callback(weight)
                    except Exception as e:
                        print(f"Error in weighbridge_callback: {e}")
                    finally:
                        # Clear the flag
                        if hasattr(self, '_from_app_update'):
                            delattr(self, '_from_app_update')
                        
            except Exception as e:
                print(f"Error in update_weight_display: {e}")
            finally:
                self.processing_callback = False
    
    def update_camera_indices(self, front_index, back_index):
        """Update camera indices
        
        Args:
            front_index: Front camera index
            back_index: Back camera index
        """
        if hasattr(self, 'main_form'):
            # Stop cameras if running
            if hasattr(self.main_form, 'front_camera'):
                self.main_form.front_camera.stop_camera()
                self.main_form.front_camera.camera_index = front_index
            
            if hasattr(self.main_form, 'back_camera'):
                self.main_form.back_camera.stop_camera()
                self.main_form.back_camera.camera_index = back_index
    
    def save_record(self):
        """Save current record to database"""
        # Validate form first
        if not self.main_form.validate_form():
            return
        
        # Get form data
        record_data = self.main_form.get_form_data()
        ticket_no = record_data.get('ticket_no', '')
        
        # Save to database
        if self.data_manager.save_record(record_data):
            # Check if this is a second weighment being completed
            is_second_weighment_complete = (
                record_data.get('second_weight') and record_data.get('second_timestamp') and 
                self.main_form.current_weighment == "second"
            )
            
            # Set appropriate message based on what was saved
            if is_second_weighment_complete:
                # Both weighments complete
                messagebox.showinfo("Success", "Record completed with both weighments!")
                
                # Remove from pending vehicles list
                if hasattr(self, 'pending_vehicles'):
                    self.pending_vehicles.remove_saved_record(ticket_no)
            else:
                # Only first weighment - must explicitly tell user it's added to pending queue
                messagebox.showinfo("Success", "First weighment saved! Vehicle added to pending queue.")
            
            # Always update the summary and pending vehicles list when saving
            self.update_summary()
            self.update_pending_vehicles()
            
            # If second weighment is done, clear form for next entry
            if is_second_weighment_complete:
                self.clear_form()
                # Generate a new ticket number
                self.main_form.generate_next_ticket_number()
                # Switch to summary tab
                self.notebook.select(1)
            else:
                # For first weighment, clear form and prepare for next entry
                self.clear_form()
                # Generate a new ticket
                self.main_form.generate_next_ticket_number()
        else:
            messagebox.showerror("Error", "Failed to save record.")
    
    def update_summary(self):
        """Update the summary view"""
        if hasattr(self, 'summary_panel'):
            self.summary_panel.update_summary()
    
    def update_pending_vehicles(self):
        """Update the pending vehicles panel"""
        try:
            if hasattr(self, 'pending_vehicles') and self.pending_vehicles:
                # Check if the widget still exists before refreshing
                if self.pending_vehicles.tree.winfo_exists():
                    self.pending_vehicles.refresh_pending_list()
        except Exception as e:
            print(f"Error updating pending vehicles: {e}")
    
    def view_records(self):
        """View all records in a separate window"""
        # Switch to the summary tab
        self.notebook.select(1)
        
        # Refresh the summary
        self.update_summary()
    
    def clear_form(self):
        """Clear the main form"""
        if hasattr(self, 'main_form'):
            self.main_form.clear_form()
    
    def logout(self):
        """Restart the entire application on logout for a clean slate"""
        # Reset user info
        self.logged_in_user = None
        self.user_role = None
        self.selected_site = None
        self.selected_incharge = None
        
        # Clean up resources before destroying app
        if hasattr(self, 'main_form'):
            self.main_form.on_closing()
        
        if hasattr(self, 'settings_panel'):
            self.settings_panel.on_closing()
        
        # Store current app details for restart
        import sys
        import os
        python_executable = sys.executable
        script_path = os.path.abspath(sys.argv[0])
        
        # Destroy the root window to close the current instance
        self.root.destroy()
        
        # Restart the application in a new process
        import subprocess
        subprocess.Popen([python_executable, script_path])
        
        # Exit this process
        sys.exit(0)
    
    def on_closing(self):
        """Handle application closing"""
        try:
            # Clean up resources
            if hasattr(self, 'main_form'):
                self.main_form.on_closing()
            
            if hasattr(self, 'settings_panel'):
                self.settings_panel.on_closing()
            
            # Close the application
            self.root.destroy()
        except Exception as e:
            print(f"Error during shutdown: {e}")
            self.root.destroy()

# Main entry point
if __name__ == "__main__":
    # Create root window
    root = tk.Tk()
    
    # Create application instance
    app = TharuniApp(root)
    
    # Start the application
    root.mainloop()