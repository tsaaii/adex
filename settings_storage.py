import os
import json
import hashlib
import config

class SettingsStorage:
    """Class for managing persistent settings storage"""
    
    def __init__(self):
        """Initialize the settings storage"""
        self.settings_file = os.path.join(config.DATA_FOLDER, 'app_settings.json')
        self.users_file = os.path.join(config.DATA_FOLDER, 'users.json')
        self.sites_file = os.path.join(config.DATA_FOLDER, 'sites.json')
        self.initialize_files()
        
    def initialize_files(self):
        """Initialize settings files if they don't exist"""
        # Create settings file with default settings
        if not os.path.exists(self.settings_file):
            default_settings = {
                "weighbridge": {
                    "com_port": "",
                    "baud_rate": 9600,
                    "data_bits": 8,
                    "parity": "None",
                    "stop_bits": 1.0
                },
                "cameras": {
                    "front_camera_type": "USB",
                    "front_camera_index": 0,
                    "front_rtsp_username": "",
                    "front_rtsp_password": "",
                    "front_rtsp_ip": "",
                    "front_rtsp_port": "554",
                    "front_rtsp_endpoint": "/stream1",
                    "back_camera_type": "USB",
                    "back_camera_index": 1,
                    "back_rtsp_username": "",
                    "back_rtsp_password": "",
                    "back_rtsp_ip": "",
                    "back_rtsp_port": "554",
                    "back_rtsp_endpoint": "/stream1"
                }
            }
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump(default_settings, f, indent=4)
        else:
            # Update existing settings file to include RTSP settings if missing
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                
                # Check if cameras section needs updating
                cameras = settings.get("cameras", {})
                updated = False
                
                # Add missing RTSP settings for front camera
                if "front_camera_type" not in cameras:
                    cameras.update({
                        "front_camera_type": "USB",
                        "front_rtsp_username": "",
                        "front_rtsp_password": "",
                        "front_rtsp_ip": "",
                        "front_rtsp_port": "554",
                        "front_rtsp_endpoint": "/stream1"
                    })
                    updated = True
                
                # Add missing RTSP settings for back camera
                if "back_camera_type" not in cameras:
                    cameras.update({
                        "back_camera_type": "USB",
                        "back_rtsp_username": "",
                        "back_rtsp_password": "",
                        "back_rtsp_ip": "",
                        "back_rtsp_port": "554",
                        "back_rtsp_endpoint": "/stream1"
                    })
                    updated = True
                
                if updated:
                    settings["cameras"] = cameras
                    with open(self.settings_file, 'w') as f:
                        json.dump(settings, f, indent=4)
                        
            except Exception as e:
                print(f"Error updating settings file: {e}")
        
        # Create users file with default admin user
        if not os.path.exists(self.users_file):
            default_users = {
                "admin": {
                    "password": self.hash_password("admin"),
                    "role": "admin",
                    "name": "Administrator"
                }
            }
            os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
            with open(self.users_file, 'w') as f:
                json.dump(default_users, f, indent=4)
        
        # Create sites file with default site, incharge, and transfer party
        if not os.path.exists(self.sites_file):
            default_sites = {
                "sites": ["Guntur"],
                "incharges": ["Site Manager"],
                "transfer_parties": ["Advitia Labs"],
                "agencies": ["Default Agency"]  # Added default agency
            }
            os.makedirs(os.path.dirname(self.sites_file), exist_ok=True)
            with open(self.sites_file, 'w') as f:
                json.dump(default_sites, f, indent=4)
        else:
            # Update existing sites file to include agencies if missing
            try:
                with open(self.sites_file, 'r') as f:
                    sites_data = json.load(f)
                    
                # Add missing fields
                if 'transfer_parties' not in sites_data:
                    sites_data['transfer_parties'] = ["Advitia Labs"]
                if 'agencies' not in sites_data:
                    sites_data['agencies'] = ["Default Agency"]
                    
                with open(self.sites_file, 'w') as f:
                    json.dump(sites_data, f, indent=4)
            except Exception as e:
                print(f"Error updating sites file: {e}")

    def get_sites(self):
        """Get sites, incharges, transfer parties and agencies
        
        Returns:
            dict: Sites data with 'sites', 'incharges', 'transfer_parties', and 'agencies' keys
        """
        try:
            with open(self.sites_file, 'r') as f:
                sites_data = json.load(f)
                
                # Ensure all fields exist
                if 'transfer_parties' not in sites_data:
                    sites_data['transfer_parties'] = ["Advitia Labs"]
                if 'agencies' not in sites_data:
                    sites_data['agencies'] = ["Default Agency"]
                
                return sites_data
        except Exception as e:
            print(f"Error reading sites: {e}")
            return {
                "sites": ["Guntur"], 
                "incharges": ["Site Manager"],
                "transfer_parties": ["Advitia Labs"],
                "agencies": ["Default Agency"]
            }

    def get_weighbridge_settings(self):
        """Get weighbridge settings from file
        
        Returns:
            dict: Weighbridge settings
        """
        try:
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
                return settings.get("weighbridge", {})
        except Exception as e:
            print(f"Error reading weighbridge settings: {e}")
            return {}
    
    def save_weighbridge_settings(self, settings):
        """Save weighbridge settings to file
        
        Args:
            settings: Weighbridge settings dict
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.settings_file, 'r') as f:
                all_settings = json.load(f)
            
            all_settings["weighbridge"] = settings
            
            with open(self.settings_file, 'w') as f:
                json.dump(all_settings, f, indent=4)
                
            return True
        except Exception as e:
            print(f"Error saving weighbridge settings: {e}")
            return False
    
    def get_camera_settings(self):
        """Get camera settings from file
        
        Returns:
            dict: Camera settings
        """
        try:
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
                return settings.get("cameras", {})
        except Exception as e:
            print(f"Error reading camera settings: {e}")
            return {}
    
    def save_camera_settings(self, settings):
        """Save camera settings to file
        
        Args:
            settings: Camera settings dict
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.settings_file, 'r') as f:
                all_settings = json.load(f)
            
            all_settings["cameras"] = settings
            
            with open(self.settings_file, 'w') as f:
                json.dump(all_settings, f, indent=4)
                
            return True
        except Exception as e:
            print(f"Error saving camera settings: {e}")
            return False
    
    def get_rtsp_url(self, camera_position):
        """Build RTSP URL for specified camera position
        
        Args:
            camera_position: "front" or "back"
            
        Returns:
            str: Complete RTSP URL or None if not configured
        """
        try:
            camera_settings = self.get_camera_settings()
            
            username = camera_settings.get(f"{camera_position}_rtsp_username", "")
            password = camera_settings.get(f"{camera_position}_rtsp_password", "")
            ip = camera_settings.get(f"{camera_position}_rtsp_ip", "")
            port = camera_settings.get(f"{camera_position}_rtsp_port", "554")
            endpoint = camera_settings.get(f"{camera_position}_rtsp_endpoint", "/stream1")
            
            if not ip:
                return None
                
            # Build RTSP URL
            if username and password:
                rtsp_url = f"rtsp://{username}:{password}@{ip}:{port}{endpoint}"
            else:
                rtsp_url = f"rtsp://{ip}:{port}{endpoint}"
                
            return rtsp_url
            
        except Exception as e:
            print(f"Error building RTSP URL: {e}")
            return None
    
    def get_users(self):
        """Get all users
        
        Returns:
            dict: User data keyed by username
        """
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading users: {e}")
            return {"admin": {"password": self.hash_password("admin"), "role": "admin", "name": "Administrator"}}
    
    def save_users(self, users):
        """Save users to file
        
        Args:
            users: Users dict
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving users: {e}")
            return False
    
    def save_sites(self, sites_data):
        """Save sites, incharges and transfer parties to file
        
        Args:
            sites_data: Dict with 'sites', 'incharges', and 'transfer_parties' keys
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure transfer_parties exists
            if 'transfer_parties' not in sites_data:
                sites_data['transfer_parties'] = ["Advitia Labs"]
                
            with open(self.sites_file, 'w') as f:
                json.dump(sites_data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving sites: {e}")
            return False
    
    def authenticate_user(self, username, password):
        """Authenticate user with username and password
        
        Args:
            username: Username
            password: Password
            
        Returns:
            tuple: (success, role)
        """
        users = self.get_users()
        if username in users:
            user_data = users[username]
            stored_hash = user_data.get('password', '')
            
            # Verify password
            if stored_hash == self.hash_password(password):
                return True, user_data.get('role', 'user')
        
        return False, None
    
    def isAuthenticated(self, username, password):
        """Check if user is authenticated for settings access
        
        Args:
            username: Username
            password: Password
            
        Returns:
            bool: True if authenticated, False otherwise
        """
        users = self.get_users()
        if username in users:
            user_data = users[username]
            stored_hash = user_data.get('password', '')
            
            # Verify password
            if stored_hash == self.hash_password(password):
                return True
        
        return False
    
    def isAdminUser(self, username):
        """Check if user is an admin
        
        Args:
            username: Username
            
        Returns:
            bool: True if admin, False otherwise
        """
        users = self.get_users()
        if username in users:
            user_data = users[username]
            return user_data.get('role', '') == 'admin'
        
        return False
    
    def hash_password(self, password):
        """Hash password using SHA-256
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return hashlib.sha256(password.encode()).hexdigest()
    
    def get_user_name(self, username):
        """Get user's full name
        
        Args:
            username: Username
            
        Returns:
            str: User's full name
        """
        users = self.get_users()
        if username in users:
            return users[username].get('name', username)
        return username
    
    def user_exists(self, username):
        """Check if user exists
        
        Args:
            username: Username
            
        Returns:
            bool: True if user exists, False otherwise
        """
        users = self.get_users()
        return username in users
    
    def site_exists(self, site_name):
        """Check if site exists
        
        Args:
            site_name: Site name
            
        Returns:
            bool: True if site exists, False otherwise
        """
        sites_data = self.get_sites()
        return site_name in sites_data.get('sites', [])
    
    def incharge_exists(self, incharge_name):
        """Check if incharge exists
        
        Args:
            incharge_name: Incharge name
            
        Returns:
            bool: True if incharge exists, False otherwise
        """
        sites_data = self.get_sites()
        return incharge_name in sites_data.get('incharges', [])
    
    def get_all_settings(self):
        """Get all settings
        
        Returns:
            dict: All settings
        """
        try:
            with open(self.settings_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading settings: {e}")
            return {
                "weighbridge": {
                    "com_port": "",
                    "baud_rate": 9600,
                    "data_bits": 8,
                    "parity": "None",
                    "stop_bits": 1.0
                },
                "cameras": {
                    "front_camera_type": "USB",
                    "front_camera_index": 0,
                    "front_rtsp_username": "",
                    "front_rtsp_password": "",
                    "front_rtsp_ip": "",
                    "front_rtsp_port": "554",
                    "front_rtsp_endpoint": "/stream1",
                    "back_camera_type": "USB",
                    "back_camera_index": 1,
                    "back_rtsp_username": "",
                    "back_rtsp_password": "",
                    "back_rtsp_ip": "",
                    "back_rtsp_port": "554",
                    "back_rtsp_endpoint": "/stream1"
                }
            }