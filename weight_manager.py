import tkinter as tk
from tkinter import messagebox
import datetime
import config

class WeightManager:
    """Manages weight capture and display functionality"""
    
    def __init__(self, main_form):
        """Initialize weight manager
        
        Args:
            main_form: Reference to the main form instance
        """
        self.main_form = main_form
        self.start_weight_monitoring()
    
    def start_weight_monitoring(self):
        """Start periodic weight monitoring using tkinter's after method"""
        def update_weight_periodically():
            self.update_current_weight_display()
            # Schedule next update in 500ms
            self.main_form.parent.after(500, update_weight_periodically)
        
        # Start the periodic updates
        self.main_form.parent.after(100, update_weight_periodically)
    
    def update_current_weight_display(self, weight=None):
        """Update the current weight display from weighbridge
        
        Args:
            weight: Weight value to display, if None will get from weighbridge
        """
        try:
            if weight is not None:
                # Use provided weight
                self.main_form.current_weight_var.set(f"{weight:.2f} kg")
            else:
                # Get current weight from weighbridge
                weighbridge, weight_var, status_var = config.get_global_weighbridge_info()
                
                if weighbridge is not None and weight_var is not None:
                    # Get weight from the weighbridge display
                    weight_str = weight_var.get()
                    
                    # Check if weighbridge is connected
                    is_connected = (weighbridge is not None and 
                                status_var.get() == "Status: Connected")
                    
                    if is_connected:
                        # Extract number from string like "123.45 kg"
                        import re
                        match = re.search(r'(\d+\.?\d*)', weight_str)
                        if match:
                            weight_value = float(match.group(1))
                            self.main_form.current_weight_var.set(f"{weight_value:.2f} kg")
                            
                            # Update display color based on connection status
                            if hasattr(self.main_form, 'current_weight_display'):
                                self.main_form.current_weight_display.config(foreground="green")
                        else:
                            self.main_form.current_weight_var.set("-- kg")
                            if hasattr(self.main_form, 'current_weight_display'):
                                self.main_form.current_weight_display.config(foreground="red")
                    else:
                        self.main_form.current_weight_var.set("Disconnected")
                        if hasattr(self.main_form, 'current_weight_display'):
                            self.main_form.current_weight_display.config(foreground="red")
                else:
                    self.main_form.current_weight_var.set("-- kg")
                    if hasattr(self.main_form, 'current_weight_display'):
                        self.main_form.current_weight_display.config(foreground="gray")
                        
        except Exception as e:
            print(f"Error updating current weight display: {e}")
            self.main_form.current_weight_var.set("Error")
            if hasattr(self.main_form, 'current_weight_display'):
                self.main_form.current_weight_display.config(foreground="red")
    
    def get_current_weighbridge_value(self):
        """Get the current value from the weighbridge using global reference"""
        try:
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
    
    def capture_weight(self):
        """Capture weight from weighbridge based on current state"""
        # Validate required fields
        if not self.main_form.form_validator.validate_basic_fields():
            return
            
        # Get current weight from weighbridge
        current_weight = self.get_current_weighbridge_value()
        if current_weight is None:
            return
        
        # Get current timestamp
        now = datetime.datetime.now()
        timestamp = now.strftime("%d-%m-%Y %H:%M:%S")
        
        # Determine which weighment to capture based on current state
        if self.main_form.current_weighment == "first":
            # Capture first weighment
            self.main_form.first_weight_var.set(f"{current_weight:.2f}")
            self.main_form.first_timestamp_var.set(timestamp)
            
            # Update current weighment state
            self.main_form.current_weighment = "second"
            self.main_form.weighment_state_var.set("Second Weighment")
            
            # Display prompt to save the first weighment
            messagebox.showinfo("First Weighment", 
                            f"First weighment recorded: {current_weight:.2f} kg\n"
                            f"Time: {timestamp}\n"
                            f"Click Save Record to add to the pending queue.")
                
        elif self.main_form.current_weighment == "second":
            # Capture second weighment
            self.main_form.second_weight_var.set(f"{current_weight:.2f}")
            self.main_form.second_timestamp_var.set(timestamp)
            
            # Calculate net weight
            self.calculate_net_weight()
            
            # Update state
            self.main_form.weighment_state_var.set("Weighment Complete")
            
            # Display prompt to save and complete the record
            messagebox.showinfo("Second Weighment", 
                            f"Second weighment recorded: {current_weight:.2f} kg\n"
                            f"Time: {timestamp}\n"
                            f"Net weight: {self.main_form.net_weight_var.get()} kg\n"
                            f"Click Save Record to complete the process.")
    
    def calculate_net_weight(self):
        """Calculate net weight as the difference between weighments"""
        first_weight_str = self.main_form.first_weight_var.get().strip()
        second_weight_str = self.main_form.second_weight_var.get().strip()
        
        try:
            if first_weight_str and second_weight_str:
                # Calculate difference if both weights are available
                first_weight = float(first_weight_str)
                second_weight = float(second_weight_str)
                
                # Calculate the absolute difference for net weight
                net_weight = abs(first_weight - second_weight)
                
                # Format to 2 decimal places
                self.main_form.net_weight_var.set(f"{net_weight:.2f}")
            elif first_weight_str:
                # If only first weight available, leave net weight empty
                self.main_form.net_weight_var.set("")
            else:
                # No weights available
                messagebox.showerror("Error", "Please enter at least one weight value")
                
        except ValueError:
            # Handle non-numeric input
            messagebox.showerror("Error", "Invalid weight values. Please enter valid numbers.")
            self.main_form.net_weight_var.set("")
    
    def handle_weighbridge_weight(self, weight):
        """Handle weight from weighbridge based on current state
        
        Args:
            weight: Current weight from weighbridge
        """
        if not self.main_form.form_validator.validate_basic_fields():
            return
            
        # Format weight to 2 decimal places
        formatted_weight = f"{weight:.2f}"
        
        # Set current timestamp
        now = datetime.datetime.now()
        timestamp = now.strftime("%d-%m-%Y %H:%M:%S")
        
        # Check if this is a first or second weighment
        if self.main_form.current_weighment == "first":
            # This is a new entry - set first weighment
            self.main_form.first_weight_var.set(formatted_weight)
            self.main_form.first_timestamp_var.set(timestamp)
            
            # Change current state to second weighment
            self.main_form.current_weighment = "second"
            self.main_form.weighment_state_var.set("Second Weighment")
            
            # Save the record to add it to the pending queue
            if self.main_form.save_callback:
                self.main_form.save_callback()
                
            # Display confirmation
            messagebox.showinfo("First Weighment", 
                            f"First weighment recorded: {formatted_weight} kg\n"
                            f"Record saved to pending queue")
                
        elif self.main_form.current_weighment == "second":
            # This is a pending entry - set second weighment
            self.main_form.second_weight_var.set(formatted_weight)
            self.main_form.second_timestamp_var.set(timestamp)
            
            # Calculate net weight
            self.calculate_net_weight()
            
            # Update state
            self.main_form.weighment_state_var.set("Weighment Complete")
            
            # Save the complete record
            if self.main_form.save_callback:
                self.main_form.save_callback()
                
            # Display confirmation
            messagebox.showinfo("Second Weighment", 
                            f"Second weighment recorded: {formatted_weight} kg\n"
                            f"Net weight: {self.main_form.net_weight_var.get()} kg\n"
                            f"Record completed")