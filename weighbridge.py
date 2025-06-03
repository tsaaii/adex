# Add this to your weighbridge.py file or create it if it doesn't exist

import serial
import serial.tools.list_ports
import threading
import time
import re

class WeighbridgeManager:
    """Enhanced weighbridge manager with test mode support"""
    
    def __init__(self, weight_callback=None):
        """Initialize weighbridge manager
        
        Args:
            weight_callback: Function to call with weight updates
        """
        self.weight_callback = weight_callback
        self.serial_connection = None
        self.is_connected = False
        self.reading_thread = None
        self.should_read = False
        
        # ADDED: Test mode support
        self.test_mode = False
        self.last_test_weight = 0.0
        
        # Weight reading configuration
        self.last_weight = 0.0
        self.weight_tolerance = 1.0  # kg tolerance for stable readings
        self.stable_readings_required = 3
        self.stable_count = 0
        
    def set_test_mode(self, enabled):
        """Set test mode on/off
        
        Args:
            enabled (bool): True to enable test mode, False to disable
        """
        self.test_mode = enabled
        print(f"WeighbridgeManager test mode set to: {enabled}")
        
        if enabled:
            # Disconnect real weighbridge if connected
            if self.is_connected:
                self.disconnect()
    
    def get_available_ports(self):
        """Get list of available COM ports
        
        Returns:
            list: Available COM port names
        """
        try:
            ports = serial.tools.list_ports.comports()
            return [port.device for port in ports]
        except Exception as e:
            print(f"Error getting COM ports: {e}")
            return []
    
    def connect(self, port, baud_rate=9600, data_bits=8, parity='None', stop_bits=1.0):
        """Connect to weighbridge
        
        Args:
            port: COM port (e.g., 'COM1')
            baud_rate: Baud rate (default 9600)
            data_bits: Data bits (default 8)
            parity: Parity setting (default 'None')
            stop_bits: Stop bits (default 1.0)
            
        Returns:
            bool: True if connection successful
        """
        try:
            if self.test_mode:
                print("Test mode enabled - simulating connection")
                self.is_connected = True
                return True
                
            # Convert parity string to serial constant
            parity_map = {
                'None': serial.PARITY_NONE,
                'Odd': serial.PARITY_ODD,
                'Even': serial.PARITY_EVEN,
                'Mark': serial.PARITY_MARK,
                'Space': serial.PARITY_SPACE
            }
            
            parity_setting = parity_map.get(parity, serial.PARITY_NONE)
            
            # Create serial connection
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=baud_rate,
                bytesize=data_bits,
                parity=parity_setting,
                stopbits=stop_bits,
                timeout=1
            )
            
            # Start reading thread
            self.should_read = True
            self.reading_thread = threading.Thread(target=self._read_weight_loop, daemon=True)
            self.reading_thread.start()
            
            self.is_connected = True
            print(f"Connected to weighbridge on {port}")
            return True
            
        except Exception as e:
            print(f"Error connecting to weighbridge: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from weighbridge
        
        Returns:
            bool: True if disconnection successful
        """
        try:
            # Stop reading thread
            self.should_read = False
            if self.reading_thread and self.reading_thread.is_alive():
                self.reading_thread.join(timeout=2)
            
            # Close serial connection
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            
            self.is_connected = False
            self.serial_connection = None
            
            print("Disconnected from weighbridge")
            return True
            
        except Exception as e:
            print(f"Error disconnecting from weighbridge: {e}")
            return False
    
    def _read_weight_loop(self):
        """Main weight reading loop (runs in separate thread)"""
        while self.should_read:
            try:
                if self.test_mode:
                    # Simulate weight readings in test mode
                    self._simulate_test_weight()
                    time.sleep(0.5)  # Update every 500ms
                    continue
                
                if self.serial_connection and self.serial_connection.is_open:
                    # Read from serial port
                    if self.serial_connection.in_waiting > 0:
                        line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            weight = self._parse_weight_string(line)
                            if weight is not None:
                                self._process_weight_reading(weight)
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
            except Exception as e:
                print(f"Error in weight reading loop: {e}")
                time.sleep(1)  # Longer delay on error
    
    def _simulate_test_weight(self):
        """Simulate weight readings for test mode"""
        try:
            import random
            
            # Simulate some variation in weight readings (±5 kg)
            base_weight = 25000  # 25 tons as base
            variation = random.uniform(-5, 5)
            simulated_weight = base_weight + variation
            
            # Add some noise to make it more realistic
            noise = random.uniform(-0.5, 0.5)
            final_weight = max(0, simulated_weight + noise)
            
            self.last_test_weight = final_weight
            
            # Call the weight callback
            if self.weight_callback:
                self.weight_callback(final_weight)
                
        except Exception as e:
            print(f"Error simulating test weight: {e}")
    
    def _parse_weight_string(self, weight_string):
        """Parse weight from weighbridge string
        
        Args:
            weight_string: Raw string from weighbridge
            
        Returns:
            float: Parsed weight or None if invalid
        """
        try:
            # Common patterns for weighbridge output
            patterns = [
                r'(\d+\.?\d*)\s*kg',  # "1234.5 kg"
                r'(\d+\.?\d*)\s*KG',  # "1234.5 KG"
                r'(\d+\.?\d*)',       # Just numbers "1234.5"
                r'ST,\s*(\d+\.?\d*)', # "ST, 1234.5"
                r'WT:\s*(\d+\.?\d*)', # "WT: 1234.5"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, weight_string)
                if match:
                    weight = float(match.group(1))
                    # Basic validation
                    if 0 <= weight <= 100000:  # 0 to 100 tons
                        return weight
            
            return None
            
        except Exception as e:
            print(f"Error parsing weight string '{weight_string}': {e}")
            return None
    
    def _process_weight_reading(self, weight):
        """Process a weight reading with stability filtering
        
        Args:
            weight: Weight reading to process
        """
        try:
            # Check if reading is stable
            if abs(weight - self.last_weight) < self.weight_tolerance:
                self.stable_count += 1
            else:
                self.stable_count = 0
            
            self.last_weight = weight
            
            # Only send stable readings to callback
            if self.stable_count >= self.stable_readings_required:
                if self.weight_callback:
                    self.weight_callback(weight)
                    
        except Exception as e:
            print(f"Error processing weight reading: {e}")
    
    def get_current_weight(self):
        """Get the current weight reading
        
        Returns:
            float: Current weight
        """
        if self.test_mode:
            return self.last_test_weight
        else:
            return self.last_weight
    
    def is_weighbridge_connected(self):
        """Check if weighbridge is connected
        
        Returns:
            bool: True if connected (or in test mode)
        """
        return self.is_connected or self.test_mode