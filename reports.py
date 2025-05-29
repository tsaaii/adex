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
        self.reports_folder = os.path.join(config.DATA_FOLDER, 'reports')
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
        """Export selected records to Excel with proper filename and saved to reports folder"""
        selected_data = self.get_selected_record_data()
        
        if not selected_data:
            messagebox.showwarning("No Selection", "Please select at least one record to export.")
            return
        
        try:
            # Generate filename with Agency_Site_Ticket format
            filename = self.generate_filename(selected_data, "xlsx")
            
            # Save to reports folder
            save_path = os.path.join(self.reports_folder, filename)
            
            # Create DataFrame
            df = pd.DataFrame(selected_data)
            
            # Export to Excel with formatting
            with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Vehicle Records', index=False)
                
                # Get the workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Vehicle Records']
                
                # Add title
                worksheet.insert_rows(1, 3)
                worksheet['A1'] = "SWACCHA ANDHRA CORPORATION - VEHICLE RECORDS"
                worksheet['A2'] = f"Export Date: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
                worksheet['A3'] = f"Records Count: {len(selected_data)}"
            
            messagebox.showinfo("Export Successful", 
                              f"Excel report saved successfully!\n\n"
                              f"File: {filename}\n"
                              f"Location: {self.reports_folder}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export to Excel:\n{str(e)}")
    
    def export_selected_to_pdf(self):
        """Export selected records to PDF with images, proper filename and saved to reports folder"""
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
            # Generate filename with Agency_Site_Ticket format
            filename = self.generate_filename(selected_data, "pdf")
            
            # Save to reports folder
            save_path = os.path.join(self.reports_folder, filename)
            
            self.create_pdf_report(selected_data, save_path)
            messagebox.showinfo("Export Successful", 
                              f"PDF report saved successfully!\n\n"
                              f"File: {filename}\n"
                              f"Location: {self.reports_folder}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export to PDF:\n{str(e)}")
    
    def generate_filename(self, selected_data, extension):
        """Generate filename based on Agency_Site_Ticket format"""
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
                # Multiple records: Agency_Site_MultipleTickets_Count_Timestamp.extension
                # Use common site/agency if all same, otherwise use "Multiple"
                sites = set(r.get('site_name', '').replace(' ', '_').replace('/', '_') for r in selected_data)
                agencies = set(r.get('agency_name', '').replace(' ', '_').replace('/', '_') for r in selected_data)
                
                site_part = list(sites)[0] if len(sites) == 1 else "Multiple"
                agency_part = list(agencies)[0] if len(agencies) == 1 else "Multiple"
                
                return f"{agency_part}_{site_part}_MultipleTickets_{len(selected_data)}records_{timestamp}.{extension}"
                
        except Exception as e:
            print(f"Error generating filename: {e}")
            # Fallback filename
            return f"Report_{len(selected_data)}records_{timestamp}.{extension}"
    
    def create_pdf_report(self, records_data, save_path):
        """Create ink-friendly PDF report with consistent styling"""
        doc = SimpleDocTemplate(save_path, pagesize=A4,
                                rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()
        elements = []

        # Custom ink-friendly styles
        title_style = ParagraphStyle(
            name='Title',
            fontSize=16,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=10
        )
        
        label_style = ParagraphStyle(
            name='Label',
            fontSize=10,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
        )

        normal_style = ParagraphStyle(
            name='Normal',
            fontSize=10,
            alignment=TA_LEFT,
            fontName='Helvetica',
        )

        for i, record in enumerate(records_data):
            if i > 0:
                elements.append(PageBreak())

            # Header
            agency = record.get('agency_name', 'Unknown Agency')
            site = record.get('site_name', 'Unknown Site')
            ticket = record.get('ticket_no', '000')
            
            elements.append(Paragraph(f"{agency}", title_style))
            elements.append(Paragraph(f"{site}", normal_style))
            elements.append(Paragraph(f"Ticket No: {ticket}", normal_style))
            elements.append(Spacer(1, 0.2*inch))

            # Info table
            info = [
                ["Date", record.get('date', ''), "Time", record.get('time', '')],
                ["Vehicle No", record.get('vehicle_no', ''), "Transfer Party", record.get('transfer_party_name', '')],
                ["Material", record.get('material', ''), "Material Type", record.get('material_type', '')],
                ["First Weight", record.get('first_weight', ''), "Time", record.get('first_timestamp', '')],
                ["Second Weight", record.get('second_weight', ''), "Time", record.get('second_timestamp', '')],
                ["Net Weight", record.get('net_weight', ''), "User", record.get('user_name', '')],
            ]

            table = Table(info, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
            table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.3*inch))

            # Section Title - Centered & Underlined
            elements.append(Paragraph("VEHICLE IMAGES", ParagraphStyle(
                name='SectionHeader',
                fontSize=12,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                underline=True,
                spaceAfter=12
            )))

            # Images (front & back)
            front_img_path = os.path.join(config.IMAGES_FOLDER, record.get('front_image', ''))
            back_img_path = os.path.join(config.IMAGES_FOLDER, record.get('back_image', ''))

            img_data = [["Front View", "Back View"]]
            row = []

            for path in [front_img_path, back_img_path]:
                if os.path.exists(path):
                    try:
                        temp_img = self.prepare_image_for_pdf(path, "Vehicle")
                        if temp_img:
                            row.append(RLImage(temp_img, width=2.5*inch, height=1.5*inch))
                            os.remove(temp_img)
                        else:
                            row.append("Image error")
                    except Exception:
                        row.append("Image error")
                else:
                    row.append("Not available")

            img_data.append(row)

            img_table = Table(img_data, colWidths=[2.75*inch, 2.75*inch])
            img_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTSIZE', (0,0), (-1,-1), 9)
            ]))
            elements.append(img_table)
            elements.append(Spacer(1, 0.2*inch))

            # Signature Fields
            elements.append(Spacer(1, 0.2*inch))
            sig_table = Table([
                ["Site Incharge", "Operator/User"],
                ["Signature: ___________________", "Signature: ___________________"],
                ["Date: ___________________", "Date: ___________________"]
            ], colWidths=[3*inch, 3*inch])

            sig_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 10)
            ]))
            elements.append(sig_table)

        doc.build(elements)

    
    def add_optimized_record_table(self, elements, record, styles):
        """Add record details in a nice 2-column table format"""
        # Prepare data in 2-column format
        data = [
            ['Field', 'Value'],
            ['Ticket Number', record.get('ticket_no', '')],
            ['Date', record.get('date', '')],
            ['Time', record.get('time', '')],
            ['Site Name', record.get('site_name', '')],
            ['Agency Name', record.get('agency_name', '')],
            ['Vehicle Number', record.get('vehicle_no', '')],
            ['Transfer Party', record.get('transfer_party_name', '')],
            ['Material', record.get('material', '')],
            ['Material Type', record.get('material_type', '')],
            ['First Weight (kg)', record.get('first_weight', '')],
            ['First Weight Time', record.get('first_timestamp', '')],
            ['Second Weight (kg)', record.get('second_weight', '')],
            ['Second Weight Time', record.get('second_timestamp', '')],
            ['Net Weight (kg)', record.get('net_weight', '')],
            ['Site Incharge', record.get('site_incharge', '')],
            ['User Name', record.get('user_name', '')]
        ]
        
        # Create table
        table = Table(data, colWidths=[2*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
    
    def add_weighment_images(self, elements, record, styles):
        """Add vehicle images to the PDF report with proper error handling"""
        try:
            front_image = record.get('front_image', '')
            back_image = record.get('back_image', '')
            
            if not front_image and not back_image:
                elements.append(Paragraph("No images available for this record", styles['Normal']))
                elements.append(Spacer(1, 0.2*inch))
                return
            
            # Add images section
            elements.append(Paragraph("VEHICLE IMAGES", styles['Heading2']))
            elements.append(Spacer(1, 0.1*inch))
            
            # Create table for images
            images_data = [['Front View', 'Back View']]
            image_row = []
            
            # Front image
            front_path = os.path.join(config.IMAGES_FOLDER, front_image) if front_image else None
            if front_path and os.path.exists(front_path):
                try:
                    # Create temporary resized image
                    temp_front = self.prepare_image_for_pdf(front_path, f"Ticket: {record.get('ticket_no', '')} - Front")
                    if temp_front:
                        image_row.append(RLImage(temp_front, width=2*inch, height=1.5*inch))
                        # Clean up temp file after use
                        try:
                            os.remove(temp_front)
                        except:
                            pass
                    else:
                        image_row.append("Image not available")
                except Exception as e:
                    print(f"Error processing front image: {e}")
                    image_row.append("Image error")
            else:
                image_row.append("No front image")
            
            # Back image
            back_path = os.path.join(config.IMAGES_FOLDER, back_image) if back_image else None
            if back_path and os.path.exists(back_path):
                try:
                    # Create temporary resized image
                    temp_back = self.prepare_image_for_pdf(back_path, f"Ticket: {record.get('ticket_no', '')} - Back")
                    if temp_back:
                        image_row.append(RLImage(temp_back, width=2*inch, height=1.5*inch))
                        # Clean up temp file after use
                        try:
                            os.remove(temp_back)
                        except:
                            pass
                    else:
                        image_row.append("Image not available")
                except Exception as e:
                    print(f"Error processing back image: {e}")
                    image_row.append("Image error")
            else:
                image_row.append("No back image")
            
            images_data.append(image_row)
            
            # Create images table
            img_table = Table(images_data, colWidths=[2.5*inch, 2.5*inch])
            img_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(img_table)
            elements.append(Spacer(1, 0.2*inch))
        
        except Exception as e:
            print(f"Error adding images to PDF: {e}")
            elements.append(Paragraph("Error loading images", styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
    
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
    
    def add_optimized_signature_fields(self, elements, record, styles):
        """Add signature fields to the PDF"""
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph("SIGNATURES", styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Signature table
        sig_data = [
            ['Site Incharge', 'Operator/User'],
            ['', ''],
            ['', ''],
            [f"Name: {record.get('site_incharge', '')}", f"Name: {record.get('user_name', '')}"],
            ['Signature: ___________________', 'Signature: ___________________'],
            ['Date: ___________________', 'Date: ___________________']
        ]
        
        sig_table = Table(sig_data, colWidths=[2.5*inch, 2.5*inch])
        sig_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        elements.append(sig_table)
        elements.append(Spacer(1, 0.3*inch))
    
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