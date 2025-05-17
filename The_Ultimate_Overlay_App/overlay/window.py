"""
UltimateOverlay - Overlay window logic.
Provides a resizable, scrollable, context-aware overlay with Home/Read buttons.
"""
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QScrollArea, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
import sys
from context.detector import get_active_window_title
from context.shortcuts import get_shortcuts_for_app
import json
import os
import threading
import keyboard

KNOWLEDGE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'knowledge.json')

def load_knowledge():
    try:
        with open(KNOWLEDGE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

class OverlayWindow:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = MovableOverlayWidget()

    def run(self):
        self.window.show()
        sys.exit(self.app.exec())

class MovableOverlayWidget(QWidget):
    ctrl_changed = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.8)
        self.setMinimumSize(250, 100)
        self.resize(350, 200)

        self.home_locked = False

        main_layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        self.home_button = QPushButton("Home")
        self.home_button.clicked.connect(self.lock_home)
        self.read_button = QPushButton("Read")
        self.read_button.clicked.connect(self.unlock_home)
        button_layout.addWidget(self.home_button)
        button_layout.addWidget(self.read_button)
        main_layout.addLayout(button_layout)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.label = QLabel("Overlay Placeholder")
        self.label.setStyleSheet("color: white; font-size: 18px; background: rgba(0,0,0,0.5); padding: 10px; border-radius: 8px;")
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.scroll.setWidget(self.label)
        main_layout.addWidget(self.scroll)
        self.setLayout(main_layout)

        self._drag_active = False
        self._drag_position = QPoint()

        # Timer for auto-updating shortcuts
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_shortcuts)
        self.timer.start(1000)  # Check every 1 second

        self.ctrl_pressed = False
        self.knowledge = load_knowledge()
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.has_focus = False
        self.block_updates = False
        self.force_homepage = False
        self.ctrl_changed.connect(self.update_overlay)
        # Start global Ctrl listener in a thread
        self._start_ctrl_listener()

    def _start_ctrl_listener(self):
        def listen_ctrl():
            while True:
                ctrl_now = keyboard.is_pressed('ctrl')
                if ctrl_now != self.ctrl_pressed:
                    print(f"[DEBUG] Ctrl state changed: {ctrl_now}")
                    self.ctrl_pressed = ctrl_now
                    self.ctrl_changed.emit()
                import time; time.sleep(0.05)
        t = threading.Thread(target=listen_ctrl, daemon=True)
        t.start()

    def focusInEvent(self, event):
        self.has_focus = True
        self.block_updates = True
        self.force_homepage = True
        print('[DEBUG] focusInEvent: force_homepage set to True')
        self.update_overlay()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.has_focus = False
        self.block_updates = False
        self.force_homepage = False
        print('[DEBUG] focusOutEvent: force_homepage set to False')
        self.update_overlay()
        super().focusOutEvent(event)

    def detect_language(self, window_title):
        # Map file extensions to languages
        ext_to_lang = {
            '.py': 'Python',
            '.sql': 'SQL',
            '.r': 'R',
            '.ttl': 'Ttl',
            '.sas': 'SAS',
            '.ipynb': 'Python',
        }
        # Map known app names to languages
        app_to_lang = {
            'rstudio': 'R',
            'sql server management studio': 'SQL',
            'jupyter': 'Python',
            'spyder': 'Python',
            'pycharm': 'Python',
            'vscode': 'Python',
        }
        if window_title:
            title_lower = window_title.lower()
            # Check app name
            for app, lang in app_to_lang.items():
                if app in title_lower:
                    return lang
            # Check file extension
            import re
            match = re.search(r'\.[a-z0-9]+', window_title)
            if match:
                ext = match.group(0)
                if ext in ext_to_lang:
                    return ext_to_lang[ext]
        return None

    def update_overlay(self):
        print(f"[DEBUG] update_overlay called. ctrl_pressed={self.ctrl_pressed}, has_focus={self.has_focus}, block_updates={self.block_updates}, force_homepage={getattr(self, 'force_homepage', False)}, home_locked={self.home_locked}")
        if getattr(self, 'home_locked', False):
            text = "<b>UltimateOverlay Menu</b><br>"
            text += "<ul style='margin:0;padding-left:18px;'>"
            text += "<li><b>Settings</b></li>"
            text += "<li><b>Reload</b></li>"
            text += "<li><b>About</b></li>"
            text += "</ul>"
            self.label.setText(text)
            return
        if self.force_homepage:
            text = "<b>UltimateOverlay Menu</b><br>"
            text += "<ul style='margin:0;padding-left:18px;'>"
            text += "<li><b>Settings</b></li>"
            text += "<li><b>Reload</b></li>"
            text += "<li><b>About</b></li>"
            text += "</ul>"
            self.label.setText(text)
            return
        if self.block_updates:
            text = "<b>UltimateOverlay Menu</b><br>"
            text += "<ul style='margin:0;padding-left:18px;'>"
            text += "<li><b>Settings</b></li>"
            text += "<li><b>Reload</b></li>"
            text += "<li><b>About</b></li>"
            text += "</ul>"
            self.label.setText(text)
            return
        else:
            window_title = get_active_window_title()
            if self.ctrl_pressed:
                shortcuts = get_shortcuts_for_app(window_title)
                if shortcuts:
                    text = "<b>Shortcuts:</b><br>" + "<br>".join(f"<b>{s['shortcut']}</b>: {s['description']}" for s in shortcuts)
                else:
                    text = "No shortcuts found for this app."
                self.label.setText(text)
            else:
                # Always try to show language knowledge first
                language = self.detect_language(window_title)
                if language and language in self.knowledge:
                    app_knowledge = self.knowledge[language]
                    text = f"<b>Basic Knowledge: {language}</b><br>" + "<br>".join(f"<b>{k['title']}</b>: {k['description']}" for k in app_knowledge)
                else:
                    # Only fallback to app knowledge if no language detected
                    app_knowledge = []
                    window_title_lower = window_title.lower() if window_title else ""
                    for app_name, knowledge_list in self.knowledge.items():
                        if app_name.lower() in window_title_lower:
                            app_knowledge = knowledge_list
                            break
                    if app_knowledge:
                        text = "<b>Basic Knowledge (App):</b><br>" + "<br>".join(f"<b>{k['title']}</b>: {k['description']}" for k in app_knowledge)
                    else:
                        text = "No basic knowledge found for this language or app."
                self.label.setText(text)

    def update_shortcuts(self):
        if getattr(self, 'home_locked', False):
            return
        self.update_overlay()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus()
            self._drag_active = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_active and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = False
            event.accept()

    def lock_home(self):
        self.home_locked = True
        self.update_overlay()

    def unlock_home(self):
        self.home_locked = False
        self.update_overlay() 