#pyinstaller --onedir --windowed --add-data "data;data" --collect-all=cv2 --collect-all=pandas --collect-all=PIL --hidden-import=serial --hidden-import=google.cloud --hidden-import=psutil --optimize=2 --strip --noupx --name="Swaccha_Andhra_SW" --icon=right.ico advitia_app.py
import tkinter as tk
import os
import datetime
import threading
import logging
from tkinter import ttk, messagebox
from pending_vehicles_panel import PendingVehiclesPanel
import config
from ui_components import HoverButton, create_styles
from camera import CameraView
from main_form import MainForm
from summary_panel import SummaryPanel
from settings_panel import SettingsPanel
from data_management import DataManager  # This now includes auto PDF generation
from reports import export_to_excel, export_to_pdf
from settings_storage import SettingsStorage
from login_dialog import LoginDialog
import pandas._libs.testing

# Set up logging for the entire application
def setup_app_logging():
    """Set up application-wide logging"""
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create log filename with current date
    log_filename = os.path.join(logs_dir, f"app_{datetime.datetime.now().strftime('%Y-%m-%d')}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,  # Changed to INFO to reduce log volume
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    return logging.getLogger('TharuniApp')

class TharuniApp:
    """FIXED: Main application class with enhanced logging and error handling"""
    
    def __init__(self, root):
        """Initialize the application with authentication and logging
        
        Args:
            root: Root Tkinter window
        """
        self.root = root
        self.root.title("Swaccha Andhra Corporation powered by Advitia Labs")
        self.root.geometry("900x580")
        self.root.minsize(900, 580)
        
        # Set up logging first
        self.logger = setup_app_logging()
        self.logger.info("="*60)
        self.logger.info("APPLICATION STARTUP")
        self.logger.info("="*60)
        
        try:
            # Set up initial configuration
            config.setup()
            self.logger.info("Configuration setup completed")
            
            # Initialize data manager with auto PDF generation
            self.data_manager = DataManager()
            self.logger.info("Data manager initialized")
            
            # Initialize settings storage
            self.settings_storage = SettingsStorage()
            self.logger.info("Settings storage initialized")
            
            # IMPORTANT: Verify settings integrity at startup
            if not self.settings_storage.verify_settings_integrity():
                self.logger.warning("Settings integrity check failed - reinitializing settings files")
                self.settings_storage.initialize_files()
            
            # Initialize UI styles
            self.style = create_styles()
            self.logger.info("UI styles initialized")
            
            # Show login dialog before creating UI
            self.logged_in_user = None
            self.user_role = None
            self.selected_site = None
            self.selected_incharge = None
            self.authenticate_user()
            
            # Initialize UI components if login successful
            if self.logged_in_user:
                self.logger.info(f"User logged in: {self.logged_in_user} (Role: {self.user_role})")
                
                # IMPORTANT: Set the data context based on login selections
                self.setup_data_context()
                
                self.create_widgets()
                
                # Start time update
                self.update_datetime()
                
                # Start periodic refresh for pending vehicles
                self.periodic_refresh()
                
                # Add window close handler with settings persistence
                self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
                
                self.logger.info("Application initialization completed successfully")
            else:
                self.logger.info("User authentication failed or canceled - exiting")
                
        except Exception as e:
            self.logger.error(f"Critical error during application initialization: {e}")
            messagebox.showerror("Initialization Error", 
                               f"Failed to initialize application:\n{str(e)}\n\nCheck logs for details.")
            self.root.quit()

    def authenticate_user(self):
        """Show login dialog and authenticate user"""
        try:
            self.logger.info("Starting user authentication")
            login = LoginDialog(self.root, self.settings_storage, show_select=True)
            
            if login.result:
                self.logged_in_user = login.username
                self.user_role = login.role
                self.selected_site = login.site
                self.selected_incharge = login.incharge  # Store the selected incharge
                self.logger.info(f"Authentication successful: {self.logged_in_user}")
            else:
                # Exit application if login failed or canceled
                self.logger.info("Authentication canceled - exiting application")
                self.root.quit()
                
        except Exception as e:
            self.logger.error(f"Error during authentication: {e}")
            messagebox.showerror("Authentication Error", f"Authentication failed: {str(e)}")
            self.root.quit()

    def setup_data_context(self):
        """Set up the data context based on login selections"""
        try:
            self.logger.info("Setting up data context")
            
            # Get the first agency from settings if none selected during login
            sites_data = self.settings_storage.get_sites()
            agencies = sites_data.get('agencies', ['Default Agency'])
            
            # Use the first agency if available, or fallback
            agency_name = agencies[0] if agencies else 'Default Agency'
            
            # Use selected site or default
            site_name = self.selected_site if self.selected_site else 'Guntur'
            
            # Set the data context for dynamic filename
            self.data_manager.set_agency_site_context(agency_name, site_name)
            
            # Store context for reference
            self.current_agency = agency_name
            self.current_site = site_name
            
            self.logger.info(f"Data context initialized: Agency='{agency_name}', Site='{site_name}'")
            self.logger.info(f"Data will be saved to: {self.data_manager.get_current_data_file()}")
            self.logger.info(f"PDFs will be saved to: {self.data_manager.today_pdf_folder}")
            
        except Exception as e:
            self.logger.error(f"Error setting up data context: {e}")
            # Fallback to default context
            self.data_manager.set_agency_site_context('Default Agency', 'Guntur')

    def create_widgets(self):
        """Create all widgets and layout for the application"""
        try:
            self.logger.info("Creating application widgets")
            
            # Create main container frame
            main_container = ttk.Frame(self.root, padding="5", style="TFrame")
            main_container.pack(fill=tk.BOTH, expand=True)
            
            # Title and header section with user and site info plus PDF status
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
            self.logger.info("Summary panel created")
            
            # Create settings panel with user info, weighbridge callback, and data manager reference
            self.settings_panel = SettingsPanel(
                settings_tab, 
                weighbridge_callback=self.update_weight_from_weighbridge,  # This is the key callback
                update_cameras_callback=self.update_camera_indices,
                current_user=self.logged_in_user,
                user_role=self.user_role
            )
            
            # IMPORTANT: Set data manager reference in settings panel for cloud backup
            if hasattr(self.settings_panel, '__dict__'):
                self.settings_panel.app_data_manager = self.data_manager
                self.logger.info("✅ Data manager reference set in settings panel")
            
            # Also store reference in parent widget for widget hierarchy search
            settings_tab.data_manager = self.data_manager
            
            # Handle role-based access to settings tabs - with error handling
            try:
                if self.user_role != 'admin' and hasattr(self.settings_panel, 'settings_notebook'):
                    # Hide user and site management tabs for non-admin users
                    self.settings_panel.settings_notebook.tab(2, state=tk.HIDDEN)  # Users tab
                    self.settings_panel.settings_notebook.tab(3, state=tk.HIDDEN)  # Sites tab
                    self.logger.info("Non-admin user - hid admin-only tabs")
            except (AttributeError, tk.TclError) as e:
                self.logger.error(f"Error setting tab visibility: {e}")
            
            # IMPORTANT: Ensure settings persistence after all widgets are created
            self.root.after(1000, self.ensure_settings_persistence)
            
            self.logger.info("Widget creation completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error creating widgets: {e}")
            raise

    def create_main_panel(self, parent):
        """Create main panel with form and pending vehicles list"""
        try:
            self.logger.info("Creating main panel")
            
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
            self.logger.info("Main form created")

            # Load sites and agencies for dropdowns in the main form
            self.main_form.load_sites_and_agencies(self.settings_storage)

            # Set the site name based on login selection if available
            if self.selected_site:
                self.main_form.set_site(self.selected_site)

            # UPDATED: Properly set agency and site incharge
            # Set the agency based on current context
            if hasattr(self, 'current_agency'):
                self.main_form.set_agency(self.current_agency)

            # Set the site incharge (separate from agency)
            if self.selected_incharge:
                self.main_form.set_site_incharge(self.selected_incharge)
            
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
            self.logger.info("Pending vehicles panel created")
            
            # Configure scroll region after adding content
            scrollable_frame.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            
            self.logger.info("Main panel creation completed")
            
        except Exception as e:
            self.logger.error(f"Error creating main panel: {e}")
            raise

    def save_record(self):
        """FIXED: Save current record to database with enhanced logging and error handling"""
        try:
            self.logger.info("="*50)
            self.logger.info("SAVE RECORD OPERATION STARTED")
            
            # Validate form first
            if not self.main_form.validate_form():
                self.logger.warning("Form validation failed - aborting save")
                return
            
            # Get form data
            record_data = self.main_form.get_form_data()
            ticket_no = record_data.get('ticket_no', '')
            
            self.logger.info(f"Saving record for ticket: {ticket_no}")
            self.logger.info(f"Form data keys: {list(record_data.keys())}")
            
            # Check if this is a complete record (both weighments)
            is_complete_record = self.main_form.is_record_complete()
            self.logger.info(f"Record is complete: {is_complete_record}")
            
            # Save to database (this will now auto-generate PDF for complete records)
            self.logger.info(f"Calling data_manager.save_record for {ticket_no}")
            
            if self.data_manager.save_record(record_data):
                self.logger.info(f"✅ Record {ticket_no} saved successfully")
                
                # FIXED: Only commit (increment) ticket number when BOTH weighments are complete
                if is_complete_record:
                    # Both weighments complete - commit the ticket number (increment counter)
                    commit_success = self.main_form.commit_current_ticket_number()
                    if commit_success:
                        self.logger.info(f"✅ Ticket {ticket_no} completed - counter incremented")
                    else:
                        self.logger.warning(f"⚠️ Warning: Failed to commit ticket number {ticket_no}")
                    
                    # FIXED: Remove from pending vehicles list AFTER successful save
                    self.logger.info(f"Removing {ticket_no} from pending vehicles list")
                    if hasattr(self, 'pending_vehicles'):
                        self.pending_vehicles.remove_saved_record(ticket_no)
                    
                    # Prepare form for new ticket (this will reserve the next ticket number)
                    self.main_form.prepare_for_new_ticket_after_completion()
                    
                    # Switch to summary tab to show completed record
                    self.notebook.select(1)
                    
                    self.logger.info(f"✅ Complete record processing finished for {ticket_no}")
                    
                else:
                    # Only first weighment - DON'T increment ticket counter yet
                    self.logger.info(f"First weighment saved for ticket {ticket_no} - counter NOT incremented")
                    messagebox.showinfo("Success", "First weighment saved! Vehicle added to pending queue.")
                    
                    # Clear form for next entry but DON'T increment ticket counter
                    self.clear_form()
                
                # Always update the summary and pending vehicles list when saving
                self.update_summary()
                self.update_pending_vehicles()
                
                self.logger.info("SAVE RECORD OPERATION COMPLETED SUCCESSFULLY")
                
            else:
                self.logger.error(f"❌ Failed to save record {ticket_no}")
                messagebox.showerror("Error", "Failed to save record. Check logs for details.")
                
        except Exception as e:
            self.logger.error(f"❌ Critical error in save_record: {e}")
            messagebox.showerror("Save Error", f"Critical error saving record:\n{str(e)}\n\nCheck logs for details.")
        finally:
            self.logger.info("="*50)

    def update_pending_vehicles(self):
        """FIXED: Update the pending vehicles panel with error handling"""
        try:
            self.logger.debug("Updating pending vehicles list")
            if hasattr(self, 'pending_vehicles') and self.pending_vehicles:
                # Check if the widget still exists before refreshing
                if hasattr(self.pending_vehicles, 'tree') and self.pending_vehicles.tree.winfo_exists():
                    self.pending_vehicles.refresh_pending_list()
                    self.logger.debug("Pending vehicles list updated successfully")
                else:
                    self.logger.warning("Pending vehicles tree widget no longer exists")
        except Exception as e:
            self.logger.error(f"Error updating pending vehicles: {e}")

    def load_pending_vehicle(self, ticket_no):
        """FIXED: Load a pending vehicle when selected from the pending vehicles panel"""
        try:
            self.logger.info(f"Loading pending vehicle: {ticket_no}")
            
            if hasattr(self, 'main_form'):
                # Switch to main tab
                self.notebook.select(0)
                
                # Load the pending ticket data into the form
                success = self.main_form.load_pending_ticket(ticket_no)
                
                if success:
                    self.logger.info(f"Successfully loaded pending ticket: {ticket_no}")
                    # Inform the user they need to capture weight manually
                    if self.is_weighbridge_connected():
                        messagebox.showinfo("Vehicle Selected", 
                                        f"Ticket {ticket_no} loaded for second weighment.\n"
                                        "Press 'Capture Weight' button when the vehicle is on the weighbridge.")
                    else:
                        messagebox.showinfo("Vehicle Selected", 
                                        f"Ticket {ticket_no} loaded for second weighment.\n"
                                        "Please connect weighbridge and capture weight when ready.")
                else:
                    self.logger.error(f"Failed to load pending ticket: {ticket_no}")
                    messagebox.showerror("Error", f"Could not load ticket {ticket_no}")
            else:
                self.logger.error("Main form not available")
                
        except Exception as e:
            self.logger.error(f"Error loading pending vehicle {ticket_no}: {e}")
            messagebox.showerror("Error", f"Error loading vehicle: {str(e)}")


    def create_header(self, parent):
        """Create compressed header with all info in single line"""
        # Main header frame
        header_frame = ttk.Frame(parent, style="TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 3))
        
        # Single styled header bar with all elements in one line
        title_box = tk.Frame(header_frame, bg=config.COLORS["header_bg"], padx=8, pady=3)
        title_box.pack(fill=tk.X)
        
        # Left side - Title
        title_label = tk.Label(title_box, 
                            text="Swaccha Andhra Corporation - RealTime Tracker", 
                            font=("Segoe UI", 12, "bold"),
                            fg=config.COLORS["white"],
                            bg=config.COLORS["header_bg"])
        title_label.pack(side=tk.LEFT)
        
        # Center - All info in single line with separators
        info_frame = tk.Frame(title_box, bg=config.COLORS["header_bg"])
        info_frame.pack(side=tk.LEFT, expand=True, padx=15)
        
        # Build info text parts
        info_parts = []
        
        # User info
        user_text = f"User: {self.logged_in_user}"
        if self.user_role == 'admin':
            user_text += " (Admin)"
        info_parts.append(user_text)
        
        # Site info
        if self.selected_site:
            info_parts.append(f"Site: {self.selected_site}")
        
        # Incharge info
        if self.selected_incharge:
            info_parts.append(f"Incharge: {self.selected_incharge}")
        
        # Data file info
        if hasattr(self, 'data_manager'):
            current_file = os.path.basename(self.data_manager.get_current_data_file())
            info_parts.append(f"Data: {current_file}")
            
            # PDF folder info
            if hasattr(self.data_manager, 'today_folder_name'):
                info_parts.append(f"PDF: {self.data_manager.today_folder_name}")
        
        # Join all info with separators
        info_text = " • ".join(info_parts)
        
        # Single info label with all details
        info_label = tk.Label(info_frame, 
                            text=info_text,
                            font=("Segoe UI", 8),
                            fg=config.COLORS["primary_light"],
                            bg=config.COLORS["header_bg"],
                            anchor="center")
        info_label.pack(expand=True)
        
        # Right side - Date, Time and Logout
        right_frame = tk.Frame(title_box, bg=config.COLORS["header_bg"])
        right_frame.pack(side=tk.RIGHT)
        
        # Date and time variables
        self.date_var = tk.StringVar()
        self.time_var = tk.StringVar()
        
        # Date and time in single line
        datetime_label = tk.Label(right_frame, 
                                text="",  # Will be updated by update_datetime
                                font=("Segoe UI", 8, "bold"),
                                fg=config.COLORS["white"],
                                bg=config.COLORS["header_bg"])
        datetime_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Store reference for datetime updates
        self.datetime_label = datetime_label
        
        # Logout button (smaller)
        logout_btn = HoverButton(right_frame, 
                            text="Logout", 
                            font=("Segoe UI", 8),
                            bg=config.COLORS["button_alt"],
                            fg=config.COLORS["white"],
                            padx=8, pady=2,
                            command=self.logout)
        logout_btn.pack(side=tk.RIGHT)

    def update_datetime(self):
        """Update date and time display in compressed format"""
        try:
            now = datetime.datetime.now()
            
            # Format: DD-MM-YYYY • HH:MM:SS
            date_str = now.strftime("%d-%m-%Y")
            time_str = now.strftime("%H:%M:%S")
            datetime_str = f"{date_str} • {time_str}"
            
            # Update individual variables if they exist (for compatibility)
            if hasattr(self, 'date_var'):
                self.date_var.set(date_str)
            if hasattr(self, 'time_var'):
                self.time_var.set(time_str)
            
            # Update combined datetime label
            if hasattr(self, 'datetime_label'):
                self.datetime_label.config(text=datetime_str)
            
            # Schedule next update
            if hasattr(self, 'root'):
                self.root.after(1000, self.update_datetime)
                
        except Exception as e:
            print(f"Error updating datetime: {e}")


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



    def periodic_refresh(self):
        """Periodically refresh data displays with error handling"""
        try:
            # Update pending vehicles list if it exists
            self.update_pending_vehicles()
            
            # Check if we need to update the daily PDF folder (date changed)
            if hasattr(self, 'data_manager'):
                self.data_manager.get_daily_pdf_folder()  # This will create new folder if date changed
            
        except Exception as e:
            self.logger.error(f"Error in periodic refresh: {e}")
        finally:
            # Schedule next refresh and store the job ID so we can cancel it if needed
            self._refresh_job = self.root.after(60000, self.periodic_refresh)  # Refresh every minute

    def update_weight_from_weighbridge(self, weight):
        """Update weight from weighbridge with error handling"""
        try:
            # Guard against recursive calls
            if hasattr(self, '_processing_weight_update') and self._processing_weight_update:
                return
            
            # Set processing flag
            self._processing_weight_update = True
            
            # Make the weight available to the main form
            if hasattr(self, 'settings_panel'):
                self.settings_panel.current_weight_var.set(f"{weight} kg")
                
            # Only update UI, don't perform automatic actions
            if self.notebook.index("current") == 0 and hasattr(self, 'main_form'):
                # Update the weight display
                if hasattr(self.main_form, 'current_weight_var'):
                    self.main_form.current_weight_var.set(f"{weight:.2f} kg")
                    
        except Exception as e:
            self.logger.error(f"Error updating weight from weighbridge: {e}")
        finally:
            # Clear processing flag
            self._processing_weight_update = False

    def is_weighbridge_connected(self):
        """Check if weighbridge is connected"""
        try:
            if hasattr(self, 'settings_panel') and hasattr(self.settings_panel, 'wb_status_var'):
                return self.settings_panel.wb_status_var.get() == "Status: Connected"
            return False
        except Exception as e:
            self.logger.error(f"Error checking weighbridge connection: {e}")
            return False

    def ensure_settings_persistence(self):
        """Ensure settings are properly loaded and persisted"""
        try:
            self.logger.info("Ensuring settings persistence...")
            
            # Verify settings integrity
            if not self.settings_storage.verify_settings_integrity():
                self.logger.warning("Settings integrity check failed - reinitializing")
                self.settings_storage.initialize_files()
            
            # Load and apply weighbridge settings if available
            wb_settings = self.settings_storage.get_weighbridge_settings()
            if wb_settings and wb_settings.get("com_port"):
                self.logger.info(f"Found saved weighbridge settings: {wb_settings}")
                
                # Try to auto-connect if settings are complete
                if hasattr(self, 'settings_panel'):
                    self.root.after(2000, self.settings_panel.auto_connect_weighbridge)
            
            self.logger.info("Settings persistence check completed")
            
        except Exception as e:
            self.logger.error(f"Error ensuring settings persistence: {e}")

    def update_camera_indices(self, settings):
        """Update camera settings with error handling"""
        try:
            self.logger.info(f"Updating camera settings: {settings}")
            
            if hasattr(self, 'main_form'):
                # Stop cameras if running
                if hasattr(self.main_form, 'front_camera'):
                    self.main_form.front_camera.stop_camera()
                    
                if hasattr(self.main_form, 'back_camera'):
                    self.main_form.back_camera.stop_camera()
                
                # Update camera settings
                if hasattr(self.main_form, 'update_camera_settings'):
                    self.main_form.update_camera_settings(settings)
            
            # Save settings to ensure persistence
            if hasattr(self, 'settings_storage'):
                self.settings_storage.save_camera_settings(settings)
                self.logger.info("Camera settings saved for persistence")
                
        except Exception as e:
            self.logger.error(f"Error updating camera settings: {e}")

    def update_summary(self):
        """Update the summary view with error handling"""
        try:
            if hasattr(self, 'summary_panel'):
                self.summary_panel.update_summary()
        except Exception as e:
            self.logger.error(f"Error updating summary: {e}")

    def view_records(self):
        """View all records in a separate window"""
        try:
            # Switch to the summary tab
            self.notebook.select(1)
            
            # Refresh the summary
            self.update_summary()
        except Exception as e:
            self.logger.error(f"Error viewing records: {e}")

    def clear_form(self):
        """Clear the main form with error handling"""
        try:
            if hasattr(self, 'main_form'):
                self.main_form.clear_form()
        except Exception as e:
            self.logger.error(f"Error clearing form: {e}")

    def on_closing(self):
        """Handle application closing with enhanced logging"""
        try:
            self.logger.info("Application closing - saving settings...")
            
            # Save settings through settings panel
            if hasattr(self, 'settings_panel'):
                self.settings_panel.on_closing()
            
            # Clean up resources
            if hasattr(self, 'main_form'):
                self.main_form.on_closing()
            
            self.logger.info("="*60)
            self.logger.info("APPLICATION SHUTDOWN COMPLETED")
            self.logger.info("="*60)
            
            # Close the application
            self.root.destroy()
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            self.root.destroy()

# Main entry point
if __name__ == "__main__":
    # Create root window
    root = tk.Tk()
    
    try:
        # Create application instance
        app = TharuniApp(root)
        
        # Start the application
        root.mainloop()
    except Exception as e:
        # Log any critical startup errors
        print(f"Critical application error: {e}")
        import traceback
        traceback.print_exc()
        
        # Show error dialog
        messagebox.showerror("Critical Error", 
                           f"Application failed to start:\n{str(e)}\n\nCheck logs for details.")
    finally:
        try:
            root.destroy()
        except:
            pass