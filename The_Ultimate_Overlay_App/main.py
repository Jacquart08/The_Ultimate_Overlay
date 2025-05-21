#!/usr/bin/env python3
"""
UltimateOverlay entry point.
Run this file to start the overlay application.
"""
try:
    # Try direct import first (when running from within the directory)
    from overlay.window import OverlayWindow
except ImportError:
    # Fallback to package import (when installed as a package)
    from The_Ultimate_Overlay_App.overlay.window import OverlayWindow

if __name__ == "__main__":
    window = OverlayWindow()
    window.run() 