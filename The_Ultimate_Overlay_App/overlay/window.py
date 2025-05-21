"""
UltimateOverlay - Overlay window logic.
Provides a resizable, scrollable, context-aware overlay with Home/Read buttons.
"""
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QScrollArea, QPushButton, QHBoxLayout, QToolTip, QSizePolicy, QLineEdit, QToolButton, QListWidget
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QGuiApplication, QCursor
import sys
from The_Ultimate_Overlay_App.context.detector import get_active_window_title
from The_Ultimate_Overlay_App.context.shortcuts import get_shortcuts_for_app
from The_Ultimate_Overlay_App.overlay.ai_widget import AIWidget
import json
import os
import threading
import keyboard
import webbrowser
import re
import time
import win32gui
import win32con
import win32com.client
import win32clipboard
import pythoncom
import ctypes
import logging
from typing import Optional
from The_Ultimate_Overlay_App.ai.completion_system import CompletionSystem
from The_Ultimate_Overlay_App.ai.config import AIConfig
import win32api

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create console handler if not already exists
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Initialize COM in the main thread
pythoncom.CoInitialize()

KNOWLEDGE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'knowledge.json')
FAVORITES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'favorites.json')

# Mapping for official documentation URLs
DOC_BASE_URLS = {
    'Python': 'https://docs.python.org/3/library/',
    'SQL': 'https://www.w3schools.com/sql/sql_{}.asp',
    'R': 'https://stat.ethz.ch/R-manual/R-devel/library/base/html/{}.html',
    'SQL Server Management Studio': 'https://learn.microsoft.com/en-us/sql/t-sql/statements/{}',
    'RStudio': 'https://rstudio.github.io/cheatsheets/',
    'Notepad': 'https://support.microsoft.com/en-us/windows/notepad-help-3e4e8a5e-7b6b-4c2a-8b8b-7a1e3c1b1b1b',
    'Cursor': 'https://support.microsoft.com/en-us/windows/keyboard-shortcuts-in-windows-4a8a1d4a-5e3e-4e3e-8e3e-4e3e4e3e4e3e',
}

# Helper to get doc URL for a knowledge/shortcut item
def get_doc_url(language, title):
    if not language or not title:
        return None
    base = DOC_BASE_URLS.get(language)
    if not base:
        return None
    if '{}' in base:
        # Insert the function/keyword, lowercased and stripped of symbols
        key = title.lower().replace(' ', '').replace('(', '').replace(')', '').replace('<-', '').replace('+', '').replace(':', '')
        return base.format(key)
    return base

def load_knowledge():
    try:
        with open(KNOWLEDGE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def load_favorites():
    try:
        with open(FAVORITES_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"knowledge": [], "shortcuts": []}

def save_favorites(favs):
    with open(FAVORITES_PATH, 'w', encoding='utf-8') as f:
        json.dump(favs, f, indent=2)

class OverlayLabel(QLabel):
    def __init__(self, text, tooltip, parent=None):
        super().__init__(text, parent)
        self._tooltip = tooltip
        self.setToolTip(tooltip)
        self.setEnabled(True)
    def enterEvent(self, event):
        QToolTip.showText(self.mapToGlobal(self.rect().center()), self._tooltip, self)
        super().enterEvent(event)
    def leaveEvent(self, event):
        QToolTip.hideText()
        super().leaveEvent(event)

class OverlayRowWidget(QWidget):
    def __init__(self, name_label, summary_label, tooltip, is_fav, on_pin_clicked, on_copy_clicked, on_doc_clicked, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(name_label)
        layout.addWidget(summary_label)
        # Pin button
        self.pin_btn = QToolButton()
        self.pin_btn.setIcon(QIcon.fromTheme('star' if is_fav else 'star-outline'))
        self.pin_btn.setCheckable(True)
        self.pin_btn.setChecked(is_fav)
        self.pin_btn.setStyleSheet('QToolButton { border: none; padding: 0 6px; }')
        self.pin_btn.clicked.connect(on_pin_clicked)
        layout.addWidget(self.pin_btn)
        # Copy button
        self.copy_btn = QToolButton()
        self.copy_btn.setIcon(QIcon.fromTheme('edit-copy'))
        self.copy_btn.setStyleSheet('QToolButton { border: none; padding: 0 6px; }')
        self.copy_btn.setToolTip('Copy to clipboard')
        self.copy_btn.clicked.connect(on_copy_clicked)
        layout.addWidget(self.copy_btn)
        # Doc button
        self.doc_btn = QToolButton()
        self.doc_btn.setIcon(QIcon(os.path.join(os.path.dirname(__file__), '../resources/web.svg')))
        self.doc_btn.setStyleSheet('QToolButton { border: none; padding: 0 6px; }')
        self.doc_btn.setToolTip('Open official documentation')
        self.doc_btn.clicked.connect(on_doc_clicked)
        layout.addWidget(self.doc_btn)
        self.setLayout(layout)
        self._tooltip = tooltip
        self._default_bg = self.palette().color(self.backgroundRole())
        # Install event filter for robust highlight
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self:
            if event.type() == event.Type.Enter:
                # Only highlight if mouse is truly over the row, not a child
                if self.rect().contains(self.mapFromGlobal(QCursor.pos())):
                    QToolTip.showText(self.mapToGlobal(self.rect().center()), self._tooltip, self)
                    self.setStyleSheet("background: #3a7bd5; border-radius: 7px;")
            elif event.type() == event.Type.Leave:
                QToolTip.hideText()
                self.setStyleSheet("")
        return super().eventFilter(obj, event)

    def set_highlighted(self, highlighted: bool):
        if highlighted:
            QToolTip.showText(self.mapToGlobal(self.rect().center()), self._tooltip, self)
            self.setStyleSheet("background: #3a7bd5; border-radius: 7px;")
        else:
            QToolTip.hideText()
            self.setStyleSheet("")

class OverlayWindow:
    def __init__(self):
        logger.info("Initializing OverlayWindow")
        try:
            # Create QApplication instance if it doesn't exist
            if not QApplication.instance():
                self.app = QApplication(sys.argv)
                logger.info("QApplication created")
            else:
                self.app = QApplication.instance()
                logger.info("Using existing QApplication instance")
            
            # Create the overlay widget
            self.window = MovableOverlayWidget()
            logger.info("MovableOverlayWidget created")
            
            # Set window position to center of screen
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.window.width()) // 2
            y = (screen.height() - self.window.height()) // 2
            self.window.move(x, y)
            
        except Exception as e:
            logger.error(f"Error in OverlayWindow.__init__: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def run(self):
        logger.info("Starting OverlayWindow.run()")
        try:
            logger.info("About to show window")
            # Add a small delay before showing the window
            QTimer.singleShot(100, self._show_window)
            logger.info("Window show scheduled")
            
            # Start the event loop and store the result
            result = self.app.exec()
            logger.info(f"Event loop ended with result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Exception in OverlayWindow.run(): {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            print("Exception in OverlayWindow.run():", e)
            traceback.print_exc()
            return 1
        finally:
            logger.info("Cleaning up COM")
            pythoncom.CoUninitialize()
    
    def _show_window(self):
        """Show window with proper initialization."""
        try:
            logger.info("Showing window")
            self.window.show()
            # Add a small delay to ensure window is properly initialized
            QTimer.singleShot(100, self._check_window_state)
        except Exception as e:
            logger.error(f"Error showing window: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _check_window_state(self):
        """Check if the window is still valid and visible."""
        try:
            if not self.window.isVisible():
                logger.error("Window is not visible after initialization")
                self.window.show()
            if not self.window.isActiveWindow():
                logger.warning("Window is not active after initialization")
                self.window.activateWindow()
                self.window.raise_()
        except Exception as e:
            logger.error(f"Error checking window state: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

class MovableOverlayWidget(QWidget):
    ctrl_changed = pyqtSignal()
    def __init__(self):
        logger.info("Initializing MovableOverlayWidget")
        try:
            super().__init__()
            logger.info("Super().__init__() completed")
            
            # Initialize COM for this thread
            pythoncom.CoInitialize()
            logger.info("COM initialized")
            
            # Set window flags to make it completely non-interactive except for dragging
            self.setWindowFlags(
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool |
                Qt.WindowType.FramelessWindowHint
            )
            logger.info("Window flags set")
            
            # Disable focus policy completely
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            
            # Make all child widgets non-focusable
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)
            self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
            self.setAttribute(Qt.WidgetAttribute.WA_NoChildEventsForParent, True)
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            
            # Add a border for better visibility
            self.setStyleSheet("""
                QWidget {
                    background-color: rgba(40, 40, 40, 0.95);
                    border: 1px solid rgba(100, 100, 100, 0.5);
                    border-radius: 5px;
                }
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    border: none;
                    background: rgba(60, 60, 60, 0.5);
                    width: 10px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: rgba(100, 100, 100, 0.5);
                    min-height: 20px;
                    border-radius: 5px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QLineEdit {
                    background-color: rgba(60, 60, 60, 0.8);
                    border: 1px solid rgba(100, 100, 100, 0.5);
                    border-radius: 3px;
                    padding: 5px;
                    color: white;
                }
            """)
            
            self.setWindowTitle("UltimateOverlay")
            self.setWindowOpacity(0.95)
            self.setMinimumSize(250, 100)
            self.resize(350, 200)
            logger.info("Window properties set")
            
            self.home_locked = False
            self.last_real_window_title = None
            self._stop_monitor = False
            self._monitor_thread = None
            self._ctrl_listener_thread = None
            self._initialized = False
            logger.info("State variables initialized")

            # Create main layout with proper spacing
            main_layout = QVBoxLayout()
            main_layout.setSpacing(8)
            main_layout.setContentsMargins(10, 10, 10, 10)
            logger.info("Main layout created")
            
            # Top row with Home/Read/AI buttons
            top_layout = QHBoxLayout()
            top_layout.setSpacing(8)
            logger.info("Top layout created")
            
            # Home button
            self.home_button = QPushButton("Home")
            self.home_button.setFixedSize(60, 30)
            self.home_button.setStyleSheet("""
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
            """)
            self.home_button.clicked.connect(self.lock_home)
            top_layout.addWidget(self.home_button)
            logger.info("Home button created and added")
            
            # Read button
            self.read_button = QPushButton("Read")
            self.read_button.setFixedSize(60, 30)
            self.read_button.setStyleSheet("""
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
            """)
            self.read_button.clicked.connect(self.unlock_home)
            top_layout.addWidget(self.read_button)
            logger.info("Read button created and added")
            
            # AI button
            logger.info("Creating AI widget")
            self.ai_widget = AIWidget()
            logger.info("AI widget created")
            self.ai_widget.toggle_button.setFixedSize(60, 30)
            self.ai_widget.toggle_button.setStyleSheet("""
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
            top_layout.addWidget(self.ai_widget.toggle_button)
            logger.info("AI button added to layout")
            
            main_layout.addLayout(top_layout)
            logger.info("Top layout added to main layout")

            # Context label
            self.context_label = QLabel()
            self.context_label.setStyleSheet("color: #aeefff; font-size: 12px; padding: 2px 0 4px 0;")
            main_layout.addWidget(self.context_label)
            logger.info("Context label created and added")

            # Search bar
            self.search_bar = QLineEdit()
            self.search_bar.setPlaceholderText("Search...")
            self.search_bar.textChanged.connect(self.update_overlay)
            main_layout.addWidget(self.search_bar)
            logger.info("Search bar created and added")

            # Create scroll area with proper styling
            self.scroll = QScrollArea()
            self.scroll.setWidgetResizable(True)
            self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            self.content_widget = QWidget()
            self.content_layout = QVBoxLayout()
            self.content_layout.setSpacing(4)
            self.content_layout.setContentsMargins(0, 0, 0, 0)
            self.content_widget.setLayout(self.content_layout)
            self.scroll.setWidget(self.content_widget)
            main_layout.addWidget(self.scroll)
            self.setLayout(main_layout)
            logger.info("Scroll area and content layout created and added")

            self._drag_active = False
            self._drag_position = QPoint()

            # Timer for auto-updating shortcuts
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.update_shortcuts)
            logger.info("Timer created")

            self.ctrl_pressed = False
            self.knowledge = load_knowledge()
            self.favorites = load_favorites()
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.has_focus = False
            self.block_updates = False
            self.force_homepage = False
            self.ctrl_changed.connect(self.update_overlay)
            logger.info("State initialized and signals connected")
            
            # Mark as initialized
            self._initialized = True
            logger.info("MovableOverlayWidget initialization completed")
            
        except Exception as e:
            logger.error(f"Error in MovableOverlayWidget.__init__: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def showEvent(self, event):
        """Handle show event with improved error handling."""
        try:
            logger.info("Window show event received")
            super().showEvent(event)
            
            if not self._initialized:
                logger.error("Window not properly initialized")
                return
                
            # Don't activate window or raise it to prevent crashes
            # Just ensure window stays on top
            self.setWindowState(Qt.WindowState.WindowActive)
            # Force update
            self.update()
            
            # Start monitoring threads if not already started
            if not hasattr(self, '_monitor_thread') or not self._monitor_thread.is_alive():
                self._start_cursor_monitor()
            if not hasattr(self, '_ctrl_listener_thread') or not self._ctrl_listener_thread.is_alive():
                self._start_ctrl_listener()
                
            # Start the update timer if not already started
            if hasattr(self, 'timer') and not self.timer.isActive():
                self.timer.start(1000)
                
        except Exception as e:
            logger.error(f"Error in showEvent: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def closeEvent(self, event):
        """Handle window close event with improved error handling."""
        try:
            logger.info("Window close event received")
            # Stop monitoring threads
            self._stop_monitor = True
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=1.0)
            if self._ctrl_listener_thread and self._ctrl_listener_thread.is_alive():
                self._ctrl_listener_thread.join(timeout=1.0)
            # Stop timer
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()
            # Cleanup COM
            pythoncom.CoUninitialize()
            super().closeEvent(event)
        except Exception as e:
            logger.error(f"Error in closeEvent: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            event.accept()  # Ensure window closes even if there's an error

    def _start_ctrl_listener(self):
        """Start Ctrl key listener in a separate thread."""
        def listen_ctrl():
            while not self._stop_monitor:
                try:
                    ctrl_now = keyboard.is_pressed('ctrl')
                    if ctrl_now != self.ctrl_pressed:
                        print(f"[DEBUG] Ctrl state changed: {ctrl_now}")
                        self.ctrl_pressed = ctrl_now
                        self.ctrl_changed.emit()
                    time.sleep(0.05)
                except Exception as e:
                    logger.error(f"Error in Ctrl listener: {str(e)}")
                    time.sleep(1)  # Longer delay on error
        self._ctrl_listener_thread = threading.Thread(target=listen_ctrl, daemon=True)
        self._ctrl_listener_thread.start()

    def focusInEvent(self, event):
        """Handle focus in event with improved error handling."""
        try:
            logger.info("Focus in event received")
            # Don't set focus or update state to prevent crashes
            event.ignore()
        except Exception as e:
            logger.error(f"Error in focusInEvent: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            event.ignore()

    def focusOutEvent(self, event):
        """Handle focus out event with improved error handling."""
        try:
            logger.info("Focus out event received")
            # Don't update state to prevent crashes
            event.ignore()
        except Exception as e:
            logger.error(f"Error in focusOutEvent: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            event.ignore()

    def detect_language_by_extension(self, window_title):
        ext_to_lang = {
            '.py': 'Python', '.sql': 'SQL', '.r': 'R', '.ttl': 'Ttl', '.sas': 'SAS', '.ipynb': 'Python',
            '.js': 'JavaScript', '.ts': 'TypeScript', '.c': 'C', '.cpp': 'C++', '.h': 'C/C++ Header', '.hpp': 'C++ Header',
            '.java': 'Java', '.html': 'HTML', '.htm': 'HTML', '.css': 'CSS', '.md': 'Markdown', '.json': 'JSON',
            '.xml': 'XML', '.yml': 'YAML', '.yaml': 'YAML', '.sh': 'Shell', '.bat': 'Batch', '.ps1': 'PowerShell',
        }
        if window_title:
            title_lower = window_title.lower()
            matches = list(re.finditer(r'\.[a-z0-9]+', title_lower))
            for match in reversed(matches):
                ext = match.group(0)
                if ext in ext_to_lang:
                    return ext_to_lang[ext]
        return None

    def detect_app_by_name(self, window_title):
        app_to_lang = {
            'rstudio': 'R', 'sql server management studio': 'SQL', 'jupyter': 'Python', 'spyder': 'Python',
            'pycharm': 'Python', 'vscode': 'Python', 'visual studio code': 'Python', 'sublime text': 'Python',
            'notepad++': 'Text', 'notepad': 'Text', 'atom': 'JavaScript', 'webstorm': 'JavaScript', 'intellij': 'Java',
            'eclipse': 'Java', 'visual studio': 'C++', 'android studio': 'Java', 'markdown': 'Markdown',
            'chrome': 'Web', 'firefox': 'Web', 'edge': 'Web', 'internet explorer': 'Web', 'excel': 'Excel',
            'word': 'Word', 'powerpoint': 'PowerPoint', 'outlook': 'Outlook', 'onenote': 'OneNote', 'teams': 'Teams',
            'windows terminal': 'Shell', 'cmd.exe': 'Shell', 'powershell': 'PowerShell',
            'cursor': 'Python', 'steam': 'Steam',
        }
        if window_title:
            title_lower = window_title.lower()
            for app, lang in app_to_lang.items():
                if app in title_lower:
                    return app
        return None

    def create_app_home(self, app_name):
        print(f"[DEBUG] create_app_home called with app_name: {app_name}")
        home = QWidget()
        layout = QVBoxLayout(home)
        # Title
        title = QLabel(f"{app_name} Home")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        layout.addWidget(title)
        # Add app-specific content
        if 'excel' in app_name.lower():
            print("[DEBUG] add_excel_home called")
            self.add_excel_home(layout)
        elif 'word' in app_name.lower():
            print("[DEBUG] add_word_home called")
            self.add_word_home(layout)
        elif any(browser in app_name.lower() for browser in ['chrome', 'firefox', 'edge', 'internet explorer']):
            print("[DEBUG] add_browser_home called")
            self.add_browser_home(layout)
        elif 'steam' in app_name.lower():
            print("[DEBUG] add_steam_home called")
            self.add_steam_home(layout)
        else:
            print("[DEBUG] add_generic_home called")
            self.add_generic_home(layout, app_name)
        return home

    def add_excel_home(self, layout):
        recent_label = QLabel("Recent Workbooks")
        recent_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(recent_label)
        workbooks_list = QListWidget()
        workbooks_list.addItems(["Financial Report.xlsx", "Sales Data.xlsx", "Inventory.xlsx"])
        workbooks_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #3d3d3d;
            }
        """)
        layout.addWidget(workbooks_list)
        actions_label = QLabel("Quick Actions")
        actions_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(actions_label)
        actions_layout = QHBoxLayout()
        new_btn = QPushButton("New Workbook")
        template_btn = QPushButton("Templates")
        recent_btn = QPushButton("Recent")
        for btn in [new_btn, template_btn, recent_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
            """)
            actions_layout.addWidget(btn)
        layout.addLayout(actions_layout)

    def add_word_home(self, layout):
        recent_docs = QLabel("Recent Documents")
        recent_docs.setStyleSheet("color: #ffffff;")
        layout.addWidget(recent_docs)
        docs_list = QListWidget()
        docs_list.addItems(["Document1.docx", "Document2.docx", "Document3.docx"])
        docs_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #3d3d3d;
            }
        """)
        layout.addWidget(docs_list)

    def add_browser_home(self, layout):
        bookmarks_label = QLabel("Quick Bookmarks")
        bookmarks_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(bookmarks_label)
        bookmarks_list = QListWidget()
        bookmarks_list.addItems(["Google", "GitHub", "Stack Overflow", "YouTube"])
        bookmarks_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #3d3d3d;
            }
        """)
        layout.addWidget(bookmarks_list)
        actions_label = QLabel("Quick Actions")
        actions_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(actions_label)
        actions_layout = QHBoxLayout()
        new_tab_btn = QPushButton("New Tab")
        incognito_btn = QPushButton("Incognito")
        history_btn = QPushButton("History")
        for btn in [new_tab_btn, incognito_btn, history_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
            """)
            actions_layout.addWidget(btn)
        layout.addLayout(actions_layout)

    def add_steam_home(self, layout):
        recent_label = QLabel("Recent Games")
        recent_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(recent_label)
        games_list = QListWidget()
        games_list.addItems(["Counter-Strike 2", "Dota 2", "Team Fortress 2"])
        games_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #3d3d3d;
            }
        """)
        layout.addWidget(games_list)
        actions_label = QLabel("Quick Actions")
        actions_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(actions_label)
        actions_layout = QHBoxLayout()
        library_btn = QPushButton("Library")
        store_btn = QPushButton("Store")
        friends_btn = QPushButton("Friends")
        for btn in [library_btn, store_btn, friends_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
            """)
            actions_layout.addWidget(btn)
        layout.addLayout(actions_layout)

    def add_generic_home(self, layout, app_name):
        recent_label = QLabel("Recent Items")
        recent_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(recent_label)
        items_list = QListWidget()
        items_list.addItems([f"Item 1 - {app_name}", f"Item 2 - {app_name}", f"Item 3 - {app_name}"])
        items_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #3d3d3d;
            }
        """)
        layout.addWidget(items_list)
        actions_label = QLabel("Quick Actions")
        actions_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(actions_label)
        actions_layout = QHBoxLayout()
        new_btn = QPushButton("New")
        open_btn = QPushButton("Open")
        settings_btn = QPushButton("Settings")
        for btn in [new_btn, open_btn, settings_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
            """)
            actions_layout.addWidget(btn)
        layout.addLayout(actions_layout)

    def update_overlay(self):
        """Update overlay content with error handling."""
        try:
            # Skip update if mouse is over the window to prevent focus issues
            if self.rect().contains(self.mapFromGlobal(QCursor.pos())):
                logger.debug("Skipping update - mouse over window")
                return

            # Skip update if window has focus to prevent crashes
            if self.hasFocus():
                logger.debug("Skipping update - window has focus")
                return

            # Skip update if window is being dragged
            if self._drag_active:
                logger.debug("Skipping update - window is being dragged")
                return

            search_text = self.search_bar.text().strip().lower() if hasattr(self, 'search_bar') else ""
            window_title = get_active_window_title()
            if window_title and window_title.strip() == self.windowTitle():
                window_title = self.last_real_window_title
            else:
                if window_title:
                    self.last_real_window_title = window_title
            context_str = window_title or "Unknown context"
            language = self.detect_language_by_extension(window_title)
            app_name = self.detect_app_by_name(window_title)
            if language:
                context_str = f"{context_str}<br><span style='color:#ffeebb;'>Language: <b>{language}</b></span>"
            if app_name:
                context_str = f"{context_str}<br><span style='color:#aeefff;'>App: <b>{app_name}</b></span>"
            self.context_label.setText(context_str)
            self.context_label.setTextFormat(Qt.TextFormat.RichText)
            print(f"[DEBUG] update_overlay called. ctrl_pressed={self.ctrl_pressed}, has_focus={self.has_focus}, block_updates={self.block_updates}, home_locked={self.home_locked}, window_title={window_title}")
            
            # Clear existing content
            for i in reversed(range(self.content_layout.count())):
                widget = self.content_layout.itemAt(i).widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
            
            home_apps = [
                'excel', 'microsoft excel', 'word', 'microsoft word', 'powerpoint', 'microsoft powerpoint',
                'outlook', 'microsoft outlook', 'onenote', 'microsoft onenote', 'teams', 'microsoft teams',
                'firefox', 'mozilla firefox', 'chrome', 'google chrome', 'edge', 'microsoft edge', 'internet explorer',
                'steam', 'epic games', 'discord', 'spotify', 'windows terminal', 'cmd.exe', 'powershell', 'windows powershell'
            ]
            if self.ctrl_pressed:
                # Shortcuts tab: use app name only
                app_name = self.detect_app_by_name(window_title)
                shortcuts = get_shortcuts_for_app(app_name)
                if shortcuts:
                    pinned = []
                    unpinned = []
                    for s in shortcuts:
                        if s['shortcut'] in self.favorites['shortcuts']:
                            pinned.append(s)
                        else:
                            unpinned.append(s)
                    for s in pinned + unpinned:
                        desc = s.get('description', '')
                        code = s.get('code', None)
                        summary = s.get('summary', '')
                        tooltip = f"{desc}"
                        if code:
                            tooltip += f"<br><hr><pre>{code}</pre>"
                        # Filter by search
                        if search_text and not (s['shortcut'].lower().startswith(search_text) or (summary and summary.lower().startswith(search_text))):
                            continue
                        is_fav = s['shortcut'] in self.favorites['shortcuts']
                        def make_copy_cb_shortcut(val=s['shortcut']):
                            return lambda: QGuiApplication.clipboard().setText(val)
                        def make_doc_cb_shortcut(app=app_name, t=s['shortcut']):
                            return lambda: webbrowser.open(get_doc_url(app, t))
                        row_widget = OverlayRowWidget(
                            QLabel(f"<b>{s['shortcut']}</b>"),
                            QLabel(summary),
                            tooltip,
                            is_fav,
                            lambda checked, t=s['shortcut']: self.pin_shortcut(t),
                            make_copy_cb_shortcut(),
                            make_doc_cb_shortcut()
                        )
                        self.content_layout.addWidget(row_widget)
                else:
                    row_widget = OverlayRowWidget(QLabel("No shortcuts found for this app."), QLabel(""), "", False, lambda checked, t=None: self.pin_shortcut(t), lambda: QGuiApplication.clipboard().setText(""), lambda: webbrowser.open(get_doc_url(language, None)))
                    self.content_layout.addWidget(row_widget)
                return

            if app_name and app_name in home_apps:
                # Check if a language is detected and knowledge exists for it
                if language and language in self.knowledge:
                    print(f"[DEBUG] Language {language} detected in home app, showing knowledge instead of home page.")
                    app_knowledge = self.knowledge[language]
                    pinned = []
                    unpinned = []
                    for k in app_knowledge:
                        if k['title'] in self.favorites['knowledge']:
                            pinned.append(k)
                        else:
                            unpinned.append(k)
                    for k in pinned + unpinned:
                        desc = k.get('description', '')
                        code = k.get('code', None)
                        summary = k.get('summary', '')
                        tooltip = f"{desc}"
                        if code:
                            tooltip += f"<br><hr><pre>{code}</pre>"
                        # Filter by search
                        if search_text and not (k['title'].lower().startswith(search_text) or (summary and summary.lower().startswith(search_text))):
                            continue
                        is_fav = k['title'] in self.favorites['knowledge']
                        def make_copy_cb(c=code):
                            return lambda: QGuiApplication.clipboard().setText(c or "")
                        def make_doc_cb(lang=language, t=k['title']):
                            return lambda: webbrowser.open(get_doc_url(lang, t))
                        row_widget = OverlayRowWidget(
                            QLabel(f"<b>{k['title']}</b>"),
                            QLabel(summary),
                            tooltip,
                            is_fav,
                            lambda checked, t=k['title']: self.pin_knowledge(t),
                            make_copy_cb(),
                            make_doc_cb()
                        )
                        self.content_layout.addWidget(row_widget)
                    return
                # Otherwise, show the home page
                print(f"[DEBUG] Showing home page for {app_name} (window title: {window_title})")
                home_widget = self.create_app_home(window_title)
                self.content_layout.addWidget(home_widget)
                return
            if getattr(self, 'home_locked', False):
                menu_items = [
                    ("Settings", "Open the settings menu.", None, None),
                    ("Reload", "Reload the overlay.", None, None),
                    ("About", "About this overlay.", None, None),
                ]
                for title, desc, code, summary in menu_items:
                    tooltip = f"{desc}"
                    if code:
                        tooltip += f"<br><hr><pre>{code}</pre>"
                    # Filter by search
                    if search_text and not (title.lower().startswith(search_text) or (summary and summary.lower().startswith(search_text))):
                        continue
                    def make_copy_cb(c=code):
                        return lambda: QGuiApplication.clipboard().setText(c or "")
                    def make_doc_cb(lang=language, t=title):
                        return lambda: webbrowser.open(get_doc_url(lang, t))
                    row_widget = OverlayRowWidget(
                        QLabel(f"<b>{title}</b>"),
                        QLabel(summary or ""),
                        tooltip,
                        False,
                        lambda checked, t=title: self.pin_knowledge(t),
                        make_copy_cb(),
                        make_doc_cb()
                    )
                    self.content_layout.addWidget(row_widget)
                return
            if self.ctrl_pressed:
                # Shortcuts tab: use app name only
                app_name = self.detect_app_by_name(window_title)
                shortcuts = get_shortcuts_for_app(app_name)
                if shortcuts:
                    pinned = []
                    unpinned = []
                    for s in shortcuts:
                        if s['shortcut'] in self.favorites['shortcuts']:
                            pinned.append(s)
                        else:
                            unpinned.append(s)
                    for s in pinned + unpinned:
                        desc = s.get('description', '')
                        code = s.get('code', None)
                        summary = s.get('summary', '')
                        tooltip = f"{desc}"
                        if code:
                            tooltip += f"<br><hr><pre>{code}</pre>"
                        # Filter by search
                        if search_text and not (s['shortcut'].lower().startswith(search_text) or (summary and summary.lower().startswith(search_text))):
                            continue
                        is_fav = s['shortcut'] in self.favorites['shortcuts']
                        def make_copy_cb_shortcut(val=s['shortcut']):
                            return lambda: QGuiApplication.clipboard().setText(val)
                        def make_doc_cb_shortcut(app=app_name, t=s['shortcut']):
                            return lambda: webbrowser.open(get_doc_url(app, t))
                        row_widget = OverlayRowWidget(
                            QLabel(f"<b>{s['shortcut']}</b>"),
                            QLabel(summary),
                            tooltip,
                            is_fav,
                            lambda checked, t=s['shortcut']: self.pin_shortcut(t),
                            make_copy_cb_shortcut(),
                            make_doc_cb_shortcut()
                        )
                        self.content_layout.addWidget(row_widget)
                else:
                    row_widget = OverlayRowWidget(QLabel("No shortcuts found for this app."), QLabel(""), "", False, lambda checked, t=None: self.pin_shortcut(t), lambda: QGuiApplication.clipboard().setText(""), lambda: webbrowser.open(get_doc_url(language, None)))
                    self.content_layout.addWidget(row_widget)
            else:
                # Knowledge tab: use file extension only
                language = self.detect_language_by_extension(window_title)
                app_knowledge = []
                if language and language in self.knowledge:
                    app_knowledge = self.knowledge[language]
                else:
                    window_title_lower = window_title.lower() if window_title else ""
                    for app_name, knowledge_list in self.knowledge.items():
                        if app_name.lower() in window_title_lower:
                            app_knowledge = knowledge_list
                            break
                if app_knowledge:
                    pinned = []
                    unpinned = []
                    for k in app_knowledge:
                        if k['title'] in self.favorites['knowledge']:
                            pinned.append(k)
                        else:
                            unpinned.append(k)
                    for k in pinned + unpinned:
                        desc = k.get('description', '')
                        code = k.get('code', None)
                        summary = k.get('summary', '')
                        tooltip = f"{desc}"
                        if code:
                            tooltip += f"<br><hr><pre>{code}</pre>"
                        # Filter by search
                        if search_text and not (k['title'].lower().startswith(search_text) or (summary and summary.lower().startswith(search_text))):
                            continue
                        is_fav = k['title'] in self.favorites['knowledge']
                        def make_copy_cb(c=code):
                            return lambda: QGuiApplication.clipboard().setText(c or "")
                        def make_doc_cb(lang=language, t=k['title']):
                            return lambda: webbrowser.open(get_doc_url(lang, t))
                        row_widget = OverlayRowWidget(
                            QLabel(f"<b>{k['title']}</b>"),
                            QLabel(summary),
                            tooltip,
                            is_fav,
                            lambda checked, t=k['title']: self.pin_knowledge(t),
                            make_copy_cb(),
                            make_doc_cb()
                        )
                        self.content_layout.addWidget(row_widget)
                else:
                    row_widget = OverlayRowWidget(QLabel("No basic knowledge found for this language or app."), QLabel(""), "", False, lambda checked, t=None: self.pin_knowledge(t), lambda: QGuiApplication.clipboard().setText(""), lambda: webbrowser.open(get_doc_url(language, None)))
                    self.content_layout.addWidget(row_widget)
            
        except Exception as e:
            logger.error(f"Error in update_overlay: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def update_shortcuts(self):
        """Update shortcuts with error handling."""
        try:
            if getattr(self, 'home_locked', False):
                return
            self.update_overlay()
        except Exception as e:
            logger.error(f"Error in update_shortcuts: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def mousePressEvent(self, event):
        """Handle mouse press with improved focus handling."""
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                # Only handle drag, never set focus
                self._drag_active = True
                self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
            else:
                event.ignore()
        except Exception as e:
            logger.error(f"Error in mousePressEvent: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            event.ignore()

    def mouseMoveEvent(self, event):
        """Handle mouse move with improved focus handling."""
        try:
            if self._drag_active and event.buttons() & Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_position)
                event.accept()
            else:
                event.ignore()
        except Exception as e:
            logger.error(f"Error in mouseMoveEvent: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            event.ignore()

    def mouseReleaseEvent(self, event):
        """Handle mouse release with improved focus handling."""
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_active = False
                event.accept()
            else:
                event.ignore()
        except Exception as e:
            logger.error(f"Error in mouseReleaseEvent: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            event.ignore()

    def mouseDoubleClickEvent(self, event):
        # Ignore double-clicks to prevent accidental close
        event.ignore()

    def lock_home(self):
        self.home_locked = True
        self.update_overlay()

    def unlock_home(self):
        self.home_locked = False
        self.update_overlay()

    def pin_knowledge(self, title):
        if title in self.favorites['knowledge']:
            self.favorites['knowledge'].remove(title)
        else:
            self.favorites['knowledge'].insert(0, title)
        save_favorites(self.favorites)
        self.update_overlay()

    def pin_shortcut(self, shortcut):
        if shortcut in self.favorites['shortcuts']:
            self.favorites['shortcuts'].remove(shortcut)
        else:
            self.favorites['shortcuts'].insert(0, shortcut)
        save_favorites(self.favorites)
        self.update_overlay()

    def _start_cursor_monitor(self):
        """Start monitoring cursor position and selection."""
        def monitor():
            last_pos = None
            last_selection = None
            last_window = None
            while not self._stop_monitor:
                try:
                    # Get current cursor position
                    cursor_pos = QCursor.pos()
                    
                    # Get active window
                    hwnd = win32gui.GetForegroundWindow()
                    if not hwnd:
                        time.sleep(0.1)
                        continue
                        
                    window_title = win32gui.GetWindowText(hwnd)
                    class_name = win32gui.GetClassName(hwnd)
                    
                    # Skip if it's our own window
                    if class_name == "Qt690QWindowToolSaveBits" or window_title == self.windowTitle():
                        time.sleep(0.1)
                        continue
                    
                    # Get selected text
                    selected_text = self._get_selected_text()
                    
                    # Check if anything changed
                    if (selected_text != last_selection or 
                        cursor_pos != last_pos or 
                        window_title != last_window):
                        
                        if selected_text:
                            logger.info(f"Text selected in {window_title}: {selected_text[:50]}...")
                            # Get window info for context
                            context = {
                                'cursor_pos': cursor_pos,
                                'app_name': self.detect_app_by_name(window_title),
                                'window_title': window_title,
                                'file_extension': self.detect_language_by_extension(window_title)
                            }
                            # Request explanation with context
                            self.ai_widget.request_explanation(selected_text, context)
                        
                        last_pos = cursor_pos
                        last_selection = selected_text
                        last_window = window_title
                    
                    time.sleep(0.1)  # Reduce CPU usage
                    
                except Exception as e:
                    logger.error(f"Error in cursor monitor: {str(e)}")
                    time.sleep(1)  # Longer delay on error
        
        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()

    def _get_selected_text(self) -> Optional[str]:
        """Get selected text from active window with improved error handling."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
                
            # Get window class name for debugging
            class_name = win32gui.GetClassName(hwnd)
            window_title = win32gui.GetWindowText(hwnd)
            logger.debug(f"Active window class: {class_name}, title: {window_title}")
            
            # Skip if it's our own window
            if class_name == "Qt690QWindowToolSaveBits" or window_title == self.windowTitle():
                return None
            
            # Try direct selection first for specific window types
            if "Chrome" in class_name or "Mozilla" in class_name:
                text = self._get_selection_direct(hwnd)
                if text and text.strip():
                    logger.info(f"Got direct selection: {text[:30]}...")
                    return text.strip()
            
            # Fallback to clipboard method
            text = self._get_selection_via_clipboard()
            if text and text.strip():
                logger.info(f"Got clipboard selection: {text[:30]}...")
                return text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting selected text: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def _get_selection_via_clipboard(self) -> Optional[str]:
        """Get selected text via clipboard with improved error handling."""
        try:
            # Save current clipboard content
            old_clipboard = QGuiApplication.clipboard().text()
            
            # Clear clipboard
            QGuiApplication.clipboard().clear()
            
            # Send Ctrl+C with proper key sequence
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            time.sleep(0.05)  # Small delay for key press
            win32api.keybd_event(ord('C'), 0, 0, 0)
            time.sleep(0.05)  # Small delay for key press
            win32api.keybd_event(ord('C'), 0, win32con.KEYEVENTF_KEYUP, 0)
            
            # Wait for clipboard to update
            time.sleep(0.1)
            
            # Get new clipboard content
            new_text = QGuiApplication.clipboard().text()
            
            # Restore old clipboard content
            QGuiApplication.clipboard().setText(old_clipboard)
            
            # Only return if we got new text
            if new_text and new_text != old_clipboard and new_text.strip():
                return new_text.strip()
            return None
            
        except Exception as e:
            logger.error(f"Error in clipboard selection: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def _get_selection_direct(self, hwnd) -> Optional[str]:
        """Get selected text directly from window with improved error handling."""
        try:
            # Try EM_GETSELTEXT first for edit controls
            try:
                length = ctypes.windll.user32.SendMessageW(hwnd, 0x043E, 0, 0)  # EM_GETSELTEXT
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.SendMessageW(hwnd, 0x043E, length + 1, buffer)  # EM_GETSELTEXT
                    text = buffer.value
                    if text and text.strip():
                        return text.strip()
            except Exception as e:
                logger.debug(f"EM_GETSELTEXT failed: {str(e)}")
            
            # Fallback to WM_GETTEXT
            length = win32gui.SendMessage(hwnd, win32con.WM_GETTEXTLENGTH, 0, 0)
            if not length:
                return None
                
            buffer = win32gui.PyMakeBuffer(length + 1)
            win32gui.SendMessage(hwnd, win32con.WM_GETTEXT, length + 1, buffer)
            text = buffer.tobytes().decode('utf-8', errors='ignore').rstrip('\0')
            
            return text.strip() if text else None
            
        except Exception as e:
            logger.error(f"Error in direct selection: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def handle_ai_completion(self, completion: str):
        """Handle AI completion with better error handling."""
        try:
            if not completion:
                logger.warning("Empty completion received")
                return
                
            logger.info(f"Handling AI completion: {completion[:50]}...")
            
            # Create completion widget
            completion_widget = QWidget(self)
            completion_widget.setStyleSheet("""
                QWidget {
                    background-color: rgba(60, 60, 60, 0.95);
                    border: 1px solid rgba(100, 100, 100, 0.5);
                    border-radius: 5px;
                    padding: 5px;
                }
            """)
            
            layout = QVBoxLayout(completion_widget)
            
            # Add completion text
            text = QLabel(completion)
            text.setWordWrap(True)
            text.setStyleSheet("color: white;")
            layout.addWidget(text)
            
            # Position the widget
            completion_widget.adjustSize()
            completion_widget.move(
                (self.width() - completion_widget.width()) // 2,
                self.height() - completion_widget.height() - 10
            )
            
            completion_widget.show()
            
            # Add a small delay before removing the completion
            QTimer.singleShot(30000, lambda: completion_widget.deleteLater())
            
        except Exception as e:
            logger.error(f"Error handling AI completion: {e}")
            logger.error(traceback.format_exc())

    def hideEvent(self, event):
        """Handle hide event with improved error handling."""
        try:
            logger.info("Window hide event received")
            super().hideEvent(event)
        except Exception as e:
            logger.error(f"Error in hideEvent: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def _get_window_info(self):
        """Get information about the active window."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return {}
            
            window_title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            
            # Detect app name
            app_name = None
            if "Mozilla" in class_name:
                app_name = "Firefox"
            elif "Chrome" in class_name:
                app_name = "Chrome"
            elif "Cursor" in window_title:
                app_name = "Cursor"
            
            # Detect file extension
            file_extension = None
            if window_title:
                # Convert window title to string and lowercase
                title_lower = str(window_title).lower()
                # Find all extensions
                extensions = [ext for ext in ['.py', '.js', '.html', '.css', '.json', '.md'] if ext in title_lower]
                if extensions:
                    file_extension = extensions[-1]  # Get the last extension found
            
            return {
                'window_title': window_title,
                'class_name': class_name,
                'app_name': app_name,
                'file_extension': file_extension
            }
            
        except Exception as e:
            logger.error(f"Error getting window info: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {} 