"""
AI widget for the overlay.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QProgressBar
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon
import logging
import os
from The_Ultimate_Overlay_App.ai.config import AIConfig
from The_Ultimate_Overlay_App.ai.completion_system import CompletionSystem
from The_Ultimate_Overlay_App.ai.model_downloader import ModelDownloader
import threading

logger = logging.getLogger(__name__)

class AIWidget(QWidget):
    """Widget for AI features."""
    
    completion_ready = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = AIConfig()
        self.completion_system = CompletionSystem(self.config)
        self.model_downloader = ModelDownloader(self.config)
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # AI toggle button
        self.toggle_button = QPushButton()
        self.toggle_button.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "../resources/ai_off.svg")))
        self.toggle_button.setCheckable(True)
        self.toggle_button.clicked.connect(self.toggle_ai)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
                min-width: 24px;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                border-color: #45a049;
            }
        """)
        layout.addWidget(self.toggle_button)
        
        # Status label
        self.status_label = QLabel("AI: Off")
        self.status_label.setStyleSheet("color: #aeefff; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 2px;
                text-align: center;
                background-color: #2d2d2d;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        
        # Check if model is installed
        if not self.model_downloader.is_model_installed():
            self.show_download_prompt()
        else:
            logger.info("Model is installed, enabling AI features")
            self.toggle_button.setEnabled(True)
    
    def show_download_prompt(self):
        """Show download prompt if model is not installed."""
        self.toggle_button.setEnabled(False)
        self.status_label.setText("AI: Model not installed")
        self.toggle_button.setText("Download Model")
        self.toggle_button.clicked.disconnect()
        self.toggle_button.clicked.connect(self.start_download)
    
    def start_download(self):
        """Start model download."""
        self.toggle_button.setEnabled(False)
        self.status_label.setText("AI: Downloading model...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        success = self.model_downloader.download_model(self.update_download_progress)
        if success:
            self.download_complete()
        else:
            self.status_label.setText("AI: Download failed")
            self.toggle_button.setEnabled(True)
            self.progress_bar.setVisible(False)
    
    def update_download_progress(self, progress: int):
        """Update download progress."""
        self.progress_bar.setValue(progress)
    
    def download_complete(self):
        """Handle download completion."""
        self.toggle_button.setEnabled(True)
        self.status_label.setText("AI: Ready")
        self.progress_bar.setVisible(False)
        self.toggle_button.setText("")
        self.toggle_button.clicked.disconnect()
        self.toggle_button.clicked.connect(self.toggle_ai)
    
    def toggle_ai(self):
        """Toggle AI features on/off."""
        if self.toggle_button.isChecked():
            logger.info("Enabling AI features")
            self.status_label.setText("AI: Loading...")
            self.toggle_button.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "../resources/ai_on.svg")))
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Start loading the model
            self.completion_system.model_manager.load_model()
            
            # Start progress update timer
            self._start_progress_timer()
        else:
            logger.info("Disabling AI features")
            self.status_label.setText("AI: Off")
            self.toggle_button.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "../resources/ai_off.svg")))
            self.progress_bar.setVisible(False)
            # Unload the model
            self.completion_system.model_manager.unload_model()
    
    def _start_progress_timer(self):
        """Start a timer to update loading progress."""
        def update_progress():
            if not self.completion_system.model_manager.is_model_loading():
                self.progress_bar.setVisible(False)
                if self.completion_system.model_manager.is_model_available():
                    self.status_label.setText("AI: Ready")
                else:
                    self.status_label.setText("AI: Failed to load")
                    self.toggle_button.setChecked(False)
                return
            
            progress = self.completion_system.model_manager.get_loading_progress()
            self.progress_bar.setValue(progress)
            QTimer.singleShot(100, update_progress)
        
        update_progress()
    
    def request_completion(self, content: str, cursor_position: int = 0, selection: str = None, file_extension: str = None, app_name: str = None):
        """Request a completion from the AI system."""
        if not self.toggle_button.isChecked():
            return
            
        if not self.completion_system.model_manager.is_model_available():
            if self.completion_system.model_manager.is_model_loading():
                self.status_label.setText("AI: Loading...")
            else:
                self.status_label.setText("AI: Model not available")
            return
            
        # Create context dictionary
        context = {
            'content': content,
            'cursor_position': cursor_position,
            'selection': selection,
            'file_extension': file_extension,
            'app_name': app_name
        }
        
        # Show generating status
        self.status_label.setText("AI: Generating...")
            
        # Get completion in a background thread
        def generate_completion():
            completion = self.completion_system.model_manager.get_completion(content, context)
            if completion:
                self.completion_ready.emit(completion)
                self.status_label.setText("AI: Ready")
            else:
                self.status_label.setText("AI: Generation failed")
        
        threading.Thread(target=generate_completion, daemon=True).start() 