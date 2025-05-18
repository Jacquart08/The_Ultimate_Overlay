"""
UltimateOverlay - Overlay window logic.
Provides a resizable, scrollable, context-aware overlay with Home/Read buttons.
"""
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QScrollArea, QPushButton, QHBoxLayout, QToolTip, QSizePolicy, QLineEdit, QToolButton
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QGuiApplication
import sys
from context.detector import get_active_window_title
from context.shortcuts import get_shortcuts_for_app
import json
import os
import threading
import keyboard
import webbrowser

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
    def enterEvent(self, event):
        QToolTip.showText(self.mapToGlobal(self.rect().center()), self._tooltip, self)
        self.setStyleSheet("background: #3a7bd5; border-radius: 7px;")
        super().enterEvent(event)
    def leaveEvent(self, event):
        QToolTip.hideText()
        self.setStyleSheet("")
        super().leaveEvent(event)

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
        self.setWindowTitle("UltimateOverlay")
        self.setWindowOpacity(0.8)
        self.setMinimumSize(250, 100)
        self.resize(350, 200)

        self.home_locked = False
        self.last_real_window_title = None

        main_layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        self.home_button = QPushButton("Home")
        self.home_button.clicked.connect(self.lock_home)
        self.read_button = QPushButton("Read")
        self.read_button.clicked.connect(self.unlock_home)
        button_layout.addWidget(self.home_button)
        button_layout.addWidget(self.read_button)
        main_layout.addLayout(button_layout)

        # Context label
        self.context_label = QLabel()
        self.context_label.setStyleSheet("color: #aeefff; font-size: 12px; padding: 2px 0 4px 0;")
        main_layout.addWidget(self.context_label)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self.update_overlay)
        main_layout.addWidget(self.search_bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_widget.setLayout(self.content_layout)
        self.scroll.setWidget(self.content_widget)
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
        self.favorites = load_favorites()
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
        print('[DEBUG] focusInEvent: focus_homepage logic removed')
        self.update_overlay()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.has_focus = False
        self.block_updates = False
        print('[DEBUG] focusOutEvent: force_homepage logic removed')
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
        search_text = self.search_bar.text().strip().lower() if hasattr(self, 'search_bar') else ""
        # Get active window title, but preserve last real context if overlay is focused
        window_title = get_active_window_title()
        if window_title and window_title.strip() == self.windowTitle():
            # Overlay is focused, use last real window title
            window_title = self.last_real_window_title
        else:
            # Only update last_real_window_title if not overlay
            if window_title:
                self.last_real_window_title = window_title
        # Update context label
        context_str = window_title or "Unknown context"
        language = self.detect_language(window_title)
        if language:
            context_str = f"{context_str}<br><span style='color:#ffeebb;'>Language: <b>{language}</b></span>"
        self.context_label.setText(context_str)
        self.context_label.setTextFormat(Qt.TextFormat.RichText)
        print(f"[DEBUG] update_overlay called. ctrl_pressed={self.ctrl_pressed}, has_focus={self.has_focus}, block_updates={self.block_updates}, home_locked={self.home_locked}, window_title={window_title}")
        # Clear previous content
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
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
            shortcuts = get_shortcuts_for_app(window_title)
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
                    def make_doc_cb_shortcut(app=window_title, t=s['shortcut']):
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
            language = self.detect_language(window_title)
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