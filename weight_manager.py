import tkinter as tk
from tkinter import messagebox
import datetime
import random
import config

class WeightManager:
    def __init__(self, main_form):
        self.main_form = main_form
        self.last_weight = 0.0
        
    def capture_weight(self):
        """Capture weight - FIXED to properly check test mode and weighbridge connection"""
        try:
            print("Capture weight called")
            
            # FIXED: Check test mode first using improved method
            if self.is_test_mode_enabled():
                print("Test mode is enabled - generating random weight")
                # Generate random weight - bypass all connection checks
                weight = self.generate_random_weight()
                print(f"Generated random weight: {weight} kg")
                
                # Update the current weight display
                self.main_form.current_weight_var.set(f"{weight:.2f} kg")
                
                # Process the weight directly
                self.process_captured_weight(weight)
                return True
                
            else:
                print("Test mode disabled - using real weighbridge")
                # FIXED: Use real weighbridge with proper connection checks
                return self.capture_real_weighbridge_weight()
                
        except Exception as e:
            print(f"Error in capture_weight: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to capture weight: {str(e)}")
            return False
    
    def is_test_mode_enabled(self):
        """IMPROVED: Check if test mode is enabled with multiple fallback methods"""
        try:
            print("Checking test mode...")
            
            # Method 1: Try to get weighbridge settings directly
            try:
                settings_storage = self.get_settings_storage()
                if settings_storage:
                    wb_settings = settings_storage.get_weighbridge_settings()
                    test_mode = wb_settings.get("test_mode", False)
                    print(f"Test mode from settings storage: {test_mode}")
                    return test_mode
            except Exception as e:
                print(f"Method 1 failed: {e}")
            
            # Method 2: Try to access through main app
            try:
                app = self.find_main_app()
                if app and hasattr(app, 'settings_panel'):
                    if hasattr(app.settings_panel, 'test_mode_var'):
                        test_mode = app.settings_panel.test_mode_var.get()
                        print(f"Test mode from app.settings_panel: {test_mode}")
                        return test_mode
            except Exception as e:
                print(f"Method 2 failed: {e}")
            
            # Method 3: Try to access weighbridge manager for test mode status
            try:
                app = self.find_main_app()
                if app and hasattr(app, 'settings_panel'):
                    if hasattr(app.settings_panel, 'weighbridge'):
                        weighbridge = app.settings_panel.weighbridge
                        if hasattr(weighbridge, 'test_mode'):
                            test_mode = weighbridge.test_mode
                            print(f"Test mode from weighbridge: {test_mode}")
                            return test_mode
            except Exception as e:
                print(f"Method 3 failed: {e}")
            
            # Method 4: Check global weighbridge reference
            try:
                manager, weight_var, status_var = config.get_global_weighbridge_info()
                if manager and hasattr(manager, 'test_mode'):
                    test_mode = manager.test_mode
                    print(f"Test mode from global reference: {test_mode}")
                    return test_mode
            except Exception as e:
                print(f"Method 4 failed: {e}")
            
            print("All methods failed - defaulting to False")
            return False
            
        except Exception as e:
            print(f"Error checking test mode: {e}")
            return False
    
    def generate_random_weight(self):
        """Generate a realistic random weight for testing"""
        try:
            import random
            
            current_weighment = getattr(self.main_form, 'current_weighment', 'first')
            print(f"Generating weight for {current_weighment} weighment")
            
            if current_weighment == "first":
                # First weighment: heavier (loaded truck)
                # Generate weight between 15,000 - 45,000 kg
                weight = random.uniform(15000, 45000)
                print(f"First weighment - generated: {weight}")
            else:
                # Second weighment: lighter (empty truck)
                # Generate weight between 5,000 - 15,000 kg
                weight = random.uniform(5000, 15000)
                print(f"Second weighment - generated: {weight}")
            
            # Round to nearest 10 kg for realism
            weight = round(weight / 10) * 10
            
            return float(weight)
            
        except Exception as e:
            print(f"Error generating random weight: {e}")
            # Fallback to simple random weight
            import random
            return round(random.uniform(5000, 30000), 2)
    
    def capture_real_weighbridge_weight(self):
        """FIXED: Capture weight from real weighbridge using the working old method"""
        try:
            print("Attempting to capture from real weighbridge")
            
            # FIXED: Use the working method from the old code
            current_weight = self.get_current_weighbridge_value()
            if current_weight is None:
                return False
            
            print(f"Captured weighbridge weight: {current_weight}")
            
            # Process the captured weight
            self.process_captured_weight(current_weight)
            return True
                
        except Exception as e:
            print(f"Error capturing real weighbridge weight: {e}")
            messagebox.showerror("Error", f"Failed to capture weighbridge weight: {str(e)}")
            return False
    
    def get_current_weighbridge_value(self):
        """FIXED: Get the current value from the weighbridge using the working old method"""
        try:
            print("Getting current weighbridge value...")
            
            # Use the same working method from the old code
            weighbridge, weight_var, status_var = config.get_global_weighbridge_info()
            
            if weighbridge is None or weight_var is None or status_var is None:
                messagebox.showerror("Application Error", 
                                "Cannot access weighbridge settings. Please restart the application.")
                return None
            
            # Get weight from the weighbridge display
            weight_str = weight_var.get()
            print(f"Weight string from weighbridge: '{weight_str}'")
            
            # FIXED: Use the exact same connection check as the working old code
            is_connected = (weighbridge is not None and 
                        status_var.get() == "Status: Connected")
            
            print(f"Weighbridge connection status: '{status_var.get()}' -> Connected: {is_connected}")
            
            if not is_connected:
                messagebox.showerror("Weighbridge Error", 
                                "Weighbridge is not connected. Please connect the weighbridge in Settings tab.")
                return None
            
            # Extract number from string like "123.45 kg" - same as old working code
            import re
            match = re.search(r'(\d+\.?\d*)', weight_str)
            if match:
                weight_value = float(match.group(1))
                print(f"Extracted weight value: {weight_value}")
                return weight_value
            else:
                messagebox.showerror("Error", "Could not read weight from weighbridge. Please check connection.")
                return None
                
        except Exception as e:
            print(f"Error in get_current_weighbridge_value: {e}")
            messagebox.showerror("Weighbridge Error", f"Error reading weighbridge: {str(e)}")
            return None
    
    def is_weighbridge_connected(self):
        """FIXED: Check if weighbridge is actually connected using the working old method"""
        try:
            print("Checking weighbridge connection...")
            
            # Use the exact same method as the working old code
            weighbridge, weight_var, status_var = config.get_global_weighbridge_info()
            
            if weighbridge is None or status_var is None:
                print("Could not get weighbridge info")
                return False
            
            # FIXED: Use the exact same check as the working old code
            is_connected = (weighbridge is not None and 
                        status_var.get() == "Status: Connected")
            
            print(f"Weighbridge status: '{status_var.get()}' -> Connected: {is_connected}")
            return is_connected
            
        except Exception as e:
            print(f"Error checking weighbridge connection: {e}")
            return False
    
    def process_captured_weight(self, weight):
        """Process the captured weight (common for both test and real mode)"""
        try:
            import datetime
            from tkinter import messagebox
            
            print(f"Processing captured weight: {weight}")
            
            current_weighment = getattr(self.main_form, 'current_weighment', 'first')
            timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            
            if current_weighment == "first":
                # First weighment
                self.main_form.first_weight_var.set(f"{weight:.2f}")
                self.main_form.first_timestamp_var.set(timestamp)
                self.main_form.current_weighment = "second"
                self.main_form.weighment_state_var.set("Second Weighment")
                
                mode_text = "TEST MODE" if self.is_test_mode_enabled() else "WEIGHBRIDGE"
                messagebox.showinfo("First Weight Captured", 
                                   f"First weighment: {weight:.2f} kg\n"
                                   f"Time: {timestamp}\n"
                                   f"Mode: {mode_text}\n\n"
                                   "Vehicle can now exit and return for second weighment.")
                
            elif current_weighment == "second":
                # Second weighment
                self.main_form.second_weight_var.set(f"{weight:.2f}")
                self.main_form.second_timestamp_var.set(timestamp)
                
                # Calculate net weight
                first_weight_str = self.main_form.first_weight_var.get()
                try:
                    first_weight = float(first_weight_str)
                    net_weight = abs(first_weight - weight)
                    self.main_form.net_weight_var.set(f"{net_weight:.2f}")
                    
                    self.main_form.weighment_state_var.set("Weighment Complete")
                    
                    mode_text = "TEST MODE" if self.is_test_mode_enabled() else "WEIGHBRIDGE"
                    messagebox.showinfo("Second Weight Captured", 
                                       f"Second weighment: {weight:.2f} kg\n"
                                       f"Net weight: {net_weight:.2f} kg\n"
                                       f"Time: {timestamp}\n"
                                       f"Mode: {mode_text}\n\n"
                                       "Both weighments complete. Ready to save record.")
                except ValueError:
                    messagebox.showerror("Error", "Invalid first weight value")
            
            return True
            
        except Exception as e:
            print(f"Error processing captured weight: {e}")
            messagebox.showerror("Error", f"Failed to process weight: {str(e)}")
            return False
    
    def get_settings_storage(self):
        """IMPROVED: Get settings storage instance with multiple fallback methods"""
        try:
            # Method 1: Try to find through parent hierarchy
            app = self.find_main_app()
            if app and hasattr(app, 'settings_storage'):
                print("Found settings_storage through main app")
                return app.settings_storage
            
            # Method 2: Try to get from main form parent
            widget = self.main_form.parent
            attempts = 0
            while widget and attempts < 10:
                attempts += 1
                if hasattr(widget, 'settings_storage'):
                    print(f"Found settings_storage at widget level {attempts}")
                    return widget.settings_storage
                if hasattr(widget, 'master'):
                    widget = widget.master
                else:
                    break
            
            # Method 3: Create new instance as fallback
            print("Creating new SettingsStorage instance")
            from settings_storage import SettingsStorage
            return SettingsStorage()
            
        except Exception as e:
            print(f"Error getting settings storage: {e}")
            return None
    
    def find_main_app(self):
        """IMPROVED: Find the main app instance with better hierarchy traversal"""
        try:
            # Start from main form and traverse up
            widget = self.main_form.parent
            attempts = 0
            
            while widget and attempts < 15:  # Increased attempts
                attempts += 1
                
                # Check for main app indicators
                if hasattr(widget, 'data_manager') and hasattr(widget, 'settings_storage'):
                    print(f"Found main app at level {attempts}")
                    return widget
                
                # Check class name for app identification
                if hasattr(widget, '__class__'):
                    class_name = widget.__class__.__name__
                    if 'App' in class_name:
                        print(f"Found app class: {class_name}")
                        return widget
                
                # Try different parent references
                if hasattr(widget, 'master') and widget.master:
                    widget = widget.master
                elif hasattr(widget, 'parent') and widget.parent:
                    widget = widget.parent
                elif hasattr(widget, 'winfo_parent'):
                    try:
                        parent_name = widget.winfo_parent()
                        if parent_name:
                            widget = widget._root().nametowidget(parent_name)
                        else:
                            break
                    except:
                        break
                else:
                    break
            
            print(f"Could not find main app after {attempts} attempts")
            return None
            
        except Exception as e:
            print(f"Error finding main app: {e}")
            return None

    def handle_weighbridge_weight(self, weight):
        """Handle weight from weighbridge - delegates to weight manager"""
        try:
            print(f"Weighbridge weight received: {weight}")
            # Update current weight display
            self.main_form.current_weight_var.set(f"{weight:.2f} kg")
            return True
        except Exception as e:
            print(f"Error handling weighbridge weight: {e}")
            return False