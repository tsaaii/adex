from tkinter import messagebox
import logging

class FormValidator:
    """FIXED: Handles form validation logic with enhanced logging and validation"""
    
    def __init__(self, main_form):
        """Initialize form validator
        
        Args:
            main_form: Reference to the main form instance
        """
        self.main_form = main_form
        self.logger = logging.getLogger('FormValidator')
        self.logger.info("FormValidator initialized")
    
    def validate_basic_fields(self):
        """FIXED: Validate that basic required fields are filled with enhanced logging"""
        try:
            self.logger.info("Validating basic fields")
            
            # Get field values and strip whitespace
            ticket_no = self.main_form.rst_var.get().strip()
            vehicle_no = self.main_form.vehicle_var.get().strip()
            agency_name = self.main_form.agency_var.get().strip()
            
            self.logger.info(f"Field values: ticket='{ticket_no}', vehicle='{vehicle_no}', agency='{agency_name}'")
            
            required_fields = {
                "Ticket No": ticket_no,
                "Vehicle No": vehicle_no,
                "Agency Name": agency_name
            }
            
            missing_fields = [field for field, value in required_fields.items() if not value]
            
            if missing_fields:
                error_msg = f"Please fill in the following required fields: {', '.join(missing_fields)}"
                self.logger.error(f"Basic validation failed: {error_msg}")
                messagebox.showerror("Validation Error", error_msg)
                return False
            
            self.logger.info("Basic validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in basic validation: {e}")
            return False
    
    def validate_weighment_data(self):
        """Validate weighment data consistency"""
        try:
            self.logger.info("Validating weighment data")
            
            first_weight = self.main_form.first_weight_var.get().strip()
            first_timestamp = self.main_form.first_timestamp_var.get().strip()
            second_weight = self.main_form.second_weight_var.get().strip()
            second_timestamp = self.main_form.second_timestamp_var.get().strip()
            
            self.logger.info(f"Weighment data: first_weight='{first_weight}', first_timestamp='{first_timestamp}', "
                           f"second_weight='{second_weight}', second_timestamp='{second_timestamp}'")
            
            # Check for consistent weighment data
            if first_weight and not first_timestamp:
                error_msg = "First weighment timestamp is missing"
                self.logger.error(error_msg)
                messagebox.showerror("Validation Error", error_msg)
                return False
            
            if second_weight and not second_timestamp:
                error_msg = "Second weighment timestamp is missing"
                self.logger.error(error_msg)
                messagebox.showerror("Validation Error", error_msg)
                return False
            
            # For new entries, first weighment is required
            if self.main_form.current_weighment == "first" and not first_weight:
                error_msg = "Please capture first weighment before saving"
                self.logger.error(error_msg)
                messagebox.showerror("Validation Error", error_msg)
                return False
            
            self.logger.info("Weighment validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in weighment validation: {e}")
            return False
    
    def validate_form(self):
        """FIXED: Validate all form fields before saving with comprehensive checks"""
        try:
            self.logger.info("Starting comprehensive form validation")
            
            # Step 1: Validate basic required fields
            if not self.validate_basic_fields():
                return False
            
            # Step 2: Validate weighment data
            if not self.validate_weighment_data():
                return False
            
            # Step 3: Validate images (optional but warn user)
            if not self.validate_images():
                # Images validation failed, but ask user if they want to continue
                result = messagebox.askyesno("Missing Images", 
                                           "No images have been captured for this weighment. "
                                           "Continue without images?")
                if not result:
                    self.logger.info("User chose not to continue without images")
                    return False
                else:
                    self.logger.info("User chose to continue without images")
            
            self.logger.info("Form validation passed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in form validation: {e}")
            return False
    
    def validate_images(self):
        """Validate that at least one image is captured for current weighment"""
        try:
            current_weighment = self.main_form.current_weighment
            self.logger.info(f"Validating images for {current_weighment} weighment")
            
            if current_weighment == "first":
                # Check first weighment images
                front_image = self.main_form.first_front_image_path
                back_image = self.main_form.first_back_image_path
            else:
                # Check second weighment images
                front_image = self.main_form.second_front_image_path
                back_image = self.main_form.second_back_image_path
            
            has_images = bool(front_image or back_image)
            self.logger.info(f"Images validation for {current_weighment}: front={bool(front_image)}, back={bool(back_image)}")
            
            return has_images
            
        except Exception as e:
            self.logger.error(f"Error validating images: {e}")
            return False
    
    def validate_vehicle_number(self):
        """FIXED: Validate that vehicle number is entered before capturing images"""
        try:
            vehicle_no = self.main_form.vehicle_var.get().strip()
            
            if not vehicle_no:
                error_msg = "Please enter a vehicle number before capturing images."
                self.logger.error(f"Vehicle validation failed: {error_msg}")
                messagebox.showerror("Error", error_msg)
                return False
            
            self.logger.info(f"Vehicle validation passed: {vehicle_no}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating vehicle number: {e}")
            return False
    
    def validate_numeric_field(self, value, field_name):
        """Validate that a field contains a valid numeric value"""
        try:
            if not value or not value.strip():
                return True  # Empty is okay, will be handled by required field validation
            
            float_value = float(value.strip())
            
            if float_value < 0:
                error_msg = f"{field_name} cannot be negative"
                self.logger.error(error_msg)
                messagebox.showerror("Validation Error", error_msg)
                return False
            
            if float_value > 999999:  # Reasonable upper limit
                error_msg = f"{field_name} value seems too large"
                self.logger.error(error_msg)
                messagebox.showerror("Validation Error", error_msg)
                return False
            
            return True
            
        except ValueError:
            error_msg = f"{field_name} must be a valid number"
            self.logger.error(error_msg)
            messagebox.showerror("Validation Error", error_msg)
            return False
        except Exception as e:
            self.logger.error(f"Error validating numeric field {field_name}: {e}")
            return False