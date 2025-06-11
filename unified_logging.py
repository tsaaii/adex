"""
FIXED: Unified Logging System for Weighbridge Application
Captures both logging statements and print statements to log files

Usage:
    # Add to your main application file (advitia_app.py):
    from unified_logging import setup_unified_logging
    
    # In your __init__ method:
    self.unified_logger = setup_unified_logging("weighbridge_app", "logs")
    
    # All print statements from all files will now be automatically logged!
"""

import sys
import os
import logging
import datetime
from io import StringIO
import threading
import time
import config

class SafeFileHandler(logging.FileHandler):
    """Safe file handler that won't crash if file operations fail"""
    
    def __init__(self, filename, mode='a', encoding='utf-8', delay=False):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            super().__init__(filename, mode, encoding, delay)
        except Exception as e:
            # Fallback to console if file handler fails
            print(f"⚠️ Could not create file handler for {filename}: {e}")
            # Create a dummy handler that just prints
            super(logging.Handler, self).__init__()
            self.stream = sys.stdout
    
    def emit(self, record):
        """Safely emit log record"""
        try:
            if self.stream is None:
                # Try to reopen the stream
                self.stream = self._open()
            
            if self.stream is not None:
                super().emit(record)
            else:
                # Fallback to print if stream is still None
                try:
                    print(f"LOG: {self.format(record)}")
                except:
                    pass
        except Exception as e:
            # Don't crash the application due to logging errors
            try:
                print(f"⚠️ Logging error: {e}")
            except:
                pass

class UnifiedLogger:
    """FIXED: Unified logging system that captures both logging and print statements"""
    
    def __init__(self, log_folder=None, app_name="advitia_app"):
        """Initialize unified logging
        
        Args:
            log_folder (str): Folder to store log files
            app_name (str): Application name for log files
        """
        self.log_folder = log_folder or config.LOGS_FOLDER
        self.app_name = app_name
        
        # Create logs directory with error handling
        try:
            os.makedirs(self.log_folder, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Could not create logs folder {self.log_folder}: {e}")
            self.log_folder = "."  # Fallback to current directory
        
        # Generate log filenames with current date
        today = datetime.datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        
        self.combined_log_file = os.path.join(self.log_folder, f"{app_name}_combined_{date_str}.log")
        self.print_log_file = os.path.join(self.log_folder, f"{app_name}_prints_{date_str}.log")
        self.app_log_file = os.path.join(self.log_folder, f"{app_name}_app_{date_str}.log")
        
        # Thread lock for file writing safety
        self.lock = threading.Lock()
        
        # Store original streams BEFORE any redirection
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Setup unified logging
        self.setup_unified_logging()
        
        # Original print to show setup complete
        try:
            original_print = self.get_original_print()
            original_print(f"📋 Unified logging initialized:")
            original_print(f"   📄 Combined log: {self.combined_log_file}")
            original_print(f"   🖨️  Print log: {self.print_log_file}")
            original_print(f"   📱 App log: {self.app_log_file}")
        except Exception as e:
            print(f"⚠️ Could not print setup message: {e}")
    
    def get_original_print(self):
        """Get reference to original print function"""
        # This ensures we can always print to console even after redirect
        try:
            if hasattr(__builtins__, 'print'):
                return __builtins__.print
            elif isinstance(__builtins__, dict) and 'print' in __builtins__:
                return __builtins__['print']
            else:
                return print  # Fallback
        except:
            return print  # Ultimate fallback
    
    def setup_unified_logging(self):
        """Setup logging that captures both logger and print statements"""
        
        # 1. Setup standard logging with multiple handlers
        self.logger = logging.getLogger('WeighbridgeApp')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Handler 1: Combined log file (everything) - SAFE VERSION
        try:
            combined_handler = SafeFileHandler(self.combined_log_file)
            combined_handler.setLevel(logging.DEBUG)
            combined_handler.setFormatter(detailed_formatter)
            self.logger.addHandler(combined_handler)
        except Exception as e:
            print(f"⚠️ Could not create combined log handler: {e}")
        
        # Handler 2: App-specific log file - SAFE VERSION
        try:
            app_handler = SafeFileHandler(self.app_log_file)
            app_handler.setLevel(logging.INFO)
            app_handler.setFormatter(detailed_formatter)
            self.logger.addHandler(app_handler)
        except Exception as e:
            print(f"⚠️ Could not create app log handler: {e}")
        
        # Handler 3: Console output (so you still see logs on screen) - SAFE VERSION
        try:
            console_handler = logging.StreamHandler(self.original_stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(simple_formatter)
            self.logger.addHandler(console_handler)
        except Exception as e:
            print(f"⚠️ Could not create console handler: {e}")
        
        # 2. Redirect print statements to both console and file - SAFE VERSION
        try:
            self.setup_print_capture()
        except Exception as e:
            print(f"⚠️ Could not setup print capture: {e}")
        
        # Log the initialization
        try:
            self.logger.info("Unified logging system initialized")
        except Exception as e:
            print(f"⚠️ Could not log initialization: {e}")
    
    def setup_print_capture(self):
        """FIXED: Setup print statement capture with better error handling"""
        
        try:
            # Create custom stdout that writes to both console and log file
            sys.stdout = PrintCapture(
                self.original_stdout, 
                self.print_log_file, 
                self.combined_log_file,
                self.lock,
                "PRINT"
            )
            
            # Also capture stderr (for error prints)
            sys.stderr = PrintCapture(
                self.original_stderr, 
                self.print_log_file, 
                self.combined_log_file,
                self.lock,
                "ERROR"
            )
        except Exception as e:
            print(f"⚠️ Error setting up print capture: {e}")
            # Don't crash - just continue without print capture
    
    def restore_stdout(self):
        """Restore original stdout (call this on app shutdown)"""
        try:
            if hasattr(self, 'original_stdout') and self.original_stdout:
                sys.stdout = self.original_stdout
            if hasattr(self, 'original_stderr') and self.original_stderr:
                sys.stderr = self.original_stderr
            
            if hasattr(self, 'logger'):
                self.logger.info("Print capture restored")
        except Exception as e:
            try:
                print(f"⚠️ Error restoring stdout: {e}")
            except:
                pass

class PrintCapture:
    """FIXED: Custom stdout that captures print statements to both console and file"""
    
    def __init__(self, original_stream, print_log_file, combined_log_file, lock, stream_type="PRINT"):
        self.original_stream = original_stream
        self.print_log_file = print_log_file
        self.combined_log_file = combined_log_file
        self.lock = lock
        self.stream_type = stream_type
        
        # Validate that original_stream is not None
        if self.original_stream is None:
            self.original_stream = sys.__stdout__ if stream_type == "PRINT" else sys.__stderr__
    
    def write(self, text):
        """FIXED: Write to both console and log file with better error handling"""
        # Always write to original console first
        try:
            if self.original_stream and hasattr(self.original_stream, 'write'):
                self.original_stream.write(text)
                if hasattr(self.original_stream, 'flush'):
                    self.original_stream.flush()
        except Exception as e:
            # Try fallback console output
            try:
                if self.stream_type == "PRINT":
                    sys.__stdout__.write(text)
                else:
                    sys.__stderr__.write(text)
            except:
                pass  # Continue even if console write fails completely
        
        # Write to log files with timestamp (only non-empty lines)
        if text.strip():
            try:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_line = f"{timestamp} - {self.stream_type} - {text.rstrip()}\n"
                
                with self.lock:
                    # Write to print-specific log
                    try:
                        with open(self.print_log_file, 'a', encoding='utf-8') as f:
                            f.write(log_line)
                    except Exception:
                        pass  # Continue if print log fails
                    
                    # Write to combined log
                    try:
                        with open(self.combined_log_file, 'a', encoding='utf-8') as f:
                            f.write(log_line)
                    except Exception:
                        pass  # Continue if combined log fails
                        
            except Exception:
                # Don't crash the application if logging fails
                pass
    
    def flush(self):
        """FIXED: Flush both outputs with error handling"""
        try:
            if self.original_stream and hasattr(self.original_stream, 'flush'):
                self.original_stream.flush()
        except Exception:
            try:
                # Fallback flush
                if self.stream_type == "PRINT":
                    sys.__stdout__.flush()
                else:
                    sys.__stderr__.flush()
            except:
                pass  # Don't crash if flush fails

class EnhancedLogger:
    """Enhanced logger that provides both logging and print-style methods"""
    
    def __init__(self, name="advitia_app", log_folder=None):
        self.name = name
        self.log_folder = log_folder or config.LOGS_FOLDER
        
        # Get or create the main logger
        self.logger = logging.getLogger(name)
        
        # Only setup if not already configured
        if not self.logger.handlers:
            self.logger.setLevel(logging.DEBUG)
            self.setup_handlers()
    
    def setup_handlers(self):
        """Setup logging handlers with error handling"""
        try:
            # Create log filename
            today = datetime.datetime.now()
            date_str = today.strftime("%Y-%m-%d")
            log_file = os.path.join(self.log_folder, f"{self.name.lower()}_enhanced_{date_str}.log")
            
            # Ensure log directory exists
            os.makedirs(self.log_folder, exist_ok=True)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            
            # File handler - SAFE VERSION
            try:
                file_handler = SafeFileHandler(log_file)
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                print(f"⚠️ Could not create file handler: {e}")
            
            # Console handler - SAFE VERSION
            try:
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.INFO)
                console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
                self.logger.addHandler(console_handler)
            except Exception as e:
                print(f"⚠️ Could not create console handler: {e}")
                
        except Exception as e:
            print(f"⚠️ Error setting up enhanced logger: {e}")
    
    # Standard logging methods with error handling
    def debug(self, message):
        """Debug level logging"""
        try:
            self.logger.debug(message)
        except:
            print(f"DEBUG: {message}")
    
    def info(self, message):
        """Info level logging"""
        try:
            self.logger.info(message)
        except:
            print(f"INFO: {message}")
    
    def warning(self, message):
        """Warning level logging"""
        try:
            self.logger.warning(message)
        except:
            print(f"WARNING: {message}")
    
    def error(self, message):
        """Error level logging"""
        try:
            self.logger.error(message)
        except:
            print(f"ERROR: {message}")
    
    def critical(self, message):
        """Critical level logging"""
        try:
            self.logger.critical(message)
        except:
            print(f"CRITICAL: {message}")
    
    # Print-style methods that also log
    def print_info(self, message):
        """Print and log info message"""
        try:
            print(f"ℹ️ {message}")
            self.logger.info(message)
        except:
            print(f"ℹ️ {message}")
    
    def print_success(self, message):
        """Print and log success message"""
        try:
            print(f"✅ {message}")
            self.logger.info(f"SUCCESS: {message}")
        except:
            print(f"✅ {message}")
    
    def print_warning(self, message):
        """Print and log warning message"""
        try:
            print(f"⚠️ {message}")
            self.logger.warning(message)
        except:
            print(f"⚠️ {message}")
    
    def print_error(self, message):
        """Print and log error message"""
        try:
            print(f"❌ {message}")
            self.logger.error(message)
        except:
            print(f"❌ {message}")
    
    def print_debug(self, message):
        """Print and log debug message"""
        try:
            print(f"🔍 {message}")
            self.logger.debug(message)
        except:
            print(f"🔍 {message}")
    
    def print_queue(self, message):
        """Print and log queue-related message"""
        try:
            print(f"📥 {message}")
            self.logger.info(f"QUEUE: {message}")
        except:
            print(f"📥 {message}")
    
    def print_sync(self, message):
        """Print and log sync-related message"""
        try:
            print(f"🔄 {message}")
            self.logger.info(f"SYNC: {message}")
        except:
            print(f"🔄 {message}")

# Easy-to-use functions for your existing code
def setup_unified_logging(app_name="advitia_app", log_folder=None):
    """FIXED: Setup unified logging for the entire application
    
    Args:
        app_name (str): Application name
        log_folder (str): Log folder path
        
    Returns:
        UnifiedLogger: Configured unified logger
    """
    try:
        log_folder = log_folder or config.LOGS_FOLDER
        return UnifiedLogger(log_folder, app_name)
    except Exception as e:
        print(f"⚠️ Could not setup unified logging: {e}")
        # Return a dummy logger that just prints
        class DummyLogger:
            def __init__(self):
                pass
            def restore_stdout(self):
                pass
        return DummyLogger()

def setup_enhanced_logger(name="advitia_app", log_folder=None):
    """Setup enhanced logger with both logging and print methods
    
    Args:
        name (str): Logger name
        log_folder (str): Log folder path
        
    Returns:
        EnhancedLogger: Configured enhanced logger
    """
    try:
        log_folder = log_folder or config.LOGS_FOLDER
        return EnhancedLogger(name, log_folder)
    except Exception as e:
        print(f"⚠️ Could not setup enhanced logger: {e}")
        return EnhancedLogger(name, ".")  # Fallback to current directory

def get_app_logger(name="advitia_app"):
    """Get the main application logger (after unified logging is setup)
    
    Args:
        name (str): Logger name
        
    Returns:
        logging.Logger: The main application logger
    """
    try:
        return logging.getLogger(name)
    except Exception as e:
        print(f"⚠️ Could not get app logger: {e}")
        # Return a dummy logger
        class DummyLogger:
            def info(self, msg): print(f"INFO: {msg}")
            def warning(self, msg): print(f"WARNING: {msg}")
            def error(self, msg): print(f"ERROR: {msg}")
            def debug(self, msg): print(f"DEBUG: {msg}")
            def critical(self, msg): print(f"CRITICAL: {msg}")
        return DummyLogger()

# Context manager for temporary print capture
class PrintCaptureContext:
    """Context manager to temporarily capture prints to a specific file"""
    
    def __init__(self, log_file_path, capture_errors=True):
        self.log_file_path = log_file_path
        self.capture_errors = capture_errors
        self.original_stdout = None
        self.original_stderr = None
        self.lock = threading.Lock()
        
    def __enter__(self):
        try:
            self.original_stdout = sys.stdout
            if self.capture_errors:
                self.original_stderr = sys.stderr
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
            
            # Redirect stdout
            sys.stdout = PrintCapture(
                self.original_stdout, 
                self.log_file_path, 
                self.log_file_path,
                self.lock,
                "PRINT"
            )
            
            # Redirect stderr if requested
            if self.capture_errors:
                sys.stderr = PrintCapture(
                    self.original_stderr, 
                    self.log_file_path, 
                    self.log_file_path,
                    self.lock,
                    "ERROR"
                )
        except Exception as e:
            print(f"⚠️ Error in print capture context: {e}")
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.original_stdout:
                sys.stdout = self.original_stdout
            if self.capture_errors and self.original_stderr:
                sys.stderr = self.original_stderr
        except Exception as e:
            print(f"⚠️ Error restoring print capture: {e}")

# Utility functions
def get_log_files_info(log_folder=None):
    """Get information about existing log files
    
    Args:
        log_folder (str): Log folder path
        
    Returns:
        dict: Information about log files
    """
    try:
        log_folder = log_folder or config.LOGS_FOLDER
        if not os.path.exists(log_folder):
            return {"error": "Log folder does not exist"}
        
        log_files = []
        total_size = 0
        
        for filename in os.listdir(log_folder):
            if filename.endswith('.log'):
                file_path = os.path.join(log_folder, filename)
                file_size = os.path.getsize(file_path)
                file_mtime = os.path.getmtime(file_path)
                
                log_files.append({
                    "name": filename,
                    "size_bytes": file_size,
                    "size_mb": round(file_size / (1024 * 1024), 2),
                    "modified": datetime.datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
                total_size += file_size
        
        return {
            "log_folder": log_folder,
            "total_files": len(log_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "files": sorted(log_files, key=lambda x: x["modified"], reverse=True)
        }
    except Exception as e:
        return {"error": f"Error getting log files info: {e}"}

def cleanup_old_logs(log_folder=None, days_to_keep=7):
    """Clean up log files older than specified days
    
    Args:
        log_folder (str): Log folder path
        days_to_keep (int): Number of days to keep logs
        
    Returns:
        dict: Cleanup results
    """
    try:
        log_folder = log_folder or config.LOGS_FOLDER
        if not os.path.exists(log_folder):
            return {"error": "Log folder does not exist"}
        
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        deleted_files = []
        total_size_freed = 0
        
        for filename in os.listdir(log_folder):
            if filename.endswith('.log'):
                file_path = os.path.join(log_folder, filename)
                file_mtime = os.path.getmtime(file_path)
                
                if file_mtime < cutoff_time:
                    file_size = os.path.getsize(file_path)
                    try:
                        os.remove(file_path)
                        deleted_files.append(filename)
                        total_size_freed += file_size
                    except Exception as e:
                        print(f"Error deleting {filename}: {e}")
        
        return {
            "deleted_files": deleted_files,
            "total_deleted": len(deleted_files),
            "size_freed_mb": round(total_size_freed / (1024 * 1024), 2)
        }
    except Exception as e:
        return {"error": f"Error during cleanup: {e}"}

# Test and example functions
def test_unified_logging():
    """Test the unified logging system"""
    print("🧪 Testing FIXED Unified Logging System")
    print("=" * 50)
    
    try:
        # Setup unified logging
        unified_logger = setup_unified_logging("test_app", "logs")
        
        # Test different types of prints
        print("📋 This is a regular print statement")
        print("✅ Success message with emoji")
        print("❌ Error message with emoji")
        print("🔄 Processing message")
        print("📊 Data: 123, Status: OK")
        
        # Test enhanced logger
        enhanced_logger = setup_enhanced_logger("TestApp", "logs")
        enhanced_logger.print_success("Enhanced logger success message")
        enhanced_logger.print_warning("Enhanced logger warning message")
        enhanced_logger.print_error("Enhanced logger error message")
        
        # Test standard logging
        app_logger = get_app_logger()
        app_logger.info("Standard logging info message")
        app_logger.warning("Standard logging warning message")
        app_logger.error("Standard logging error message")
        
        print("🎉 Test completed! Check the logs folder for output files.")
        
        # Show log files info
        log_info = get_log_files_info("logs")
        print(f"\n📁 Log files created: {log_info.get('total_files', 0)}")
        for file_info in log_info.get('files', []):
            print(f"   📄 {file_info['name']} ({file_info['size_mb']} MB)")
            
    except Exception as e:
        print(f"⚠️ Test failed: {e}")

if __name__ == "__main__":
    # Run the test when script is executed directly
    test_unified_logging()