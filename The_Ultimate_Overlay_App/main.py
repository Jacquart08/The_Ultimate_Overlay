#!/usr/bin/env python3
"""
UltimateOverlay entry point.
Run this file to start the overlay application.
"""
from overlay.window import OverlayWindow

if __name__ == "__main__":
    window = OverlayWindow()
    window.run() 