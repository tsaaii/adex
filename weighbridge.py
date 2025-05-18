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
    
    def connect(self, com_port, baud_rate, data_bits, parity, stop_bits):
        """Connect to weighbridge with specified parameters
        
        Args:
            com_port: COM port name
            baud_rate: Baud rate (int)
            data_bits: Data bits (int)
            parity: Parity setting (string, first letter used)
            stop_bits: Stop bits (float)
            
        Returns:
            bool: True if connected successfully, False otherwise
        """
        if not com_port:
            return False
        
        try:
            # Convert parity to serial.PARITY_* value
            parity_map = {
                'N': serial.PARITY_NONE,
                'O': serial.PARITY_ODD,
                'E': serial.PARITY_EVEN,
                'M': serial.PARITY_MARK,
                'S': serial.PARITY_SPACE
            }
            parity = parity_map.get(parity[0].upper(), serial.PARITY_NONE)
            
            # Convert stop bits
            stop_bits_map = {
                1.0: serial.STOPBITS_ONE,
                1.5: serial.STOPBITS_ONE_POINT_FIVE,
                2.0: serial.STOPBITS_TWO
            }
            stop_bits = stop_bits_map.get(stop_bits, serial.STOPBITS_ONE)
            
            # Create serial connection
            self.serial_port = serial.Serial(
                port=com_port,
                baudrate=baud_rate,
                bytesize=data_bits,
                parity=parity,
                stopbits=stop_bits,
                timeout=1
            )
            
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
            if self.serial_port:
                self.serial_port.close()
                self.serial_port = None
            raise e
    
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
        """Process weighbridge data with professional stability detection for vehicle standstill"""
        # Configuration parameters
        STABILITY_READINGS = 8        # Number of consecutive readings to confirm stability
        STABILITY_TOLERANCE = 0.5     # Maximum kg variation for stability (0.5 kg)
        READING_TIMEOUT = 5.0         # Maximum seconds to wait for readings per cycle
        MIN_READINGS_FOR_DECISION = 5  # Minimum readings needed to make a decision
        
        while self.weight_processing:
            try:
                if not self.weight_buffer:
                    time.sleep(0.1)
                    continue
                
                # Start a new stability detection cycle
                stability_window = []
                cycle_start_time = time.time()
                
                # Collect readings until stability is confirmed or timeout
                while time.time() - cycle_start_time < READING_TIMEOUT and self.weight_processing:
                    if self.weight_buffer:
                        # Process raw data
                        line = self.weight_buffer.pop(0)
                        # Clean the line - remove special characters
                        cleaned = re.sub(r'[^\d.]', '', line)
                        # Find all sequences of digits (with optional decimal point)
                        matches = re.findall(r'\d+\.?\d*', cleaned)
                        
                        for match in matches:
                            if len(match) >= 6:  # At least 6 digits (valid weight)
                                try:
                                    weight = float(match)
                                    # Add to stability window
                                    stability_window.append(weight)
                                except ValueError:
                                    pass
                    
                    # Check for stability when we have enough readings
                    if len(stability_window) >= STABILITY_READINGS:
                        # Get just the most recent readings for stability check
                        recent_weights = stability_window[-STABILITY_READINGS:]
                        max_weight = max(recent_weights)
                        min_weight = min(recent_weights)
                        
                        # Check if variation is within tolerance - this indicates vehicle standstill
                        if max_weight - min_weight <= STABILITY_TOLERANCE:
                            # We have stability - calculate average of stable readings
                            stable_weight = sum(recent_weights) / len(recent_weights)
                            
                            # Report the stable weight
                            if self.update_callback:
                                self.update_callback(stable_weight)
                                
                            # Move to next cycle after successful detection
                            break
                    
                    time.sleep(0.05)  # Small delay between checks
                
                # If we exit the loop without finding stability but have enough readings
                if len(stability_window) >= MIN_READINGS_FOR_DECISION and time.time() - cycle_start_time >= READING_TIMEOUT:
                    # Fall back to frequency analysis
                    freq = defaultdict(int)
                    for weight in stability_window:
                        # Round to nearest 0.5 to group similar readings
                        rounded = round(weight * 2) / 2
                        freq[rounded] += 1
                    
                    if freq:
                        # Find the most frequent weight value
                        most_common_weight = max(freq.items(), key=lambda x: x[1])[0]
                        
                        # Report it
                        if self.update_callback:
                            self.update_callback(most_common_weight)
                
                # Short delay before starting next detection cycle
                time.sleep(0.1)
                    
            except Exception as e:
                print(f"Weight processing error: {str(e)}")
                time.sleep(1)