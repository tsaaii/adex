import serial
import serial.tools.list_ports
import threading
import time
import re
from collections import defaultdict
from tkinter import messagebox


class WeighbridgeManager:
    """Class to manage weighbridge connection and data processing"""
    
    def __init__(self, update_callback=None):
        """Initialize weighbridge manager
        
        Args:
            update_callback: Function to call when weight is updated
        """
        self.serial_port = None
        self.weighbridge_connected = False
        self.weight_buffer = []
        self.weight_processing = False
        self.weight_thread = None
        self.weight_update_thread = None
        self.update_callback = update_callback
    
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
    
    def connect(self, com_port, baud_rate, data_bits, parity, stop_bits):
        """Connect to weighbridge with specified parameters and enhanced error handling
        
        Args:
            com_port: COM port name
            baud_rate: Baud rate (int)
            data_bits: Data bits (int)
            parity: Parity setting (string, first letter used)
            stop_bits: Stop bits (float)
            
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
        """Read data from weighbridge in a separate thread"""
        while self.weighbridge_connected and self.serial_port:
            try:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('ascii', errors='ignore').strip()
                    if line:
                        self.weight_buffer.append(line)
            except Exception as e:
                print(f"Weighbridge read error: {str(e)}")
                time.sleep(0.1)
    
    def _process_weighbridge_data(self):
        """Process weighbridge data to find most common valid weight"""
        while self.weight_processing:
            try:
                if not self.weight_buffer:
                    time.sleep(0.1)
                    continue
                
                # Process data in 20-second windows
                start_time = time.time()
                window_data = []
                
                while time.time() - start_time < 20 and self.weight_processing:
                    if self.weight_buffer:
                        line = self.weight_buffer.pop(0)
                        # Clean the line - remove special characters
                        cleaned = re.sub(r'[^\d.]', '', line)
                        # Find all sequences of digits (with optional decimal point)
                        matches = re.findall(r'\d+\.?\d*', cleaned)
                        for match in matches:
                            if len(match) >= 6:  # At least 6 digits
                                try:
                                    weight = float(match)
                                    window_data.append(weight)
                                except ValueError:
                                    pass
                    time.sleep(0.05)
                
                if window_data:
                    # Find the most common weight in the window
                    freq = defaultdict(int)
                    for weight in window_data:
                        freq[weight] += 1
                    
                    if freq:
                        most_common = max(freq.items(), key=lambda x: x[1])[0]
                        # Update with the new weight through callback
                        if self.update_callback:
                            self.update_callback(most_common)
                
            except Exception as e:
                print(f"Weight processing error: {str(e)}")
                time.sleep(1)