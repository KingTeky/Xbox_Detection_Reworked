"""
ViGEmBus Driver Detection and Installation Helper
=================================================
This module provides functions to check if the ViGEmBus driver is installed
and guide users through the installation process.
"""

import subprocess
import sys
import os
import webbrowser
import tkinter as tk
from tkinter import messagebox
import requests
from pathlib import Path


def check_vigembus_installed():
    """
    Check if ViGEmBus driver is installed by attempting to create a virtual gamepad.

    Returns:
        bool: True if driver is installed and working, False otherwise
    """
    try:
        import vgamepad as vg

        # Try to create a virtual gamepad
        test_gamepad = vg.VX360Gamepad()
        # If we get here, the driver is working
        return True
    except Exception as e:
        print(f"ViGEmBus driver check failed: {e}")
        return False


def check_vigembus_device_manager():
    """
    Check if ViGEmBus appears in device manager using PowerShell.

    Returns:
        bool: True if device is found, False otherwise
    """
    try:
        # Use PowerShell to check device manager
        cmd = 'Get-PnpDevice | Where-Object {$_.FriendlyName -like "*Virtual Gamepad Emulation*"}'
        result = subprocess.run(
            ["powershell", "-Command", cmd], capture_output=True, text=True, timeout=10
        )

        return "Virtual Gamepad Emulation" in result.stdout
    except Exception as e:
        print(f"Device manager check failed: {e}")
        return False


def get_vigembus_download_url():
    """
    Get the latest ViGEmBus download URL from GitHub API.

    Returns:
        str: Download URL for the latest installer, or None if failed
    """
    try:
        api_url = "https://api.github.com/repos/ViGEm/ViGEmBus/releases/latest"
        response = requests.get(api_url, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Look for x64 installer
            for asset in data["assets"]:
                if "x64" in asset["name"] and asset["name"].endswith(".exe"):
                    return asset["browser_download_url"]

            # Fallback to any .exe file
            for asset in data["assets"]:
                if asset["name"].endswith(".exe"):
                    return asset["browser_download_url"]

    except Exception as e:
        print(f"Failed to get download URL: {e}")

    return None


def download_vigembus_installer():
    """
    Download the ViGEmBus installer to the current directory.

    Returns:
        str: Path to downloaded installer, or None if failed
    """
    try:
        download_url = get_vigembus_download_url()
        if not download_url:
            return None

        filename = "ViGEmBus_Setup_x64.exe"
        filepath = Path(filename)

        print(f"Downloading ViGEmBus installer from: {download_url}")

        response = requests.get(download_url, timeout=30)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(response.content)

        print(f"Downloaded installer to: {filepath.absolute()}")
        return str(filepath.absolute())

    except Exception as e:
        print(f"Failed to download installer: {e}")
        return None


def install_vigembus_driver():
    """
    Attempt to install the ViGEmBus driver by running the installer.

    Returns:
        bool: True if installation appears successful, False otherwise
    """
    try:
        installer_path = download_vigembus_installer()
        if not installer_path:
            return False

        print(f"Running installer: {installer_path}")

        # Run the installer with elevated privileges
        result = subprocess.run([installer_path], timeout=120)  # 2 minutes timeout

        return result.returncode == 0

    except Exception as e:
        print(f"Failed to install driver: {e}")
        return False


def show_installation_dialog():
    """
    Show a GUI dialog to guide the user through ViGEmBus installation.

    Returns:
        bool: True if user completed installation, False if cancelled
    """
    root = tk.Tk()
    root.withdraw()  # Hide main window

    # First, explain what's needed
    message = """ViGEmBus Driver Required

The Xbox Color Tracker requires the ViGEmBus driver to create virtual Xbox controllers.

This driver is safe and developed by the ViGEm project (used by many gaming applications).

Would you like to:
1. Download and install automatically
2. Go to the download page manually
3. Skip (application may not work properly)"""

    result = messagebox.askyesnocancel(
        "Driver Installation Required", message, icon="question"
    )

    if result is True:  # Yes - automatic installation
        try:
            # Show progress message
            progress_msg = messagebox.showinfo(
                "Installing Driver",
                "Downloading and installing ViGEmBus driver...\n\n"
                "Please wait and follow any installation prompts that appear.",
            )

            success = install_vigembus_driver()

            if success:
                messagebox.showinfo(
                    "Installation Complete",
                    "ViGEmBus driver has been installed successfully!\n\n"
                    "You may need to restart your computer for changes to take effect.",
                )
                return True
            else:
                messagebox.showerror(
                    "Installation Failed",
                    "Automatic installation failed. Please try manual installation.",
                )
                webbrowser.open("https://github.com/ViGEm/ViGEmBus/releases")
                return False

        except Exception as e:
            messagebox.showerror(
                "Installation Error",
                f"An error occurred during installation:\n{e}\n\n"
                "Please try manual installation.",
            )
            webbrowser.open("https://github.com/ViGEm/ViGEmBus/releases")
            return False

    elif result is False:  # No - manual installation
        webbrowser.open("https://github.com/ViGEm/ViGEmBus/releases")
        messagebox.showinfo(
            "Manual Installation",
            "Please download and run the ViGEmBus installer from the opened webpage.\n\n"
            "Look for 'ViGEmBus_Setup_x64.exe' in the latest release.",
        )
        return False

    else:  # Cancel - skip installation
        messagebox.showwarning(
            "Installation Skipped",
            "ViGEmBus driver installation was skipped.\n\n"
            "The virtual controller functionality will not work without this driver.",
        )
        return False


def ensure_vigembus_driver():
    """
    Comprehensive function to ensure ViGEmBus driver is installed and working.

    Returns:
        bool: True if driver is confirmed working, False otherwise
    """
    print("Checking ViGEmBus driver installation...")

    # First check if it's already working
    if check_vigembus_installed():
        print("✅ ViGEmBus driver is installed and working!")
        return True

    print("❌ ViGEmBus driver not detected or not working")

    # Check if it's installed but not working
    if check_vigembus_device_manager():
        print("⚠️  ViGEmBus device found in Device Manager but not working")
        messagebox.showwarning(
            "Driver Issue",
            "ViGEmBus driver is installed but not working properly.\n\n"
            "Try restarting your computer or reinstalling the driver.",
        )
        return False

    # Driver is not installed, prompt for installation
    print("Prompting user for driver installation...")
    installation_result = show_installation_dialog()

    if installation_result:
        # Re-check if installation was successful
        if check_vigembus_installed():
            print("✅ ViGEmBus driver successfully installed and working!")
            return True
        else:
            print("❌ Driver installation completed but still not working")
            return False

    return False


if __name__ == "__main__":
    # Test the driver detection
    print("ViGEmBus Driver Check")
    print("=" * 30)

    if ensure_vigembus_driver():
        print("Driver check completed successfully!")
    else:
        print("Driver check failed or was cancelled.")
        sys.exit(1)
