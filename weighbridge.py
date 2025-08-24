import serial
import serial.tools.list_ports
import threading
import time
import re
import datetime
import os
import signal
import sys
from contextlib import contextmanager

# Import the unified logging system - maintain compatibility
try:
    from unified_logging import setup_enhanced_logger
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False

import config

class WeighbridgeManager:
    """Optimized weighbridge manager with regex processing moved out of main serial loop"""
    
    def __init__(self, weight_callback=None):
        """Initialize weighbridge manager - loads regex patterns from settings"""
        # Setup logging
        self.setup_logging()
        
        self.weight_callback = weight_callback
        self.serial_connection = None
        self.is_connected = False
        self.reading_thread = None
        self.should_read = False
        
        # Test mode support - REQUIRED for compatibility
        self.test_mode = False
        self.last_test_weight = 0.0
        
        # Weight reading configuration - balanced for speed and stability
        self.last_weight = 0.0
        self.weight_tolerance = getattr(config, 'WEIGHT_TOLERANCE', 1.0)
        self.stable_readings_required = getattr(config, 'STABLE_READINGS_REQUIRED', 2)
        self.stable_count = 0
        
        # Connection monitoring
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.last_successful_read = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
        self.reconnect_delay = 1.0
        
        # OPTIMIZED: Initialize regex pattern variables - will be loaded from settings
        self.weight_pattern = re.compile(r'(\d+\.?\d*)')  # Start with default
        self.regex_pattern_string = r'(\d+\.?\d*)'
        self.custom_regex_pattern = None
        self.use_custom_pattern = False
        
        # NEW: Pre-compiled pattern cache to avoid recompilation
        self._pattern_cache = {}
        self._current_pattern_key = None
        
        # Register signal handlers
        self._register_signal_handlers()

    def update_regex_pattern(self, pattern_string):
        """Update regex pattern from settings - optimized with caching"""
        try:
            if pattern_string and pattern_string.strip():
                self.regex_pattern_string = pattern_string.strip()
                
                # Check cache first to avoid recompilation
                if pattern_string in self._pattern_cache:
                    self.weight_pattern = self._pattern_cache[pattern_string]
                    self._current_pattern_key = pattern_string
                else:
                    # Compile new pattern and cache it
                    self.weight_pattern = re.compile(self.regex_pattern_string)
                    self._pattern_cache[pattern_string] = self.weight_pattern
                    self._current_pattern_key = pattern_string
                    
                    # Limit cache size to prevent memory issues
                    if len(self._pattern_cache) > 10:
                        # Remove oldest entries
                        oldest_key = list(self._pattern_cache.keys())[0]
                        del self._pattern_cache[oldest_key]
                
                self.use_custom_pattern = True
                self.logger.print_success(f"Regex pattern updated and cached: {pattern_string}")
                return True
            else:
                # Use default pattern
                self.regex_pattern_string = r'(\d+\.?\d*)'
                if self.regex_pattern_string not in self._pattern_cache:
                    self._pattern_cache[self.regex_pattern_string] = re.compile(self.regex_pattern_string)
                self.weight_pattern = self._pattern_cache[self.regex_pattern_string]
                self._current_pattern_key = self.regex_pattern_string
                self.use_custom_pattern = False
                self.logger.print_warning("Empty pattern provided, using default: (\\d+\\.?\\d*)")
                return False
        except re.error as e:
            self.logger.print_error(f"Invalid regex pattern '{pattern_string}': {e}")
            # Fallback to default pattern on error
            self.regex_pattern_string = r'(\d+\.?\d*)'
            if self.regex_pattern_string not in self._pattern_cache:
                self._pattern_cache[self.regex_pattern_string] = re.compile(self.regex_pattern_string)
            self.weight_pattern = self._pattern_cache[self.regex_pattern_string]
            self._current_pattern_key = self.regex_pattern_string
            self.use_custom_pattern = False
            self.logger.print_warning("Using default pattern due to regex error: (\\d+\\.?\\d*)")
            return False
        except Exception as e:
            self.logger.print_error(f"Unexpected error updating regex pattern: {e}")
            return False

    def load_settings_and_apply_regex(self, settings_storage):
        """Load regex pattern from settings storage and apply it"""
        try:
            if not settings_storage:
                self.logger.print_info("No settings storage provided, using default pattern")
                return self.update_regex_pattern(r'(\d+\.?\d*)')
            
            wb_settings = settings_storage.get_weighbridge_settings()
            regex_pattern = wb_settings.get("regex_pattern", r'(\d+\.?\d*)')
            
            self.logger.print_info(f"Loading regex pattern from settings: {regex_pattern}")
            success = self.update_regex_pattern(regex_pattern)
            
            if success:
                self.logger.print_info("Regex pattern loaded successfully from settings")
            else:
                self.logger.print_info("Using default regex pattern")
                
            return success
            
        except Exception as e:
            self.logger.print_error(f"Error loading regex from settings: {e}")
            self.logger.print_info("Falling back to default regex pattern")
            return self.update_regex_pattern(r'(\d+\.?\d*)')

    def get_current_regex_pattern(self):
        """Get the currently active regex pattern string
        
        Returns:
            str: Current regex pattern string
        """
        return self.regex_pattern_string or r'(\d+\.?\d*)'

    def setup_logging(self):
        """Balanced logging - not too verbose, not completely silent"""
        try:
            if LOGGING_AVAILABLE:
                self.logger = setup_enhanced_logger("weighbridge", config.LOGS_FOLDER)
            else:
                self.logger = self._create_fallback_logger()
        except Exception as e:
            self.logger = self._create_fallback_logger()
    
    def _create_fallback_logger(self):
        """Balanced logger - show important messages only"""
        class BalancedLogger:
            def info(self, msg): pass  # Silent for performance
            def warning(self, msg): pass  # Silent for performance
            def error(self, msg): print(f"ERROR: {msg}")  # Show errors
            def debug(self, msg): pass  # Silent for performance
            def critical(self, msg): print(f"CRITICAL: {msg}")  # Show critical
            def print_info(self, msg): pass  # Silent for performance
            def print_success(self, msg): print(f"✅ {msg}")  # Show success
            def print_warning(self, msg): pass  # Silent for performance
            def print_error(self, msg): print(f"❌ {msg}")  # Show errors
            def print_debug(self, msg): pass  # Silent for performance
            def print_critical(self, msg): print(f"🚨 {msg}")  # Show critical
        
        return BalancedLogger()
    
    def _register_signal_handlers(self):
        """Register signal handlers"""
        try:
            def signal_handler(signum, frame):
                self.close()
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except Exception as e:
            pass
    
    def set_test_mode(self, enabled):
        """Set test mode
        
        Args:
            enabled (bool): True to enable test mode, False to disable
        """
        self.test_mode = enabled
        
        if enabled:
            if self.is_connected:
                self.disconnect()
    
    def get_available_ports(self):
        """Get available COM ports
        
        Returns:
            list: List of available COM port names
        """
        try:
            ports = serial.tools.list_ports.comports()
            return [port.device for port in ports]
        except Exception as e:
            return []
    
    def _parse_weight(self, data_line):
        """OPTIMIZED: Parse weight using cached compiled regex pattern
        
        Args:
            data_line: Raw data string from weighbridge
            
        Returns:
            float: Parsed weight in kg, or None if parsing failed
        """
        try:
            # Use cached compiled pattern - no regex compilation in main loop
            match = self.weight_pattern.search(data_line)
            if match:
                return float(match.group(1))
            return None
            
        except:
            return None

    def connect(self, port, baud_rate=9600, data_bits=8, parity='None', stop_bits=1.0, settings_storage=None):
        """Connect to weighbridge - optimized version"""
        self.connection_attempts += 1
        
        try:
            # Load regex pattern from settings if available
            if settings_storage:
                self.load_settings_and_apply_regex(settings_storage)
            
            # Parameter validation
            is_valid, error_msg = self._validate_serial_parameters(port, baud_rate, data_bits, parity, stop_bits)
            if not is_valid:
                return False
            
            if self.test_mode:
                self.is_connected = True
                self._start_test_mode_thread()
                return True
            
            # Close existing connection
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
                time.sleep(0.1)  # Reasonable delay
            
            # Parity conversion
            parity_map = {
                'None': serial.PARITY_NONE,
                'Odd': serial.PARITY_ODD,
                'Even': serial.PARITY_EVEN,
                'Mark': serial.PARITY_MARK,
                'Space': serial.PARITY_SPACE
            }
            parity_setting = parity_map.get(parity, serial.PARITY_NONE)
            
            # OPTIMIZED serial connection - faster timeout
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=baud_rate,
                bytesize=data_bits,
                parity=parity_setting,
                stopbits=stop_bits,
                timeout=0.02,  # FASTER timeout - 20ms (was 50ms)
                write_timeout=1.0,
                exclusive=True
            )
            
            if self.serial_connection.is_open:
                # Buffer clear
                self.serial_connection.reset_input_buffer()
                self.serial_connection.reset_output_buffer()
                
                # Reset counters
                self.consecutive_errors = 0
                
                # Start OPTIMIZED reading thread
                self.should_read = True
                self.reading_thread = threading.Thread(target=self._optimized_read_loop, daemon=True)
                self.reading_thread.start()
                
                self.is_connected = True
                self.connection_attempts = 0
                self.last_successful_read = datetime.datetime.now()
                
                return True
            else:
                return False
            
        except Exception as e:
            return False
    
    def _validate_serial_parameters(self, port, baud_rate, data_bits, parity, stop_bits):
        """Validate serial parameters
        
        Args:
            port (str): COM port
            baud_rate (int): Baud rate
            data_bits (int): Data bits
            parity (str): Parity setting
            stop_bits (float): Stop bits
            
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            if not port or not isinstance(port, str):
                return False, "Invalid port specified"
            
            valid_baud_rates = [300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600, 115200]
            if baud_rate not in valid_baud_rates:
                return False, f"Invalid baud rate: {baud_rate}"
            
            if data_bits not in [5, 6, 7, 8]:
                return False, f"Invalid data bits: {data_bits}"
            
            valid_parity = ['None', 'Odd', 'Even', 'Mark', 'Space']
            if parity not in valid_parity:
                return False, f"Invalid parity: {parity}"
            
            if stop_bits not in [1, 1.5, 2]:
                return False, f"Invalid stop bits: {stop_bits}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def _start_test_mode_thread(self):
        """Start test mode thread"""
        try:
            self.should_read = True
            self.reading_thread = threading.Thread(target=self._optimized_read_loop, daemon=True)
            self.reading_thread.start()
        except Exception as e:
            pass
    
    def _optimized_read_loop(self):
        """OPTIMIZED reading loop - uses cached compiled regex for maximum speed"""
        raw_data_buffer = []  # Buffer for collecting data
        
        while self.should_read:
            try:
                if self.test_mode:
                    self._simulate_test_weight()
                    time.sleep(0.2)
                    continue
                
                if self.serial_connection and self.serial_connection.is_open:
                    if self.serial_connection.in_waiting > 0:
                        try:
                            # FAST read
                            line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                            
                            if line:
                                # CRITICAL OPTIMIZATION: Use pre-compiled cached pattern
                                # No regex compilation in main loop!
                                weight = self._parse_weight(line)
                                
                                if weight is not None:
                                    self._process_weight(weight)
                                    self.consecutive_errors = 0
                                    self.last_successful_read = datetime.datetime.now()
                        
                        except serial.SerialException:
                            self.consecutive_errors += 1
                            if self.consecutive_errors >= self.max_consecutive_errors:
                                break
                            time.sleep(self.reconnect_delay)
                            continue
                
                # OPTIMIZED delay - faster response
                time.sleep(0.005)  # 5ms delay (was 10ms)
                
            except Exception:
                self.consecutive_errors += 1
                if self.consecutive_errors >= self.max_consecutive_errors:
                    break
                time.sleep(0.05)
    
    def _simulate_test_weight(self):
        """Optimized test mode simulation"""
        try:
            import random
            base_weights = [5000, 12000, 18000, 25000, 30000]
            selected_base = random.choice(base_weights)
            variation = random.uniform(-100, 100)
            
            simulated_weight = selected_base + variation
            self.last_test_weight = simulated_weight
            self._process_weight(simulated_weight)
            
        except Exception:
            pass
    
    def _process_weight(self, weight):
        """OPTIMIZED weight processing - fast but stable
        
        Args:
            weight (float): Weight value in kg
        """
        try:
            # Range check
            if weight < 0 or weight > 100000:
                return
            
            # OPTIMIZED stability check
            if abs(weight - self.last_weight) <= self.weight_tolerance:
                self.stable_count += 1
            else:
                self.stable_count = 0
            
            self.last_weight = weight
            
            # Report weights when stable - optimized requirements
            if self.stable_count >= self.stable_readings_required:
                if self.weight_callback:
                    self.weight_callback(weight)
                    
        except Exception:
            pass
    
    def disconnect(self):
        """Optimized disconnect
        
        Returns:
            bool: True if disconnection successful
        """
        try:
            self.should_read = False
            if self.reading_thread and self.reading_thread.is_alive():
                self.reading_thread.join(timeout=1.0)
            
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
                
            self.is_connected = False
            return True
            
        except Exception:
            return False
    
    def close(self):
        """Optimized cleanup
        
        Returns:
            bool: True if cleanup successful
        """
        try:
            return self.disconnect()
        except Exception:
            return False
    
    def get_current_weight(self):
        """Get current weight
        
        Returns:
            float: Current weight in kg
        """
        return self.last_weight
    
    def get_connection_status(self):
        """Get connection status with optimization info"""
        return {
            'connected': self.is_connected,
            'test_mode': self.test_mode,
            'last_weight': self.last_weight,
            'connection_attempts': self.connection_attempts,
            'consecutive_errors': self.consecutive_errors,
            'pattern': self.regex_pattern_string or '(\\d+\\.?\\d*)',
            'pattern_loaded_from_settings': self.use_custom_pattern,
            'optimized': True,
            'pattern_cache_size': len(self._pattern_cache),
            'current_pattern_cached': self._current_pattern_key is not None
        }

# Context manager for compatibility - NO CHANGES
@contextmanager
def open_weighbridge(*args, **kwargs):
    """Context manager for safe weighbridge operations"""
    mgr = WeighbridgeManager()
    try:
        if mgr.connect(*args, **kwargs):
            yield mgr
        else:
            raise RuntimeError("Failed to connect to weighbridge")
    finally:
        mgr.close()