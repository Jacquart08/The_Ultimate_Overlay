#!/usr/bin/env python3
"""
Main entry point for the Ultimate Overlay application.
"""
import sys
import logging
from PyQt6.QtWidgets import QApplication
from The_Ultimate_Overlay_App.overlay.window import OverlayWindow

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the application."""
    try:
        logger.info("Starting Ultimate Overlay application")
        app = QApplication(sys.argv)
        
        # Create and run the overlay window
        overlay = OverlayWindow()
        exit_code = overlay.run()
        
        logger.info(f"Application exiting with code: {exit_code}")
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main() 