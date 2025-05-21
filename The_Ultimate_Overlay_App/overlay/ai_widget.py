"""
AI widget for the overlay.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QProgressBar, QTextEdit, QToolTip, QMessageBox, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint, QSize, QRect
from PyQt6.QtGui import QIcon, QFont, QCursor
import logging
import os
from The_Ultimate_Overlay_App.ai.config import AIConfig
from The_Ultimate_Overlay_App.ai.completion_system import CompletionSystem
from The_Ultimate_Overlay_App.ai.model_downloader import ModelDownloader
import threading
import time

logger = logging.getLogger(__name__)

class AIWidget(QWidget):
    """Widget for AI features."""
    
    completion_ready = pyqtSignal(str, str)  # completion, query_text
    download_progress = pyqtSignal(int)
    download_complete = pyqtSignal()
    download_failed = pyqtSignal()
    load_complete = pyqtSignal()
    load_failed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize state variables first
        self.is_enabled = False
        self.is_loading = False
        self.is_downloading = False
        self.explanation_widgets = []
        self._pending_text = None
        self._pending_context = None
        self._query_text = None
        
        # Initialize components
        self.config = AIConfig()
        self.completion_system = CompletionSystem(self.config)
        self.model_downloader = ModelDownloader(self.config)
        
        # Connect signals
        self.download_progress.connect(self.update_download_progress)
        self.download_complete.connect(self._download_complete)
        self.download_failed.connect(self._download_failed)
        self.load_complete.connect(self._load_complete)
        self.load_failed.connect(self._load_failed)
        
        # Set up UI
        self.setup_ui()
        
        # Start periodic model status check
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.refresh_model_status)
        self.status_timer.start(5000)  # Check every 5 seconds
        
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
    
    def request_explanation(self, selected_text, context=None, query_text=None):
        """Request an explanation with proper error handling."""
        if not selected_text or not self.is_enabled or self.is_loading:
            logger.warning(f"Cannot generate explanation: enabled={self.is_enabled}, loading={self.is_loading}")
            return
            
        try:
            # Store selected text and context for processing
            self._pending_text = selected_text
            self._pending_context = context
            self._query_text = query_text
            
            # Use QTimer to process in the main thread
            QTimer.singleShot(0, self._process_explanation_request)
            
        except Exception as e:
            logger.error(f"Error requesting explanation: {str(e)}")
    
    def _process_explanation_request(self):
        """Process explanation request in the main thread."""
        try:
            if not hasattr(self, '_pending_text') or not self._pending_text:
                return
                
            # Get stored text and context
            selected_text = self._pending_text
            context = self._pending_context
            query_text = self._query_text
            
            # Show a temporary status message
            self.status_label.setText("AI: Generating...")
            
            # Start explanation in background thread
            threading.Thread(target=self._generate_explanation, 
                           args=(selected_text, context, query_text),
                           daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error processing explanation request: {str(e)}")
            
        finally:
            # Clear pending data
            self._pending_text = None
            self._pending_context = None
            self._query_text = None
    
    def _generate_explanation(self, selected_text, context=None, query_text=None):
        """Generate explanation with error handling."""
        try:
            logger.info(f"Generating explanation for text: {selected_text[:50]}...")
            
            # Generate completion using the model
            completion = self.completion_system.get_completion(
                text=selected_text,
                context=context
            )
            
            # Use Qt's signal/slot to update UI from the main thread
            if completion:
                logger.info("Generated completion successfully")
                # Update status
                QTimer.singleShot(0, lambda: self.status_label.setText("AI: Ready"))
                # Emit the completion signal to display in overlay
                self.completion_ready.emit(completion, query_text)
            else:
                logger.warning("No completion generated")
                QTimer.singleShot(0, lambda: self.status_label.setText("AI: Failed"))
                # Emit an error message for display
                self.completion_ready.emit("No explanation could be generated. Please try with different text.", query_text)
            
        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Set status to error and emit error message
            QTimer.singleShot(0, lambda: self.status_label.setText("AI: Error"))
            self.completion_ready.emit(f"Error generating explanation: {str(e)}", query_text) 