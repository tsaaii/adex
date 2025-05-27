from tkinter import messagebox

class FormValidator:
    """Handles form validation logic"""
    
    def __init__(self, main_form):
        """Initialize form validator
        
        Args:
            main_form: Reference to the main form instance
        """
        self.main_form = main_form
    
    def validate_basic_fields(self):
        """Validate that basic required fields are filled"""
        required_fields = {
            "Ticket No": self.main_form.rst_var.get(),
            "Vehicle No": self.main_form.vehicle_var.get(),
            "Agency Name": self.main_form.agency_var.get()
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value.strip()]
        
        if missing_fields:
            messagebox.showerror("Validation Error", 
                            f"Please fill in the following required fields: {', '.join(missing_fields)}")
            return False
            
        return True
    
    def validate_form(self):
        """Validate all form fields before saving"""
        required_fields = {
            "Ticket No": self.main_form.rst_var.get(),
            "Vehicle No": self.main_form.vehicle_var.get(),
            "Agency Name": self.main_form.agency_var.get()
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value.strip()]
        
        if missing_fields:
            messagebox.showerror("Validation Error", 
                            f"Please fill in the following required fields: {', '.join(missing_fields)}")
            return False
        
        # For first time entry, we need first weighment and timestamp
        if (self.main_form.current_weighment == "first" and 
            (not self.main_form.first_weight_var.get() or not self.main_form.first_timestamp_var.get())):
            messagebox.showerror("Validation Error", "Please capture first weighment before saving.")
            return False
            
        # If this is a second weighment being completed, check if the second weight and timestamp exist
        if (self.main_form.current_weighment == "second" and 
            self.main_form.second_weight_var.get() and not self.main_form.second_timestamp_var.get()):
            messagebox.showerror("Validation Error", "Second weighment timestamp is missing.")
            return False
        
        # Validate at least one image is captured
        if not self.main_form.front_image_path and not self.main_form.back_image_path:
            result = messagebox.askyesno("Missing Images", 
                                    "No images have been captured. Continue without images?")
            if not result:
                return False
            
        return True
    
    def validate_vehicle_number(self):
        """Validate that vehicle number is entered before capturing images"""
        if not self.main_form.vehicle_var.get().strip():
            messagebox.showerror("Error", "Please enter a vehicle number before capturing images.")
            return False
        return True