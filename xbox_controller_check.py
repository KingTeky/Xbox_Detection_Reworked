"""
Xbox Controller Detection and Troubleshooting Module
====================================================
This module provides functions to detect Xbox controllers and guide users through
driver installation and troubleshooting steps.
"""

import subprocess
import sys
import os
import webbrowser
import tkinter as tk
from tkinter import messagebox
import platform
from pathlib import Path


def check_xbox_controller_drivers():
    """
    Check if Xbox controller drivers are installed and working.

    Returns:
        tuple: (bool, str) - (driver_status, message)
    """
    try:
        # Check if we're on Windows
        if platform.system() != "Windows":
            return False, "Xbox controller detection is only supported on Windows"

        # Use PowerShell to check for Xbox controllers in Device Manager
        cmd = """
        Get-PnpDevice | Where-Object {
            $_.FriendlyName -like "*Xbox*" -or 
            $_.FriendlyName -like "*Controller*" -or
            $_.HardwareID -like "*VID_045E*"
        } | Select-Object FriendlyName, Status, InstanceId
        """

        result = subprocess.run(
            ["powershell", "-Command", cmd], capture_output=True, text=True, timeout=15
        )

        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout.strip()

            # Check if any Xbox controllers are found
            if "Xbox" in output or "Controller" in output:
                # Check if any have error status
                if "Error" in output or "Unknown" in output:
                    return (
                        False,
                        f"Xbox controller found but has driver issues:\n{output}",
                    )
                else:
                    return (
                        True,
                        f"Xbox controller drivers appear to be working:\n{output}",
                    )
            else:
                return False, "No Xbox controllers detected in Device Manager"
        else:
            return False, "Could not check Device Manager for Xbox controllers"

    except Exception as e:
        return False, f"Error checking Xbox controller drivers: {e}"


def test_inputs_library():
    """
    Test if the inputs library can detect any gamepads.

    Returns:
        tuple: (bool, str) - (success, message)
    """
    try:
        from inputs import DeviceManager, get_gamepad

        # Try to get device manager
        device_manager = DeviceManager()
        gamepads = device_manager.gamepads

        if gamepads:
            gamepad_info = []
            for gamepad in gamepads:
                gamepad_info.append(f"- {gamepad.name}")

            return True, f"Found {len(gamepads)} gamepad(s):\n" + "\n".join(
                gamepad_info
            )
        else:
            return False, "No gamepads detected by inputs library"

    except ImportError:
        return False, "inputs library not installed. Run: pip install inputs"
    except Exception as e:
        return False, f"Error testing inputs library: {e}"


def test_controller_input():
    """
    Test if controller input is working by attempting to read events.

    Returns:
        tuple: (bool, str) - (success, message)
    """
    try:
        from inputs import get_gamepad
        import time

        # Try to read controller events for 2 seconds
        print("Testing controller input for 2 seconds...")
        start_time = time.time()
        events_detected = 0

        while time.time() - start_time < 2.0:
            try:
                events = get_gamepad()
                if events:
                    events_detected += len(events)
                time.sleep(0.1)
            except Exception:
                break

        if events_detected > 0:
            return (
                True,
                f"Controller input working! Detected {events_detected} events in 2 seconds",
            )
        else:
            return (
                False,
                "No controller input detected. Try pressing buttons on your Xbox controller.",
            )

    except ImportError:
        return False, "inputs library not installed"
    except Exception as e:
        return False, f"Error testing controller input: {e}"


def get_xbox_driver_download_info():
    """
    Get information about downloading Xbox controller drivers.

    Returns:
        dict: Driver download information
    """
    return {
        "official_url": "https://www.microsoft.com/en-us/download/details.aspx?id=48145",
        "windows_update": "Check Windows Update for automatic driver installation",
        "device_manager": "Device Manager > Action > Scan for hardware changes",
        "troubleshooter": "Settings > Update & Security > Troubleshoot > Hardware and Devices",
    }


def show_controller_troubleshooting_dialog():
    """
    Show a comprehensive troubleshooting dialog for Xbox controller issues.

    Returns:
        bool: True if user wants to continue, False to exit
    """
    root = tk.Tk()
    root.withdraw()  # Hide main window

    # First, check current status
    driver_status, driver_msg = check_xbox_controller_drivers()
    inputs_status, inputs_msg = test_inputs_library()

    # Create status message
    status_message = f"""Xbox Controller Status Check:

DRIVER STATUS: {'✅ WORKING' if driver_status else '❌ ISSUE DETECTED'}
{driver_msg}

INPUTS LIBRARY: {'✅ WORKING' if inputs_status else '❌ ISSUE DETECTED'}
{inputs_msg}

"""

    if driver_status and inputs_status:
        # Everything looks good, but offer to test input
        test_choice = messagebox.askyesno(
            "Controller Status - Good",
            status_message
            + "Everything appears to be working!\n\nWould you like to test controller input?",
            icon="question",
        )

        if test_choice:
            messagebox.showinfo(
                "Testing Controller",
                "Please press some buttons on your Xbox controller for the next 2 seconds...",
            )

            test_status, test_msg = test_controller_input()

            messagebox.showinfo(
                "Test Results",
                f"Controller Input Test:\n\n{test_msg}",
                icon="info" if test_status else "warning",
            )

        return True

    else:
        # Show troubleshooting options
        troubleshoot_message = (
            status_message
            + """
TROUBLESHOOTING OPTIONS:

1. Automatic Fix - Let me try to help automatically
2. Manual Steps - Show me what to do manually  
3. Skip - Continue anyway (controller may not work)

What would you like to do?"""
        )

        # Create custom dialog with three options
        dialog = tk.Toplevel()
        dialog.title("Xbox Controller Troubleshooting")
        dialog.geometry("600x500")
        dialog.transient(root)
        dialog.grab_set()

        # Add status text
        text_widget = tk.Text(dialog, wrap=tk.WORD, height=20, width=70)
        text_widget.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, troubleshoot_message)
        text_widget.config(state=tk.DISABLED)

        # Add scrollbar
        scrollbar = tk.Scrollbar(dialog, command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)

        result = [None]  # Use list to store result

        def auto_fix():
            result[0] = "auto"
            dialog.destroy()

        def manual_steps():
            result[0] = "manual"
            dialog.destroy()

        def skip_fix():
            result[0] = "skip"
            dialog.destroy()

        # Add buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(fill=tk.X, pady=10)

        tk.Button(
            button_frame, text="Automatic Fix", command=auto_fix, bg="lightgreen"
        ).pack(side=tk.LEFT, padx=20)
        tk.Button(
            button_frame, text="Manual Steps", command=manual_steps, bg="lightblue"
        ).pack(side=tk.LEFT, padx=20)
        tk.Button(button_frame, text="Skip", command=skip_fix, bg="lightcoral").pack(
            side=tk.RIGHT, padx=20
        )

        # Wait for user choice
        root.wait_window(dialog)

        # Handle user choice
        if result[0] == "auto":
            return handle_automatic_fix()
        elif result[0] == "manual":
            return show_manual_steps()
        else:  # skip
            messagebox.showwarning(
                "Skipping Controller Fix",
                "Xbox controller troubleshooting was skipped.\n\n"
                "The application may not detect your controller properly.",
            )
            return True

    return False


def handle_automatic_fix():
    """
    Attempt automatic fixes for Xbox controller issues.

    Returns:
        bool: True if fixes were attempted, False if failed
    """
    try:
        messagebox.showinfo(
            "Automatic Fix",
            "Attempting automatic fixes...\n\n"
            "This will:\n"
            "1. Scan for hardware changes\n"
            "2. Update Windows (if needed)\n"
            "3. Download drivers (if needed)\n\n"
            "Please wait...",
        )

        # Step 1: Scan for hardware changes
        try:
            subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "Get-PnpDevice | Where-Object {$_.Status -eq 'Error'} | Enable-PnpDevice -Confirm:$false",
                ],
                timeout=30,
                check=False,
            )

            # Rescan hardware
            subprocess.run(["pnputil", "/scan-devices"], timeout=30, check=False)
        except:
            pass  # Continue even if this fails

        # Step 2: Open Windows Update
        try:
            subprocess.run(["ms-settings:windowsupdate"], check=False)
            messagebox.showinfo(
                "Windows Update",
                "Windows Update has been opened.\n\n"
                "Please:\n"
                "1. Click 'Check for updates'\n"
                "2. Install any available updates\n"
                "3. Restart if prompted\n\n"
                "Then test your controller again.",
            )
        except:
            pass

        # Step 3: Check if controller is now working
        driver_status, driver_msg = check_xbox_controller_drivers()
        inputs_status, inputs_msg = test_inputs_library()

        if driver_status and inputs_status:
            messagebox.showinfo(
                "Fix Successful!",
                "Great! Your Xbox controller appears to be working now.\n\n"
                "The application should be able to detect your controller.",
            )
            return True
        else:
            messagebox.showwarning(
                "Automatic Fix Incomplete",
                "The automatic fix didn't fully resolve the issue.\n\n"
                "You may need to:\n"
                "- Restart your computer\n"
                "- Manually install drivers\n"
                "- Try a different USB port\n\n"
                "Would you like to see manual troubleshooting steps?",
            )
            return show_manual_steps()

    except Exception as e:
        messagebox.showerror(
            "Automatic Fix Failed",
            f"An error occurred during automatic fix:\n{e}\n\n"
            "Please try manual troubleshooting steps.",
        )
        return show_manual_steps()


def show_manual_steps():
    """
    Show manual troubleshooting steps for Xbox controller issues.

    Returns:
        bool: True if user wants to continue
    """
    driver_info = get_xbox_driver_download_info()

    manual_steps = f"""MANUAL XBOX CONTROLLER TROUBLESHOOTING STEPS:

🔧 BASIC STEPS:
1. Try a different USB port (preferably USB 3.0)
2. Try a different USB cable
3. Restart your computer
4. Test the controller on another device

🚀 DRIVER INSTALLATION:
1. Download official drivers:
   {driver_info['official_url']}

2. Windows Update method:
   - Open Settings > Update & Security > Windows Update
   - Click "Check for updates"
   - Install any available updates

3. Device Manager method:
   - Right-click Start button > Device Manager
   - Look for devices with yellow warning icons
   - Right-click > Update driver > Search automatically

4. Hardware troubleshooter:
   - Settings > Update & Security > Troubleshoot
   - Additional troubleshooters > Hardware and Devices
   - Run the troubleshooter

🔍 ADVANCED STEPS:
1. Uninstall and reinstall controller:
   - Device Manager > Xbox Controller
   - Right-click > Uninstall device
   - Unplug controller, restart PC, plug back in

2. Check for Windows feature updates:
   - Some controller support requires newer Windows versions

3. Try Windows compatibility mode:
   - For older controllers, try compatibility settings

📱 WIRELESS CONTROLLERS:
1. Use Xbox Wireless Adapter for Windows
2. Pair controller via Bluetooth (Windows 10/11)
3. Check battery level
4. Re-pair the controller

⚠️ COMMON ISSUES:
- Some third-party controllers may not work with 'inputs' library
- USB hubs can cause connection issues
- Antivirus software may block controller drivers
- Windows S mode may prevent driver installation

Would you like to continue with the application anyway?"""

    # Create scrollable dialog
    dialog = tk.Toplevel()
    dialog.title("Manual Troubleshooting Steps")
    dialog.geometry("700x600")
    dialog.grab_set()

    # Add text widget with scrollbar
    frame = tk.Frame(dialog)
    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    text_widget = tk.Text(frame, wrap=tk.WORD, font=("Consolas", 10))
    scrollbar = tk.Scrollbar(frame, command=text_widget.yview)

    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    text_widget.config(yscrollcommand=scrollbar.set)
    text_widget.insert(tk.END, manual_steps)
    text_widget.config(state=tk.DISABLED)

    result = [False]

    def continue_anyway():
        result[0] = True
        dialog.destroy()

    def open_driver_page():
        webbrowser.open(driver_info["official_url"])

    def exit_app():
        result[0] = False
        dialog.destroy()

    # Add buttons
    button_frame = tk.Frame(dialog)
    button_frame.pack(fill=tk.X, pady=10)

    tk.Button(
        button_frame, text="Download Drivers", command=open_driver_page, bg="lightblue"
    ).pack(side=tk.LEFT, padx=10)
    tk.Button(
        button_frame, text="Continue Anyway", command=continue_anyway, bg="lightgreen"
    ).pack(side=tk.LEFT, padx=10)
    tk.Button(
        button_frame, text="Exit Application", command=exit_app, bg="lightcoral"
    ).pack(side=tk.RIGHT, padx=10)

    dialog.wait_window()
    return result[0]


def ensure_xbox_controller():
    """
    Comprehensive function to ensure Xbox controller is working.

    Returns:
        bool: True if controller should work or user wants to continue anyway
    """
    print("Checking Xbox controller...")

    # Quick check first
    driver_status, _ = check_xbox_controller_drivers()
    inputs_status, _ = test_inputs_library()

    if driver_status and inputs_status:
        print("✅ Xbox controller appears to be working!")
        return True

    print("❌ Xbox controller issues detected")

    # Show troubleshooting dialog
    return show_controller_troubleshooting_dialog()


if __name__ == "__main__":
    # Test the controller detection
    print("Xbox Controller Detection Test")
    print("=" * 40)

    if ensure_xbox_controller():
        print("Controller check completed successfully!")
    else:
        print("Controller check failed or was cancelled.")
        sys.exit(1)
