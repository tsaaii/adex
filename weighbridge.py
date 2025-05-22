import serial
import serial.tools.list_ports
import threading
import time
import re
from collections import defaultdict
from tkinter import messagebox
import psutil


class WeighbridgeManager:
    """Class to manage weighbridge connection and data processing for 6-digit weight values between markers"""
    
    def __init__(self, update_callback=None, settings_update_callback=None, main_form_callback=None):
        """Initialize weighbridge manager with callbacks for different UI components
        
        Args:
            update_callback: General callback for weight updates
            settings_update_callback: Callback to update weight in settings tab
            main_form_callback: Callback to send weight to main form for first/second weighment
        """
        self.serial_port = None
        self.weighbridge_connected = False
        self.weight_buffer = []
        self.weight_processing = False
        self.weight_thread = None
        self.weight_update_thread = None
        
        # Store callbacks for different UI components
        self.update_callback = update_callback
        self.settings_update_callback = settings_update_callback
        self.main_form_callback = main_form_callback
        
        self.last_weight = None  # Store last weight to prevent recursive updates
        
        # Add constants for weight filtering - wide range to accept all 6-digit weights
        self.MIN_VALID_WEIGHT = 1.0       # Minimum valid weight in kg
        self.MAX_VALID_WEIGHT = 999999.0  # Maximum valid weight (6 digits)
        
        # Default serial port settings (will be overridden by settings panel)
        self.default_settings = {
            "baud_rate": 9600,
            "data_bits": 8,
            "parity": 'N',
            "stop_bits": 1
        }
    
    def get_available_ports(self):
        """Get list of available COM ports"""
        return [port.device for port in serial.tools.list_ports.comports()]
    
    def check_port_availability(self, com_port):
        """Check if the COM port is available and not in use by another application
        
        Args:
            com_port: COM port to check
            
        Returns:
            tuple: (available, message) - boolean indicating if port is available and message explaining status
        """
        if not com_port:
            return False, "No COM port specified"
            
        try:
            # Check if port exists
            all_ports = self.get_available_ports()
            if com_port not in all_ports:
                return False, f"COM port {com_port} not found on this system"
                
            # Try to open the port with minimal settings
            test_port = None
            try:
                test_port = serial.Serial(com_port, timeout=0.1)
                test_port.close()
                return True, "Port available"
            except serial.SerialException as e:
                if "PermissionError" in str(e) or "access is denied" in str(e).lower():
                    # Port exists but is in use
                    return False, f"COM port {com_port} is in use by another application"
                else:
                    # Other serial error
                    return False, f"COM port error: {str(e)}"
            finally:
                if test_port and test_port.is_open:
                    test_port.close()
        except Exception as e:
            return False, f"Error checking port: {str(e)}"
    
    def get_settings_from_panel(self, settings_dict):
        """Get serial port settings from the settings panel
        
        Args:
            settings_dict: Dictionary with COM port, baud rate, data bits, parity, and stop bits
        
        Returns:
            dict: Validated settings dictionary
        """
        # Validate or use defaults if invalid
        validated = {}
        
        # Baud rate - common values: 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200
        try:
            validated["baud_rate"] = int(settings_dict.get("baud_rate", 9600))
        except (ValueError, TypeError):
            validated["baud_rate"] = 9600
            
        # Data bits - common values: 5, 6, 7, 8
        try:
            data_bits = int(settings_dict.get("data_bits", 8))
            if data_bits not in [5, 6, 7, 8]:
                data_bits = 8
            validated["data_bits"] = data_bits
        except (ValueError, TypeError):
            validated["data_bits"] = 8
            
        # Parity - common values: N (None), E (Even), O (Odd), M (Mark), S (Space)
        parity = str(settings_dict.get("parity", "N")).upper()
        if parity and parity[0] in "NEOMS":
            validated["parity"] = parity[0]
        else:
            validated["parity"] = "N"
            
        # Stop bits - common values: 1, 1.5, 2
        try:
            stop_bits = float(settings_dict.get("stop_bits", 1))
            if stop_bits not in [1, 1.5, 2]:
                stop_bits = 1
            validated["stop_bits"] = stop_bits
        except (ValueError, TypeError):
            validated["stop_bits"] = 1
            
        # COM port
        validated["com_port"] = str(settings_dict.get("com_port", ""))
        
        return validated
    
    def connect_with_settings(self, settings_dict):
        """Connect to weighbridge using settings from settings panel
        
        Args:
            settings_dict: Dictionary with COM port, baud rate, data bits, parity, and stop bits
            
        Returns:
            tuple: (success, message)
        """
        # Get validated settings
        settings = self.get_settings_from_panel(settings_dict)
        
        try:
            # Connect using settings
            self.connect(
                settings["com_port"], 
                settings["baud_rate"],
                settings["data_bits"],
                settings["parity"],
                settings["stop_bits"]
            )
            return True, f"Connected to {settings['com_port']} successfully"
        except Exception as e:
            return False, str(e)
    
    def find_and_close_port_users(self, com_port):
        """Attempt to find processes using the COM port (Windows only)
        
        Args:
            com_port: COM port name
            
        Returns:
            list: Process names using the port (or empty list if can't determine)
        """
        using_processes = []
        
        try:
            port_number = int(com_port.replace("COM", ""))
            device_path = f"\\\\.\\COM{port_number}"
            
            # Check all processes to see if they have the port open
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    # Check if any open files in this process match our COM port
                    proc_files = proc.open_files()
                    if any(device_path.lower() in str(f).lower() for f in proc_files):
                        using_processes.append(proc.info['name'])
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    # Can't check this process, continue to next
                    continue
        except Exception as e:
            print(f"Error finding port users: {e}")
            
        return using_processes
    
    def connect(self, com_port, baud_rate, data_bits=8, parity='N', stop_bits=1):
        """Connect to weighbridge with specified parameters and enhanced error handling
        
        Args:
            com_port: COM port name
            baud_rate: Baud rate (int)
            data_bits: Data bits (int), default is 8 for weighbridge 
            parity: Parity setting (string, first letter used), default 'N' (None)
            stop_bits: Stop bits (float), default 1
            
        Returns:
            bool: True if connected successfully, False otherwise
        
        Raises:
            Exception: With descriptive error message if connection fails
        """
        if not com_port:
            raise Exception("Please select a COM port")
        
        # Store last attempted port for retries
        self.last_port_attempt = {
            "com_port": com_port,
            "baud_rate": baud_rate,
            "data_bits": data_bits,
            "parity": parity,
            "stop_bits": stop_bits
        }
        
        # Check port availability before trying to connect
        available, message = self.check_port_availability(com_port)
        if not available:
            # Check what processes might be using it
            using_processes = self.find_and_close_port_users(com_port)
            
            # Add detailed information to the error message
            if using_processes:
                message += f"\nThe following processes may be using the port: {', '.join(using_processes)}"
                message += "\nTry closing these applications and try again."
            else:
                message += "\n\nTroubleshooting tips:\n"
                message += "1. Check if the weighbridge is properly connected\n"
                message += "2. Restart the weighbridge device\n"
                message += "3. Try a different COM port\n"
                message += "4. Check USB connections or adapters\n"
                message += "5. Try restarting your computer"
                
            raise Exception(message)
        
        try:
            # Convert parity to serial.PARITY_* value
            parity_map = {
                'N': serial.PARITY_NONE,
                'O': serial.PARITY_ODD,
                'E': serial.PARITY_EVEN,
                'M': serial.PARITY_MARK,
                'S': serial.PARITY_SPACE
            }
            parity_value = parity_map.get(parity[0].upper(), serial.PARITY_NONE)
            
            # Convert stop bits
            stop_bits_map = {
                1.0: serial.STOPBITS_ONE,
                1.5: serial.STOPBITS_ONE_POINT_FIVE,
                2.0: serial.STOPBITS_TWO
            }
            stop_bits_value = stop_bits_map.get(stop_bits, serial.STOPBITS_ONE)
            
            # Create serial connection with extended error handling
            try:
                self.serial_port = serial.Serial(
                    port=com_port,
                    baudrate=baud_rate,
                    bytesize=data_bits,
                    parity=parity_value,
                    stopbits=stop_bits_value,
                    timeout=2,  # Increased timeout for more reliable connection
                    write_timeout=2,  # Added write timeout
                    inter_byte_timeout=None,
                    exclusive=True  # Try to get exclusive access to the port
                )
            except serial.SerialException as e:
                error_msg = str(e).lower()
                
                if "permission" in error_msg or "access is denied" in error_msg:
                    using_processes = self.find_and_close_port_users(com_port)
                    error_text = "Permission error: COM port is in use."
                    if using_processes:
                        error_text += f"\nPossibly by: {', '.join(using_processes)}"
                    raise Exception(error_text)
                elif "cannot find" in error_msg or "does not exist" in error_msg:
                    raise Exception(f"COM port {com_port} does not exist or is not available")
                elif "device attached" in error_msg and "not functioning" in error_msg:
                    raise Exception(
                        f"Device error on {com_port}:\n"
                        "The weighbridge is not responding or is not properly connected.\n"
                        "Please check the physical connection and restart the device."
                    )
                else:
                    # General serial error
                    raise Exception(f"Connection error: {str(e)}")
            
            # Reset state and buffers
            self.weight_buffer = []
            self.last_weight = None
            
            # Start processing
            self.weighbridge_connected = True
            
            # Start weight reading thread
            self.weight_thread = threading.Thread(target=self._read_weighbridge_data, daemon=True)
            self.weight_thread.start()
            
            # Start weight processing thread
            self.weight_processing = True
            self.weight_update_thread = threading.Thread(target=self._process_weighbridge_data, daemon=True)
            self.weight_update_thread.start()
            
            return True
            
        except Exception as e:
            # Clean up on error
            if self.serial_port:
                try:
                    self.serial_port.close()
                except:
                    pass
                self.serial_port = None
            
            # Re-raise the exception with our enhanced message
            raise e
    
    def retry_connection(self):
        """Retry the last connection attempt"""
        if not self.last_port_attempt:
            return False, "No previous connection settings to retry"
            
        try:
            result = self.connect(
                self.last_port_attempt["com_port"],
                self.last_port_attempt["baud_rate"],
                self.last_port_attempt["data_bits"],
                self.last_port_attempt["parity"],
                self.last_port_attempt["stop_bits"]
            )
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)
    
    def disconnect(self):
        """Disconnect from weighbridge
        
        Returns:
            bool: True if disconnected successfully, False otherwise
        """
        try:
            self.weight_processing = False
            self.weighbridge_connected = False
            
            if self.weight_thread and self.weight_thread.is_alive():
                self.weight_thread.join(1.0)
                
            if self.weight_update_thread and self.weight_update_thread.is_alive():
                self.weight_update_thread.join(1.0)
                
            if self.serial_port:
                self.serial_port.close()
                self.serial_port = None
                
            return True
                
        except Exception as e:
            print(f"Error disconnecting weighbridge: {e}")
            return False
    
    def _read_weighbridge_data(self):
        """Read data from weighbridge in a separate thread and accumulate all data"""
        while self.weighbridge_connected and self.serial_port:
            try:
                if self.serial_port.in_waiting > 0:
                    # Get raw bytes - try readline first (more likely to get a complete message)
                    try:
                        raw_bytes = self.serial_port.readline()
                    except:
                        # Fallback to reading whatever is available
                        raw_bytes = self.serial_port.read(self.serial_port.in_waiting)
                    
                    if raw_bytes:
                        # Commented out serial data debug printing
                        # ascii_repr = ' '.join([f"{b:02X}({chr(b) if 32 <= b <= 126 else '•'})" for b in raw_bytes])
                        # print(f"Serial data received: {ascii_repr}")
                        
                        # Add to buffer for processing
                        self.weight_buffer.append(raw_bytes)
                        
                # Sleep to avoid high CPU usage
                time.sleep(0.05)
            except Exception as e:
                print(f"Weighbridge read error: {str(e)}")
                time.sleep(0.1)
    
    def _process_weighbridge_data(self):
        """Process weighbridge data specifically looking for 6 digits between any marker characters"""
        last_update_time = 0
        update_interval = 0.2  # More responsive update interval (200ms)
        
        while self.weight_processing:
            try:
                current_time = time.time()
                
                # Process data more frequently
                if not self.weight_buffer or current_time - last_update_time < update_interval:
                    time.sleep(0.05)  # Short sleep to avoid CPU hogging
                    continue
                
                # Process all available data in the buffer
                window_data = []
                
                while self.weight_buffer:
                    raw_bytes = self.weight_buffer.pop(0)
                    
                    # Look for any sequences of exactly 6 digits between non-digit characters
                    # Iterate through the bytes
                    idx = 0
                    digit_sequence = []
                    in_digit_sequence = False
                    
                    while idx < len(raw_bytes):
                        byte = raw_bytes[idx]
                        is_digit = 48 <= byte <= 57  # ASCII codes for 0-9
                        
                        # Logic for handling digits and non-digits
                        if is_digit:
                            # Add to current sequence if we're in one
                            if in_digit_sequence:
                                digit_sequence.append(byte)
                            # Start a new sequence if we're not
                            else:
                                digit_sequence = [byte]
                                in_digit_sequence = True
                        else:
                            # End of a digit sequence - check if it's exactly 6 digits
                            if in_digit_sequence and len(digit_sequence) == 6:
                                # Convert digit sequence to a string and then a number
                                digit_string = ''.join([chr(b) for b in digit_sequence])
                                try:
                                    weight = float(digit_string)
                                    
                                    # Only print the weight matches
                                    print(f"Found 6-digit weight: {weight}")
                                    
                                    # Add to window data
                                    window_data.append(weight)
                                    
                                    # Immediate update for faster response - update UI immediately when a 6-digit weight is found
                                    self._update_all_ui_components(weight)
                                except ValueError:
                                    # Not a valid number, ignore
                                    pass
                            
                            # Reset for next sequence
                            in_digit_sequence = False
                            digit_sequence = []
                        
                        idx += 1
                    
                    # Check end of buffer for a complete 6-digit sequence
                    if in_digit_sequence and len(digit_sequence) == 6:
                        digit_string = ''.join([chr(b) for b in digit_sequence])
                        try:
                            weight = float(digit_string)
                            print(f"Found 6-digit weight at end: {weight}")
                            window_data.append(weight)
                            
                            # Immediate update for faster response
                            self._update_all_ui_components(weight)
                        except ValueError:
                            pass
                
                if window_data:
                    try:
                        # Find the most common weight in the window
                        freq = defaultdict(int)
                        for weight in window_data:
                            freq[weight] += 1
                        
                        if freq:
                            most_common = max(freq.items(), key=lambda x: x[1])[0]
                            frequency = max(freq.items(), key=lambda x: x[1])[1]
                            
                            # Only update if frequency threshold met (at least 2 times)
                            if frequency >= 2:
                                # Only update if the weight has changed significantly
                                if self.last_weight is None or abs(most_common - self.last_weight) > 0.1:
                                    self.last_weight = most_common
                                    
                                    # Print weight update
                                    print(f"Updating weight: {most_common} kg (frequency: {frequency})")
                                    
                                    # Update all UI components with weight
                                    self._update_all_ui_components(most_common)
                    except Exception as e:
                        print(f"Error analyzing weight data: {e}")
                
                # Update the last update time
                last_update_time = current_time
                    
            except Exception as e:
                print(f"Weight processing error: {str(e)}")
                time.sleep(0.5)  # Shorter sleep on error
    
    def _update_all_ui_components(self, weight):
        """Update all UI components with the weight value
        
        Args:
            weight: The weight value to update
        """
        # Update settings tab display
        if self.settings_update_callback:
            try:
                # Try running callback directly in this thread for immediate update
                self.settings_update_callback(weight)
            except Exception as e:
                print(f"Error updating settings display: {e}")
        
        # Send to main form for first/second weighment
        if self.main_form_callback:
            try:
                self.main_form_callback(weight)
            except Exception as e:
                print(f"Error sending to main form: {e}")
        
        # Call the general update callback if provided
        if self.update_callback:
            try:
                self.update_callback(weight)
            except Exception as e:
                print(f"Error in update callback: {e}")
        
        # Debug message to confirm callbacks were called
        print(f"Weight {weight} sent to all UI components")