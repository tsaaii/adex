import tkinter as tk
from tkinter import ttk, messagebox

import config
from ui_components import HoverButton

class LoginDialog:
    """Login dialog for application authentication"""
    
    def __init__(self, parent, settings_storage, show_select=False):
        """Initialize login dialog
        
        Args:
            parent: Parent window
            settings_storage: Settings storage instance
            show_select: Whether to show user/site selection dropdowns
        """
        self.parent = parent
        self.settings_storage = settings_storage
        self.show_select = show_select
        self.result = False  # Login success flag
        self.role = None  # User role
        self.username = None  # Username
        self.site = None  # Selected site
        
        # Create login window
        self.create_dialog()
    
    def create_dialog(self):
        """Create login dialog UI"""
        # Create top level window
        self.window = tk.Toplevel(self.parent)
        self.window.title("Login - Advitia Labs")
        self.window.geometry("400x350")
        self.window.resizable(False, False)
        self.window.transient(self.parent)  # Make window modal
        self.window.grab_set()  # Make window modal
        
        # Center window
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.parent.winfo_width() // 2) - (width // 2)
        y = (self.parent.winfo_height() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")
        
        # Apply style
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo/Title frame
        logo_frame = ttk.Frame(main_frame)
        logo_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Title
        title_label = ttk.Label(logo_frame, text="Advitia Labs", font=("Segoe UI", 20, "bold"))
        title_label.pack(pady=5)
        
        # Subtitle
        subtitle_label = ttk.Label(logo_frame, text="Weighbridge Management System", font=("Segoe UI", 12))
        subtitle_label.pack(pady=5)
        
        # Form fields
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X, pady=10)
        
        # User selection (only shown if show_select is True)
        if self.show_select:
            # User selection frame
            user_select_frame = ttk.Frame(form_frame)
            user_select_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(user_select_frame, text="User:", font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=5)
            
            # Get users for dropdown
            users = self.settings_storage.get_users()
            usernames = list(users.keys())
            
            self.username_var = tk.StringVar()
            username_combo = ttk.Combobox(user_select_frame, textvariable=self.username_var, 
                                        values=usernames, font=("Segoe UI", 11), width=23)
            username_combo.pack(side=tk.RIGHT, padx=5)
            if usernames:
                username_combo.current(0)
            
            # Site selection frame
            site_select_frame = ttk.Frame(form_frame)
            site_select_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(site_select_frame, text="Site:", font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=5)
            
            # Get sites for dropdown
            sites_data = self.settings_storage.get_sites()
            sites = sites_data.get("sites", ["Guntur"])
            
            self.site_var = tk.StringVar()
            site_combo = ttk.Combobox(site_select_frame, textvariable=self.site_var, 
                                    values=sites, font=("Segoe UI", 11), width=23)
            site_combo.pack(side=tk.RIGHT, padx=5)
            if sites:
                site_combo.current(0)
        else:
            # Username entry
            username_frame = ttk.Frame(form_frame)
            username_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(username_frame, text="Username:", font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=5)
            self.username_var = tk.StringVar()
            username_entry = ttk.Entry(username_frame, textvariable=self.username_var, width=25, font=("Segoe UI", 11))
            username_entry.pack(side=tk.RIGHT, padx=5)
            username_entry.focus_set()  # Set focus to username
        
        # Password
        password_frame = ttk.Frame(form_frame)
        password_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(password_frame, text="Password:", font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=5)
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(password_frame, textvariable=self.password_var, show="*", width=25, font=("Segoe UI", 11))
        password_entry.pack(side=tk.RIGHT, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        login_btn = HoverButton(button_frame, text="Login", 
                              bg=config.COLORS["primary"],
                              fg=config.COLORS["button_text"],
                              font=("Segoe UI", 11, "bold"),
                              padx=15, pady=5,
                              command=self.login)
        login_btn.pack(side=tk.LEFT, padx=5)
        
        exit_btn = HoverButton(button_frame, text="Exit", 
                             bg=config.COLORS["error"],
                             fg=config.COLORS["button_text"],
                             font=("Segoe UI", 11),
                             padx=15, pady=5,
                             command=self.exit_app)
        exit_btn.pack(side=tk.RIGHT, padx=5)
        
        # Status message
        self.status_var = tk.StringVar()
        status_label = ttk.Label(main_frame, textvariable=self.status_var, 
                               foreground="red", font=("Segoe UI", 10))
        status_label.pack(pady=(15, 0))
        
        # Bind Enter key to login
        self.window.bind("<Return>", lambda event: self.login())
        
        # Set default credentials hint
        self.status_var.set("Default admin credentials: admin/admin")
        
        # Wait for window to be destroyed
        self.parent.wait_window(self.window)
    
    def login(self):
        """Handle login"""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        if not username or not password:
            self.status_var.set("Please enter username and password")
            return
        
        # Authenticate
        success, role = self.settings_storage.authenticate_user(username, password)
        
        if success:
            self.result = True
            self.role = role
            self.username = username
            if hasattr(self, 'site_var'):
                self.site = self.site_var.get()
            self.window.destroy()
        else:
            self.status_var.set("Invalid username or password")
    
    def exit_app(self):
        """Exit application"""
        self.result = False
        # Signal to exit application
        self.parent.quit()
        self.window.destroy()