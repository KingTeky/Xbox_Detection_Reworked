#!/usr/bin/env python3
"""
Test script to verify logo integration in the Xbox Color Tracker
"""
import tkinter as tk
from tkinter import ttk
import os
from PIL import Image, ImageTk


def test_logo_loading():
    """Test if the logo can be loaded successfully"""
    print("Testing logo loading...")

    # Create test window
    root = tk.Tk()
    root.title("Logo Test")
    root.geometry("400x300")

    try:
        # Test logo path
        logo_path = os.path.join(
            os.path.dirname(__file__), "All_icons_pngs", "KT_OD_App_iconV6.png"
        )
        print(f"Looking for logo at: {logo_path}")

        if os.path.exists(logo_path):
            print("✅ Logo file found!")

            # Load and display logo
            logo_img = Image.open(logo_path)
            print(f"Original logo size: {logo_img.size}")

            # Resize for display
            logo_img = logo_img.resize((120, 120), Image.LANCZOS)
            logo_photo = ImageTk.PhotoImage(logo_img)

            # Display in window
            frame = ttk.LabelFrame(root, text="Logo Test", padding="20")
            frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            logo_label = tk.Label(frame, image=logo_photo)
            logo_label.pack(pady=10)

            text_label = ttk.Label(
                frame,
                text="Logo loaded successfully!",
                font=("Arial", 12, "bold"),
                foreground="green",
            )
            text_label.pack(pady=10)

            # Keep a reference to prevent garbage collection
            root.logo_photo = logo_photo

            print("✅ Logo loaded and displayed successfully!")

        else:
            print("❌ Logo file not found!")
            error_label = ttk.Label(
                root,
                text="Logo file not found!",
                font=("Arial", 12, "bold"),
                foreground="red",
            )
            error_label.pack(expand=True)

    except Exception as e:
        print(f"❌ Error loading logo: {e}")
        error_label = ttk.Label(
            root, text=f"Error: {e}", font=("Arial", 10), foreground="red"
        )
        error_label.pack(expand=True)

    # Run for 3 seconds then close
    root.after(3000, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    test_logo_loading()
    print("Logo test completed!")
