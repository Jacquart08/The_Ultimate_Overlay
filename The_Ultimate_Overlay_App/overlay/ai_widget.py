"""
AI widget for the overlay.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QProgressBar, QTextEdit, QToolTip, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QSize
from PyQt6.QtGui import QIcon, QFont, QCursor
import logging
import os
from The_Ultimate_Overlay_App.ai.config import AIConfig
from The_Ultimate_Overlay_App.ai.completion_system import CompletionSystem
from The_Ultimate_Overlay_App.ai.model_downloader import ModelDownloader
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

class AIWidget(QWidget):
    """Widget for AI features."""
    
    completion_ready = pyqtSignal(str)
    download_progress = pyqtSignal(int)
    download_complete = pyqtSignal()
    download_failed = pyqtSignal()
    load_complete = pyqtSignal()
    load_failed = pyqtSignal()
    
    def __init__(self, parent=None):
        logger.info("Initializing AIWidget")
        try:
            super().__init__(parent)
            logger.info("Super().__init__() completed")
            
            # Initialize state variables first
            self.is_enabled = False
            self.is_loading = False
            self.is_downloading = False
            self.explanation_widgets = []
            logger.info("State variables initialized")
            
            # Initialize components
            try:
                logger.info("Creating AIConfig")
                self.config = AIConfig()
                logger.info("AIConfig created")
                
                logger.info("Creating CompletionSystem")
                self.completion_system = CompletionSystem(self.config)
                logger.info("CompletionSystem created")
                
                logger.info("Creating ModelDownloader")
                self.model_downloader = ModelDownloader(self.config)
                logger.info("ModelDownloader created")
            except Exception as e:
                logger.error(f"Error initializing AI components: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Initialize with None to prevent further errors
                self.config = None
                self.completion_system = None
                self.model_downloader = None
            
            # Connect signals
            try:
                self.download_progress.connect(self.update_download_progress)
                self.download_complete.connect(self._download_complete)
                self.download_failed.connect(self._download_failed)
                self.load_complete.connect(self._load_complete)
                self.load_failed.connect(self._load_failed)
                logger.info("Signals connected")
            except Exception as e:
                logger.error(f"Error connecting signals: {str(e)}")
            
            # Set up UI
            try:
                self.setup_ui()
                logger.info("UI setup completed")
            except Exception as e:
                logger.error(f"Error setting up UI: {str(e)}")
            
            # Start periodic model status check
            try:
                self.status_timer = QTimer()
                self.status_timer.timeout.connect(self.refresh_model_status)
                self.status_timer.start(5000)  # Check every 5 seconds
                logger.info("Status timer started")
            except Exception as e:
                logger.error(f"Error starting status timer: {str(e)}")
            
            logger.info("AIWidget initialization completed")
            
        except Exception as e:
            logger.error(f"Error in AIWidget.__init__: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # AI toggle button
        self.toggle_button = QPushButton("AI")
        self.toggle_button.setCheckable(True)
        self.toggle_button.clicked.connect(self.toggle_ai)
        self.toggle_button.setFixedSize(60, 30)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #4d4d4d;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                border-color: #45a049;
                color: white;
            }
            QPushButton:disabled {
                background-color: #1d1d1d;
                color: #666666;
                border-color: #2d2d2d;
            }
        """)
        layout.addWidget(self.toggle_button)
        
        # Status label
        self.status_label = QLabel("AI: Off")
        self.status_label.setStyleSheet("color: #aeefff; font-size: 10px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #2d2d2d;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        
        # Initial model status check
        self.refresh_model_status()
    
    def refresh_model_status(self):
        """Check model status and update UI accordingly."""
        if self.is_downloading or self.is_loading:
            return  # Don't interrupt ongoing operations
            
        try:
            if not self.model_downloader.is_model_installed():
                self.toggle_button.setEnabled(True)
                self.status_label.setText("AI: Model not installed")
                self.toggle_button.setText("Download Model")
                self.toggle_button.setChecked(False)
                self.is_enabled = False
                
                # Ensure correct button connection
                try:
                    self.toggle_button.clicked.disconnect()
                except Exception:
                    pass
                self.toggle_button.clicked.connect(self.start_download)
            else:
                if not self.is_enabled:
                    self.toggle_button.setEnabled(True)
                    self.toggle_button.setText("AI")
                    self.status_label.setText("AI: Ready")
                    
                    # Ensure correct button connection
                    try:
                        self.toggle_button.clicked.disconnect()
                    except Exception:
                        pass
                    self.toggle_button.clicked.connect(self.toggle_ai)
        except Exception as e:
            logger.error(f"Error checking model status: {str(e)}")
            self.status_label.setText("AI: Error")
            self.toggle_button.setEnabled(False)
    
    def start_download(self):
        """Start model download with error handling."""
        if self.is_downloading:
            return
            
        try:
            self.is_downloading = True
            self.toggle_button.setEnabled(False)
            self.status_label.setText("AI: Downloading model...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Start download in a separate thread
            threading.Thread(target=self._download_thread, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error starting download: {str(e)}")
            self.is_downloading = False
            self.status_label.setText("AI: Download failed")
            self.toggle_button.setEnabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "Error", f"Failed to start download: {str(e)}")
    
    def _download_thread(self):
        """Handle download in background thread."""
        try:
            success = self.model_downloader.download_model(
                lambda p: self.download_progress.emit(p)
            )
            if success:
                self.download_complete.emit()
            else:
                self.download_failed.emit()
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            self.download_failed.emit()
    
    def update_download_progress(self, progress: int):
        """Update download progress from signal."""
        self.progress_bar.setValue(progress)
    
    def _download_complete(self):
        """Handle download completion."""
        try:
            logger.info("Download complete, attempting to load model...")
            self.is_downloading = False
            self.toggle_button.setEnabled(True)
            self.progress_bar.setVisible(False)
            
            if self.model_downloader.load_model():
                logger.info("Model loaded successfully")
                self.is_enabled = True
                self.toggle_button.setChecked(True)
                self.status_label.setText("AI: Ready")
                self.load_complete.emit()
                
                # Update button connection
                try:
                    self.toggle_button.clicked.disconnect()
                except Exception:
                    pass
                self.toggle_button.clicked.connect(self.toggle_ai)
            else:
                logger.error("Failed to load model after download")
                self.status_label.setText("AI: Load Failed")
                self.toggle_button.setChecked(False)
                self.load_failed.emit()
                # Show error message to user
                QMessageBox.critical(
                    self,
                    "Model Load Failed",
                    "Failed to load the AI model. Please check the logs for details."
                )
        except Exception as e:
            logger.error(f"Error in download completion handler: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.status_label.setText("AI: Error")
            self.toggle_button.setChecked(False)
            self.load_failed.emit()
            # Show error message to user
            QMessageBox.critical(
                self,
                "Model Load Error",
                f"An error occurred while loading the model: {str(e)}"
            )
    
    def _download_failed(self):
        """Handle download failure from signal."""
        self.is_downloading = False
        self.toggle_button.setEnabled(True)
        self.status_label.setText("AI: Download failed")
        self.progress_bar.setVisible(False)
        self.toggle_button.setText("Retry Download")
        
        try:
            self.toggle_button.clicked.disconnect()
        except Exception:
            pass
        self.toggle_button.clicked.connect(self.start_download)
        
        QMessageBox.warning(self, "Download Failed", 
                          "Failed to download the model. Please check your internet connection and try again.")
    
    def toggle_ai(self):
        """Toggle AI features with proper state management."""
        if self.is_downloading or self.is_loading:
            return
            
        self.is_enabled = self.toggle_button.isChecked()
        
        if self.is_enabled:
            self.start_loading()
        else:
            self.stop_loading()
    
    def start_loading(self):
        """Start loading the model."""
        try:
            self.is_loading = True
            logger.info("Enabling AI features")
            self.status_label.setText("AI: Loading...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Start loading in background thread
            threading.Thread(target=self._load_thread, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error starting model load: {str(e)}")
            self.load_failed.emit()
    
    def _load_thread(self):
        """Handle model loading in background thread."""
        try:
            success = self.completion_system.model_manager.load_model()
            if success:
                self.load_complete.emit()
            else:
                self.load_failed.emit()
        except Exception as e:
            logger.error(f"Load error: {str(e)}")
            self.load_failed.emit()
    
    def _load_complete(self):
        """Handle model load completion."""
        try:
            logger.info("Model load complete")
            self.is_loading = False
            self.is_enabled = True
            self.toggle_button.setChecked(True)
            self.toggle_button.setEnabled(True)
            self.status_label.setText("AI: Ready")
            self.progress_bar.setVisible(False)
            
            # Test the model with a simple completion
            test_completion = self.completion_system.get_completion("Test")
            if test_completion:
                logger.info("Model test successful")
            else:
                logger.warning("Model test failed - no completion generated")
                
        except Exception as e:
            logger.error(f"Error in load completion handler: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.status_label.setText("AI: Error")
            self.toggle_button.setChecked(False)
            # Show error message to user
            QMessageBox.critical(
                self,
                "Model Load Error",
                f"An error occurred while loading the model: {str(e)}"
            )
    
    def _load_failed(self):
        """Handle model load failure."""
        try:
            logger.error("Model load failed")
            self.is_enabled = False
            self.toggle_button.setChecked(False)
            self.status_label.setText("AI: Load Failed")
            # Show error message to user
            QMessageBox.critical(
                self,
                "Model Load Failed",
                "Failed to load the AI model. Please check the logs for details."
            )
        except Exception as e:
            logger.error(f"Error in load failure handler: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.status_label.setText("AI: Error")
            self.toggle_button.setChecked(False)
    
    def stop_loading(self):
        """Stop AI features and unload model."""
        try:
            logger.info("Disabling AI features")
            self.status_label.setText("AI: Off")
            self.progress_bar.setVisible(False)
            self.completion_system.model_manager.unload_model()
            self.is_enabled = False
        except Exception as e:
            logger.error(f"Error stopping AI: {str(e)}")
    
    def request_explanation(self, selected_text: str, context: dict):
        """Request an explanation for the selected text."""
        if not self.is_enabled or self.is_loading:
            logger.debug("AI is not enabled or still loading")
            return
            
        if not selected_text or not selected_text.strip():
            logger.debug("No text selected")
            return
            
        logger.info(f"Requesting explanation for text: {selected_text[:50]}...")
        
        # Show initial tooltip
        cursor_pos = context.get('cursor_pos', QCursor.pos())
        QToolTip.showText(cursor_pos, "Analyzing selected text...", self)
        
        try:
            # Generate explanation
            completion = self._generate_explanation(selected_text, context)
            
            if completion:
                logger.info(f"Generated completion: {completion[:50]}...")
                # Show completion in tooltip
                QToolTip.showText(cursor_pos, completion, self)
            else:
                logger.warning("No completion generated")
                QToolTip.showText(cursor_pos, "Could not generate explanation", self)
                
        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            QToolTip.showText(cursor_pos, f"Error: {str(e)}", self)

    def _generate_explanation(self, selected_text: str, context: dict) -> Optional[str]:
        """Generate an explanation for the selected text."""
        try:
            if not self.model_manager or not self.model_manager.is_loaded():
                logger.warning("Model not available for completion")
                return None
                
            # Prepare prompt with context
            prompt = f"Context: {context.get('app_name', 'Unknown')} - {context.get('window_title', '')}\n"
            prompt += f"Selected text: {selected_text}\n"
            prompt += "Please provide a helpful explanation or completion:"
            
            # Get completion from model
            completion = self.model_manager.get_completion(prompt)
            
            if completion:
                logger.info(f"Generated completion: {completion[:50]}...")
                return completion
            else:
                logger.warning("No completion generated")
                return None
                
        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            return None
    
    def copy_explanation(self):
        """Copy explanation to clipboard with error handling."""
        try:
            text = QToolTip.text()
            if text:
                from PyQt6.QtWidgets import QApplication
                QApplication.clipboard().setText(text)
        except Exception as e:
            logger.error(f"Error copying explanation: {str(e)}")
    
    def clear_explanation(self):
        """Clear explanation with error handling."""
        try:
            QToolTip.hideText()
        except Exception as e:
            logger.error(f"Error clearing explanation: {str(e)}") 