# Enhanced Xbox Color Tracker with improved UI and configuration options
import tkinter.simpledialog
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog
import json
import configparser
import datetime
import threading
import time
import os
from typing import Dict, List, Tuple, Optional
import cv2
import numpy as np
from PIL import Image, ImageTk
import webbrowser
import tempfile
import mss
import pygetwindow as gw

# Import existing components from the original app
from inputs import get_gamepad
import psutil
import vgamepad as vg
import win32gui
import win32api
from ultralytics import YOLO
import pytesseract
import sys
import os


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# ...existing imports and code...
# Constants
MIN_CAPTURE_INTERVAL_MS = 10
MAX_CAPTURE_INTERVAL_MS = 200
DEFAULT_CAPTURE_INTERVAL_MS = 50
MEMORY_WARNING_THRESHOLD = 85
WATCHDOG_TIMEOUT_SECONDS = 10
CRITICAL_MEMORY_THRESHOLD = 95
FPS_UPDATE_INTERVAL = 2.0
CONTROLLER_RECONNECT_INTERVAL = 5.0


class ConfigManager:
    """Manages application configuration and profiles"""

    def __init__(self, config_file="config.json"):
        self.config_file = resource_path(config_file)
        self.profiles = {}
        self.current_profile = "Default"
        self.default_config = {
            "detection": {
                "color_tolerance": 30,
                "contour_threshold": 10,
                "capture_interval": 50,
                "auto_tracking": True,
                "multiple_colors": False,
            },
            "controller": {
                "sensitivity": 0.08,
                "deadzone": 0.2,
                "response_time": 0.01,
                "smoothing": True,
            },
            "performance": {
                "max_fps": 60,
                "memory_limit": 85,
                "quality_preset": "balanced",
            },
            "ui": {"theme": "light", "preview_size": "medium", "show_advanced": False},
        }
        self.load_config()

    def load_config(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
                self.profiles = data.get("profiles", {"Default": self.default_config})
                self.current_profile = data.get("current_profile", "Default")
        except FileNotFoundError:
            self.profiles = {"Default": self.default_config}
            self.save_config()

    def save_config(self):
        """Save configuration to file"""
        data = {"profiles": self.profiles, "current_profile": self.current_profile}
        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_setting(self, category: str, key: str):
        """Get a specific setting value"""
        return self.profiles[self.current_profile].get(category, {}).get(key)

    def set_setting(self, category: str, key: str, value):
        """Set a specific setting value"""
        if category not in self.profiles[self.current_profile]:
            self.profiles[self.current_profile][category] = {}
        self.profiles[self.current_profile][category][key] = value
        self.save_config()


class XboxController:
    """Xbox Controller class from original app"""

    MAX_JOY_VAL = 32767.0
    MAX_TRIG_VAL = 255

    def __init__(self, log_function=None):
        self.log_function = log_function or print
        self.LeftJoystickY = 0
        self.LeftJoystickX = 0
        self.RightJoystickY = 0
        self.RightJoystickX = 0
        self.LeftTrigger = 0
        self.RightTrigger = 0
        self.LeftBumper = 0
        self.RightBumper = 0
        self.A = 0
        self.X = 0
        self.Y = 0
        self.B = 0
        self.LeftThumb = 0
        self.RightThumb = 0
        self.Back = 0
        self.Start = 0
        self.LeftDPad = 0
        self.RightDPad = 0
        self.UpDPad = 0
        self.DownDPad = 0
        self._monitor_thread = None
        self._running = False
        self._last_event_time = time.time()
        self.virtual_controller = vg.VX360Gamepad()

    def log_status(self, message):
        self.log_function(message)

    def is_active(self):
        return time.time() - self._last_event_time < 5.0

    def start_monitoring(self):
        if not self._monitor_thread or not self._monitor_thread.is_alive():
            self._running = True
            self._monitor_thread = threading.Thread(target=self._monitor_controller)
            self._monitor_thread.daemon = True
            self._monitor_thread.start()
            return True
        return False

    def stop_monitoring(self):
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)

    def _monitor_controller(self):
        try:
            while self._running:
                try:
                    events = get_gamepad()
                    if events:
                        self._last_event_time = time.time()
                        for event in events:
                            self._process_event(event)
                except IOError:
                    time.sleep(0.1)
                    continue
        except Exception as e:
            print(f"Controller error: {e}")
            self._running = False

    def _process_event(self, event):
        """Process individual controller events"""
        if event.code == "ABS_X":
            self.LeftJoystickX = event.state / self.MAX_JOY_VAL
        elif event.code == "ABS_Y":
            self.LeftJoystickY = event.state / self.MAX_JOY_VAL
        elif event.code == "BTN_TL":
            self.LeftBumper = event.state
        # Add more event processing as needed

    def simulate_right_stick(self, x_value, y_value):
        x_val_converted = int(x_value * 32767)
        y_val_converted = int(y_value * 32767)
        x_val_converted = max(-32768, min(32767, x_val_converted))
        y_val_converted = max(-32768, min(32767, y_val_converted))
        self.virtual_controller.right_joystick(
            x_value=x_val_converted, y_value=y_val_converted
        )
        self.virtual_controller.update()


class MarkdownViewer:
    """Rich markdown viewer for about section"""

    def __init__(self, parent):
        self.parent = parent
        self.window = None

    def show_about(self):
        """Show the about dialog with rich markdown formatting"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        # Create the about window
        self.window = tk.Toplevel(self.parent)
        self.window.title("About - Xbox Color Tracker Enhanced Edition")
        self.window.geometry("800x600")
        self.window.transient(self.parent)
        self.window.grab_set()

        # Set window icon using the multi-icon .ico file
        try:
            icon_path = os.path.join(
                os.path.dirname(__file__),
                "All_icons_pngs",
                "KT_OD_App_iconV3.1Multi.ico",
            )
            if os.path.exists(icon_path):
                self.window.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error loading about dialog icon: {e}")

        # Create main frame
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header with logo
        self.create_header(main_frame)

        # Content area with scrollbar
        self.create_content_area(main_frame)

        # Button frame
        self.create_button_frame(main_frame)

        # Center the window
        self.center_window()

    def create_header(self, parent):
        """Create the header with logo and title"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        # Try to load and display logo from PNG for header display
        try:
            logo_path = os.path.join(
                os.path.dirname(__file__), "All_icons_pngs", "KT_OD_App_iconV6.png"
            )
            if os.path.exists(logo_path):
                logo_img = Image.open(logo_path)
                logo_img = logo_img.resize((64, 64), Image.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_img)
                logo_label = ttk.Label(header_frame, image=self.logo_photo)
                logo_label.pack(side=tk.LEFT, padx=(0, 10))
            else:
                # Fallback: try to extract from .ico file
                ico_path = os.path.join(
                    os.path.dirname(__file__),
                    "All_icons_pngs",
                    "KT_OD_App_iconV3.1Multi.ico",
                )
                if os.path.exists(ico_path):
                    ico_img = Image.open(ico_path)
                    ico_img = ico_img.resize((64, 64), Image.LANCZOS)
                    self.logo_photo = ImageTk.PhotoImage(ico_img)
                    logo_label = ttk.Label(header_frame, image=self.logo_photo)
                    logo_label.pack(side=tk.LEFT, padx=(0, 10))
        except Exception as e:
            print(f"Error loading header logo: {e}")

        # Title and version
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        title_label = ttk.Label(
            title_frame, text="Xbox Color Tracker", font=("Arial", 16, "bold")
        )
        title_label.pack(anchor=tk.W)

        subtitle_label = ttk.Label(
            title_frame,
            text="Enhanced Edition v2.0 - KT Object Detection System",
            font=("Arial", 10),
        )
        subtitle_label.pack(anchor=tk.W)

        # Separator
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

    def create_content_area(self, parent):
        """Create the scrollable content area"""
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Create text widget with scrollbar
        text_frame = ttk.Frame(content_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.text_widget = tk.Text(
            text_frame,
            wrap=tk.WORD,
            width=80,
            height=25,
            font=("Segoe UI", 10),
            bg="white",
            fg="black",
        )

        scrollbar = ttk.Scrollbar(
            text_frame, orient=tk.VERTICAL, command=self.text_widget.yview
        )
        self.text_widget.configure(yscrollcommand=scrollbar.set)

        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Setup text tags and insert content
        self.setup_text_tags()
        self.insert_formatted_content()
        self.text_widget.configure(state=tk.DISABLED)

    def setup_text_tags(self):
        """Setup text tags for rich formatting"""
        self.text_widget.tag_configure(
            "title", font=("Arial", 14, "bold"), foreground="#0078d4"
        )
        self.text_widget.tag_configure(
            "subtitle", font=("Arial", 12, "bold"), foreground="#333333"
        )
        self.text_widget.tag_configure(
            "header", font=("Arial", 11, "bold"), foreground="#0078d4"
        )

    def insert_formatted_content(self):
        """Insert the formatted about content"""

        self.text_widget.configure(state=tk.NORMAL)

        # Clear existing content
        self.text_widget.delete(1.0, tk.END)

        # Title and Header
        self.text_widget.insert(
            tk.END, "🎮 Xbox Color Tracker - Enhanced Edition\n\n", "title"
        )

        self.text_widget.insert(
            tk.END, "KT Object Detection System v2.0\n\n", "subtitle"
        )

        # Enhanced Description
        self.text_widget.insert(
            tk.END,
            "Professional-grade AI-powered object detection and tracking system with Xbox controller integration. "
            "Features a modern tabbed interface with comprehensive profile management, real-time performance monitoring, "
            "and advanced detection algorithms optimized for gaming automation and accessibility applications.\n\n",
            "header",
        )

        # Key Features Section
        self.text_widget.insert(tk.END, "🎯 Key Features:\n\n", "header")

        feature_list = [
            "🎨 Advanced Color Detection - HSV color space analysis with adjustable tolerance (0-100)",
            "🤖 YOLOv8 AI Detection - Real-time person detection using pre-trained neural network",
            "🖥️ Multi-Source Capture - Screen capture with monitor selection and game window targeting",
            "🎮 Xbox Controller Simulation - Virtual Xbox 360 controller via ViGEm Bus Driver",
            "📊 Real-time Performance Monitoring - CPU usage, memory consumption, and FPS tracking",
            "📁 Advanced Profile Management - Complete CRUD operations with import/export functionality",
            "🔧 Dynamic Controller Status - Real-time Xbox controller connection monitoring",
            "⚙️ Comprehensive Settings - Horizontal/vertical sensitivity, tolerance adjustment, and detection modes",
            "🎯 Sub-pixel Accuracy - Precise target tracking with automatic controller centering",
            "📱 Modern UI - Four-tab interface with real-time status updates and rich about dialog",
            "🔄 Resource Management - Automatic cleanup, memory monitoring, and thread management",
            "📈 Live Statistics - Real-time detection feedback and performance metrics",
        ]

        for feature in feature_list:
            self.text_widget.insert(tk.END, f"• {feature}\n")

        self.text_widget.insert(tk.END, "\n")

        # Application Architecture Section
        self.text_widget.insert(tk.END, "🏗️ Application Architecture:\n\n", "header")

        architecture_info = [
            "📱 Four-Tab Interface: Detection, Controller, Performance, and Profiles",
            "🔧 ConfigManager: JSON-based configuration with resource_path integration",
            "🎮 XboxController: Threading-based controller monitoring with virtual simulation",
            "📊 MarkdownViewer: Rich text about dialog with comprehensive documentation",
            "🎯 EnhancedColorPickerApp: Main application controller with event handling",
            "💾 Profile System: Complete profile management with validation and error handling",
        ]

        for info in architecture_info:
            self.text_widget.insert(tk.END, f"• {info}\n")

        self.text_widget.insert(tk.END, "\n")

        # Technical Specifications
        self.text_widget.insert(tk.END, "⚙️ Technical Specifications:\n\n", "header")

        tech_specs = [
            "🧠 AI Model: YOLOv8n (Nano) - 6.2MB model optimized for real-time inference",
            "📹 Video Processing: OpenCV 4.11.0 with MSS screen capture library",
            "🎮 Controller: vgamepad + ViGEm virtual Xbox 360 controller emulation",
            "🖼️ Image Processing: PIL/Pillow 11.2.1 for image manipulation and display",
            "🔍 Detection: HSV color space analysis with contour detection algorithms",
            "📊 Performance: 20+ FPS color detection, 10+ FPS YOLO detection",
            "💾 Memory: Intelligent garbage collection with psutil monitoring",
            "🔧 Threading: Multi-threaded architecture with daemon threads for stability",
            "💿 Packaging: PyInstaller 6.8.0 with complete dependency bundling",
            "🔒 Resource Management: Automatic temp file cleanup and memory optimization",
        ]

        for spec in tech_specs:
            self.text_widget.insert(tk.END, f"• {spec}\n")

        self.text_widget.insert(tk.END, "\n")

        # Detection Modes Section
        self.text_widget.insert(tk.END, "🎯 Detection Modes:\n\n", "header")

        modes = [
            (
                "🎨 Color Detection Mode",
                "HSV-based color tracking with adjustable tolerance (0-100%). Perfect for tracking crosshairs, "
                "UI elements, or specific colored objects. Features real-time color selection with RGB preview "
                "and automatic contour detection for precise targeting.",
            ),
            (
                "🤖 YOLO AI Detection Mode",
                "Advanced person detection using YOLOv8 Nano neural network. Automatically identifies and tracks "
                "people in real-time with high accuracy. Includes confidence scoring and bounding box detection "
                "for robust tracking in various lighting conditions.",
            ),
            (
                "🎮 Controller Integration",
                "Virtual Xbox 360 controller simulation with customizable sensitivity settings. Features automatic "
                "stick centering, deadzone management, and Left Bumper (LB) activation system for precise control.",
            ),
        ]

        for mode_name, description in modes:
            self.text_widget.insert(tk.END, f"{mode_name}:\n")
            self.text_widget.insert(tk.END, f"   {description}\n\n")

        # Video Sources Section
        self.text_widget.insert(tk.END, "📹 Video Sources:\n\n", "header")

        sources = [
            (
                "🖥️ Screen Capture",
                "Multi-monitor screen capture with individual monitor selection. Supports dynamic monitor "
                "detection and refresh functionality. Optimized for full-screen applications and multi-display "
                "gaming setups with automatic resolution detection.",
            ),
            (
                "🎮 Game Window Capture",
                "Targeted application window capture with automatic window detection. Features live window "
                "refresh and Xbox app integration. Perfect for windowed games and streaming applications "
                "with automatic window resizing support.",
            ),
            (
                "📊 Performance Optimization",
                "Intelligent capture optimization based on system resources. Automatic frame rate adjustment "
                "and memory management to ensure smooth operation across different hardware configurations.",
            ),
        ]

        for source_name, description in sources:
            self.text_widget.insert(tk.END, f"{source_name}:\n")
            self.text_widget.insert(tk.END, f"   {description}\n\n")

        # Profile Management Section
        self.text_widget.insert(tk.END, "📁 Profile Management:\n\n", "header")

        profile_features = [
            "💾 Complete CRUD Operations: Create, Read, Update, Delete profiles with validation",
            "📤 Import/Export: JSON-based profile sharing with error handling and validation",
            "🔄 Profile Switching: Real-time profile switching with automatic settings application",
            "📋 Profile Duplication: One-click profile copying with automatic naming",
            "🛡️ Data Validation: Comprehensive profile structure validation and error recovery",
            "📊 Profile Details: Real-time profile information display with formatted output",
            "🎯 Default Management: Protected default profile with reset functionality",
            "🔧 Settings Integration: Automatic UI synchronization with profile changes",
        ]

        for feature in profile_features:
            self.text_widget.insert(tk.END, f"• {feature}\n")

        self.text_widget.insert(tk.END, "\n")

        # Usage Instructions
        self.text_widget.insert(tk.END, "📖 Quick Start Guide:\n\n", "header")

        instructions = [
            "1️⃣ Select Detection Mode: Choose between Color Detection or YOLO AI Detection",
            "2️⃣ Configure Video Source: Select Screen Capture or Game Window with appropriate settings",
            "3️⃣ Set Target Parameters: Configure color (for Color mode) and tolerance settings",
            "4️⃣ Adjust Controller Sensitivity: Fine-tune horizontal and vertical sensitivity scales",
            "5️⃣ Monitor Performance: Check CPU and memory usage in the Performance tab",
            "6️⃣ Manage Profiles: Save current settings as profiles for different games/applications",
            "7️⃣ Start Detection: Click 'Start Detection' to begin real-time tracking",
            "8️⃣ Controller Activation: Hold Left Bumper (LB) on physical controller to activate movement",
            "9️⃣ Monitor Status: Watch real-time detection feedback and controller connection status",
        ]

        for instruction in instructions:
            self.text_widget.insert(tk.END, f"{instruction}\n")

        self.text_widget.insert(tk.END, "\n")

        # System Requirements
        self.text_widget.insert(tk.END, "💻 System Requirements:\n\n", "header")

        requirements = [
            "🖥️ Operating System: Windows 10/11 (64-bit) with DirectX 11",
            "🧠 Processor: Intel Core i5-8400 / AMD Ryzen 5 2600 or better",
            "💾 Memory: 8GB RAM minimum (16GB recommended for YOLO detection)",
            "🎮 Controller: Xbox One/Series controller (wired or wireless with adapter)",
            "📹 Graphics: DirectX 11 compatible GPU (CUDA optional for AI acceleration)",
            "🔌 Connectivity: USB port for controller, internet for initial model download",
            "💿 Storage: 2GB free disk space (additional space for profiles and logs)",
            "📊 Dependencies: Automatic - all dependencies bundled in executable",
        ]

        for req in requirements:
            self.text_widget.insert(tk.END, f"• {req}\n")

        self.text_widget.insert(tk.END, "\n")

        # Performance Optimization Tips
        self.text_widget.insert(tk.END, "⚡ Performance Optimization:\n\n", "header")

        tips = [
            "🎯 Use Color Detection mode for maximum performance (20+ FPS)",
            "🖥️ Close unnecessary applications to free system resources",
            "📊 Monitor system usage in the Performance tab and adjust accordingly",
            "🎮 Use wired controller connection for lowest input latency",
            "📹 Select specific monitor or window rather than full desktop capture",
            "🔧 Adjust tolerance settings to balance accuracy and performance",
            "💾 Regular profile backups to prevent configuration loss",
            "🔄 Restart application periodically for optimal memory management",
        ]

        for tip in tips:
            self.text_widget.insert(tk.END, f"• {tip}\n")

        self.text_widget.insert(tk.END, "\n")

        # Advanced Features Section
        self.text_widget.insert(tk.END, "🔧 Advanced Features:\n\n", "header")

        advanced_features = [
            "🎨 Dynamic Color Selection: Real-time color picker with RGB preview",
            "📊 Live Performance Metrics: Real-time CPU and memory monitoring",
            "🔄 Auto-refresh Systems: Dynamic monitor and window detection",
            "🎯 Precision Targeting: Sub-pixel accuracy with smoothing algorithms",
            "🛡️ Error Recovery: Comprehensive exception handling and logging",
            "📱 Modern UI: Responsive tabbed interface with status indicators",
            "🔧 Resource Management: Automatic cleanup and thread management",
            "📈 Real-time Feedback: Live detection status and target information",
        ]

        for feature in advanced_features:
            self.text_widget.insert(tk.END, f"• {feature}\n")

        self.text_widget.insert(tk.END, "\n")

        # Troubleshooting Section
        self.text_widget.insert(tk.END, "🔧 Troubleshooting:\n\n", "header")

        troubleshooting = [
            (
                "Controller shows 'Disconnected'",
                "Check USB connection, install Xbox controller drivers, or try different USB port",
            ),
            (
                "High CPU usage during detection",
                "Switch to Color Detection mode, reduce tolerance, or close background applications",
            ),
            (
                "Detection not finding targets",
                "Verify video source selection, check color selection, or adjust tolerance settings",
            ),
            (
                "YOLO model loading errors",
                "Ensure internet connection for initial download, check Windows Defender exclusions",
            ),
            (
                "Application crashes or freezes",
                "Check system resources, restart as administrator, or verify all dependencies",
            ),
            (
                "Profile import/export issues",
                "Verify JSON file format, check file permissions, or try different file location",
            ),
        ]

        for problem, solution in troubleshooting:
            self.text_widget.insert(tk.END, f"❓ {problem}:\n")
            self.text_widget.insert(tk.END, f"   💡 {solution}\n\n")

        # Version Information
        self.text_widget.insert(tk.END, "📋 Version Information:\n\n", "header")

        version_info = [
            "🎮 Application: Xbox Color Tracker Enhanced Edition v2.0",
            "🏢 System: KT Object Detection System",
            "🐍 Python: 3.10.3 with comprehensive dependency management",
            "🔧 Build: PyInstaller 6.8.0 with complete resource bundling",
            "📅 Architecture: Multi-threaded with real-time performance monitoring",
            "🛡️ Security: Local processing with no data transmission",
            "📊 Performance: Optimized for 60+ FPS color detection",
        ]

        for info in version_info:
            self.text_widget.insert(tk.END, f"• {info}\n")

        self.text_widget.insert(tk.END, "\n")

        # Footer
        self.text_widget.insert(tk.END, "🏢 KT Object Detection System\n", "header")
        self.text_widget.insert(
            tk.END, "Enhanced Edition v2.0 - Professional Gaming Automation\n"
        )
        self.text_widget.insert(
            tk.END,
            "Built with Python 3.10, OpenCV 4.11, YOLOv8, and modern UI frameworks\n\n",
        )

        self.text_widget.insert(
            tk.END,
            "For real-time status updates and technical information, monitor the application status bar "
            "and Performance tab. All processing occurs locally for maximum privacy and security.\n\n",
        )

        self.text_widget.insert(
            tk.END,
            "🎯 Designed for accessibility, gaming automation, and professional applications requiring "
            "precise object tracking and controller simulation.\n",
        )

        # Lock the text widget
        self.text_widget.configure(state=tk.DISABLED)

    def create_button_frame(self, parent):
        """Create the button frame"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Close button
        ttk.Button(button_frame, text="Close", command=self.window.destroy).pack(
            side=tk.RIGHT, padx=5
        )

    def center_window(self):
        """Center the window on screen"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")


class EnhancedColorPickerApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Xbox Color Tracker- Enhanced Edition")
        self.master.geometry("1200x800")

        # Set main window icon using the multi-icon .ico file
        try:
            icon_path = os.path.join(
                os.path.dirname(__file__),
                "All_icons_pngs",
                "KT_OD_App_iconV3.1Multi.ico",
            )
            if os.path.exists(icon_path):
                self.master.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error loading main window icon: {e}")

        # Initialize configuration manager
        self.config_manager = ConfigManager()
        self.markdown_viewer = MarkdownViewer(self.master)

        # Initialize basic attributes
        self.target_color = (255, 0, 0)  # Default to red
        self.detection_active = False
        self.yolo_detection_active = False
        self.controller = XboxController(log_function=self.log_status)

        # Initialize detection mode and source variables
        self.detection_mode = None
        self.video_source = None
        self.capture_source = None
        self.monitor_index = 0
        self.target_window = ""

        # Apply theme
        self.setup_theme()

        # Initialize all existing components
        self.init_existing_components()

        # Create enhanced UI
        self.create_enhanced_ui()

        # Start controller monitoring
        self.controller.start_monitoring()

    def log_status(self, message):
        """Enhanced status logging"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"

        # Update status bar
        if hasattr(self, "status_left"):
            self.status_left.config(
                text=message[:50] + "..." if len(message) > 50 else message
            )

        # Log to console
        print(full_message)

    def setup_theme(self):
        """Setup application theme"""
        self.theme = self.config_manager.get_setting("ui", "theme") or "light"
        self.style = ttk.Style()

        if self.theme == "dark":
            self.style.theme_use("clam")
            self.style.configure("TFrame", background="#2d2d2d")
            self.style.configure("TLabel", background="#2d2d2d", foreground="white")
            self.style.configure("TButton", background="#404040", foreground="white")
            self.style.configure(
                "TLabelFrame", background="#2d2d2d", foreground="white"
            )
            self.master.configure(bg="#2d2d2d")
        else:
            self.style.theme_use("winnative")

    def create_enhanced_ui(self):
        """Create the enhanced user interface"""
        # Create main container
        main_container = ttk.Frame(self.master)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create header with logo and about button
        self.create_header(main_container)

        # Create main notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Create tabs
        self.create_detection_tab()
        self.create_controller_tab()
        self.create_performance_tab()
        self.create_profiles_tab()

        # Add status bar
        self.create_status_bar()

        # Start periodic controller status updates
        self.start_controller_monitoring()  # <-- ADDED

    def create_header(self, parent):
        """Create header with logo and about button"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 5))

        # Logo section
        logo_frame = ttk.Frame(header_frame)
        logo_frame.pack(side=tk.LEFT)

        # Try to load logo for header display
        try:
            logo_path = os.path.join(
                os.path.dirname(__file__), "All_icons_pngs", "KT_OD_App_iconV6.png"
            )
            if os.path.exists(logo_path):
                logo_img = Image.open(logo_path)
                logo_img = logo_img.resize((48, 48), Image.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_img)
                logo_label = ttk.Label(logo_frame, image=self.logo_photo)
                logo_label.pack(side=tk.LEFT, padx=(0, 10))
            else:
                # Fallback: try to extract from .ico file
                ico_path = os.path.join(
                    os.path.dirname(__file__),
                    "All_icons_pngs",
                    "KT_OD_App_iconV3.1Multi.ico",
                )
                if os.path.exists(ico_path):
                    ico_img = Image.open(ico_path)
                    ico_img = ico_img.resize((48, 48), Image.LANCZOS)
                    self.logo_photo = ImageTk.PhotoImage(ico_img)
                    logo_label = ttk.Label(logo_frame, image=self.logo_photo)
                    logo_label.pack(side=tk.LEFT, padx=(0, 10))
        except Exception as e:
            print(f"Error loading header logo: {e}")

        # Title
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        title_label = ttk.Label(
            title_frame,
            text="Xbox Color Tracker - Enhanced Edition",
            font=("Arial", 14, "bold"),
        )
        title_label.pack(anchor=tk.W)

        subtitle_label = ttk.Label(
            title_frame, text="KT Object Detection System v2.0", font=("Arial", 9)
        )
        subtitle_label.pack(anchor=tk.W)

        # About button
        about_button = ttk.Button(
            header_frame, text="ℹ️ About", command=self.show_about_dialog
        )
        about_button.pack(side=tk.RIGHT, padx=(10, 0))

        # Separator
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

    def show_about_dialog(self):
        """Show the rich about dialog"""
        self.markdown_viewer.show_about()

    def create_detection_tab(self):
        """Create the main detection tab"""
        detection_frame = ttk.Frame(self.notebook)
        self.notebook.add(detection_frame, text="🎯 Detection")

        # Create paned window for resizable layout
        paned = ttk.PanedWindow(detection_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - Controls
        left_panel = ttk.Frame(paned)
        paned.add(left_panel, weight=2)

        # Right panel - Preview
        right_panel = ttk.Frame(paned)
        paned.add(right_panel, weight=1)

        # Create control sections
        self.create_detection_mode_controls(left_panel)
        self.create_video_source_controls(left_panel)
        self.create_color_controls(left_panel)
        self.create_detection_controls(left_panel)
        self.create_detection_buttons(left_panel)

        # Create enhanced preview
        self.create_enhanced_preview(right_panel)

    def create_detection_mode_controls(self, parent):
        """Create detection mode selection controls"""
        mode_frame = ttk.LabelFrame(parent, text="🎯 Detection Mode", padding="10")
        mode_frame.pack(fill=tk.X, pady=5)

        # Detection mode selection
        self.detection_mode = tk.StringVar(value="color")

        mode_buttons_frame = ttk.Frame(mode_frame)
        mode_buttons_frame.pack(fill=tk.X, pady=2)

        ttk.Radiobutton(
            mode_buttons_frame,
            text="🎨 Color Detection",
            variable=self.detection_mode,
            value="color",
            command=self.on_detection_mode_change,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            mode_buttons_frame,
            text="🤖 YOLO Detection",
            variable=self.detection_mode,
            value="yolo",
            command=self.on_detection_mode_change,
        ).pack(side=tk.LEFT, padx=5)

        # Mode description
        self.mode_description = ttk.Label(
            mode_frame,
            text="Track objects by color similarity",
            font=("Arial", 9),
            foreground="gray",
        )
        self.mode_description.pack(fill=tk.X, pady=2)

    def create_video_source_controls(self, parent):
        """Create video source selection controls"""
        source_frame = ttk.LabelFrame(parent, text="📹 Video Source", padding="10")
        source_frame.pack(fill=tk.X, pady=5)

        # Video source selection
        self.video_source = tk.StringVar(value="screen")

        source_buttons_frame = ttk.Frame(source_frame)
        source_buttons_frame.pack(fill=tk.X, pady=2)

        ttk.Radiobutton(
            source_buttons_frame,
            text="🖥️ Screen",
            variable=self.video_source,
            value="screen",
            command=self.on_video_source_change,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            source_buttons_frame,
            text="🎮 Game Window",
            variable=self.video_source,
            value="window",
            command=self.on_video_source_change,
        ).pack(side=tk.LEFT, padx=5)

        # Source-specific controls
        self.source_controls_frame = ttk.Frame(source_frame)
        self.source_controls_frame.pack(fill=tk.X, pady=5)

        # Initially show screen controls
        self.create_screen_controls()

    def create_screen_controls(self):
        """Create screen capture controls"""
        # Clear existing controls
        for widget in self.source_controls_frame.winfo_children():
            widget.destroy()

        # Monitor selection
        monitor_frame = ttk.Frame(self.source_controls_frame)
        monitor_frame.pack(fill=tk.X, pady=2)

        ttk.Label(monitor_frame, text="Monitor:").pack(side=tk.LEFT)

        self.monitor_var = tk.StringVar()
        self.monitor_combo = ttk.Combobox(
            monitor_frame, textvariable=self.monitor_var, state="readonly", width=20
        )
        self.monitor_combo.pack(side=tk.LEFT, padx=5)

        # Refresh monitors
        ttk.Button(
            monitor_frame, text="🔄 Refresh", command=self.refresh_monitors
        ).pack(side=tk.LEFT, padx=5)

        # Load available monitors
        self.refresh_monitors()

    def create_window_controls(self):
        """Create window capture controls"""
        # Clear existing controls
        for widget in self.source_controls_frame.winfo_children():
            widget.destroy()

        # Window selection
        window_frame = ttk.Frame(self.source_controls_frame)
        window_frame.pack(fill=tk.X, pady=2)

        ttk.Label(window_frame, text="Game Window:").pack(side=tk.LEFT)

        self.window_var = tk.StringVar()
        self.window_combo = ttk.Combobox(
            window_frame, textvariable=self.window_var, state="readonly", width=25
        )
        self.window_combo.pack(side=tk.LEFT, padx=5)

        # Refresh windows
        ttk.Button(window_frame, text="🔄 Refresh", command=self.refresh_windows).pack(
            side=tk.LEFT, padx=5
        )

        # Load available windows
        self.refresh_windows()

    def create_color_controls(self, parent):
        """Create color selection controls"""
        color_frame = ttk.LabelFrame(parent, text="🎨 Color Selection", padding="10")
        color_frame.pack(fill=tk.X, pady=5)

        # Primary color
        primary_frame = ttk.Frame(color_frame)
        primary_frame.pack(fill=tk.X, pady=2)

        ttk.Label(primary_frame, text="Primary Color:").pack(side=tk.LEFT)
        self.primary_color_btn = ttk.Button(
            primary_frame, text="Select", command=lambda: self.select_color("primary")
        )
        self.primary_color_btn.pack(side=tk.LEFT, padx=5)

        self.primary_color_display = tk.Label(
            primary_frame,
            width=5,
            height=1,
            bg="#FF0000",
            relief="solid",
            borderwidth=1,
        )
        self.primary_color_display.pack(side=tk.LEFT, padx=5)

    def create_detection_controls(self, parent):
        """Create detection parameter controls"""
        detection_frame = ttk.LabelFrame(
            parent, text="🔍 Detection Parameters", padding="10"
        )
        detection_frame.pack(fill=tk.X, pady=5)

        # Enhanced tolerance control
        tolerance_frame = ttk.Frame(detection_frame)
        tolerance_frame.pack(fill=tk.X, pady=2)

        ttk.Label(tolerance_frame, text="Color Tolerance:").pack(side=tk.LEFT)

        # Enhanced scale with value display
        scale_frame = ttk.Frame(detection_frame)
        scale_frame.pack(fill=tk.X, pady=2)

        self.tolerance_scale = ttk.Scale(
            scale_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=200,
            command=self.on_tolerance_change,
        )
        self.tolerance_scale.set(30)
        self.tolerance_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.tolerance_value_label = ttk.Label(scale_frame, text="30", width=4)
        self.tolerance_value_label.pack(side=tk.RIGHT)

    def create_detection_buttons(self, parent):
        """Create detection control buttons"""
        button_frame = ttk.LabelFrame(
            parent, text="🎮 Detection Controls", padding="10"
        )
        button_frame.pack(fill=tk.X, pady=5)

        # Main control buttons
        controls_frame = ttk.Frame(button_frame)
        controls_frame.pack(fill=tk.X, pady=2)

        self.start_button = ttk.Button(
            controls_frame, text="▶️ Start Detection", command=self.start_detection
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            controls_frame,
            text="⏹️ Stop Detection",
            command=self.stop_detection,
            state="disabled",
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Status indicators
        status_frame = ttk.Frame(button_frame)
        status_frame.pack(fill=tk.X, pady=5)

        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT)

        self.detection_status = ttk.Label(
            status_frame, text="Stopped", foreground="red", font=("Arial", 9, "bold")
        )
        self.detection_status.pack(side=tk.LEFT, padx=5)

        self.target_info = ttk.Label(
            status_frame,
            text="No target detected",
            foreground="gray",
            font=("Arial", 9),
        )
        self.target_info.pack(side=tk.LEFT, padx=10)

    def create_enhanced_preview(self, parent):
        """Create enhanced preview"""
        preview_frame = ttk.LabelFrame(parent, text="📺 Live Preview", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True)

        # Enhanced canvas
        self.enhanced_canvas = tk.Canvas(
            preview_frame, bg="dark grey", width=300, height=200
        )
        self.enhanced_canvas.pack(fill=tk.BOTH, expand=True)

    def create_controller_tab(self):
        """Create controller configuration tab"""
        controller_frame = ttk.Frame(self.notebook)
        self.notebook.add(controller_frame, text="🎮 Controller")

        # Controller status
        status_frame = ttk.LabelFrame(
            controller_frame, text="Controller Status", padding="10"
        )
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        # Create dynamic status label
        self.controller_status_label = ttk.Label(
            status_frame, text="Status: Checking...", font=("Arial", 10, "bold")
        )
        self.controller_status_label.pack(side=tk.LEFT)

        # Add refresh button
        ttk.Button(
            status_frame, text="🔄 Refresh", command=self.update_controller_status
        ).pack(side=tk.LEFT, padx=10)

        # Sensitivity settings
        sensitivity_frame = ttk.LabelFrame(
            controller_frame, text="Sensitivity Settings", padding="10"
        )
        sensitivity_frame.pack(fill=tk.X, padx=10, pady=5)

        # Horizontal sensitivity
        h_sens_frame = ttk.Frame(sensitivity_frame)
        h_sens_frame.pack(fill=tk.X, pady=2)

        ttk.Label(h_sens_frame, text="Horizontal Sensitivity:").pack(side=tk.LEFT)
        self.h_sensitivity_scale = ttk.Scale(
            h_sens_frame, from_=0.01, to=0.2, orient=tk.HORIZONTAL, length=200
        )
        self.h_sensitivity_scale.set(0.08)
        self.h_sensitivity_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.h_sens_value = ttk.Label(h_sens_frame, text="0.08", width=6)
        self.h_sens_value.pack(side=tk.RIGHT)

        # Initial status update
        self.update_controller_status()

    def update_controller_status(self):
        """Update controller status display"""
        try:
            # Check if controller is actually connected
            is_connected = self.check_controller_connection()

            if is_connected:
                self.controller_status_label.config(
                    text="Status: Connected ✅", foreground="green"
                )
            else:
                self.controller_status_label.config(
                    text="Status: Disconnected ❌", foreground="red"
                )

        except Exception as e:
            self.controller_status_label.config(
                text="Status: Error", foreground="orange"
            )
            self.log_status(f"Error checking controller status: {e}")

    def check_controller_connection(self):
        """Check if Xbox controller is actually connected"""
        try:
            # Method 1: Try to get gamepad input (non-blocking)

            # Try to create a gamepad instance
            try:
                test_events = get_gamepad()
                return True
            except Exception:
                return False

        except Exception as e:
            # Method 2: Check if controller thread is active and receiving data
            if hasattr(self, "controller") and self.controller:
                return self.controller.is_active()
            return False

    def start_controller_monitoring(self):
        """Start periodic controller status updates"""

        def monitor_loop():
            while True:
                try:
                    # Update status every 2 seconds
                    self.master.after(0, self.update_controller_status)
                    time.sleep(2)
                except Exception as e:
                    self.log_status(f"Controller monitoring error: {e}")
                    time.sleep(5)

        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()

    def create_performance_tab(self):
        """Create performance monitoring tab"""
        perf_frame = ttk.Frame(self.notebook)
        self.notebook.add(perf_frame, text="⚡ Performance")

        # Performance metrics
        metrics_frame = ttk.LabelFrame(perf_frame, text="System Metrics", padding="10")
        metrics_frame.pack(fill=tk.X, padx=10, pady=5)

        # Add performance metrics display
        self.cpu_label = ttk.Label(metrics_frame, text="CPU Usage: 0%")
        self.cpu_label.pack(fill=tk.X, pady=2)

        self.memory_label = ttk.Label(metrics_frame, text="Memory Usage: 0%")
        self.memory_label.pack(fill=tk.X, pady=2)

        # Start periodic performance updates
        self.update_performance_metrics()  # <-- ADDED

    def create_enhanced_ui(self):
        """Create the enhanced user interface"""
        # Create main container
        main_container = ttk.Frame(self.master)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create header with logo and about button
        self.create_header(main_container)

        # Create main notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Create tabs
        self.create_detection_tab()
        self.create_controller_tab()
        self.create_performance_tab()
        self.create_profiles_tab()

        # Add status bar
        self.create_status_bar()

        # Start periodic controller status updates
        self.start_controller_monitoring()  # <-- ADDED

    # ...existing methods...

    def update_performance_metrics(self):
        """Update CPU and memory usage labels every second"""
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            mem_percent = psutil.virtual_memory().percent
            self.cpu_label.config(text=f"CPU Usage: {cpu_percent}%")
            self.memory_label.config(text=f"Memory Usage: {mem_percent}%")
        except Exception as e:
            self.log_status(f"Error updating performance metrics: {e}")
        # Schedule next update
        self.master.after(1000, self.update_performance_metrics)

    def create_profiles_tab(self):
        """Create profiles management tab"""
        profiles_frame = ttk.Frame(self.notebook)
        self.notebook.add(profiles_frame, text="📁 Profiles")

        # Profile selection
        selection_frame = ttk.LabelFrame(
            profiles_frame, text="Profile Selection", padding="10"
        )
        selection_frame.pack(fill=tk.X, padx=10, pady=5)

        profile_frame = ttk.Frame(selection_frame)
        profile_frame.pack(fill=tk.X)

        ttk.Label(profile_frame, text="Current Profile:").pack(side=tk.LEFT)
        self.current_profile_var = tk.StringVar(
            value=self.config_manager.current_profile
        )
        self.profile_combo = ttk.Combobox(
            profile_frame,
            textvariable=self.current_profile_var,
            values=list(self.config_manager.profiles.keys()),
            state="readonly",
            width=20,
        )
        self.profile_combo.pack(side=tk.LEFT, padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_change)

        # Load profile button
        ttk.Button(
            profile_frame, text="📂 Load Profile", command=self.load_profile
        ).pack(side=tk.LEFT, padx=5)

        # Profile Management Section
        management_frame = ttk.LabelFrame(
            profiles_frame, text="Profile Management", padding="10"
        )
        management_frame.pack(fill=tk.X, padx=10, pady=5)

        # Save current settings as new profile
        save_frame = ttk.Frame(management_frame)
        save_frame.pack(fill=tk.X, pady=5)

        ttk.Label(save_frame, text="Save Current Settings As:").pack(side=tk.LEFT)
        self.new_profile_name = tk.StringVar()
        self.profile_name_entry = ttk.Entry(
            save_frame, textvariable=self.new_profile_name, width=20
        )
        self.profile_name_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(save_frame, text="💾 Save Profile", command=self.save_profile).pack(
            side=tk.LEFT, padx=5
        )

        # Profile operations
        operations_frame = ttk.Frame(management_frame)
        operations_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            operations_frame, text="📝 Rename Profile", command=self.rename_profile
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            operations_frame, text="🗑️ Delete Profile", command=self.delete_profile
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            operations_frame,
            text="📋 Duplicate Profile",
            command=self.duplicate_profile,
        ).pack(side=tk.LEFT, padx=5)

        # Profile Details Section
        details_frame = ttk.LabelFrame(
            profiles_frame, text="Profile Details", padding="10"
        )
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create text widget for profile details
        self.profile_details_text = tk.Text(
            details_frame,
            height=10,
            width=50,
            font=("Courier", 9),
            bg="white",
            fg="black",
            state=tk.DISABLED,
        )

        # Add scrollbar for profile details
        details_scrollbar = ttk.Scrollbar(
            details_frame, orient=tk.VERTICAL, command=self.profile_details_text.yview
        )
        self.profile_details_text.configure(yscrollcommand=details_scrollbar.set)

        self.profile_details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Import/Export Section
        import_export_frame = ttk.LabelFrame(
            profiles_frame, text="Import/Export", padding="10"
        )
        import_export_frame.pack(fill=tk.X, padx=10, pady=5)

        ie_buttons_frame = ttk.Frame(import_export_frame)
        ie_buttons_frame.pack(fill=tk.X)

        ttk.Button(
            ie_buttons_frame, text="📥 Import Profile", command=self.import_profile
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            ie_buttons_frame, text="📤 Export Profile", command=self.export_profile
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            ie_buttons_frame, text="🔄 Reset to Default", command=self.reset_to_default
        ).pack(side=tk.LEFT, padx=5)

        # Update profile details display
        self.update_profile_details()

    def on_profile_change(self, event=None):
        """Handle profile selection change"""
        try:
            selected_profile = self.current_profile_var.get()
            if selected_profile and selected_profile in self.config_manager.profiles:
                self.config_manager.current_profile = selected_profile
                self.config_manager.save_config()
                self.load_profile_settings()
                self.update_profile_details()
                self.log_status(f"Switched to profile: {selected_profile}")
        except Exception as e:
            self.log_status(f"Error changing profile: {e}")

    def load_profile(self):
        """Load the selected profile"""
        try:
            selected_profile = self.current_profile_var.get()
            if selected_profile and selected_profile in self.config_manager.profiles:
                self.config_manager.current_profile = selected_profile
                self.config_manager.save_config()
                self.load_profile_settings()
                self.update_profile_details()
                self.log_status(f"Loaded profile: {selected_profile}")
                messagebox.showinfo(
                    "Profile Loaded",
                    f"Profile '{selected_profile}' loaded successfully!",
                )
            else:
                messagebox.showwarning(
                    "Load Profile", "Please select a valid profile to load."
                )
        except Exception as e:
            self.log_status(f"Error loading profile: {e}")
            messagebox.showerror("Error", f"Failed to load profile: {e}")

    def save_profile(self):
        """Save current settings as a new profile"""
        try:
            profile_name = self.new_profile_name.get().strip()
            if not profile_name:
                messagebox.showwarning("Save Profile", "Please enter a profile name.")
                return

            # Check if profile already exists
            if profile_name in self.config_manager.profiles:
                result = messagebox.askyesno(
                    "Profile Exists",
                    f"Profile '{profile_name}' already exists. Overwrite?",
                )
                if not result:
                    return

            # Collect current settings
            current_settings = {
                "detection": {
                    "color_tolerance": int(self.tolerance_scale.get()),
                    "contour_threshold": 10,
                    "capture_interval": 50,
                    "auto_tracking": True,
                    "multiple_colors": False,
                    "detection_mode": self.detection_mode.get(),
                    "video_source": self.video_source.get(),
                    "target_color": self.target_color,
                },
                "controller": {
                    "sensitivity": self.h_sensitivity_scale.get(),
                    "deadzone": 0.2,
                    "response_time": 0.01,
                    "smoothing": True,
                },
                "performance": {
                    "max_fps": 60,
                    "memory_limit": 85,
                    "quality_preset": "balanced",
                },
                "ui": {
                    "theme": self.theme,
                    "preview_size": "medium",
                    "show_advanced": False,
                },
            }

            # Save profile
            self.config_manager.profiles[profile_name] = current_settings
            self.config_manager.save_config()

            # Update UI
            self.profile_combo["values"] = list(self.config_manager.profiles.keys())
            self.current_profile_var.set(profile_name)
            self.config_manager.current_profile = profile_name
            self.new_profile_name.set("")
            self.update_profile_details()

            self.log_status(f"Profile '{profile_name}' saved successfully")
            messagebox.showinfo(
                "Profile Saved", f"Profile '{profile_name}' saved successfully!"
            )

        except Exception as e:
            self.log_status(f"Error saving profile: {e}")
            messagebox.showerror("Error", f"Failed to save profile: {e}")

    def rename_profile(self):
        """Rename the current profile"""
        try:
            current_name = self.current_profile_var.get()
            if current_name == "Default":
                messagebox.showwarning(
                    "Rename Profile", "Cannot rename the Default profile."
                )
                return

            # Get new name from user
            new_name = tk.simpledialog.askstring(
                "Rename Profile",
                f"Enter new name for profile '{current_name}':",
                initialvalue=current_name,
            )

            if not new_name or new_name.strip() == "":
                return

            new_name = new_name.strip()
            if new_name == current_name:
                return

            if new_name in self.config_manager.profiles:
                messagebox.showwarning(
                    "Rename Profile", f"Profile '{new_name}' already exists."
                )
                return

            # Rename profile
            self.config_manager.profiles[new_name] = self.config_manager.profiles[
                current_name
            ]
            del self.config_manager.profiles[current_name]
            self.config_manager.current_profile = new_name
            self.config_manager.save_config()

            # Update UI
            self.profile_combo["values"] = list(self.config_manager.profiles.keys())
            self.current_profile_var.set(new_name)
            self.update_profile_details()

            self.log_status(f"Profile renamed from '{current_name}' to '{new_name}'")
            messagebox.showinfo(
                "Profile Renamed", f"Profile renamed to '{new_name}' successfully!"
            )

        except Exception as e:
            self.log_status(f"Error renaming profile: {e}")
            messagebox.showerror("Error", f"Failed to rename profile: {e}")

    def delete_profile(self):
        """Delete the selected profile"""
        try:
            profile_name = self.current_profile_var.get()
            if profile_name == "Default":
                messagebox.showwarning(
                    "Delete Profile", "Cannot delete the Default profile."
                )
                return

            if len(self.config_manager.profiles) <= 1:
                messagebox.showwarning(
                    "Delete Profile", "Cannot delete the last profile."
                )
                return

            # Confirm deletion
            result = messagebox.askyesno(
                "Delete Profile",
                f"Are you sure you want to delete profile '{profile_name}'?\nThis action cannot be undone.",
            )
            if not result:
                return

            # Delete profile
            del self.config_manager.profiles[profile_name]

            # Switch to Default profile
            self.config_manager.current_profile = "Default"
            self.config_manager.save_config()

            # Update UI
            self.profile_combo["values"] = list(self.config_manager.profiles.keys())
            self.current_profile_var.set("Default")
            self.load_profile_settings()
            self.update_profile_details()

            self.log_status(f"Profile '{profile_name}' deleted")
            messagebox.showinfo(
                "Profile Deleted", f"Profile '{profile_name}' deleted successfully!"
            )

        except Exception as e:
            self.log_status(f"Error deleting profile: {e}")
            messagebox.showerror("Error", f"Failed to delete profile: {e}")

    def duplicate_profile(self):
        """Duplicate the current profile"""
        try:
            current_name = self.current_profile_var.get()
            new_name = tk.simpledialog.askstring(
                "Duplicate Profile",
                f"Enter name for duplicate of '{current_name}':",
                initialvalue=f"{current_name}_copy",
            )

            if not new_name or new_name.strip() == "":
                return

            new_name = new_name.strip()
            if new_name in self.config_manager.profiles:
                messagebox.showwarning(
                    "Duplicate Profile", f"Profile '{new_name}' already exists."
                )
                return

            # Duplicate profile
            self.config_manager.profiles[new_name] = self.config_manager.profiles[
                current_name
            ].copy()
            self.config_manager.save_config()

            # Update UI
            self.profile_combo["values"] = list(self.config_manager.profiles.keys())
            self.current_profile_var.set(new_name)
            self.config_manager.current_profile = new_name
            self.update_profile_details()

            self.log_status(f"Profile '{current_name}' duplicated as '{new_name}'")
            messagebox.showinfo(
                "Profile Duplicated",
                f"Profile duplicated as '{new_name}' successfully!",
            )

        except Exception as e:
            self.log_status(f"Error duplicating profile: {e}")
            messagebox.showerror("Error", f"Failed to duplicate profile: {e}")

    def import_profile(self):
        """Import profile from file"""
        try:
            file_path = filedialog.askopenfilename(
                title="Import Profile",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            )
            if not file_path:
                return

            with open(file_path, "r") as f:
                profile_data = json.load(f)

            # Validate profile structure
            required_keys = ["detection", "controller", "performance", "ui"]
            if not all(key in profile_data for key in required_keys):
                messagebox.showerror("Import Error", "Invalid profile file format.")
                return

            # Get profile name
            profile_name = tk.simpledialog.askstring(
                "Import Profile",
                "Enter name for imported profile:",
                initialvalue=os.path.splitext(os.path.basename(file_path))[0],
            )

            if not profile_name or profile_name.strip() == "":
                return

            profile_name = profile_name.strip()
            if profile_name in self.config_manager.profiles:
                result = messagebox.askyesno(
                    "Profile Exists",
                    f"Profile '{profile_name}' already exists. Overwrite?",
                )
                if not result:
                    return

            # Import profile
            self.config_manager.profiles[profile_name] = profile_data
            self.config_manager.save_config()

            # Update UI
            self.profile_combo["values"] = list(self.config_manager.profiles.keys())
            self.current_profile_var.set(profile_name)
            self.config_manager.current_profile = profile_name
            self.load_profile_settings()
            self.update_profile_details()

            self.log_status(f"Profile '{profile_name}' imported successfully")
            messagebox.showinfo(
                "Profile Imported", f"Profile '{profile_name}' imported successfully!"
            )

        except Exception as e:
            self.log_status(f"Error importing profile: {e}")
            messagebox.showerror("Error", f"Failed to import profile: {e}")

    def export_profile(self):
        """Export current profile to file"""
        try:
            profile_name = self.current_profile_var.get()
            file_path = filedialog.asksaveasfilename(
                title="Export Profile",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialvalue=f"{profile_name}.json",
            )
            if not file_path:
                return

            profile_data = self.config_manager.profiles[profile_name]
            with open(file_path, "w") as f:
                json.dump(profile_data, f, indent=2)

            self.log_status(f"Profile '{profile_name}' exported to {file_path}")
            messagebox.showinfo(
                "Profile Exported", f"Profile '{profile_name}' exported successfully!"
            )

        except Exception as e:
            self.log_status(f"Error exporting profile: {e}")
            messagebox.showerror("Error", f"Failed to export profile: {e}")

    def reset_to_default(self):
        """Reset current profile to default settings"""
        try:
            result = messagebox.askyesno(
                "Reset to Default",
                "Reset current profile to default settings?\nThis will overwrite all current settings.",
            )
            if not result:
                return

            profile_name = self.current_profile_var.get()
            self.config_manager.profiles[profile_name] = (
                self.config_manager.default_config.copy()
            )
            self.config_manager.save_config()

            self.load_profile_settings()
            self.update_profile_details()

            self.log_status(f"Profile '{profile_name}' reset to default settings")
            messagebox.showinfo(
                "Reset Complete", f"Profile '{profile_name}' reset to default settings!"
            )

        except Exception as e:
            self.log_status(f"Error resetting profile: {e}")
            messagebox.showerror("Error", f"Failed to reset profile: {e}")

    def load_profile_settings(self):
        """Load settings from current profile into UI"""
        try:
            profile = self.config_manager.profiles[self.config_manager.current_profile]

            # Load detection settings
            detection = profile.get("detection", {})
            if "color_tolerance" in detection:
                self.tolerance_scale.set(detection["color_tolerance"])
            if "detection_mode" in detection:
                self.detection_mode.set(detection["detection_mode"])
            if "video_source" in detection:
                self.video_source.set(detection["video_source"])
            if "target_color" in detection:
                self.target_color = detection["target_color"]
                # Update color display
                hex_color = "#{:02x}{:02x}{:02x}".format(*self.target_color)
                self.primary_color_display.config(bg=hex_color)

            # Load controller settings
            controller = profile.get("controller", {})
            if "sensitivity" in controller:
                self.h_sensitivity_scale.set(controller["sensitivity"])

            # Update UI components
            self.on_detection_mode_change()
            self.on_video_source_change()

            self.log_status(
                f"Profile settings loaded: {self.config_manager.current_profile}"
            )

        except Exception as e:
            self.log_status(f"Error loading profile settings: {e}")

    def update_profile_details(self):
        """Update the profile details display"""
        try:
            profile_name = self.current_profile_var.get()
            if profile_name not in self.config_manager.profiles:
                return

            profile = self.config_manager.profiles[profile_name]

            # Format profile details
            details = f"Profile: {profile_name}\n"
            details += "=" * 50 + "\n\n"

            # Detection settings
            details += "🎯 Detection Settings:\n"
            detection = profile.get("detection", {})
            details += f"  • Mode: {detection.get('detection_mode', 'N/A')}\n"
            details += f"  • Video Source: {detection.get('video_source', 'N/A')}\n"
            details += (
                f"  • Color Tolerance: {detection.get('color_tolerance', 'N/A')}\n"
            )
            details += f"  • Target Color: {detection.get('target_color', 'N/A')}\n\n"

            # Controller settings
            details += "🎮 Controller Settings:\n"
            controller = profile.get("controller", {})
            details += f"  • Sensitivity: {controller.get('sensitivity', 'N/A')}\n"
            details += f"  • Deadzone: {controller.get('deadzone', 'N/A')}\n"
            details += f"  • Response Time: {controller.get('response_time', 'N/A')}\n"
            details += f"  • Smoothing: {controller.get('smoothing', 'N/A')}\n\n"

            # Performance settings
            details += "⚡ Performance Settings:\n"
            performance = profile.get("performance", {})
            details += f"  • Max FPS: {performance.get('max_fps', 'N/A')}\n"
            details += f"  • Memory Limit: {performance.get('memory_limit', 'N/A')}%\n"
            details += (
                f"  • Quality Preset: {performance.get('quality_preset', 'N/A')}\n\n"
            )

            # UI settings
            details += "🖥️ UI Settings:\n"
            ui = profile.get("ui", {})
            details += f"  • Theme: {ui.get('theme', 'N/A')}\n"
            details += f"  • Preview Size: {ui.get('preview_size', 'N/A')}\n"
            details += f"  • Show Advanced: {ui.get('show_advanced', 'N/A')}\n"

            # Update text widget
            self.profile_details_text.config(state=tk.NORMAL)
            self.profile_details_text.delete(1.0, tk.END)
            self.profile_details_text.insert(tk.END, details)
            self.profile_details_text.config(state=tk.DISABLED)

        except Exception as e:
            self.log_status(f"Error updating profile details: {e}")

    def create_status_bar(self):
        """Create enhanced status bar"""
        self.status_bar = ttk.Frame(self.master)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Status sections
        self.status_left = ttk.Label(self.status_bar, text="Ready")
        self.status_left.pack(side=tk.LEFT, padx=5)

        # Add separator
        ttk.Separator(self.status_bar, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=2)

    # Event handlers
    def on_detection_mode_change(self):
        """Handle detection mode change"""
        mode = self.detection_mode.get()
        descriptions = {
            "color": "Track objects by color similarity",
            "yolo": "AI-powered object detection (people, cars, etc.)",
        }
        self.mode_description.config(text=descriptions.get(mode, ""))
        self.log_status(f"Detection mode changed to: {mode}")

    def on_video_source_change(self):
        """Handle video source change"""
        source = self.video_source.get()

        if source == "screen":
            self.create_screen_controls()
        elif source == "window":
            self.create_window_controls()

        self.log_status(f"Video source changed to: {source}")

    def refresh_monitors(self):
        """Refresh the list of available monitors"""
        try:
            with mss.mss() as sct:
                monitors = sct.monitors[1:]  # Skip the "All in One" monitor
                monitor_list = []
                for i, monitor in enumerate(monitors):
                    monitor_list.append(
                        f"Monitor {i+1} ({monitor['width']}x{monitor['height']})"
                    )

                self.monitor_combo["values"] = monitor_list
                if monitor_list:
                    self.monitor_combo.set(monitor_list[0])

                self.log_status(f"Found {len(monitor_list)} monitors")
        except Exception as e:
            self.log_status(f"Error refreshing monitors: {e}")

    def refresh_windows(self):
        """Refresh the list of available windows"""
        try:
            windows = gw.getAllWindows()
            window_list = []
            for window in windows:
                if (
                    window.title
                    and len(window.title) > 0
                    and window.width > 100
                    and window.height > 100
                ):
                    window_list.append(f"{window.title}")

            self.window_combo["values"] = window_list
            if window_list:
                self.window_combo.set(window_list[0])

            self.log_status(f"Found {len(window_list)} windows")
        except Exception as e:
            self.log_status(f"Error refreshing windows: {e}")

    def select_color(self, color_type):
        """Enhanced color selection with preview"""
        try:
            color_code, hex_code = colorchooser.askcolor(
                title=f"Select {color_type.title()} Color"
            )
            if color_code:
                r, g, b = int(color_code[0]), int(color_code[1]), int(color_code[2])
                if color_type == "primary":
                    self.target_color = (r, g, b)
                    self.primary_color_display.config(bg=hex_code)
                    self.log_status(f"Primary color set to RGB: {self.target_color}")
        except Exception as e:
            self.log_status(f"Error selecting {color_type} color: {e}")

    def on_tolerance_change(self, value):
        """Handle tolerance scale changes"""
        int_value = int(float(value))
        self.tolerance_value_label.config(text=str(int_value))

    def start_detection(self):
        """Start the detection process"""
        try:
            mode = self.detection_mode.get()
            source = self.video_source.get()

            # Initialize capture based on source
            if not self.initialize_capture_source():
                self.log_status("Failed to initialize capture source")
                return

            self.detection_active = True
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.detection_status.config(text="Running", foreground="green")

            # Start appropriate detection based on mode
            if mode == "color":
                self.start_color_detection()
            elif mode == "yolo":
                self.start_yolo_detection()

            self.log_status(f"Detection started - Mode: {mode}, Source: {source}")
        except Exception as e:
            self.log_status(f"Error starting detection: {e}")
            self.stop_detection()

    def stop_detection(self):
        """Stop the detection process"""
        try:
            self.detection_active = False
            self.yolo_detection_active = False

            # Release capture resources
            if hasattr(self, "capture_source") and self.capture_source:
                if hasattr(self.capture_source, "release"):
                    self.capture_source.release()
                self.capture_source = None

            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.detection_status.config(text="Stopped", foreground="red")
            self.target_info.config(text="No target detected")

            # Reset controller
            if hasattr(self, "controller"):
                self.controller.simulate_right_stick(0, 0)

            # Thread cleanup: join detection thread if running
            if (
                hasattr(self, "detection_thread")
                and self.detection_thread
                and self.detection_thread.is_alive()
            ):
                self.detection_thread.join(timeout=1.0)

            self.log_status("Detection stopped")
        except Exception as e:
            self.log_status(f"Error stopping detection: {e}")

    def initialize_capture_source(self):
        """Initialize the capture source based on selection"""
        try:
            source = self.video_source.get()

            if source == "screen":
                # Initialize screen capture
                self.capture_source = "screen"
                monitor_selection = self.monitor_var.get()
                if monitor_selection:
                    # Extract monitor number from selection
                    import re

                    match = re.search(r"Monitor (\d+)", monitor_selection)
                    if match:
                        self.monitor_index = int(match.group(1)) - 1
                    else:
                        self.monitor_index = 0
                else:
                    self.monitor_index = 0
                return True

            elif source == "window":
                # Initialize window capture
                self.capture_source = "window"
                window_title = self.window_var.get()
                if window_title:
                    self.target_window = window_title
                    return True
                else:
                    self.log_status("No window selected")
                    return False

            return False

        except Exception as e:
            self.log_status(f"Error initializing capture source: {e}")
            return False

    def start_color_detection(self):
        """Start color-based detection"""

        def color_detection_loop():
            while self.detection_active:
                try:
                    # Capture frame based on source
                    frame = self.capture_frame()
                    if frame is None:
                        continue

                    # Perform color detection
                    target_found, center_x, center_y = self.detect_color(frame)

                    if target_found:
                        # Calculate controller input
                        stick_x, stick_y = self.calculate_controller_input(
                            center_x, center_y, frame.shape
                        )

                        # Update UI
                        self.master.after(
                            0,
                            lambda: self.update_detection_ui(
                                f"Color detected at ({center_x}, {center_y})", True
                            ),
                        )

                        # Move controller if LB is pressed
                        if (
                            hasattr(self.controller, "LeftBumper")
                            and self.controller.LeftBumper
                        ):
                            self.controller.simulate_right_stick(stick_x, stick_y)
                    else:
                        # No target found
                        self.master.after(
                            0,
                            lambda: self.update_detection_ui(
                                "No color target detected", False
                            ),
                        )
                        self.controller.simulate_right_stick(0, 0)

                    # Control loop timing
                    time.sleep(0.05)  # 20 FPS

                except Exception as e:
                    self.log_status(f"Error in color detection: {e}")
                    time.sleep(0.1)

        # Start detection thread
        self.detection_thread = threading.Thread(
            target=color_detection_loop, daemon=True
        )
        self.detection_thread.start()

    def start_yolo_detection(self):
        """Start YOLO-based detection"""
        if not self.yolo_model:
            self.log_status("YOLO model not available")
            return

        self.yolo_detection_active = True

        def yolo_detection_loop():
            while self.yolo_detection_active:
                try:
                    # Capture frame
                    frame = self.capture_frame()
                    if frame is None:
                        continue

                    # Run YOLO detection
                    results = self.yolo_model(frame)

                    # Process results for person detection
                    person_detections = []
                    for result in results:
                        boxes = result.boxes
                        if boxes is not None:
                            for box in boxes:
                                if box.cls[0] == 0:  # Person class
                                    person_detections.append(box)

                    if person_detections:
                        # Use the first (most confident) detection
                        box = person_detections[0]
                        x1, y1, x2, y2 = box.xyxy[0]
                        center_x = int((x1 + x2) / 2)
                        center_x = int((x1 + x2) / 2)
                        center_y = int((y1 + y2) / 2)

                        # Calculate controller input
                        stick_x, stick_y = self.calculate_controller_input(
                            center_x, center_y, frame.shape
                        )

                        # Update UI
                        self.master.after(
                            0,
                            lambda: self.update_detection_ui(
                                f"Person detected at ({center_x}, {center_y})", True
                            ),
                        )

                        # Move controller if LB is pressed
                        if (
                            hasattr(self.controller, "LeftBumper")
                            and self.controller.LeftBumper
                        ):
                            self.controller.simulate_right_stick(stick_x, stick_y)
                    else:
                        # No person detected
                        self.master.after(
                            0,
                            lambda: self.update_detection_ui(
                                "No person detected", False
                            ),
                        )
                        self.controller.simulate_right_stick(0, 0)

                    time.sleep(0.1)  # 10 FPS for YOLO

                except Exception as e:
                    self.log_status(f"Error in YOLO detection: {e}")
                    time.sleep(0.1)

        # Start detection thread
        self.detection_thread = threading.Thread(
            target=yolo_detection_loop, daemon=True
        )
        self.detection_thread.start()

    def capture_frame(self):
        """Capture a frame from the selected source"""
        try:
            if self.capture_source == "screen":
                # Screen capture
                with mss.mss() as sct:
                    monitor = sct.monitors[self.monitor_index + 1]
                    screenshot = sct.grab(monitor)
                    frame = np.array(screenshot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    return frame

            elif self.capture_source == "window":
                # Window capture
                try:
                    window = gw.getWindowsWithTitle(self.target_window)[0]
                    if window:
                        bbox = (window.left, window.top, window.right, window.bottom)
                        with mss.mss() as sct:
                            screenshot = sct.grab(bbox)
                            frame = np.array(screenshot)
                            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                            return frame
                except IndexError:
                    self.log_status(f"Window '{self.target_window}' not found")
                    return None

            return None

        except Exception as e:
            self.log_status(f"Error capturing frame: {e}")
            return None

    def detect_color(self, frame):
        """Detect target color in frame"""
        try:
            # Convert to HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Create color range
            target_bgr = np.array(
                [[[self.target_color[2], self.target_color[1], self.target_color[0]]]],
                dtype=np.uint8,
            )
            target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)[0][0]

            tolerance = int(self.tolerance_scale.get())

            # Create mask
            lower_bound = np.array([max(0, target_hsv[0] - tolerance), 50, 50])
            upper_bound = np.array([min(179, target_hsv[0] + tolerance), 255, 255])
            mask = cv2.inRange(hsv, lower_bound, upper_bound)

            # Find contours
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if contours:
                # Find largest contour
                largest_contour = max(contours, key=cv2.contourArea)

                # Get center
                M = cv2.moments(largest_contour)
                if M["m00"] != 0:
                    center_x = int(M["m10"] / M["m00"])
                    center_y = int(M["m01"] / M["m00"])
                    return True, center_x, center_y

            return False, 0, 0

        except Exception as e:
            self.log_status(f"Error in color detection: {e}")
            return False, 0, 0

    def calculate_controller_input(self, target_x, target_y, frame_shape):
        """Calculate controller input based on target position"""
        try:
            height, width = frame_shape[:2]

            # Calculate center offset
            center_x = width / 2
            center_y = height / 2

            # Calculate normalized offset
            offset_x = (target_x - center_x) / center_x
            offset_y = (target_y - center_y) / center_y

            # Apply sensitivity
            sensitivity = self.h_sensitivity_scale.get()
            stick_x = offset_x * sensitivity
            stick_y = offset_y * sensitivity

            # Clamp values
            stick_x = max(-1.0, min(1.0, stick_x))
            stick_y = max(-1.0, min(1.0, stick_y))

            return stick_x, stick_y

        except Exception as e:
            self.log_status(f"Error calculating controller input: {e}")
            return 0, 0

    def update_detection_ui(self, message, target_found):
        """Update the detection UI with current status"""
        try:
            self.target_info.config(
                text=message, foreground="green" if target_found else "gray"
            )
        except Exception as e:
            self.log_status(f"Error updating UI: {e}")

    def init_existing_components(self):
        """Initialize existing components from the original app"""
        # Initialize variables that might be referenced
        self.monitors = []
        self.detection_thread = None
        self.last_status_update = 0
        self.status_update_interval = 0.5
        self.process = psutil.Process(os.getpid())
        self.capture_source = None
        self.monitor_index = 0
        self.target_window = ""

        # Initialize threading lock
        self.lock = threading.Lock()

        # Initialize YOLO model if available
        try:
            self.yolo_model = YOLO(resource_path("yolov8n.pt"))
            self.log_status("YOLO model loaded successfully")
        except Exception as e:
            self.yolo_model = None
            self.log_status(f"YOLO model not available: {e}")

        # Setup application icon
        self.setup_application_icon()

    def setup_application_icon(self):
        """Setup application icon with multiple fallback methods"""
        icon_path = resource_path(
            os.path.join("All_icons_pngs", "KT_OD_App_iconV3.1Multi.ico")
        )
        try:
            if os.path.exists(icon_path):
                self.master.iconbitmap(icon_path)
                self.log_status(f"Icon loaded: {icon_path}")
                return True
            else:
                self.log_status(f"Icon file not found: {icon_path}")
        except Exception as e:
            self.log_status(f"Failed to load icon {icon_path}: {e}")

        return False


if __name__ == "__main__":
    root = tk.Tk()
    app = EnhancedColorPickerApp(root)
    root.mainloop()
