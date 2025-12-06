# This version removes mouse and keyboard dependencies while preserving Xbox controller functionality
from inputs import get_gamepad
from tkinter import ttk, colorchooser, messagebox
import tkinter as tk  # Added missing import
import threading  # Added missing import
import time  # Added missing import
import datetime  # Added missing import for timestamp formatting
import traceback  # Added missing import for error handling
import cv2
import numpy as np
from PIL import Image, ImageTk
import pygetwindow as gw
import mss
import mss.tools
import gc
import psutil
import os
import vgamepad as vg
import win32gui  # Added missing import for window management
import win32api  # Added missing import for API calls

# Add imports for YOLOv8 and Tesseract
from ultralytics import YOLO
import pytesseract

# Ensure Tesseract is configured correctly
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Constants for performance tuning
MIN_CAPTURE_INTERVAL_MS = 10
MAX_CAPTURE_INTERVAL_MS = 200
DEFAULT_CAPTURE_INTERVAL_MS = 50
MEMORY_WARNING_THRESHOLD = 85
WATCHDOG_TIMEOUT_SECONDS = 10
CRITICAL_MEMORY_THRESHOLD = 95
FPS_UPDATE_INTERVAL = 2.0
CONTROLLER_RECONNECT_INTERVAL = 5.0


class XboxController:
    # Added missing class constants
    MAX_JOY_VAL = 32767.0
    MAX_TRIG_VAL = 255

    def __init__(self, log_function=None):
        """Initialize the XboxController."""
        self.log_function = (
            log_function or print
        )  # Default to print if no log function is provided

        # Initialize controller properties
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
        """Log a status message using the provided log function."""
        self.log_function(message)

    def is_active(self):
        """Check if controller is sending events"""
        # Consider controller inactive if no events for 5 seconds
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

    def read(self):
        # Return the buttons/triggers that you care about in this method
        x = self.LeftJoystickX
        y = self.LeftJoystickY
        a = self.A
        b = self.X
        rb = self.RightBumper
        lb = self.LeftBumper
        return [x, y, a, b, rb, lb]

    def _monitor_controller(self):
        """Monitor the physical controller for input events."""
        try:
            while self._running:
                try:
                    events = get_gamepad()
                    if events:
                        self._last_event_time = time.time()

                    for event in events:
                        if event.code == "ABS_Y":
                            self.LeftJoystickY = (
                                event.state / XboxController.MAX_JOY_VAL
                            )
                        elif event.code == "ABS_X":
                            self.LeftJoystickX = (
                                event.state / XboxController.MAX_JOY_VAL
                            )
                        elif event.code == "ABS_RY":
                            self.RightJoystickY = (
                                event.state / XboxController.MAX_JOY_VAL
                            )
                        elif event.code == "ABS_RX":
                            self.RightJoystickX = (
                                event.state / XboxController.MAX_JOY_VAL
                            )
                        elif event.code == "ABS_Z":
                            self.LeftTrigger = event.state / XboxController.MAX_TRIG_VAL
                        elif event.code == "ABS_RZ":
                            self.RightTrigger = (
                                event.state / XboxController.MAX_TRIG_VAL
                            )
                        elif event.code == "BTN_TL":
                            self.LeftBumper = event.state
                        elif event.code == "BTN_TR":
                            self.RightBumper = event.state
                        elif event.code == "BTN_SOUTH":
                            self.A = event.state
                        elif event.code == "BTN_NORTH":
                            self.X = event.state
                        elif event.code == "BTN_WEST":
                            self.Y = event.state
                        elif event.code == "BTN_EAST":
                            self.B = event.state
                except IOError:
                    # Handle disconnection gracefully
                    print("Controller disconnected. Retrying...")
                    time.sleep(1.0)  # Wait before retrying
        except Exception as e:
            print(f"Controller error: {e}")
            self._running = False

    def simulate_right_stick(self, x_value, y_value):
        """
        Send right stick movement to the virtual controller.
        """
        # Convert from -1.0/1.0 range to -32768/32767 range
        x_val_converted = int(x_value * 32767)
        y_val_converted = int(y_value * 32767)

        # Clamp values to valid range
        x_val_converted = max(-32768, min(32767, x_val_converted))
        y_val_converted = max(-32768, min(32767, y_val_converted))

        # Send to virtual controller
        self.virtual_controller.right_joystick(
            x_value=x_val_converted, y_value=y_val_converted
        )
        self.virtual_controller.update()


class ColorPickerApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Xbox Color Tracker")
        self.master.geometry("900x700")  # Increased size to accommodate logo

        # Set window icon using the multi-icon .ico file
        try:
            icon_path = os.path.join(
                os.path.dirname(__file__),
                "All_icons_pngs",
                "KT_OD_App_iconV3.1Multi.ico",
            )
            if os.path.exists(icon_path):
                self.master.iconbitmap(icon_path)
                self.log_status("Window icon loaded successfully from .ico file")
            else:
                self.log_status("Warning: Multi-icon .ico file not found")
        except Exception as e:
            self.log_status(f"Warning: Could not load window icon from .ico file - {e}")

        # Set up better exception handling
        tk.Tk.report_callback_exception = self.handle_exception

        # Check for ViGEmBus driver before initializing virtual controller
        try:
            from driver_check import ensure_vigembus_driver

            if not ensure_vigembus_driver():
                self.log_status(
                    "Warning: ViGEmBus driver not available - virtual controller disabled"
                )
        except ImportError:
            self.log_status(
                "Warning: driver_check module not found - virtual controller may not work"
            )
        except Exception as e:
            self.log_status(f"Warning: Driver check failed - {e}")

        # Check Xbox controller drivers and connectivity
        try:
            from xbox_controller_check import ensure_xbox_controller

            if not ensure_xbox_controller():
                self.log_status(
                    "Warning: Xbox controller issues detected - input may not work properly"
                )
        except ImportError:
            self.log_status(
                "Warning: xbox_controller_check module not found - controller detection disabled"
            )
        except Exception as e:
            self.log_status(f"Warning: Xbox controller check failed - {e}")

        # Initialize controller
        self.controller = XboxController(log_function=self.log_status)

        # Initialize target color (default: white)
        self.target_color = (255, 255, 255)

        # Flag for color detection
        self.detection_active = False
        self.detection_thread = None

        # Performance monitoring
        self.last_status_update = 0
        self.status_update_interval = 0.5  # seconds

        # Cache for screen capture optimization
        self.last_capture_hash = None

        # Counter for garbage collection
        self._gc_counter = 0

        # Set up system resource monitoring
        self.process = psutil.Process(os.getpid())

        # Load YOLOv8n model (pretrained on COCO or custom dataset)
        self.yolo_model = YOLO("yolov8n.pt")  # Replace with your custom model if needed

        # Flag for YOLO detection
        self.yolo_detection_active = False

        # Create main UI
        self.create_ui()

        # Initialize app components
        self.initialize_app()

        # After other initializations
        self.watchdog_last_update = time.time()
        self.master.after(5000, self.check_watchdog)  # Check every 5 seconds

        self.auto_tracking_enabled = (
            True  # Default auto-tracking on when color is detected
        )

        from threading import Lock

        self.lock = Lock()

        self.frame_skip = tk.IntVar(value=1)  # Default to process every frame

    def create_ui(self):
        """Build the user interface with improved layout"""
        # Create main container
        main_container = ttk.Frame(self.master)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Create top panel for video source controls
        top_panel = ttk.Frame(main_container, padding="10")
        top_panel.grid(
            row=0, column=0, columnspan=3, sticky="nsew"
        )  # Span all three columns

        # Add video source selection dropdown
        ttk.Label(top_panel, text="Video Source:").pack(side=tk.LEFT, padx=5)
        self.video_source = tk.StringVar(value="Monitor")  # Default to Monitor
        self.video_source_dropdown = ttk.Combobox(
            top_panel, textvariable=self.video_source, state="readonly", width=15
        )
        self.video_source_dropdown["values"] = ["Monitor", "Window", "Capture Card"]
        self.video_source_dropdown.pack(side=tk.LEFT, padx=5)
        self.video_source_dropdown.bind(
            "<<ComboboxSelected>>", self.on_video_source_change
        )

        # Add capture card dropdown (hidden by default)
        self.capture_card_index = tk.StringVar(value="0")  # Default to index 0
        self.capture_card_dropdown = ttk.Combobox(
            top_panel, textvariable=self.capture_card_index, state="readonly", width=10
        )
        self.capture_card_dropdown["values"] = self.get_capture_card_options()
        self.capture_card_dropdown.pack(side=tk.LEFT, padx=5)
        self.capture_card_dropdown.pack_forget()  # Hide initially

        # Add a button to initialize the selected capture card
        self.capture_card_button = ttk.Button(
            top_panel, text="Use Capture Card", command=self.use_selected_capture_card
        )
        self.capture_card_button.pack(side=tk.LEFT, padx=5)
        self.capture_card_button.pack_forget()  # Hide initially

        # Add a button to stop using the capture card
        self.stop_capture_card_button = ttk.Button(
            top_panel, text="Stop Capture Card", command=self.stop_capture_card
        )
        self.stop_capture_card_button.pack(side=tk.LEFT, padx=5)
        self.stop_capture_card_button.pack_forget()  # Hide initially

        # Add YOLO detection buttons
        start_yolo_button = ttk.Button(
            top_panel, text="Start YOLO Detection", command=self.start_yolo_detection
        )
        start_yolo_button.pack(side=tk.LEFT, padx=5)

        stop_yolo_button = ttk.Button(
            top_panel, text="Stop YOLO Detection", command=self.stop_yolo_detection
        )
        stop_yolo_button.pack(side=tk.LEFT, padx=5)

        # Create left panel for controls
        left_panel = ttk.Frame(main_container, padding="10")
        left_panel.grid(row=1, column=0, sticky="nsew")

        # Create right panel for preview
        right_panel = ttk.Frame(main_container, padding="10")
        right_panel.grid(row=1, column=1, sticky="nsew")

        # Create logo panel
        logo_panel = ttk.Frame(main_container, padding="10")
        logo_panel.grid(row=1, column=2, sticky="nsew")

        # Configure the grid
        main_container.columnconfigure(0, weight=3)  # Left panel gets more space
        main_container.columnconfigure(1, weight=1)  # Right panel gets less space
        main_container.columnconfigure(2, weight=0)  # Logo panel fixed width
        main_container.rowconfigure(1, weight=1)

        # ===== LOGO PANEL CONTENTS =====
        self.setup_logo_panel(logo_panel)

        # ===== LEFT PANEL CONTENTS =====

        # Create frame for controls
        control_frame = ttk.Frame(left_panel)
        control_frame.pack(fill=tk.X, pady=5)

        # Create color selection button
        self.color_button = ttk.Button(
            control_frame, text="Select Target Color", command=self.choose_color
        )
        self.add_tooltip(self.color_button, "Choose the color to track")
        self.color_button.pack(side=tk.LEFT, padx=5)

        # Create color display label
        self.color_display = tk.Label(control_frame, width=5, height=1, bg="#FFFFFF")
        self.color_display.pack(side=tk.LEFT, padx=5)

        # Create color value label
        self.color_value = ttk.Label(control_frame, text="RGB: (255, 255, 255)")
        self.color_value.pack(side=tk.LEFT, padx=5)

        # New separate start and stop buttons
        self.start_button = ttk.Button(
            control_frame, text="Start Detection", command=self.start_detection
        )
        self.add_tooltip(self.start_button, "Start color detection")
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            control_frame,
            text="Stop Detection",
            command=self.stop_detection,
            state=tk.DISABLED,
        )
        self.add_tooltip(self.stop_button, "Stop color detection")
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Create exit button
        exit_button = ttk.Button(control_frame, text="Exit", command=self.on_exit)
        exit_button.pack(side=tk.RIGHT, padx=5)

        # Second row of controls
        control_frame2 = ttk.Frame(left_panel)
        control_frame2.pack(fill=tk.X, pady=5)

        # Create controller status label
        self.controller_status = ttk.Label(
            control_frame2, text="Controller: Disconnected", foreground="red"
        )
        self.controller_status.pack(side=tk.LEFT, padx=5)

        # Add tracking indicator
        self.tracking_indicator = ttk.Label(
            control_frame2, text="Idle", foreground="gray"
        )
        self.tracking_indicator.pack(side=tk.LEFT, padx=5)

        # Add Xbox Remote Play mode toggle
        self.remote_play_mode = tk.BooleanVar(value=False)
        remote_play_check = ttk.Checkbutton(
            control_frame2,
            text="Xbox Remote Play Mode",
            variable=self.remote_play_mode,
            command=self.toggle_remote_play_mode,
        )
        self.add_tooltip(
            remote_play_check, "Track colors within an Xbox Remote Play window"
        )
        remote_play_check.pack(side=tk.LEFT, padx=5)

        # Window title for Xbox Remote Play
        self.xbox_window_title = "Xbox Remote Play"

        # Add reset controller button
        reset_controller_btn = ttk.Button(
            control_frame2, text="Reset Controller", command=self.reset_controller
        )
        reset_controller_btn.pack(side=tk.RIGHT, padx=5)

        # Status frame
        status_frame = ttk.LabelFrame(left_panel, text="Status", padding="10")
        status_frame.pack(fill=tk.X, pady=5)

        # System resources info
        self.system_info = ttk.Label(
            status_frame, text="Memory: 0% | CPU: 0%", anchor=tk.W
        )
        self.system_info.pack(fill=tk.X, pady=(0, 5))

        # Add FPS counter label
        self.fps_label = ttk.Label(status_frame, text="FPS: 0.0", anchor=tk.W)
        self.fps_label.pack(fill=tk.X, pady=(0, 5))

        # Status text with scrollbar
        status_frame_inner = ttk.Frame(status_frame)
        status_frame_inner.pack(fill=tk.BOTH, expand=True)

        self.status_text = tk.Text(status_frame_inner, height=5, width=50, wrap=tk.WORD)
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add scrollbar to status text
        status_scrollbar = ttk.Scrollbar(
            status_frame_inner, command=self.status_text.yview
        )
        status_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=status_scrollbar.set)

        self.log_status("Application started")

        # Detection box frame
        box_frame = ttk.LabelFrame(left_panel, text="Detection Box", padding="10")
        box_frame.pack(fill=tk.X, pady=5)

        # Box controls
        ttk.Label(box_frame, text="X:").grid(row=0, column=0, padx=5, pady=5)
        self.box_x = ttk.Entry(box_frame, width=5)
        self.box_x.insert(0, "860")
        self.box_x.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(box_frame, text="Y:").grid(row=0, column=2, padx=5, pady=5)
        self.box_y = ttk.Entry(box_frame, width=5)
        self.box_y.insert(0, "440")
        self.box_y.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(box_frame, text="Width:").grid(row=0, column=4, padx=5, pady=5)
        self.box_width = ttk.Entry(box_frame, width=5)
        self.box_width.insert(0, "400")
        self.box_width.grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(box_frame, text="Height:").grid(row=0, column=6, padx=5, pady=5)
        self.box_height = ttk.Entry(box_frame, width=5)
        self.box_height.insert(0, "350")
        self.box_height.grid(row=0, column=7, padx=5, pady=5)

        # Add frame for detection parameters
        param_frame = ttk.LabelFrame(
            left_panel, text="Detection Parameters", padding="10"
        )
        param_frame.pack(fill=tk.X, pady=5)

        # Color tolerance control
        ttk.Label(param_frame, text="Color Tolerance:").grid(
            row=0, column=0, padx=5, pady=5
        )
        self.color_tolerance = ttk.Scale(
            param_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=200
        )
        self.color_tolerance.set(30)  # Default value
        self.color_tolerance.grid(row=0, column=1, padx=5, pady=5)
        self.tolerance_value = ttk.Label(param_frame, text="30")
        self.tolerance_value.grid(row=0, column=2, padx=5, pady=5)
        self.color_tolerance.bind("<Motion>", self.update_tolerance_display)
        self.add_tooltip(
            self.color_tolerance,
            "How much variation in color to accept (higher = more tolerant)",
        )

        # Contour size threshold control
        ttk.Label(param_frame, text="Minimum Size:").grid(
            row=1, column=0, padx=5, pady=5
        )
        self.contour_threshold = ttk.Scale(
            param_frame, from_=1, to=100, orient=tk.HORIZONTAL, length=200
        )
        self.contour_threshold.set(10)  # Default value lowered from 20 to 10
        self.contour_threshold.grid(row=1, column=1, padx=5, pady=5)
        self.threshold_value = ttk.Label(param_frame, text="20")
        self.threshold_value.grid(row=1, column=2, padx=5, pady=5)
        self.contour_threshold.bind("<Motion>", self.update_threshold_display)
        self.add_tooltip(
            self.contour_threshold,
            "Minimum size of color area to detect (higher = larger areas)",
        )

        # Capture interval control
        ttk.Label(param_frame, text="Capture Interval (ms):").grid(
            row=2, column=0, padx=5, pady=5
        )
        self.capture_interval = ttk.Scale(
            param_frame,
            from_=MIN_CAPTURE_INTERVAL_MS,
            to=MAX_CAPTURE_INTERVAL_MS,
            orient=tk.HORIZONTAL,
            length=200,
        )
        self.capture_interval.set(DEFAULT_CAPTURE_INTERVAL_MS)  # Default value 50ms
        self.capture_interval.grid(row=2, column=1, padx=5, pady=5)
        self.interval_value = ttk.Label(
            param_frame, text=str(DEFAULT_CAPTURE_INTERVAL_MS)
        )
        self.interval_value.grid(row=2, column=2, padx=5, pady=5)
        self.capture_interval.bind("<Motion>", self.update_interval_display)
        self.add_tooltip(
            self.capture_interval,
            "Time between captures (lower = more responsive but higher CPU usage)",
        )

        # Monitor selection frame
        monitor_frame = ttk.LabelFrame(
            left_panel, text="Monitor Selection", padding="10"
        )
        monitor_frame.pack(fill=tk.X, pady=5)

        # Get all monitors
        self.monitors = self.get_monitors()
        self.selected_monitor = tk.StringVar()  # Use StringVar instead of IntVar

        # Create monitor selection dropdown
        ttk.Label(monitor_frame, text="Select Monitor:").grid(
            row=0, column=0, padx=5, pady=5
        )
        monitor_dropdown = ttk.Combobox(
            monitor_frame,
            textvariable=self.selected_monitor,
            state="readonly",
            width=30,
        )

        # Populate dropdown with monitor details
        monitor_options = []
        for i, m in enumerate(self.monitors):
            monitor_options.append(
                f"Monitor {i+1}: {m['width']}x{m['height']} at ({m['left']},{m['top']})"
            )

        monitor_dropdown["values"] = monitor_options
        monitor_dropdown.set(monitor_options[1])  # Set to monitor 2
        monitor_dropdown.current(1)  # Set to monitor 2
        monitor_dropdown.grid(row=0, column=1, padx=5, pady=5)
        monitor_dropdown.bind("<<ComboboxSelected>>", self.on_monitor_selected)

        # Add refresh button
        refresh_btn = ttk.Button(
            monitor_frame, text="Refresh", command=self.refresh_monitors
        )
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)

        # ===== RIGHT PANEL CONTENTS =====

        # Create monitor preview frame
        self.preview_frame = ttk.LabelFrame(
            right_panel, text="Monitor Preview", padding="10"
        )
        self.preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.preview_canvas = tk.Canvas(
            self.preview_frame, width=500, height=400, bg="dark grey"
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.preview_image = None
        self.preview_image_on_canvas = None

        # Results frame to display detected colors
        results_frame = ttk.LabelFrame(
            left_panel, text="Detection Results", padding="10"
        )
        results_frame.pack(fill=tk.X, pady=5)

        # Color detection indicator label
        self.color_found_label = ttk.Label(
            results_frame, text="No color detected", foreground="gray"
        )
        self.color_found_label.pack(fill=tk.X, pady=5)

        # Color location
        self.color_location_label = ttk.Label(
            results_frame, text="Location: N/A", foreground="gray"
        )
        self.color_location_label.pack(fill=tk.X, pady=5)

    def setup_logo_panel(self, logo_panel):
        """Set up the logo panel with branding"""
        # Create logo frame
        logo_frame = ttk.LabelFrame(
            logo_panel, text="KT Object Detection", padding="10"
        )
        logo_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Load and display logo - try PNG first, then .ico as fallback
        try:
            # First try the PNG for better quality in UI display
            logo_path = os.path.join(
                os.path.dirname(__file__), "All_icons_pngs", "KT_OD_App_iconV6.png"
            )
            if os.path.exists(logo_path):
                logo_img = Image.open(logo_path)
                # Resize logo to fit nicely in the panel
                logo_img = logo_img.resize((120, 120), Image.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(logo_img)

                # Create logo label
                logo_label = tk.Label(logo_frame, image=self.logo_image, bg="white")
                logo_label.pack(pady=10)
                self.log_status("Logo panel loaded successfully from PNG")
            else:
                # Fallback to .ico file if PNG not available
                ico_path = os.path.join(
                    os.path.dirname(__file__),
                    "All_icons_pngs",
                    "KT_OD_App_iconV3.1Multi.ico",
                )
                if os.path.exists(ico_path):
                    logo_img = Image.open(ico_path)
                    # Resize logo to fit nicely in the panel
                    logo_img = logo_img.resize((120, 120), Image.LANCZOS)
                    self.logo_image = ImageTk.PhotoImage(logo_img)

                    # Create logo label
                    logo_label = tk.Label(logo_frame, image=self.logo_image, bg="white")
                    logo_label.pack(pady=10)
                    self.log_status("Logo panel loaded successfully from .ico file")
                else:
                    # Text fallback if no icon files found
                    raise FileNotFoundError("No icon files found")

            # Add branding text
            brand_label = ttk.Label(
                logo_frame,
                text="KT Object Detection",
                font=("Arial", 12, "bold"),
                foreground="navy",
            )
            brand_label.pack(pady=5)

            version_label = ttk.Label(
                logo_frame,
                text="Xbox Color Tracker",
                font=("Arial", 10),
                foreground="gray",
            )
            version_label.pack(pady=2)

            # Add separator
            separator = ttk.Separator(logo_frame, orient="horizontal")
            separator.pack(fill=tk.X, pady=10)

            # Add info labels
            info_frame = ttk.Frame(logo_frame)
            info_frame.pack(fill=tk.X, pady=5)

            ttk.Label(
                info_frame,
                text="Real-time Detection",
                font=("Arial", 9),
                foreground="darkgreen",
            ).pack(anchor=tk.W)
            ttk.Label(
                info_frame,
                text="AI-Powered Tracking",
                font=("Arial", 9),
                foreground="darkgreen",
            ).pack(anchor=tk.W)
            ttk.Label(
                info_frame,
                text="Xbox Integration",
                font=("Arial", 9),
                foreground="darkgreen",
            ).pack(anchor=tk.W)

        except Exception as e:
            # Error fallback - text-based logo
            fallback_label = ttk.Label(
                logo_frame,
                text="KT\nObject\nDetection",
                font=("Arial", 16, "bold"),
                foreground="navy",
            )
            fallback_label.pack(expand=True)
            self.log_status(f"Error loading logo, using text fallback: {e}")

    def initialize_app(self):
        """Set up initial app state and timers"""
        # Initialize monitor preview
        self.master.after(1000, self.update_monitor_preview)

        # Update preview periodically
        self.master.after(3000, self.periodic_preview_update)

        # Initialize controller and update status periodically
        self.master.after(1000, self.update_controller_status)

        # Update system resource info
        self.master.after(2000, self.update_system_info)

    def add_tooltip(self, widget, text):
        """Add tooltip to a widget"""

        def show_tooltip(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25

            # Create a toplevel window
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")

            label = ttk.Label(
                tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1
            )
            label.pack()

            self._tooltip = tooltip

        def hide_tooltip(event):
            if hasattr(self, "_tooltip") and self._tooltip is not None:
                try:
                    self._tooltip.destroy()
                except:
                    pass  # Ignore any errors during destruction
                self._tooltip = None

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions"""
        error_msg = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )
        self.log_status(f"Unhandled exception: {exc_value}")
        print(error_msg)  # Print to console

        # Show error dialog for serious errors
        if not isinstance(exc_value, (IOError, ConnectionError)):
            messagebox.showerror("Error", f"An error occurred: {exc_value}")

    def update_system_info(self):
        """Update system resource usage information"""
        try:
            # Get memory and CPU usage
            memory_percent = psutil.virtual_memory().percent
            cpu_percent = self.process.cpu_percent(interval=None)

            # Update label with info
            self.system_info.config(
                text=f"Memory: {memory_percent}% | CPU: {cpu_percent:.1f}%",
                foreground=(
                    "red" if memory_percent > MEMORY_WARNING_THRESHOLD else "black"
                ),
            )

            # Warning for high memory usage
            if memory_percent > MEMORY_WARNING_THRESHOLD:
                self.log_status(f"Warning: High memory usage ({memory_percent}%)")
                # Force garbage collection
                gc.collect()

        except Exception as e:
            print(f"Error updating system info: {e}")

        # Schedule next update
        self.master.after(3000, self.update_system_info)

    def update_controller_status(self):
        """Check controller status and update the UI with automatic reconnection"""
        try:
            # Try to start controller monitoring if not already running
            if (
                not self.controller._monitor_thread
                or not self.controller._monitor_thread.is_alive()
            ):
                if self.controller.start_monitoring():
                    self.controller_status.config(
                        text="Controller: Connected", foreground="green"
                    )
                    self.log_status("Controller connected")
                else:
                    self.controller_status.config(
                        text="Controller: Error", foreground="red"
                    )
                    self.log_status("Failed to start controller monitoring")
                    # Add automatic reconnection attempt
                    self.master.after(
                        int(CONTROLLER_RECONNECT_INTERVAL * 1000),
                        self.reconnect_controller,
                    )
            else:
                # Update status based on recent activity
                if self.controller.is_active():
                    self.controller_status.config(
                        text="Controller: Active", foreground="green"
                    )
                else:
                    self.controller_status.config(
                        text="Controller: Idle", foreground="orange"
                    )
                    # If controller hasn't been active for a while, attempt reconnection
                    if (
                        time.time() - self.controller._last_event_time > 10.0
                    ):  # 10 seconds of inactivity
                        self.log_status("Controller inactive - attempting reconnection")
                        self.reconnect_controller()
        except Exception as e:
            self.controller_status.config(text="Controller: Error", foreground="red")
            self.log_status(f"Controller error: {e}")
            # Schedule reconnection attempt
            self.master.after(
                int(CONTROLLER_RECONNECT_INTERVAL * 1000), self.reconnect_controller
            )

        # Schedule next check
        self.master.after(2000, self.update_controller_status)

    def reconnect_controller(self):
        """Attempt to reconnect to the controller"""
        try:
            self.log_status("Attempting controller reconnection...")
            # Stop current monitoring if running
            self.controller.stop_monitoring()
            # Small delay to ensure clean shutdown
            time.sleep(0.5)
            # Attempt to start monitoring again
            if self.controller.start_monitoring():
                self.controller_status.config(
                    text="Controller: Reconnected", foreground="green"
                )
                self.log_status("Controller successfully reconnected")
            else:
                self.controller_status.config(
                    text="Controller: Disconnected", foreground="red"
                )
                self.log_status("Reconnection failed")
        except Exception as e:
            self.log_status(f"Error during controller reconnection: {e}")

    def choose_color(self):
        try:
            color_code, hex_code = colorchooser.askcolor(title="Select Target Color")
            if color_code:
                r, g, b = int(color_code[0]), int(color_code[1]), int(color_code[2])
                self.target_color = (r, g, b)
                self.color_display.config(bg=hex_code)
                self.color_value.config(text=f"RGB: {self.target_color}")
                self.log_status(f"Target color set to RGB: {self.target_color}")
        except Exception as e:
            self.log_status(f"Error selecting color: {e}")

    def log_status(self, message):
        """Add timestamped message to status text with rate limiting"""
        current_time = time.time()

        # Rate limit identical messages
        if hasattr(self, "_last_message") and self._last_message == message:
            if current_time - self.last_status_update < self.status_update_interval:
                return

        self._last_message = message
        self.last_status_update = current_time

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)

        # Limit status text length to prevent memory growth
        num_lines = int(self.status_text.index("end-1c").split(".")[0])
        if num_lines > 100:  # Keep only the last 100 lines
            self.status_text.delete("1.0", f"{num_lines-100}.0")

    def start_detection(self):
        """
        Starts the color detection process in a separate thread.

        This method initializes and starts the color detection loop if it is not already active.
        It disables the start button and enables the stop button in the GUI to reflect the
        active detection state. If YOLO detection is active, it stops the YOLO detection
        process before starting the color detection.

        Actions performed:
        - Stops YOLO detection if it is active.
        - Sets the detection_active flag to True.
        - Updates the GUI buttons to reflect the detection state.
        - Starts the color detection loop in a daemon thread.
        - Logs a status message indicating that color detection has started.

        Note:
            The color detection loop runs in a separate thread to avoid blocking the main
            GUI thread.

        Log Message:
            "Color detection started - Press LB button to check colors"
        """
        if self.yolo_detection_active:
            self.stop_yolo_detection()
        if not self.detection_active:
            self.detection_active = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.detection_thread = threading.Thread(target=self.color_detection_loop)
            self.detection_thread.daemon = True
            self.detection_thread.start()
            self.log_status("Color detection started - Press LB button to check colors")

    def stop_detection(self):
        """Stop the color detection"""
        if self.detection_active:
            # Stop detection
            self.detection_active = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=2.0)
            self.tracking_indicator.config(text="Idle", foreground="gray")
            self.color_found_label.config(text="No color detected", foreground="gray")
            self.color_location_label.config(text="Location: N/A", foreground="gray")
            self.log_status("Color detection stopped")

    def screen_grab(self):
        """Grab screen image or capture card frame."""
        selected_source = self.video_source.get()

        if selected_source == "Monitor":
            # Capture from the selected monitor
            monitor_idx = self.get_monitor_index()
            monitor = self.monitors[monitor_idx]
            with mss.mss() as sct:
                monitor_dict = sct.monitors[
                    monitor_idx + 1
                ]  # MSS uses 1-based indexing
                screenshot = sct.grab(monitor_dict)
                img = Image.frombytes(
                    "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
                )
                return img

        elif selected_source == "Window":
            # Capture from the selected window
            if self.remote_play_mode.get():
                try:
                    # Find the window by title
                    window = gw.getWindowsWithTitle(self.xbox_window_title)
                    if not window:
                        self.log_status(f"Window '{self.xbox_window_title}' not found")
                        return None

                    window = window[0]  # Take the first matching window

                    # Get window position and size
                    left, top = window.left, window.top
                    width, height = window.width, window.height

                    # Capture the window
                    with mss.mss() as sct:
                        monitor = {
                            "left": left,
                            "top": top,
                            "width": width,
                            "height": height,
                        }
                        screenshot = sct.grab(monitor)
                        img = Image.frombytes(
                            "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
                        )
                        return img
                except Exception as e:
                    self.log_status(f"Error capturing window: {e}")
                    return None
            else:
                self.log_status("No window selected for capture")
                return None

        elif selected_source == "Capture Card":
            # Capture from the capture card
            if hasattr(self, "capture_card") and self.capture_card.isOpened():
                ret, frame = self.capture_card.read()
                if ret:
                    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    return img
                else:
                    self.log_status("Failed to read frame from capture card")
                    return None
            else:
                self.log_status("Capture card not initialized or unavailable")
                return None

        else:
            self.log_status("Invalid video source selected")
            return None

    def color_detection_loop(self):
        """
        Main detection loop that monitors controller and checks colors

        This method runs in a separate thread and is responsible for detecting the target color
        in the specified area of the screen. It uses the Xbox controller input to adjust the
        position of the detection box and to provide haptic feedback when the target color is
        detected. The method also includes optimization features such as skipping frames and
        adjusting the detection box size based on the distance of the detected color from the
        target color.

        The detection loop will run until the `detection_active` flag is set to False.

        Note: This method is intended to be run in a separate thread as a daemon.
        """
        self.log_status(
            "Detection loop running - Hold LB button to track colors in the detection box"
        )

        # Variables for optimization
        last_capture_time = 0
        was_tracking = False
        box_img = None
        frames_processed = 0
        fps_start_time = time.time()
        current_fps = 0

        while self.detection_active:
            self.watchdog_last_update = time.time()

            try:
                if self.controller.LeftBumper:  # When LB button is pressed
                    min_capture_interval = (
                        float(self.capture_interval.get()) / 1000.0
                    )  # Convert ms to seconds
                    if time.time() - last_capture_time >= min_capture_interval:
                        if not was_tracking:
                            self.tracking_indicator.config(
                                text="Tracking", foreground="green"
                            )
                            was_tracking = True

                        box_x, box_y, box_width, box_height = self.get_detection_box()
                        last_capture_time = time.time()

                        monitor_idx = self.get_monitor_index()
                        monitor = self.monitors[monitor_idx]

                        # Ensure the box is within the monitor bounds
                        box_x = max(monitor["left"], box_x)
                        box_y = max(monitor["top"], box_y)
                        box_width = min(
                            monitor["width"] - (box_x - monitor["left"]), box_width
                        )
                        box_height = min(
                            monitor["height"] - (box_y - monitor["top"]), box_height
                        )

                        # Grab the screen image
                        with mss.mss() as sct:
                            monitor = {
                                "left": box_x,
                                "top": box_y,
                                "width": box_width,
                                "height": box_height,
                            }
                            screenshot = sct.grab(monitor)
                            box_img = Image.frombytes(
                                "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
                            )

                        # Convert the image to numpy array for processing
                        np_img = np.array(box_img)
                        img_hsv = cv2.cvtColor(np_img, cv2.COLOR_RGB2HSV)

                        # Define the color range for detection
                        target_r, target_g, target_b = self.target_color
                        rgb_color = np.uint8([[[target_b, target_g, target_r]]])
                        hsv_color = cv2.cvtColor(rgb_color, cv2.COLOR_BGR2HSV)[0][0]
                        tolerance = int(self.color_tolerance.get())
                        h_tolerance = min(int(tolerance / 1.5), 90)
                        s_tolerance = tolerance * 1.2
                        v_tolerance = tolerance * 1.2

                        # Create a mask for the target color
                        lower_bound = np.array(
                            [
                                max(0, int(hsv_color[0]) - h_tolerance),
                                max(0, int(hsv_color[1]) - s_tolerance),
                                max(0, int(hsv_color[2]) - v_tolerance),
                            ],
                            dtype=np.uint8,
                        )
                        upper_bound = np.array(
                            [
                                min(179, int(hsv_color[0]) + h_tolerance),
                                min(255, int(hsv_color[1]) + s_tolerance),
                                min(255, int(hsv_color[2]) + v_tolerance),
                            ],
                            dtype=np.uint8,
                        )
                        mask = cv2.inRange(img_hsv, lower_bound, upper_bound)

                        # Find contours in the mask
                        contours, _ = cv2.findContours(
                            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                        )
                        valid_contours = [
                            c for c in contours if cv2.contourArea(c) > 10
                        ]  # Filter by size

                        # Update the tracking indicator and controller feedback
                        if valid_contours:
                            # Get the largest contour for both tracking and visualization
                            largest_contour = max(valid_contours, key=cv2.contourArea)

                            # Update UI status
                            self.color_found_label.config(
                                text="Color detected!", foreground="green"
                            )

                            if self.auto_tracking_enabled:
                                M = cv2.moments(largest_contour)
                                if M["m00"] != 0:
                                    cx = int(M["m10"] / M["m00"])
                                    cy = int(M["m01"] / M["m00"])
                                    screen_box_x = monitor["left"] + max(
                                        0, box_x - monitor["left"]
                                    )
                                    screen_box_y = monitor["top"] + max(
                                        0, box_y - monitor["top"]
                                    )
                                    screen_x = screen_box_x + cx
                                    screen_y = screen_box_y + cy

                                    # Update location label
                                    self.color_location_label.config(
                                        text=f"Location: ({screen_x}, {screen_y})",
                                        foreground="black",
                                    )

                                    # Move the crosshair
                                    box_center_x = screen_box_x + (box_width // 2)
                                    box_center_y = screen_box_y + (box_height // 2)
                                    offset_x = screen_x - box_center_x
                                    offset_y = screen_y - box_center_y
                                    scale_factor = 0.08  # Sensitivity scale
                                    stick_x = max(
                                        -1.0, min(1.0, offset_x * scale_factor)
                                    )
                                    stick_y = max(
                                        -1.0, min(1.0, offset_y * scale_factor)
                                    )
                                    self.controller.simulate_right_stick(
                                        stick_x, stick_y
                                    )
                                    self.log_status(
                                        f"Moving crosshair: Right stick ({stick_x:.2f}, {stick_y:.2f}) for offset ({offset_x}, {offset_y})"
                                    )

                            # Draw the largest contour for visualization
                            cv2.drawContours(
                                np_img, [largest_contour], -1, (255, 0, 0), 2
                            )
                        else:
                            # Reset UI when no color detected
                            self.color_found_label.config(
                                text="No color detected", foreground="gray"
                            )
                            self.color_location_label.config(
                                text="Location: N/A", foreground="gray"
                            )
                            # Stop controller movement
                            self.controller.simulate_right_stick(0, 0)

                        # Show the processed image in the preview
                        self.show_preview(np_img)

                        # Update FPS
                        frames_processed += 1
                        if time.time() - fps_start_time >= FPS_UPDATE_INTERVAL:
                            current_fps = frames_processed / FPS_UPDATE_INTERVAL
                            self.fps_label.config(text=f"FPS: {current_fps:.1f}")
                            frames_processed = 0
                            fps_start_time = time.time()

                        # Periodically force garbage collection
                        if time.time() % 30 < 0.1:
                            gc.collect()
                else:
                    # When LB is not pressed, reset tracking state
                    if was_tracking:
                        self.tracking_indicator.config(text="Idle", foreground="gray")
                        self.color_found_label.config(
                            text="No color detected", foreground="gray"
                        )
                        self.color_location_label.config(
                            text="Location: N/A", foreground="gray"
                        )
                        self.controller.simulate_right_stick(0, 0)
                        was_tracking = False
                    time.sleep(0.01)  # Small delay to prevent excessive CPU usage

            except Exception as e:
                self.log_status(f"Error in detection loop: {e}")
                time.sleep(0.1)

        # Reset tracking indicator and controller on exit
        self.tracking_indicator.config(text="Idle", foreground="gray")
        self.color_found_label.config(text="No color detected", foreground="gray")
        self.color_location_label.config(text="Location: N/A", foreground="gray")
        self.controller.simulate_right_stick(0, 0)

    def show_preview(self, img_np):
        """Display the preview of the processed image."""
        img = Image.fromarray(cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB))
        self.preview_image = ImageTk.PhotoImage(img)
        self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_image)
        self.preview_canvas.image = self.preview_image  # Keep a reference

    def on_exit(self):
        """Clean shutdown of the application."""
        self.log_status("Shutting down application...")
        # Stop detection thread
        if self.detection_active:
            self.detection_active = False
        # Stop controller monitoring
        try:
            self.controller.stop_monitoring()
        except Exception as e:
            self.log_status(f"Error stopping controller: {e}")
        gc.collect()
        # Clean up image resources
        self.preview_image = None
        # Force garbage collection before exit
        gc.collect()
        # Stop detection thread
        # Release the capture card
        if hasattr(self, "capture_card") and self.capture_card.isOpened():
            self.capture_card.release()
            self.log_status("Capture card released")
        # Final cleanup and exit
        self.master.quit()

    def find_video_window(self):
        """Find any video source window with user selection."""
        try:
            # Use pygetwindow to get all windows, including hidden and minimized
            all_windows = gw.getAllWindows()

            # Debug log to print all retrieved windows
            for w in all_windows:
                print(
                    f"Window Title: {w.title}, Visible: {w.isVisible}, Minimized: {w.isMinimized}"
                )

            # Filter out windows with empty titles
            video_windows = [w for w in all_windows if w.title.strip()]

            # Ensure minimized windows are included
            video_windows = [w for w in video_windows if w.isVisible or w.isMinimized]

            if not video_windows:
                messagebox.showinfo(
                    "No Windows Found", "No video source windows were detected."
                )
                self.remote_play_mode.set(False)
                return False

            # Create a dialog for window selection
            window_dialog = tk.Toplevel(self.master)
            window_dialog.title("Select Video Source Window")
            window_dialog.geometry("400x300")
            window_dialog.transient(self.master)
            window_dialog.grab_set()  # Make dialog modal

            # Add instructions
            ttk.Label(
                window_dialog,
                text="Select the correct video source window:",
                font=("Arial", 12, "bold"),
            ).pack(pady=10)

            # Create a frame for the listbox and scrollbar
            list_frame = ttk.Frame(window_dialog)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

            # Add scrollbar
            scrollbar = ttk.Scrollbar(list_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Create listbox with window titles
            window_list = tk.Listbox(
                list_frame,
                height=10,
                width=50,
                yscrollcommand=scrollbar.set,
                font=("Arial", 10),
            )
            window_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=window_list.yview)

            # Populate the listbox
            for window in video_windows:
                window_list.insert(
                    tk.END, f"{window.title} (Visible: {window.isVisible})"
                )

            # Set the first item as selected
            if window_list.size() > 0:
                window_list.selection_set(0)

            # Variable to store the selected window
            selected_window = [None]  # Using list to store by reference

            # Function to handle selection
            def on_select():
                selection = window_list.curselection()
                if selection:
                    selected_window[0] = video_windows[selection[0]]
                    self.xbox_window_title = selected_window[0].title
                    self.log_status(
                        f"Selected video source window: {self.xbox_window_title}"
                    )
                    window_dialog.destroy()

            def on_cancel():
                self.remote_play_mode.set(False)
                window_dialog.destroy()
                self.log_status("Window selection cancelled")

            # Add buttons
            button_frame = ttk.Frame(window_dialog)
            button_frame.pack(fill=tk.X, pady=10)

            ttk.Button(button_frame, text="Select", command=on_select).pack(
                side=tk.LEFT, padx=20
            )
            ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(
                side=tk.RIGHT, padx=20
            )

            # Wait for the dialog to close
            self.master.wait_window(window_dialog)

            # Return whether a window was selected
            return selected_window[0] is not None

        except Exception as e:
            self.log_status(f"Error finding video source windows: {e}")
            self.remote_play_mode.set(False)
            return False

    def on_video_source_change(self, event=None):
        """Handle changes in the selected video source."""
        selected_source = self.video_source.get()

        if selected_source == "Monitor":
            # Hide capture card controls
            self.capture_card_dropdown.pack_forget()
            self.capture_card_button.pack_forget()
            self.stop_capture_card_button.pack_forget()  # Hide stop button
            self.remote_play_mode.set(False)  # Disable Remote Play mode
            self.log_status("Switched to monitor as video source")

        elif selected_source == "Window":
            # Hide capture card controls
            self.capture_card_dropdown.pack_forget()
            self.capture_card_button.pack_forget()
            self.stop_capture_card_button.pack_forget()  # Hide stop button
            self.remote_play_mode.set(True)  # Enable Remote Play mode
            self.find_video_window()  # Prompt user to select a window
            self.log_status("Switched to window as video source")

        elif selected_source == "Capture Card":
            # Show capture card controls
            self.capture_card_dropdown.pack(side=tk.LEFT, padx=5)
            self.capture_card_button.pack(side=tk.LEFT, padx=5)
            self.stop_capture_card_button.pack(side=tk.LEFT, padx=5)  # Show stop button
            self.remote_play_mode.set(False)  # Disable Remote Play mode
            self.log_status("Switched to capture card as video source")

    def get_capture_card_options(self):
        """Get a list of available capture card inputs."""
        options = []
        for i in range(10):  # Check the first 10 device indices
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                options.append(str(i))  # Add the index as a string
                cap.release()
        if not options:
            options.append("No devices found")
        return options

    def use_selected_capture_card(self):
        """Switch to using the selected capture card as the video source."""
        selected_index = int(self.capture_card_index.get())
        if self.initialize_capture_card(device_index=selected_index):
            self.remote_play_mode.set(False)  # Disable Remote Play mode
            self.log_status(f"Switched to capture card at index {selected_index}")
            # Start a thread to display the capture card feed
            threading.Thread(target=self.display_capture_card_feed, daemon=True).start()
        else:
            self.log_status(
                f"Failed to switch to capture card at index {selected_index}"
            )

    def initialize_capture_card(self, device_index=0):
        """Initialize the capture card as a video source."""
        try:
            self.capture_card = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)
            if not self.capture_card.isOpened():
                raise ValueError(f"Failed to open capture card at index {device_index}")
            self.log_status(f"Capture card initialized at index {device_index}")
            return True
        except Exception as e:
            self.log_status(f"Error initializing capture card: {e}")
            return False

    def display_capture_card_feed(self):
        """Display the capture card feed in the preview."""
        try:
            if hasattr(self, "capture_card") and self.capture_card.isOpened():
                while hasattr(self, "capture_card") and self.capture_card.isOpened():
                    # Check if we should stop
                    if (
                        not hasattr(self, "capture_card")
                        or not self.capture_card.isOpened()
                    ):
                        break

                    # Read a frame
                    ret, frame = self.capture_card.read()
                    if not ret:
                        time.sleep(0.1)
                        continue

                    # Convert to RGB for display
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)

                    # Resize to fit the preview area
                    canvas_width = self.preview_canvas.winfo_width()
                    canvas_height = self.preview_canvas.winfo_height()

                    if canvas_width > 1 and canvas_height > 1:
                        # Calculate aspect ratio
                        aspect_ratio = frame.shape[1] / frame.shape[0]

                        # Resize with aspect ratio preserved
                        if (canvas_width / canvas_height) > aspect_ratio:
                            new_width = int(canvas_height * aspect_ratio)
                            new_height = canvas_height
                        else:
                            new_width = canvas_width
                            new_height = int(canvas_width / aspect_ratio)

                        # Resize the image
                        img = img.resize((new_width, new_height), Image.LANCZOS)

                        # Update the preview image
                        self.preview_image = ImageTk.PhotoImage(img)

                        # Center image on canvas
                        x_offset = (canvas_width - new_width) // 2
                        y_offset = (canvas_height - new_height) // 2

                        # Clear canvas and display the new image
                        self.master.after(0, lambda: self.preview_canvas.delete("all"))
                        self.master.after(
                            0,
                            lambda: self.preview_canvas.create_image(
                                x_offset,
                                y_offset,
                                anchor=tk.NW,
                                image=self.preview_image,
                            ),
                        )

                    # Sleep to control frame rate
                    time.sleep(1 / 30)  # ~30 FPS

            else:
                self.log_status("Capture card not available for display")

        except Exception as e:
            self.log_status(f"Error displaying capture card feed: {e}")

    def toggle_remote_play_mode(self):
        """Toggle between full screen and Xbox Remote Play window mode"""
        mode = (
            "Xbox Remote Play window" if self.remote_play_mode.get() else "full screen"
        )
        self.log_status(f"Switched to {mode} capture mode")
        if self.remote_play_mode.get():
            self.find_xbox_window()

    def find_xbox_window(self):
        """Find Xbox Remote Play window with user selection"""
        try:
            all_windows = gw.getAllWindows()
            xbox_windows = [w for w in all_windows if "Xbox" in w.title]

            if not xbox_windows:
                self.log_status(
                    "No Xbox windows found. Please open Xbox Remote Play first."
                )
                self.remote_play_mode.set(False)
                return False

            # Create a dialog for window selection
            window_dialog = tk.Toplevel(self.master)
            window_dialog.title("Select Xbox Window")
            window_dialog.geometry("400x300")
            window_dialog.transient(self.master)
            window_dialog.grab_set()  # Make dialog modal

            # Add instructions
            ttk.Label(
                window_dialog,
                text="Select the correct Xbox window:",
                font=("Arial", 12, "bold"),
            ).pack(pady=10)

            # Create a frame for the listbox and scrollbar
            list_frame = ttk.Frame(window_dialog)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

            # Add scrollbar
            scrollbar = ttk.Scrollbar(list_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Create listbox with window titles
            window_list = tk.Listbox(
                list_frame,
                height=10,
                width=50,
                yscrollcommand=scrollbar.set,
                font=("Arial", 10),
            )
            window_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=window_list.yview)

            # Populate the listbox
            for window in xbox_windows:
                window_list.insert(
                    tk.END, f"{window.title} (Visible: {window.isVisible})"
                )

            # Set the first item as selected
            if window_list.size() > 0:
                window_list.selection_set(0)

            # Variable to store the selected window
            selected_window = [None]  # Using list to store by reference

            # Function to handle selection
            def on_select():
                selection = window_list.curselection()
                if selection:
                    selected_window[0] = xbox_windows[selection[0]]
                    self.xbox_window_title = selected_window[0].title
                    self.log_status(f"Selected Xbox window: {self.xbox_window_title}")
                    window_dialog.destroy()

            def on_cancel():
                self.remote_play_mode.set(False)
                window_dialog.destroy()
                self.log_status("Window selection cancelled")

            # Add buttons
            button_frame = ttk.Frame(window_dialog)
            button_frame.pack(fill=tk.X, pady=10)

            ttk.Button(button_frame, text="Select", command=on_select).pack(
                side=tk.LEFT, padx=20
            )
            ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(
                side=tk.RIGHT, padx=20
            )

            # Wait for the dialog to close
            self.master.wait_window(window_dialog)

            # Return whether a window was selected
            return selected_window[0] is not None

        except Exception as e:
            self.log_status(f"Error finding Xbox windows: {e}")
            self.remote_play_mode.set(False)
            return False

    def check_watchdog(self):
        """Monitor and recover from detection loop hangs"""
        if self.detection_active or self.yolo_detection_active:
            if time.time() - self.watchdog_last_update > WATCHDOG_TIMEOUT_SECONDS:
                self.log_status(
                    "⚠️ Watchdog detected hanging detection loop - recovering"
                )
                if self.detection_active:
                    self.stop_detection()
                    self.start_detection()
                elif self.yolo_detection_active:
                    self.stop_yolo_detection()
                    self.start_yolo_detection()
        self.master.after(5000, self.check_watchdog)

    def get_monitors(self):
        """Retrieve monitor information"""
        monitors = []
        try:
            # Use mss to get monitor information
            with mss.mss() as sct:
                for i, monitor in enumerate(
                    sct.monitors[1:], 1
                ):  # Skip the "all monitors" entry
                    monitors.append(
                        {
                            "left": monitor["left"],
                            "top": monitor["top"],
                            "width": monitor["width"],
                            "height": monitor["height"],
                            "number": i,
                        }
                    )
            if not monitors:
                monitors.append(
                    {
                        "left": 0,
                        "top": 0,
                        "width": self.master.winfo_screenwidth(),
                        "height": self.master.winfo_screenheight(),
                        "number": 1,
                    }
                )
        except Exception as e:
            self.log_status(f"Error getting monitors: {e}")
            monitors.append(
                {
                    "left": 0,
                    "top": 0,
                    "width": self.master.winfo_screenwidth(),
                    "height": self.master.winfo_screenheight(),
                    "number": 1,
                }
            )
        return monitors

    def update_monitor_preview(self, event=None):
        """Update the monitor preview"""
        try:
            monitor_idx = self.get_monitor_index()
            if monitor_idx >= len(self.monitors):
                monitor_idx = 0
                self.selected_monitor.set(0)

            monitor = self.monitors[monitor_idx]
            with mss.mss() as sct:
                monitor_dict = sct.monitors[monitor_idx + 1]
                screenshot = sct.grab(monitor_dict)
                img = Image.frombytes(
                    "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
                )

                canvas_width = 320
                canvas_height = 180
                aspect_ratio = screenshot.width / screenshot.height
                if (canvas_width / canvas_height) > aspect_ratio:
                    new_width = int(canvas_height * aspect_ratio)
                    new_height = canvas_height
                else:
                    new_width = canvas_width
                    new_height = int(canvas_width / aspect_ratio)

                img = img.resize((new_width, new_height), Image.LANCZOS)
                self.preview_image = ImageTk.PhotoImage(img)
                x_offset = (canvas_width - new_width) // 2
                y_offset = (canvas_height - new_height) // 2
                self.preview_canvas.delete("all")
                self.preview_image_on_canvas = self.preview_canvas.create_image(
                    x_offset, y_offset, anchor=tk.NW, image=self.preview_image
                )

                try:
                    box_x, box_y, box_width, box_height = self.get_detection_box()
                    rel_x = box_x - monitor["left"]
                    rel_y = box_y - monitor["top"]
                    preview_box_x = x_offset + int(
                        rel_x * (new_width / monitor["width"])
                    )
                    preview_box_y = y_offset + int(
                        rel_y * (new_height / monitor["height"])
                    )
                    preview_box_width = int(box_width * (new_width / monitor["width"]))
                    preview_box_height = int(
                        box_height * (new_height / monitor["height"])
                    )
                    self.preview_canvas.create_rectangle(
                        preview_box_x,
                        preview_box_y,
                        preview_box_x + preview_box_width,
                        preview_box_y + preview_box_height,
                        outline="green",
                        width=2,
                    )
                except Exception as e:
                    self.log_status(f"Error drawing detection box: {e}")

                self.log_status(f"Updated preview for Monitor {monitor_idx+1}")

        except Exception as e:
            self.log_status(f"Error updating monitor preview: {e}")

    def periodic_preview_update(self):
        """Update the preview periodically with memory management"""
        try:
            if not self.detection_active:
                self.update_monitor_preview()
                self._gc_counter += 1
                if self._gc_counter > 10:
                    gc.collect()
                    self._gc_counter = 0
        except Exception as e:
            self.log_status(f"Error in preview update: {e}")

        self.master.after(5000, self.periodic_preview_update)

    def refresh_monitors(self):
        """Refresh the list of monitors"""
        try:
            self.monitors = self.get_monitors()
            monitor_options = []
            for i, m in enumerate(self.monitors):
                monitor_options.append(
                    f"Monitor {i+1}: {m['width']}x{m['height']} at ({m['left']},{m['top']})"
                )

            for child in self.master.winfo_children():
                if isinstance(child, ttk.Frame):
                    for frame in child.winfo_children():
                        if isinstance(frame, ttk.LabelFrame) and frame.winfo_children():
                            for widget in frame.winfo_children():
                                if isinstance(widget, ttk.Combobox):
                                    widget["values"] = monitor_options
                                    widget.current(0)
                                    break

            monitor_idx = self.get_monitor_index()
            if monitor_idx < len(self.monitors):
                monitor = self.monitors[monitor_idx]
                box_width = int(self.box_width.get())
                box_height = int(self.box_height.get())
                center_x = monitor["left"] + (monitor["width"] // 2) - (box_width // 2)
                center_y = monitor["top"] + (monitor["height"] // 2) - (box_height // 2)
                self.box_x.delete(0, tk.END)
                self.box_x.insert(0, str(center_x))
                self.box_y.delete(0, tk.END)
                self.box_y.insert(0, str(center_y))
                self.update_monitor_preview()

            self.log_status("Monitor list refreshed")
        except Exception as e:
            self.log_status(f"Error refreshing monitors: {e}")

    def get_monitor_index(self):
        """Get the index of the selected monitor"""
        try:
            monitor_value = self.selected_monitor.get()
            if isinstance(monitor_value, str) and monitor_value.startswith("Monitor "):
                try:
                    monitor_idx = (
                        int(monitor_value.split(":")[0].replace("Monitor ", "")) - 1
                    )
                    return monitor_idx
                except:
                    return 0
            return int(monitor_value)
        except Exception as e:
            self.log_status(f"Error getting monitor index: {e}")
            return 0

    def get_detection_box(self):
        """Get the coordinates and size of the detection box"""
        try:
            x = int(self.box_x.get())
            y = int(self.box_y.get())
            width = int(self.box_width.get())
            height = int(self.box_height.get())
            return x, y, width, height
        except Exception as e:
            self.log_status(f"Error getting detection box: {e}")
            return 100, 100, 200, 200

    def on_monitor_selected(self, event=None):
        """Handle monitor selection change"""
        try:
            monitor_dropdown = event.widget
            idx = monitor_dropdown.current()
            selected_text = monitor_dropdown.get()
            self.selected_monitor.set(selected_text)
            monitor = self.monitors[idx]
            box_width = int(self.box_width.get())
            box_height = int(self.box_height.get())
            center_x = monitor["left"] + (monitor["width"] // 2) - (box_width // 2)
            center_y = monitor["top"] + (monitor["height"] // 2) - (box_height // 2)
            self.box_x.delete(0, tk.END)
            self.box_x.insert(0, str(center_x))
            self.box_y.delete(0, tk.END)
            self.box_y.insert(0, str(center_y))
            self.update_monitor_preview()
            self.log_status(f"Selected monitor {idx+1} - Detection box centered")
        except Exception as e:
            self.log_status(f"Error changing monitor: {e}")

    def update_detection_box_with_controller(self):
        """Update detection box position based on controller input"""
        try:
            if self.controller.is_active():
                x, y, width, height = self.get_detection_box()
                joy_x = self.controller.LeftJoystickX
                joy_y = -self.controller.LeftJoystickY
                if abs(joy_x) > 0.2 or abs(joy_y) > 0.2:
                    monitor_idx = self.get_monitor_index()
                    if monitor_idx >= len(self.monitors):
                        monitor_idx = 0
                    monitor = self.monitors[monitor_idx]
                    move_factor = 10
                    move_x = int(joy_x * move_factor)
                    move_y = int(joy_y * move_factor)
                    new_x = max(
                        monitor["left"],
                        min(x + move_x, monitor["left"] + monitor["width"] - width),
                    )
                    new_y = max(
                        monitor["top"],
                        min(y + move_y, monitor["top"] + monitor["height"] - height),
                    )
                    self.log_status(
                        f"Box moving to: ({new_x}, {new_y}) on monitor {monitor_idx+1}"
                    )
                    if new_x != x or new_y != y:
                        self.box_x.delete(0, tk.END)
                        self.box_x.insert(0, str(new_x))
                        self.box_y.delete(0, tk.END)
                        self.box_y.insert(0, str(new_y))
                        self.update_monitor_preview()
        except Exception as e:
            self.log_status(f"Error updating box with controller: {e}")
        self.master.after(50, self.update_detection_box_with_controller)

    def update_tolerance_display(self, event=None):
        value = int(self.color_tolerance.get())
        self.tolerance_value.config(text=str(value))

    def update_threshold_display(self, event=None):
        value = int(self.contour_threshold.get())
        self.threshold_value.config(text=str(value))

    def update_interval_display(self, event=None):
        value = int(self.capture_interval.get())
        self.interval_value.config(text=str(value))

    def reset_controller(self):
        """Reset the virtual controller to neutral position"""
        try:
            self.controller.simulate_right_stick(0, 0)
            self.log_status("Controller reset to neutral position")
        except Exception as e:
            self.log_status(f"Error resetting controller: {e}")

    def start_yolo_detection(self):
        """
        Starts the YOLOv8 detection process in a separate thread.
        """
        if self.detection_active:
            self.stop_detection()
        if not self.yolo_detection_active:
            self.yolo_detection_active = True
            self.log_status("YOLOv8 detection started")
            threading.Thread(target=self.yolo_detection_loop, daemon=True).start()

    def stop_yolo_detection(self):
        """Stop YOLOv8-based object detection."""
        self.yolo_detection_active = False
        self.log_status("YOLOv8 detection stopped")

    def yolo_detection_loop(self):
        """YOLOv8 detection loop with controller tracking."""
        while self.yolo_detection_active:
            with self.lock:
                try:
                    if not self.controller.LeftBumper:
                        # Reset tracking indicator and stop stick movement
                        self.tracking_indicator.config(text="Idle", foreground="gray")
                        self.controller.simulate_right_stick(0, 0)
                        time.sleep(0.01)
                        continue

                    self.tracking_indicator.config(text="Tracking", foreground="green")
                    img = self.screen_grab()
                    if img is None:
                        self.log_status("No valid frame captured")
                        time.sleep(0.1)
                        continue

                    box_x, box_y, box_width, box_height = self.get_detection_box()
                    monitor_idx = self.get_monitor_index()
                    monitor = self.monitors[monitor_idx]
                    screen_box_x = monitor["left"] + max(0, box_x - monitor["left"])
                    screen_box_y = monitor["top"] + max(0, box_y - monitor["top"])

                    img_np = np.array(img)
                    img_rgb = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                    rel_x = max(0, box_x - monitor["left"])
                    rel_y = max(0, box_y - monitor["top"])
                    crop_img = img_rgb[
                        rel_y : rel_y + box_height, rel_x : rel_x + box_width
                    ]

                    results = self.yolo_model(crop_img)
                    person_detections = []
                    for result in results:
                        for box in result.boxes:
                            cls = int(box.cls[0])
                            if cls == 0:  # Person class in COCO
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                conf = box.conf[0]
                                person_detections.append((x1, y1, x2, y2, conf))

                    if person_detections:
                        # Find the person with the highest confidence
                        x1, y1, x2, y2, conf = max(
                            person_detections, key=lambda x: x[4]
                        )
                        self.log_status(f"Detected person with confidence {conf:.2f}")
                        cx = (x1 + x2) // 2  # Horizontal center (unchanged)
                        cy_upper = y1 + int(
                            0.25 * (y2 - y1)
                        )  # Vertical position at 25% from the top
                        screen_x = screen_box_x + cx  # X-coordinate remains centered
                        screen_y = (
                            screen_box_y + cy_upper
                        )  # Y-coordinate adjusted to upper chest

                        # Calculate offsets and simulate stick movement
                        box_center_x = screen_box_x + (box_width // 2)
                        box_center_y = screen_box_y + (box_height // 2)
                        offset_x = screen_x - box_center_x
                        offset_y = screen_y - box_center_y
                        scale_factor = 0.08  # Adjust sensitivity
                        stick_x = max(-1.0, min(1.0, offset_x * scale_factor))
                        stick_y = max(-1.0, min(1.0, offset_y * scale_factor))
                        self.controller.simulate_right_stick(stick_x, stick_y)

                        # Update UI with detection info
                        self.color_found_label.config(
                            text="Person detected!", foreground="green"
                        )
                        self.color_location_label.config(
                            text=f"Location: ({screen_x}, {screen_y})",
                            foreground="black",
                        )
                        self.log_status(
                            f"Moving joystick towards person at ({screen_x}, {screen_y}) - Joystick: ({stick_x:.2f}, {stick_y:.2f})"
                        )
                    else:
                        # No person detected, reset stick movement
                        self.color_found_label.config(
                            text="No person detected", foreground="gray"
                        )
                        self.color_location_label.config(
                            text="Location: N/A", foreground="gray"
                        )
                        self.controller.simulate_right_stick(0, 0)

                    # Ensure continuous updates
                    self.controller.virtual_controller.update()

                    time.sleep(self.capture_interval.get() / 1000.0)
                    memory_percent = psutil.virtual_memory().percent
                    if memory_percent > CRITICAL_MEMORY_THRESHOLD:
                        self.log_status(f"Critical memory usage ({memory_percent}%)")
                        gc.collect()

                except Exception as e:
                    self.log_status(f"Error in YOLO detection loop: {e}")
                    time.sleep(0.1)

        # Reset tracking indicator and controller on exit
        self.tracking_indicator.config(text="Idle", foreground="gray")
        self.color_found_label.config(text="No person detected", foreground="gray")
        self.color_location_label.config(text="Location: N/A", foreground="gray")
        self.controller.simulate_right_stick(0, 0)
        self.controller.virtual_controller.update()

    def stop_capture_card(self):
        """Stop using the capture card as the video source."""
        if hasattr(self, "capture_card") and self.capture_card.isOpened():
            self.capture_card.release()
            self.log_status("Capture card stopped and released")
        else:
            self.log_status("No active capture card to stop")
        self.stop_capture_card_button.pack_forget()  # Hide the stop button
        self.capture_card_dropdown.pack_forget()  # Hide the capture card dropdown
        self.capture_card_button.pack_forget()  # Hide the capture card button
        self.remote_play_mode.set(False)  # Disable Remote Play mode
