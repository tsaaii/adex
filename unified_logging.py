"""
Unified Logging System for Weighbridge Application
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
class UnifiedLogger:
    """Unified logging system that captures both logging and print statements"""
    
    def __init__(self, log_folder=None, app_name="advitia_app"):
        """Initialize unified logging
        
        Args:
            log_folder (str): Folder to store log files
            app_name (str): Application name for log files
        """
        self.log_folder = config.LOGS_FOLDER
        self.app_name = app_name
        
        # Create logs directory
        os.makedirs(log_folder, exist_ok=True)
        
        # Generate log filenames with current date
        today = datetime.datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        
        self.combined_log_file = os.path.join(log_folder, f"{app_name}_combined_{date_str}.log")
        self.print_log_file = os.path.join(log_folder, f"{app_name}_prints_{date_str}.log")
        self.app_log_file = os.path.join(log_folder, f"{app_name}_app_{date_str}.log")
        
        # Thread lock for file writing safety
        self.lock = threading.Lock()
        
        # Setup unified logging
        self.setup_unified_logging()
        
        # Original print to show setup complete
        original_print = self.get_original_print()
        original_print(f"📋 Unified logging initialized:")
        original_print(f"   📄 Combined log: {self.combined_log_file}")
        original_print(f"   🖨️  Print log: {self.print_log_file}")
        original_print(f"   📱 App log: {self.app_log_file}")
    
    def get_original_print(self):
        """Get reference to original print function"""
        # This ensures we can always print to console even after redirect
        return __builtins__['print'] if isinstance(__builtins__, dict) else __builtins__.print
    
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
        
        # Handler 1: Combined log file (everything)
        combined_handler = logging.FileHandler(self.combined_log_file, encoding='utf-8')
        combined_handler.setLevel(logging.DEBUG)
        combined_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(combined_handler)
        
        # Handler 2: App-specific log file
        app_handler = logging.FileHandler(self.app_log_file, encoding='utf-8')
        app_handler.setLevel(logging.INFO)
        app_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(app_handler)
        
        # Handler 3: Console output (so you still see logs on screen)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        self.logger.addHandler(console_handler)
        
        # 2. Redirect print statements to both console and file
        self.setup_print_capture()
        
        # Log the initialization
        self.logger.info("Unified logging system initialized")
    
    def setup_print_capture(self):
        """Setup print statement capture"""
        
        # Store original stdout and stderr
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
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
    
    def restore_stdout(self):
        """Restore original stdout (call this on app shutdown)"""
        try:
            if hasattr(self, 'original_stdout'):
                sys.stdout = self.original_stdout
            if hasattr(self, 'original_stderr'):
                sys.stderr = self.original_stderr
            self.logger.info("Print capture restored")
        except Exception as e:
            print(f"Error restoring stdout: {e}")

class PrintCapture:
    """Custom stdout that captures print statements to both console and file"""
    
    def __init__(self, original_stream, print_log_file, combined_log_file, lock, stream_type="PRINT"):
        self.original_stream = original_stream
        self.print_log_file = print_log_file
        self.combined_log_file = combined_log_file
        self.lock = lock
        self.stream_type = stream_type
        
    def write(self, text):
        """Write to both console and log file"""
        # Always write to original console first
        try:
            self.original_stream.write(text)
            self.original_stream.flush()
        except:
            pass  # Continue even if console write fails
        
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
                    except Exception as e:
                        pass  # Continue if print log fails
                    
                    # Write to combined log
                    try:
                        with open(self.combined_log_file, 'a', encoding='utf-8') as f:
                            f.write(log_line)
                    except Exception as e:
                        pass  # Continue if combined log fails
                        
            except Exception as e:
                # Fallback to original stream if all logging fails
                try:
                    self.original_stream.write(f"⚠️ Log write error: {e}\n")
                except:
                    pass
    
    def flush(self):
        """Flush both outputs"""
        try:
            self.original_stream.flush()
        except:
            pass

class EnhancedLogger:
    """Enhanced logger that provides both logging and print-style methods"""
    
    def __init__(self, name="advitia_app", log_folder=None):
        self.name = name
        self.log_folder = config.LOGS_FOLDER
        
        # Get or create the main logger
        self.logger = logging.getLogger(name)
        
        # Only setup if not already configured
        if not self.logger.handlers:
            self.logger.setLevel(logging.DEBUG)
            self.setup_handlers()
    
    def setup_handlers(self):
        """Setup logging handlers"""
        log_folder = config.LOGS_FOLDER
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
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        self.logger.addHandler(console_handler)
    
    # Standard logging methods
    def debug(self, message):
        """Debug level logging"""
        self.logger.debug(message)
    
    def info(self, message):
        """Info level logging"""
        self.logger.info(message)
    
    def warning(self, message):
        """Warning level logging"""
        self.logger.warning(message)
    
    def error(self, message):
        """Error level logging"""
        self.logger.error(message)
    
    def critical(self, message):
        """Critical level logging"""
        self.logger.critical(message)
    
    # Print-style methods that also log
    def print_info(self, message):
        """Print and log info message"""
        print(f"ℹ️ {message}")
        self.logger.info(message)
    
    def print_success(self, message):
        """Print and log success message"""
        print(f"✅ {message}")
        self.logger.info(f"SUCCESS: {message}")
    
    def print_warning(self, message):
        """Print and log warning message"""
        print(f"⚠️ {message}")
        self.logger.warning(message)
    
    def print_error(self, message):
        """Print and log error message"""
        print(f"❌ {message}")
        self.logger.error(message)
    
    def print_debug(self, message):
        """Print and log debug message"""
        print(f"🔍 {message}")
        self.logger.debug(message)
    
    def print_queue(self, message):
        """Print and log queue-related message"""
        print(f"📥 {message}")
        self.logger.info(f"QUEUE: {message}")
    
    def print_sync(self, message):
        """Print and log sync-related message"""
        print(f"🔄 {message}")
        self.logger.info(f"SYNC: {message}")

# Easy-to-use functions for your existing code
def setup_unified_logging(app_name="advitia_app", log_folder=None):
    """Setup unified logging for the entire application
    
    Args:
        app_name (str): Application name
        log_folder (str): Log folder path
        
    Returns:
        UnifiedLogger: Configured unified logger
    """
    log_folder = config.LOGS_FOLDER
    return UnifiedLogger(log_folder, app_name)

def setup_enhanced_logger(name="advitia_app", log_folder=None):
    """Setup enhanced logger with both logging and print methods
    
    Args:
        name (str): Logger name
        log_folder (str): Log folder path
        
    Returns:
        EnhancedLogger: Configured enhanced logger
    """
    log_folder = config.LOGS_FOLDER
    return EnhancedLogger(name, log_folder)

def get_app_logger(name="advitia_app"):
    """Get the main application logger (after unified logging is setup)
    
    Args:
        name (str): Logger name
        
    Returns:
        logging.Logger: The main application logger
    """
    return logging.getLogger(name)

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
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        if self.capture_errors and self.original_stderr:
            sys.stderr = self.original_stderr

# Utility functions
def get_log_files_info(log_folder=None):
    """Get information about existing log files
    
    Args:
        log_folder (str): Log folder path
        
    Returns:
        dict: Information about log files
    """
    log_folder = config.LOGS_FOLDER
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

def cleanup_old_logs(log_folder=None, days_to_keep=7):
    """Clean up log files older than specified days
    
    Args:
        log_folder (str): Log folder path
        days_to_keep (int): Number of days to keep logs
        
    Returns:
        dict: Cleanup results
    """
    log_folder = config.LOGS_FOLDER
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

# Test and example functions
def test_unified_logging():
    """Test the unified logging system"""
    print("🧪 Testing Unified Logging System")
    print("=" * 50)
    
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
    print(f"\n📁 Log files created: {log_info['total_files']}")
    for file_info in log_info['files']:
        print(f"   📄 {file_info['name']} ({file_info['size_mb']} MB)")

if __name__ == "__main__":
    # Run the test when script is executed directly
    test_unified_logging()