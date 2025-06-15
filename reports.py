import os
import datetime
import csv
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import config
import tkcalendar


# Try to import optional dependencies
try:
    from tkcalendar import DateEntry
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False
    print("tkcalendar not available - using basic date entry")

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import cv2

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ReportLab not available - PDF generation will be limited")



class ReportGenerator:
    """Enhanced report generator with selection and filtering capabilities"""
    
    def __init__(self, parent, data_manager=None):
        """Initialize the report generator
        
        Args:
            parent: Parent widget
            data_manager: Data manager instance
        """
        self.parent = parent
        self.data_manager = data_manager
        self.selected_records = []
        self.address_config = self.load_address_config()
        self.all_records = []
        
        # Ensure reports folder exists
        self.reports_folder = config.REPORTS_FOLDER
        os.makedirs(self.reports_folder, exist_ok=True)
        
    def load_address_config(self):
        """Load address configuration from JSON file"""
        try:
            config_file = os.path.join(config.DATA_FOLDER, 'address_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return json.load(f)
            else:
                # Create default config
                default_config = {
                    "agencies": {
                        "Default Agency": {
                            "name": "Default Agency",
                            "address": "123 Main Street\nCity, State - 123456",
                            "contact": "+91-1234567890",
                            "email": "info@agency.com"
                        },
                        "Tharuni": {
                            "name": "Tharuni Environmental Services",
                            "address": "Environmental Complex\nGuntur, Andhra Pradesh - 522001",
                            "contact": "+91-9876543210",
                            "email": "info@tharuni.com"
                        }
                    },
                    "sites": {
                        "Guntur": {
                            "name": "Guntur Processing Site",
                            "address": "Industrial Area, Guntur\nAndhra Pradesh - 522001",
                            "contact": "+91-9876543210"
                        },
                        "Addanki": {
                            "name": "Addanki Collection Center",
                            "address": "Main Road, Addanki\nAndhra Pradesh - 523201",
                            "contact": "+91-9876543211"
                        }
                    }
                }
                
                # Save default config
                os.makedirs(config.DATA_FOLDER, exist_ok=True)
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=4)
                
                return default_config
        except Exception as e:
            print(f"Error loading address config: {e}")
            return {"agencies": {}, "sites": {}}
    
    def show_report_dialog(self):
        """Show the enhanced report selection dialog"""
        # Create report dialog window
        self.report_window = tk.Toplevel(self.parent)
        self.report_window.title("Generate Reports - Select Records")
        self.report_window.geometry("1000x750")
        self.report_window.resizable(True, True)
        
        # Configure grid weights
        self.report_window.columnconfigure(0, weight=1)
        self.report_window.rowconfigure(1, weight=1)
        
        # Create main frames
        self.create_filter_frame()
        self.create_selection_frame()
        self.create_action_frame()
        
        # Load initial data
        self.refresh_records()
    
    def create_filter_frame(self):
        """Create the filter controls frame"""
        filter_frame = ttk.LabelFrame(self.report_window, text="Filters & Search", padding=10)
        filter_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        filter_frame.columnconfigure(1, weight=1)
        filter_frame.columnconfigure(3, weight=1)
        
        # Date range filter
        ttk.Label(filter_frame, text="From Date:").grid(row=0, column=0, sticky="w", padx=5)
        
        if CALENDAR_AVAILABLE:
            self.from_date = DateEntry(filter_frame, width=12, background='darkblue',
                                      foreground='white', borderwidth=2,
                                      date_pattern='dd-mm-yyyy')
        else:
            self.from_date = ttk.Entry(filter_frame, width=15)
            # Set placeholder
            self.from_date.insert(0, "DD-MM-YYYY")
        
        self.from_date.grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(filter_frame, text="To Date:").grid(row=0, column=2, sticky="w", padx=5)
        
        if CALENDAR_AVAILABLE:
            self.to_date = DateEntry(filter_frame, width=12, background='darkblue',
                                    foreground='white', borderwidth=2,
                                    date_pattern='dd-mm-yyyy')
            # Set default date range (last 30 days)
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=30)
            self.from_date.set_date(start_date.date())
            self.to_date.set_date(end_date.date())
        else:
            self.to_date = ttk.Entry(filter_frame, width=15)
            self.to_date.insert(0, "DD-MM-YYYY")
        
        self.to_date.grid(row=0, column=3, sticky="w", padx=5)
        
        # Vehicle Number filter
        ttk.Label(filter_frame, text="Vehicle No:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.vehicle_var = tk.StringVar()
        vehicle_entry = ttk.Entry(filter_frame, textvariable=self.vehicle_var)
        vehicle_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # Transfer Party filter
        ttk.Label(filter_frame, text="Transfer Party:").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.transfer_party_var = tk.StringVar()
        self.transfer_party_combo = ttk.Combobox(filter_frame, textvariable=self.transfer_party_var)
        self.transfer_party_combo.grid(row=1, column=3, sticky="ew", padx=5, pady=5)
        
        # Material filter
        ttk.Label(filter_frame, text="Material:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.material_var = tk.StringVar()
        self.material_combo = ttk.Combobox(filter_frame, textvariable=self.material_var)
        self.material_combo.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        # Record status filter
        ttk.Label(filter_frame, text="Status:").grid(row=2, column=2, sticky="w", padx=5, pady=5)
        self.status_var = tk.StringVar(value="All")
        status_combo = ttk.Combobox(filter_frame, textvariable=self.status_var, 
                                   values=["All", "Complete", "Incomplete"], state="readonly")
        status_combo.grid(row=2, column=3, sticky="ew", padx=5, pady=5)
        
        # Buttons frame
        button_frame = ttk.Frame(filter_frame)
        button_frame.grid(row=3, column=0, columnspan=4, pady=10)
        
        # Apply filter button
        filter_btn = ttk.Button(button_frame, text="Apply Filters", command=self.apply_filters)
        filter_btn.pack(side=tk.LEFT, padx=5)
        
        # Clear filters button
        clear_btn = ttk.Button(button_frame, text="Clear Filters", command=self.clear_filters)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Refresh button
        refresh_btn = ttk.Button(button_frame, text="Refresh Data", command=self.refresh_records)
        refresh_btn.pack(side=tk.LEFT, padx=5)
    
    def create_selection_frame(self):
        """Create the record selection frame with checkboxes"""
        selection_frame = ttk.LabelFrame(self.report_window, text="Select Records for Export", padding=5)
        selection_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        selection_frame.columnconfigure(0, weight=1)
        selection_frame.rowconfigure(1, weight=1)
        
        # Selection controls
        control_frame = ttk.Frame(selection_frame)
        control_frame.grid(row=0, column=0, sticky="ew", pady=5)
        
        # Select all/none buttons
        select_all_btn = ttk.Button(control_frame, text="Select All", command=self.select_all_records)
        select_all_btn.pack(side=tk.LEFT, padx=5)
        
        select_none_btn = ttk.Button(control_frame, text="Select None", command=self.select_no_records)
        select_none_btn.pack(side=tk.LEFT, padx=5)
        
        # Records count label
        self.records_count_var = tk.StringVar(value="Records: 0 | Selected: 0")
        count_label = ttk.Label(control_frame, textvariable=self.records_count_var)
        count_label.pack(side=tk.RIGHT, padx=5)
        
        # Create treeview for record selection
        tree_frame = ttk.Frame(selection_frame)
        tree_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Define columns
        columns = ("select", "ticket", "date", "vehicle", "agency", "material", "first_weight", "second_weight", "status")
        self.records_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # Define headings
        self.records_tree.heading("select", text="☐")
        self.records_tree.heading("ticket", text="Ticket No")
        self.records_tree.heading("date", text="Date")
        self.records_tree.heading("vehicle", text="Vehicle No")
        self.records_tree.heading("agency", text="Agency")
        self.records_tree.heading("material", text="Material")
        self.records_tree.heading("first_weight", text="First Weight")
        self.records_tree.heading("second_weight", text="Second Weight")
        self.records_tree.heading("status", text="Status")
        
        # Define column widths
        self.records_tree.column("select", width=30, minwidth=30)
        self.records_tree.column("ticket", width=80, minwidth=80)
        self.records_tree.column("date", width=80, minwidth=80)
        self.records_tree.column("vehicle", width=100, minwidth=100)
        self.records_tree.column("agency", width=120, minwidth=120)
        self.records_tree.column("material", width=80, minwidth=80)
        self.records_tree.column("first_weight", width=80, minwidth=80)
        self.records_tree.column("second_weight", width=80, minwidth=80)
        self.records_tree.column("status", width=80, minwidth=80)
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.records_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.records_tree.xview)
        self.records_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.records_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Bind double-click to toggle selection
        self.records_tree.bind("<Double-1>", self.toggle_record_selection)
        self.records_tree.bind("<Button-1>", self.on_tree_click)
    
    def create_action_frame(self):
        """Create the action buttons frame"""
        action_frame = ttk.LabelFrame(self.report_window, text="Export Options", padding=10)
        action_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        # Export buttons
        excel_btn = ttk.Button(action_frame, text="📊 Export to Excel", 
                              command=self.export_selected_to_excel)
        excel_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        pdf_btn = ttk.Button(action_frame, text="📄 Export to PDF", 
                            command=self.export_selected_to_pdf)
        pdf_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Address config button
        config_btn = ttk.Button(action_frame, text="⚙️ Configure Address", 
                               command=self.show_address_config)
        config_btn.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Close button
        close_btn = ttk.Button(action_frame, text="Close", command=self.report_window.destroy)
        close_btn.pack(side=tk.RIGHT, padx=10, pady=5)
    
    def refresh_records(self):
        """Refresh the records from data manager"""
        if not self.data_manager:
            return
        
        # Get all records
        self.all_records = self.data_manager.get_all_records()
        
        # Populate filter dropdowns
        self.populate_filter_dropdowns()
        
        # Apply current filters
        self.apply_filters()
    
    def populate_filter_dropdowns(self):
        """Populate the filter dropdown options"""
        if not self.all_records:
            return
        
        # Get unique values for dropdowns
        transfer_parties = set()
        materials = set()
        
        for record in self.all_records:
            transfer_party = record.get('transfer_party_name', '').strip()
            material = record.get('material', '').strip()
            
            if transfer_party:
                transfer_parties.add(transfer_party)
            if material:
                materials.add(material)
        
        # Update combobox values
        self.transfer_party_combo['values'] = [''] + sorted(list(transfer_parties))
        self.material_combo['values'] = [''] + sorted(list(materials))
    
    def apply_filters(self):
        """Apply the current filters to display records"""
        if not self.all_records:
            return
        
        filtered_records = []
        
        # Get filter values
        from_date_str = ""
        to_date_str = ""
        
        if CALENDAR_AVAILABLE:
            try:
                from_date_str = self.from_date.get_date().strftime("%d-%m-%Y")
                to_date_str = self.to_date.get_date().strftime("%d-%m-%Y")
            except:
                pass
        else:
            from_date_str = self.from_date.get().strip()
            to_date_str = self.to_date.get().strip()
        
        vehicle_filter = self.vehicle_var.get().strip().lower()
        transfer_party_filter = self.transfer_party_var.get().strip().lower()
        material_filter = self.material_var.get().strip().lower()
        status_filter = self.status_var.get()
        
        for record in self.all_records:
            # Date filter
            if from_date_str and to_date_str:
                try:
                    record_date = datetime.datetime.strptime(record.get('date', ''), "%d-%m-%Y")
                    from_date = datetime.datetime.strptime(from_date_str, "%d-%m-%Y")
                    to_date = datetime.datetime.strptime(to_date_str, "%d-%m-%Y")
                    
                    if not (from_date <= record_date <= to_date):
                        continue
                except:
                    pass
            
            # Vehicle filter
            if vehicle_filter:
                vehicle_no = record.get('vehicle_no', '').lower()
                if vehicle_filter not in vehicle_no:
                    continue
            
            # Transfer party filter
            if transfer_party_filter:
                transfer_party = record.get('transfer_party_name', '').lower()
                if transfer_party_filter not in transfer_party:
                    continue
            
            # Material filter
            if material_filter:
                material = record.get('material', '').lower()
                if material_filter not in material:
                    continue
            
            # Status filter
            if status_filter != "All":
                first_weight = record.get('first_weight', '').strip()
                second_weight = record.get('second_weight', '').strip()
                is_complete = bool(first_weight and second_weight)
                
                if status_filter == "Complete" and not is_complete:
                    continue
                elif status_filter == "Incomplete" and is_complete:
                    continue
            
            filtered_records.append(record)
        
        # Update the treeview
        self.update_records_display(filtered_records)
    
    def update_records_display(self, records):
        """Update the treeview with filtered records"""
        # Clear existing items
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)
        
        # Add records
        for record in records:
            ticket_no = record.get('ticket_no', '')
            date = record.get('date', '')
            vehicle_no = record.get('vehicle_no', '')
            agency = record.get('agency_name', '')
            material = record.get('material', '')
            first_weight = record.get('first_weight', '')
            second_weight = record.get('second_weight', '')
            
            # Determine status
            status = "Complete" if (first_weight and second_weight) else "Incomplete"
            
            self.records_tree.insert("", "end", values=(
                "☐", ticket_no, date, vehicle_no, agency, material, 
                first_weight, second_weight, status
            ), tags=(ticket_no,))
        
        # Update count
        self.update_selection_count()
    
    def clear_filters(self):
        """Clear all filters"""
        if CALENDAR_AVAILABLE:
            # Reset date range
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=30)
            self.from_date.set_date(start_date.date())
            self.to_date.set_date(end_date.date())
        else:
            self.from_date.delete(0, tk.END)
            self.to_date.delete(0, tk.END)
            self.from_date.insert(0, "DD-MM-YYYY")
            self.to_date.insert(0, "DD-MM-YYYY")
        
        self.vehicle_var.set("")
        self.transfer_party_var.set("")
        self.material_var.set("")
        self.status_var.set("All")
        
        # Refresh display
        self.apply_filters()
    
    def on_tree_click(self, event):
        """Handle tree click events"""
        item = self.records_tree.identify('item', event.x, event.y)
        column = self.records_tree.identify('column', event.x, event.y)
        
        if item and column == '#1':  # Click on select column
            self.toggle_record_selection(event)
    
    def toggle_record_selection(self, event):
        """Toggle selection of a record"""
        item = self.records_tree.selection()[0] if self.records_tree.selection() else None
        if not item:
            return
        
        values = list(self.records_tree.item(item, 'values'))
        ticket_no = values[1]  # Ticket number is at index 1
        
        if values[0] == "☐":  # Not selected
            values[0] = "☑"
            self.selected_records.append(ticket_no)
        else:  # Selected
            values[0] = "☐"
            if ticket_no in self.selected_records:
                self.selected_records.remove(ticket_no)
        
        self.records_tree.item(item, values=values)
        self.update_selection_count()
    
    def select_all_records(self):
        """Select all visible records"""
        self.selected_records = []
        for item in self.records_tree.get_children():
            values = list(self.records_tree.item(item, 'values'))
            values[0] = "☑"
            ticket_no = values[1]
            self.selected_records.append(ticket_no)
            self.records_tree.item(item, values=values)
        
        self.update_selection_count()
    
    def select_no_records(self):
        """Deselect all records"""
        self.selected_records = []
        for item in self.records_tree.get_children():
            values = list(self.records_tree.item(item, 'values'))
            values[0] = "☐"
            self.records_tree.item(item, values=values)
        
        self.update_selection_count()
    
    def update_selection_count(self):
        """Update the selection count display"""
        total_records = len(self.records_tree.get_children())
        selected_count = len(self.selected_records)
        self.records_count_var.set(f"Records: {total_records} | Selected: {selected_count}")
    
    def get_selected_record_data(self):
        """Get the full data for selected records"""
        if not self.selected_records:
            return []
        
        selected_data = []
        for record in self.all_records:
            if record.get('ticket_no', '') in self.selected_records:
                selected_data.append(record)
        
        return selected_data
    
    def export_selected_to_excel(self):
        """Export selected records to Excel with summary format"""
        selected_data = self.get_selected_record_data()
        
        if not selected_data:
            messagebox.showwarning("No Selection", "Please select at least one record to export.")
            return
        
        try:
            # Generate filename based on applied filters
            filename = self.generate_filtered_filename(selected_data, "xlsx")
            
            # Save to reports folder
            save_path = os.path.join(self.reports_folder, filename)
            
            # Calculate summary data
            total_trips = len(selected_data)
            total_net_weight = 0
            date_range = self.get_date_range_info(selected_data)
            applied_filters = self.get_applied_filters_info()
            
            for record in selected_data:
                try:
                    net_weight = float(record.get('net_weight', 0) or 0)
                    total_net_weight += net_weight
                except (ValueError, TypeError):
                    pass
            
            # Create DataFrame with summary information
            df = pd.DataFrame(selected_data)
            
            # Export to Excel with enhanced formatting and summary
            with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
                # Create summary sheet
                summary_data = {
                    'Metric': ['Total Number of Trips', 'Total Net Weight (kg)', 'Date Range', 'Applied Filters', 'Export Date'],
                    'Value': [total_trips, f"{total_net_weight:.2f}", date_range, applied_filters, datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Add detailed records
                df.to_excel(writer, sheet_name='Detailed Records', index=False)
                
                # Get the workbook and format summary sheet
                workbook = writer.book
                summary_ws = writer.sheets['Summary']
                
                # Add title to summary sheet
                summary_ws.insert_rows(1, 3)
                summary_ws['A1'] = "SWACCHA ANDHRA CORPORATION - FILTERED REPORT SUMMARY"
                summary_ws['A2'] = f"Generated on: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
                summary_ws['A3'] = ""  # Empty row for spacing
            
            messagebox.showinfo("Export Successful", 
                              f"Excel summary report saved successfully!\n\n"
                              f"File: {filename}\n"
                              f"Records: {total_trips}\n"
                              f"Total Weight: {total_net_weight:.2f} kg\n"
                              f"Location: {self.reports_folder}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export to Excel:\n{str(e)}")
    
    def export_selected_to_pdf(self):
        """FIXED: Always export to PDF summary format regardless of filters applied"""
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("PDF Export Error", 
                            "ReportLab library is not installed.\n"
                            "Please install it using: pip install reportlab")
            return
        
        selected_data = self.get_selected_record_data()
        
        if not selected_data:
            messagebox.showwarning("No Selection", "Please select at least one record to export.")
            return
        
        try:
            # ALWAYS use summary format for advanced reports (FIXED LOGIC)
            if len(selected_data) == 1:
                # Single record - use individual format
                filename = self.generate_filename(selected_data, "pdf")
                save_path = os.path.join(self.reports_folder, filename)
                
                self.create_pdf_report(selected_data, save_path)
                messagebox.showinfo("Export Successful", 
                                f"Individual PDF report saved successfully!\n\n"
                                f"File: {filename}\n"
                                f"Location: {self.reports_folder}")
            else:
                # Multiple records - ALWAYS use summary format
                filename = self.generate_filtered_filename(selected_data, "pdf")
                save_path = os.path.join(self.reports_folder, filename)
                
                print(f"📄 EXPORT DEBUG: Creating summary PDF for {len(selected_data)} records with applied filters")
                self.create_summary_pdf_report(selected_data, save_path)
                
                messagebox.showinfo("Export Successful", 
                                f"Summary PDF Report saved successfully!\n\n"
                                f"File: {filename}\n"
                                f"Records: {len(selected_data)}\n"
                                f"Location: {self.reports_folder}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export to PDF:\n{str(e)}")

    def get_applied_filters_info(self):
        """Get information about currently applied filters"""
        try:
            filters = []
            
            # Date range
            if CALENDAR_AVAILABLE:
                try:
                    from_date_str = self.from_date.get_date().strftime("%d-%m-%Y")
                    to_date_str = self.to_date.get_date().strftime("%d-%m-%Y")
                    if from_date_str and to_date_str:
                        if from_date_str == to_date_str:
                            filters.append(f"Date: {from_date_str}")
                        else:
                            filters.append(f"Date Range: {from_date_str} to {to_date_str}")
                except:
                    pass
            
            # Vehicle filter
            vehicle_filter = self.vehicle_var.get().strip()
            if vehicle_filter:
                filters.append(f"Vehicle: {vehicle_filter}")
            
            # Transfer party filter
            transfer_party_filter = self.transfer_party_var.get().strip()
            if transfer_party_filter:
                filters.append(f"Transfer Party: {transfer_party_filter}")
            
            # Material filter
            material_filter = self.material_var.get().strip()
            if material_filter:
                filters.append(f"Material: {material_filter}")
            
            # Status filter
            status_filter = self.status_var.get()
            if status_filter and status_filter != "All":
                filters.append(f"Status: {status_filter}")
            
            return " | ".join(filters) if filters else "No specific filters applied"
            
        except Exception as e:
            print(f"Error getting applied filters info: {e}")
            return "Filter information unavailable"

    def generate_filtered_filename(self, selected_data, extension):
        """Generate filename based on applied filters and selected data"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Get common site/agency if all records are from same site/agency
            sites = set(r.get('site_name', '').replace(' ', '_').replace('/', '_') for r in selected_data)
            agencies = set(r.get('agency_name', '').replace(' ', '_').replace('/', '_') for r in selected_data)
            
            site_part = list(sites)[0] if len(sites) == 1 else "Multiple_Sites"
            agency_part = list(agencies)[0] if len(agencies) == 1 else "Multiple_Agencies"
            
            # Clean up the parts
            site_part = site_part.replace('/', '_').replace(' ', '_')[:15]  # Limit length
            agency_part = agency_part.replace('/', '_').replace(' ', '_')[:15]  # Limit length
            
            # Check what filters are applied
            filter_parts = []
            
            # Date range
            if CALENDAR_AVAILABLE:
                try:
                    from_date_str = self.from_date.get_date().strftime("%d-%m-%Y")
                    to_date_str = self.to_date.get_date().strftime("%d-%m-%Y")
                    if from_date_str and to_date_str:
                        if from_date_str == to_date_str:
                            filter_parts.append(f"Date_{from_date_str.replace('-', '')}")
                        else:
                            filter_parts.append(f"DateRange_{from_date_str.replace('-', '')}_to_{to_date_str.replace('-', '')}")
                except:
                    pass
            
            # Vehicle filter
            vehicle_filter = self.vehicle_var.get().strip()
            if vehicle_filter:
                clean_vehicle = vehicle_filter.replace(' ', '_').replace('/', '_')[:10]
                filter_parts.append(f"Vehicle_{clean_vehicle}")
            
            # Transfer party filter
            transfer_party_filter = self.transfer_party_var.get().strip()
            if transfer_party_filter:
                clean_party = transfer_party_filter.replace(' ', '_').replace('/', '_')[:10]
                filter_parts.append(f"Party_{clean_party}")
            
            # Material filter
            material_filter = self.material_var.get().strip()
            if material_filter:
                clean_material = material_filter.replace(' ', '_').replace('/', '_')[:10]
                filter_parts.append(f"Material_{clean_material}")
            
            # Status filter
            status_filter = self.status_var.get()
            if status_filter and status_filter != "All":
                filter_parts.append(f"Status_{status_filter}")
            
            # Build filename
            if filter_parts:
                filter_string = "_".join(filter_parts[:2])  # Limit to first 2 filters to keep filename reasonable
                if len(filter_parts) > 2:
                    filter_string += "_Plus"
                return f"{agency_part}_{site_part}_Filtered_{filter_string}_{len(selected_data)}records.{extension}"
            else:
                return f"{agency_part}_{site_part}_Summary_{len(selected_data)}records_{timestamp}.{extension}"
                
        except Exception as e:
            print(f"Error generating filtered filename: {e}")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"Filtered_Report_{len(selected_data)}records_{timestamp}.{extension}"

    def create_summary_pdf_report(self, records_data, save_path):
        """Create a summary PDF report for filtered records (always used for multiple records)"""
        if not REPORTLAB_AVAILABLE:
            return False
            
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Create document with optimized margins
            doc = SimpleDocTemplate(save_path, pagesize=A4,
                                    rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            
            styles = getSampleStyleSheet()
            elements = []

            # Create styles
            header_style = ParagraphStyle(
                name='HeaderStyle',
                fontSize=16,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                textColor=colors.black,
                spaceAfter=8,
                spaceBefore=4
            )
            
            subheader_style = ParagraphStyle(
                name='SubHeaderStyle',
                fontSize=10,
                alignment=TA_CENTER,
                fontName='Helvetica',
                textColor=colors.black,
                spaceAfter=6
            )
            
            summary_header_style = ParagraphStyle(
                name='SummaryHeaderStyle',
                fontSize=12,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                textColor=colors.darkblue,
                spaceAfter=8,
                spaceBefore=12
            )
            
            summary_style = ParagraphStyle(
                name='SummaryStyle',
                fontSize=10,
                alignment=TA_CENTER,
                fontName='Helvetica',
                textColor=colors.black,
                spaceAfter=4
            )
            
            attribution_style = ParagraphStyle(
                name='AttributionStyle',
                fontSize=8,
                alignment=TA_CENTER,
                fontName='Helvetica',
                textColor=colors.grey,
                spaceAfter=8,
                spaceBefore=8
            )

            # Calculate summary data
            total_trips = len(records_data)
            total_net_weight = 0
            date_range = self.get_date_range_info(records_data)
            applied_filters = self.get_applied_filters_info()
            
            for record in records_data:
                try:
                    net_weight = float(record.get('net_weight', 0) or 0)
                    total_net_weight += net_weight
                except (ValueError, TypeError):
                    pass

            # Get agency and site information
            first_record = records_data[0] if records_data else {}
            agency_name = first_record.get('agency_name', 'Unknown Agency')
            site_name = first_record.get('site_name', 'Unknown Site')
            
            agency_info = self.address_config.get('agencies', {}).get(agency_name, {})
            site_info = self.address_config.get('sites', {}).get(site_name, {})
            
            # Add title with agency info
            elements.append(Paragraph(agency_info.get('name', agency_name), header_style))
            
            # Add agency address if available
            if agency_info.get('address'):
                agency_address = agency_info.get('address', '').replace('\n', '<br/>')
                elements.append(Paragraph(agency_address, subheader_style))
            
            # Contact information
            contact_info = []
            if agency_info.get('contact'):
                contact_info.append(f"Phone: {agency_info.get('contact')}")
            if agency_info.get('email'):
                contact_info.append(f"Email: {agency_info.get('email')}")
            if site_info.get('contact') and site_info.get('contact') != agency_info.get('contact'):
                contact_info.append(f"Site Phone: {site_info.get('contact')}")
            
            if contact_info:
                elements.append(Paragraph(" | ".join(contact_info), subheader_style))
            
            # Header info
            elements.append(Spacer(1, 8))
            elements.append(Paragraph(f"Export Date: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}", subheader_style))
            elements.append(Paragraph(f"Applied Filters: {applied_filters}", subheader_style))
            
            # SUMMARY section
            elements.append(Paragraph("FILTERED RECORDS SUMMARY", summary_header_style))
            elements.append(Paragraph(f"Total Number of Trips: {total_trips}", summary_style))
            elements.append(Paragraph(f"Total Net Weight: {total_net_weight:.2f} kg", summary_style))
            elements.append(Paragraph(f"Date Range: {date_range}", summary_style))
            
            # Attribution line
            timestamp = datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')
            attribution_text = f"Report generated by Advitia Labs at {timestamp}"
            elements.append(Paragraph("─" * 40, attribution_style))
            elements.append(Paragraph(attribution_text, attribution_style))
            
            elements.append(Spacer(1, 12))
            
            # Detailed records section
            elements.append(Paragraph("DETAILED RECORDS", summary_header_style))
            
            # Create table data for all records
            table_data = [['S.No', 'Date', 'Ticket', 'Vehicle', 'Agency', 'Material', 'Net Wt (kg)']]
            
            for i, record in enumerate(records_data, 1):
                # Use shorter agency name if too long
                agency_display = record.get('agency_name', 'N/A')
                if len(agency_display) > 15:
                    agency_display = agency_display[:12] + "..."
                    
                table_data.append([
                    str(i),
                    record.get('date', 'N/A'),
                    record.get('ticket_no', 'N/A'),
                    record.get('vehicle_no', 'N/A'),
                    agency_display,
                    record.get('material_type', record.get('material', 'N/A')),
                    f"{float(record.get('net_weight', 0) or 0):.1f}"
                ])
            
            # Create table
            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(table)
            
            # Build PDF
            doc.build(elements)
            
            print(f"📄 PDF EXPORT: Successfully created summary PDF with {total_trips} records")
            print(f"   - Total Net Weight: {total_net_weight:.2f} kg")
            print(f"   - Applied Filters: {applied_filters}")
            print(f"   - Date Range: {date_range}")
            
            return True
            
        except Exception as e:
            print(f"Error creating summary PDF report: {e}")
            return False

    def get_date_range_info(self, records_data):
        """Get human-readable date range from records"""
        try:
            if not records_data:
                return "Unknown"
                
            dates = []
            for record in records_data:
                date_str = record.get('date', '')
                if date_str:
                    try:
                        date_obj = datetime.datetime.strptime(date_str, "%d-%m-%Y")
                        dates.append(date_obj)
                    except:
                        pass
            
            if not dates:
                return "Unknown"
                
            min_date = min(dates)
            max_date = max(dates)
            
            if min_date.date() == max_date.date():
                return min_date.strftime("%d-%m-%Y")
            else:
                return f"{min_date.strftime('%d-%m-%Y')} to {max_date.strftime('%d-%m-%Y')}"
                
        except Exception as e:
            print(f"Error getting date range info: {e}")
            return "Unknown"

    def generate_filename(self, selected_data, extension):
        """Generate filename based on Agency_Site_Ticket format (for single records)"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if len(selected_data) == 1:
                # Single record: Agency_Site_Ticket.extension
                record = selected_data[0]
                ticket_no = record.get('ticket_no', 'Unknown').replace('/', '_')
                site_name = record.get('site_name', 'Unknown').replace(' ', '_').replace('/', '_')
                agency_name = record.get('agency_name', 'Unknown').replace(' ', '_').replace('/', '_')
                return f"{agency_name}_{site_name}_{ticket_no}.{extension}"
            else:
                # This shouldn't be used for multiple records anymore
                return f"Report_{len(selected_data)}records_{timestamp}.{extension}"
                
        except Exception as e:
            print(f"Error generating filename: {e}")
            # Fallback filename
            return f"Report_{len(selected_data)}records_{timestamp}.{extension}"
    
    def create_pdf_report(self, records_data, save_path):
        """Create PDF report with 4-image grid for complete records (used only for single records)"""
        doc = SimpleDocTemplate(save_path, pagesize=A4,
                                rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        
        styles = getSampleStyleSheet()
        elements = []

        # Ink-friendly styles with increased font sizes
        header_style = ParagraphStyle(
            name='HeaderStyle',
            fontSize=18,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            spaceAfter=6,
            spaceBefore=6
        )
        
        subheader_style = ParagraphStyle(
            name='SubHeaderStyle',
            fontSize=12,
            alignment=TA_CENTER,
            fontName='Helvetica',
            textColor=colors.black,
            spaceAfter=12
        )
        
        section_header_style = ParagraphStyle(
            name='SectionHeader',
            fontSize=13,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            spaceAfter=6,
            spaceBefore=6
        )

        label_style = ParagraphStyle(
            name='LabelStyle',
            fontSize=11,
            fontName='Helvetica-Bold',
            textColor=colors.black
        )

        value_style = ParagraphStyle(
            name='ValueStyle',
            fontSize=11,
            fontName='Helvetica',
            textColor=colors.black
        )

        for i, record in enumerate(records_data):
            if i > 0:
                elements.append(PageBreak())

            # Get agency information from address config
            agency_name = record.get('agency_name', 'Unknown Agency')
            agency_info = self.address_config.get('agencies', {}).get(agency_name, {})
            
            # Header Section with Agency Info
            elements.append(Paragraph(agency_info.get('name', agency_name), header_style))
            
            if agency_info.get('address'):
                address_text = agency_info.get('address', '').replace('\n', '<br/>')
                elements.append(Paragraph(address_text, subheader_style))
            
            # Contact information
            contact_info = []
            if agency_info.get('contact'):
                contact_info.append(f"Phone: {agency_info.get('contact')}")
            if agency_info.get('email'):
                contact_info.append(f"Email: {agency_info.get('email')}")
            
            if contact_info:
                elements.append(Paragraph(" | ".join(contact_info), subheader_style))
            
            elements.append(Spacer(1, 0.2*inch))

            # Print date and ticket information
            print_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            ticket_no = record.get('ticket_no', '000')
            
            elements.append(Paragraph(f"Print Date: {print_date}", value_style))
            elements.append(Paragraph(f"Ticket No: {ticket_no}", header_style))
            elements.append(Spacer(1, 0.15*inch))

            # Vehicle Information
            elements.append(Paragraph("VEHICLE INFORMATION", section_header_style))
            
            # Get material from material_type field if material is empty
            material_value = record.get('material', '') or record.get('material_type', '')
            user_name_value = record.get('user_name', '') or "Not specified"
            site_incharge_value = record.get('site_incharge', '') or "Not specified"
            
            vehicle_data = [
                [Paragraph("<b>Vehicle No:</b>", label_style), Paragraph(record.get('vehicle_no', ''), value_style), 
                Paragraph("<b>Date:</b>", label_style), Paragraph(record.get('date', ''), value_style), 
                Paragraph("<b>Time:</b>", label_style), Paragraph(record.get('time', ''), value_style)],
                [Paragraph("<b>Material:</b>", label_style), Paragraph(material_value, value_style), 
                Paragraph("<b>Site Name:</b>", label_style), Paragraph(record.get('site_name', ''), value_style), 
                Paragraph("<b>Transfer Party:</b>", label_style), Paragraph(record.get('transfer_party_name', ''), value_style)],
                [Paragraph("<b>Agency Name:</b>", label_style), Paragraph(record.get('agency_name', ''), value_style), 
                Paragraph("<b>User Name:</b>", label_style), Paragraph(user_name_value, value_style), 
                Paragraph("<b>Site Incharge:</b>", label_style), Paragraph(site_incharge_value, value_style)]
            ]
            
            vehicle_inner_table = Table(vehicle_data, colWidths=[1.2*inch, 1.3*inch, 1.0*inch, 1.3*inch, 1.2*inch, 1.5*inch])
            vehicle_inner_table.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 13),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 2),
                ('RIGHTPADDING', (0,0), (-1,-1), 2),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            
            vehicle_table = Table([[vehicle_inner_table]], colWidths=[7.5*inch])
            vehicle_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('LEFTPADDING', (0,0), (-1,-1), 12),
                ('RIGHTPADDING', (0,0), (-1,-1), 12),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            elements.append(vehicle_table)
            elements.append(Spacer(1, 0.15*inch))

            # Weighment Information
            elements.append(Paragraph("WEIGHMENT DETAILS", section_header_style))
            first_weight_str = record.get('first_weight', '').strip()
            second_weight_str = record.get('second_weight', '').strip()
            net_weight_str = record.get('net_weight', '').strip()

            if not net_weight_str and first_weight_str and second_weight_str:
                try:
                    first_weight = float(first_weight_str)
                    second_weight = float(second_weight_str)
                    calculated_net = abs(first_weight - second_weight)
                    net_weight_str = f"{calculated_net:.2f}"
                except (ValueError, TypeError):
                    net_weight_str = "Calculation Error"

            # If we still don't have net weight, try to calculate from available data
            if not net_weight_str or net_weight_str == "Calculation Error":
                if first_weight_str and second_weight_str:
                    try:
                        first_weight = float(first_weight_str)
                        second_weight = float(second_weight_str)
                        calculated_net = abs(first_weight - second_weight)
                        net_weight_str = f"{calculated_net:.2f}"
                    except (ValueError, TypeError):
                        net_weight_str = "Unable to calculate"
                else:
                    net_weight_str = "Not Available"

            # Format display weights
            first_weight_display = f"{first_weight_str} kg" if first_weight_str else "Not captured"
            second_weight_display = f"{second_weight_str} kg" if second_weight_str else "Not captured"
            net_weight_display = f"{net_weight_str} kg" if net_weight_str and net_weight_str not in ["Not Available", "Unable to calculate", "Calculation Error"] else net_weight_str
            weighment_data = [
                [Paragraph("<b>First Weight:</b>", label_style), Paragraph(first_weight_display, value_style), 
                Paragraph("<b>First Time:</b>", label_style), Paragraph(record.get('first_timestamp', '') or "Not captured", value_style)],
                [Paragraph("<b>Second Weight:</b>", label_style), Paragraph(second_weight_display, value_style), 
                Paragraph("<b>Second Time:</b>", label_style), Paragraph(record.get('second_timestamp', '') or "Not captured", value_style)],
                [Paragraph("<b>Net Weight:</b>", label_style), Paragraph(net_weight_display, value_style)]
            ]
            
            weighment_inner_table = Table(weighment_data, colWidths=[1.5*inch, 1.5*inch, 1.2*inch, 2.8*inch])
            weighment_inner_table.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 14),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 2),
                ('RIGHTPADDING', (0,0), (-1,-1), 2),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('SPAN', (2,2), (3,2)),
                ('ALIGN', (2,2), (3,2), 'RIGHT'),
            ]))
            
            weighment_table = Table([[weighment_inner_table]], colWidths=[7.5*inch])
            weighment_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('LEFTPADDING', (0,0), (-1,-1), 12),
                ('RIGHTPADDING', (0,0), (-1,-1), 12),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            elements.append(weighment_table)
            elements.append(Spacer(1, 0.15*inch))

            # NEW: 4-Image Grid Section
            elements.append(Paragraph("VEHICLE IMAGES (4-Image System)", section_header_style))
            
            # Get all 4 image paths
            first_front_img_path = os.path.join(config.IMAGES_FOLDER, record.get('first_front_image', ''))
            first_back_img_path = os.path.join(config.IMAGES_FOLDER, record.get('first_back_image', ''))
            second_front_img_path = os.path.join(config.IMAGES_FOLDER, record.get('second_front_image', ''))
            second_back_img_path = os.path.join(config.IMAGES_FOLDER, record.get('second_back_image', ''))

            # Create 2x2 image grid with headers
            img_data = [
                ["1ST WEIGHMENT - FRONT", "1ST WEIGHMENT - BACK"],
                [None, None],  # Will be filled with first weighment images
                ["2ND WEIGHMENT - FRONT", "2ND WEIGHMENT - BACK"], 
                [None, None]   # Will be filled with second weighment images
            ]

            # Process first weighment front image
            first_front_img = None
            if os.path.exists(first_front_img_path):
                try:
                    temp_img = self.prepare_image_for_pdf(first_front_img_path, f"Ticket: {ticket_no} - 1st Front")
                    if temp_img:
                        first_front_img = RLImage(temp_img, width=3.5*inch, height=2.0*inch)
                        os.remove(temp_img)
                except Exception as e:
                    print(f"Error processing first front image: {e}")
            
            if first_front_img is None:
                first_front_img = "1st Front\nImage not available"

            # Process first weighment back image
            first_back_img = None
            if os.path.exists(first_back_img_path):
                try:
                    temp_img = self.prepare_image_for_pdf(first_back_img_path, f"Ticket: {ticket_no} - 1st Back")
                    if temp_img:
                        first_back_img = RLImage(temp_img, width=3.5*inch, height=2.0*inch)
                        os.remove(temp_img)
                except Exception as e:
                    print(f"Error processing first back image: {e}")
            
            if first_back_img is None:
                first_back_img = "1st Back\nImage not available"

            # Process second weighment front image
            second_front_img = None
            if os.path.exists(second_front_img_path):
                try:
                    temp_img = self.prepare_image_for_pdf(second_front_img_path, f"Ticket: {ticket_no} - 2nd Front")
                    if temp_img:
                        second_front_img = RLImage(temp_img, width=3.5*inch, height=2.0*inch)
                        os.remove(temp_img)
                except Exception as e:
                    print(f"Error processing second front image: {e}")
            
            if second_front_img is None:
                second_front_img = "2nd Front\nImage not available"

            # Process second weighment back image
            second_back_img = None
            if os.path.exists(second_back_img_path):
                try:
                    temp_img = self.prepare_image_for_pdf(second_back_img_path, f"Ticket: {ticket_no} - 2nd Back")
                    if temp_img:
                        second_back_img = RLImage(temp_img, width=3.5*inch, height=2.0*inch)
                        os.remove(temp_img)
                except Exception as e:
                    print(f"Error processing second back image: {e}")
            
            if second_back_img is None:
                second_back_img = "2nd Back\nImage not available"

            # Fill the image grid
            img_data[1] = [first_front_img, first_back_img]
            img_data[3] = [second_front_img, second_back_img]

            # Create images table with 2x2 grid
            img_table = Table(img_data, colWidths=[3.5*inch, 3.5*inch], 
                             rowHeights=[0.3*inch, 2*inch, 0.3*inch, 2*inch])
            img_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (1,0), 10),  # Header row 1
                ('FONTSIZE', (0,2), (1,2), 10),  # Header row 2
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                # Header background
                ('BACKGROUND', (0,0), (1,0), colors.lightgrey),
                ('BACKGROUND', (0,2), (1,2), colors.lightgrey),
            ]))
            elements.append(img_table)
            
            # Add operator signature line at bottom right
            elements.append(Spacer(1, 0.3*inch))
            
            signature_table = Table([["", "Operator's Signature"]], colWidths=[5*inch, 2.5*inch])
            signature_table.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 11),
                ('ALIGN', (1,0), (1,0), 'RIGHT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ]))
            elements.append(signature_table)

        # Build the PDF
        doc.build(elements)

    def prepare_image_for_pdf(self, image_path, watermark_text):
        """Prepare image for PDF by resizing and adding watermark"""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            # Resize image for PDF (maintain aspect ratio)
            height, width = img.shape[:2]
            max_width = 400
            max_height = 300
            
            # Calculate scaling factor
            scale_w = max_width / width
            scale_h = max_height / height
            scale = min(scale_w, scale_h)
            
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            img_resized = cv2.resize(img, (new_width, new_height))
            
            # Add watermark
            from camera import add_watermark  # Import the watermark function
            watermarked_img = add_watermark(img_resized, watermark_text)
            
            # Save temporary file
            temp_filename = f"temp_pdf_image_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
            temp_path = os.path.join(config.IMAGES_FOLDER, temp_filename)
            
            cv2.imwrite(temp_path, watermarked_img)
            return temp_path
            
        except Exception as e:
            print(f"Error preparing image for PDF: {e}")
            return None
    
    # [All the other methods remain the same - show_address_config, create_agencies_config, etc.]
    # ... (keeping the rest of the methods unchanged for brevity)
    
    def show_address_config(self):
        """Show address configuration dialog"""
        config_window = tk.Toplevel(self.report_window)
        config_window.title("Address Configuration")
        config_window.geometry("600x500")
        config_window.resizable(True, True)
        
        # Create notebook for different sections
        notebook = ttk.Notebook(config_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Agencies tab
        agencies_frame = ttk.Frame(notebook)
        notebook.add(agencies_frame, text="Agencies")
        self.create_agencies_config(agencies_frame)
        
        # Sites tab
        sites_frame = ttk.Frame(notebook)
        notebook.add(sites_frame, text="Sites")
        self.create_sites_config(sites_frame)
        
        # Buttons frame
        buttons_frame = ttk.Frame(config_window)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        save_btn = ttk.Button(buttons_frame, text="Save Configuration", 
                             command=self.save_address_config)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        close_btn = ttk.Button(buttons_frame, text="Close", 
                              command=config_window.destroy)
        close_btn.pack(side=tk.RIGHT, padx=5)
    
    def create_agencies_config(self, parent):
        """Create agencies configuration interface"""
        # Agencies listbox
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(list_frame, text="Select Agency:").pack(anchor=tk.W)
        
        self.agencies_listbox = tk.Listbox(list_frame, height=8)
        self.agencies_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.agencies_listbox.bind('<<ListboxSelect>>', self.on_agency_select)
        
        # Agency details frame
        details_frame = ttk.LabelFrame(parent, text="Agency Details", padding=10)
        details_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Agency name
        ttk.Label(details_frame, text="Agency Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.agency_name_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.agency_name_var, width=40).grid(row=0, column=1, sticky=tk.EW, pady=2)
        
        # Address
        ttk.Label(details_frame, text="Address:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.agency_address_text = tk.Text(details_frame, height=3, width=40)
        self.agency_address_text.grid(row=1, column=1, sticky=tk.EW, pady=2)
        
        # Contact
        ttk.Label(details_frame, text="Contact:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.agency_contact_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.agency_contact_var, width=40).grid(row=2, column=1, sticky=tk.EW, pady=2)
        
        # Email
        ttk.Label(details_frame, text="Email:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.agency_email_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.agency_email_var, width=40).grid(row=3, column=1, sticky=tk.EW, pady=2)
        
        details_frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(details_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="Add Agency", command=self.add_agency).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Update Agency", command=self.update_agency).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Agency", command=self.delete_agency).pack(side=tk.LEFT, padx=5)
        
        # Load agencies
        self.load_agencies_list()
    
    def create_sites_config(self, parent):
        """Create sites configuration interface"""
        # Similar structure for sites
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(list_frame, text="Select Site:").pack(anchor=tk.W)
        
        self.sites_listbox = tk.Listbox(list_frame, height=8)
        self.sites_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.sites_listbox.bind('<<ListboxSelect>>', self.on_site_select)
        
        # Site details frame
        details_frame = ttk.LabelFrame(parent, text="Site Details", padding=10)
        details_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Site name
        ttk.Label(details_frame, text="Site Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.site_name_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.site_name_var, width=40).grid(row=0, column=1, sticky=tk.EW, pady=2)
        
        # Address
        ttk.Label(details_frame, text="Address:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.site_address_text = tk.Text(details_frame, height=3, width=40)
        self.site_address_text.grid(row=1, column=1, sticky=tk.EW, pady=2)
        
        # Contact
        ttk.Label(details_frame, text="Contact:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.site_contact_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.site_contact_var, width=40).grid(row=2, column=1, sticky=tk.EW, pady=2)
        
        details_frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(details_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="Add Site", command=self.add_site).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Update Site", command=self.update_site).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Site", command=self.delete_site).pack(side=tk.LEFT, padx=5)
        
        # Load sites
        self.load_sites_list()
    
    def load_agencies_list(self):
        """Load agencies into listbox"""
        self.agencies_listbox.delete(0, tk.END)
        for agency_name in self.address_config.get('agencies', {}):
            self.agencies_listbox.insert(tk.END, agency_name)
    
    def load_sites_list(self):
        """Load sites into listbox"""
        self.sites_listbox.delete(0, tk.END)
        for site_name in self.address_config.get('sites', {}):
            self.sites_listbox.insert(tk.END, site_name)
    
    def on_agency_select(self, event):
        """Handle agency selection"""
        selection = self.agencies_listbox.curselection()
        if selection:
            agency_name = self.agencies_listbox.get(selection[0])
            agency_data = self.address_config.get('agencies', {}).get(agency_name, {})
            
            self.agency_name_var.set(agency_data.get('name', agency_name))
            self.agency_address_text.delete(1.0, tk.END)
            self.agency_address_text.insert(1.0, agency_data.get('address', ''))
            self.agency_contact_var.set(agency_data.get('contact', ''))
            self.agency_email_var.set(agency_data.get('email', ''))
    
    def on_site_select(self, event):
        """Handle site selection"""
        selection = self.sites_listbox.curselection()
        if selection:
            site_name = self.sites_listbox.get(selection[0])
            site_data = self.address_config.get('sites', {}).get(site_name, {})
            
            self.site_name_var.set(site_data.get('name', site_name))
            self.site_address_text.delete(1.0, tk.END)
            self.site_address_text.insert(1.0, site_data.get('address', ''))
            self.site_contact_var.set(site_data.get('contact', ''))
    
    def add_agency(self):
        """Add new agency"""
        name = self.agency_name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter agency name")
            return
        
        agency_data = {
            'name': name,
            'address': self.agency_address_text.get(1.0, tk.END).strip(),
            'contact': self.agency_contact_var.get().strip(),
            'email': self.agency_email_var.get().strip()
        }
        
        if 'agencies' not in self.address_config:
            self.address_config['agencies'] = {}
        
        self.address_config['agencies'][name] = agency_data
        self.load_agencies_list()
        messagebox.showinfo("Success", "Agency added successfully")
    
    def update_agency(self):
        """Update selected agency"""
        selection = self.agencies_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select an agency to update")
            return
        
        old_name = self.agencies_listbox.get(selection[0])
        new_name = self.agency_name_var.get().strip()
        
        if not new_name:
            messagebox.showerror("Error", "Please enter agency name")
            return
        
        agency_data = {
            'name': new_name,
            'address': self.agency_address_text.get(1.0, tk.END).strip(),
            'contact': self.agency_contact_var.get().strip(),
            'email': self.agency_email_var.get().strip()
        }
        
        # Remove old entry if name changed
        if old_name != new_name and old_name in self.address_config.get('agencies', {}):
            del self.address_config['agencies'][old_name]
        
        self.address_config['agencies'][new_name] = agency_data
        self.load_agencies_list()
        messagebox.showinfo("Success", "Agency updated successfully")
    
    def delete_agency(self):
        """Delete selected agency"""
        selection = self.agencies_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select an agency to delete")
            return
        
        agency_name = self.agencies_listbox.get(selection[0])
        
        if messagebox.askyesno("Confirm", f"Delete agency '{agency_name}'?"):
            if agency_name in self.address_config.get('agencies', {}):
                del self.address_config['agencies'][agency_name]
                self.load_agencies_list()
                # Clear form
                self.agency_name_var.set('')
                self.agency_address_text.delete(1.0, tk.END)
                self.agency_contact_var.set('')
                self.agency_email_var.set('')
                messagebox.showinfo("Success", "Agency deleted successfully")
    
    def add_site(self):
        """Add new site"""
        name = self.site_name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter site name")
            return
        
        site_data = {
            'name': name,
            'address': self.site_address_text.get(1.0, tk.END).strip(),
            'contact': self.site_contact_var.get().strip()
        }
        
        if 'sites' not in self.address_config:
            self.address_config['sites'] = {}
        
        self.address_config['sites'][name] = site_data
        self.load_sites_list()
        messagebox.showinfo("Success", "Site added successfully")
    
    def update_site(self):
        """Update selected site"""
        selection = self.sites_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a site to update")
            return
        
        old_name = self.sites_listbox.get(selection[0])
        new_name = self.site_name_var.get().strip()
        
        if not new_name:
            messagebox.showerror("Error", "Please enter site name")
            return
        
        site_data = {
            'name': new_name,
            'address': self.site_address_text.get(1.0, tk.END).strip(),
            'contact': self.site_contact_var.get().strip()
        }
        
        # Remove old entry if name changed
        if old_name != new_name and old_name in self.address_config.get('sites', {}):
            del self.address_config['sites'][old_name]
        
        self.address_config['sites'][new_name] = site_data
        self.load_sites_list()
        messagebox.showinfo("Success", "Site updated successfully")
    
    def delete_site(self):
        """Delete selected site"""
        selection = self.sites_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a site to delete")
            return
        
        site_name = self.sites_listbox.get(selection[0])
        
        if messagebox.askyesno("Confirm", f"Delete site '{site_name}'?"):
            if site_name in self.address_config.get('sites', {}):
                del self.address_config['sites'][site_name]
                self.load_sites_list()
                # Clear form
                self.site_name_var.set('')
                self.site_address_text.delete(1.0, tk.END)
                self.site_contact_var.set('')
                messagebox.showinfo("Success", "Site deleted successfully")
    
    def save_address_config(self):
        """Save address configuration to file"""
        try:
            config_file = os.path.join(config.DATA_FOLDER, 'address_config.json')
            with open(config_file, 'w') as f:
                json.dump(self.address_config, f, indent=4)
            messagebox.showinfo("Success", "Configuration saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")


# Legacy export functions for backward compatibility
def export_to_excel(filename=None, data_manager=None):
    """Export records to Excel - now saves to reports folder with proper naming"""
    if data_manager:
        generator = ReportGenerator(None, data_manager)
        
        # Auto-select all records for quick export
        generator.all_records = data_manager.get_all_records()
        generator.selected_records = [record.get('ticket_no', '') for record in generator.all_records]
        
        if generator.selected_records:
            generator.export_selected_to_excel()
            return True
        else:
            messagebox.showwarning("No Records", "No records found to export.")
            return False
    return False

def export_to_pdf(filename=None, data_manager=None):
    """Export records to PDF - now saves to reports folder with proper naming"""
    if data_manager:
        generator = ReportGenerator(None, data_manager)
        
        # Auto-select all records for quick export
        generator.all_records = data_manager.get_all_records()
        generator.selected_records = [record.get('ticket_no', '') for record in generator.all_records]
        
        if generator.selected_records:
            generator.export_selected_to_pdf()
            return True
        else:
            messagebox.showwarning("No Records", "No records found to export.")
            return False
    return False