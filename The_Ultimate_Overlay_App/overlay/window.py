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
        
        # Top row with Home/Read buttons and AI widget
        top_layout = QHBoxLayout()
        
        # Left side: Home/Read buttons
        button_layout = QHBoxLayout()
        self.home_button = QPushButton("Home")
        self.home_button.clicked.connect(self.lock_home)
        self.read_button = QPushButton("Read")
        self.read_button.clicked.connect(self.unlock_home)
        button_layout.addWidget(self.home_button)
        button_layout.addWidget(self.read_button)
        top_layout.addLayout(button_layout)
        
        # Right side: AI widget
        self.ai_widget = AIWidget()
        self.ai_widget.completion_ready.connect(self.handle_ai_completion)
        self.ai_widget.setFixedHeight(30)  # Set fixed height for the AI widget
        top_layout.addWidget(self.ai_widget)
        
        main_layout.addLayout(top_layout)

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
        
        # Start monitoring cursor position and selection
        self._start_cursor_monitor()

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
        if self.rect().contains(self.mapFromGlobal(QCursor.pos())):
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
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
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

    def _start_cursor_monitor(self):
        """Start monitoring cursor position and selection for AI completions."""
        def monitor_cursor():
            last_content = None
            while True:
                try:
                    # Get current window info
                    window_title = get_active_window_title()
                    if not window_title:
                        continue
                    
                    # Get file extension if available
                    file_extension = self.detect_language_by_extension(window_title)
                    app_name = self.detect_app_by_name(window_title)
                    
                    # Get selected text if any
                    selected_text = None
                    if keyboard.is_pressed('shift'):
                        # For now, we'll use the window title as content
                        # In a real implementation, you'd need to get the actual text content
                        content = window_title
                    else:
                        # Use the window title as context
                        content = f"Context: {window_title}"
                    
                    # Only request completion if content has changed
                    if content != last_content:
                        last_content = content
                        # Request completion if AI is enabled
                        self.ai_widget.request_completion(
                            content=content,
                            cursor_position=0,  # For now, we'll use 0
                            selection=selected_text,
                            file_extension=file_extension,
                            app_name=app_name
                        )
                    
                except Exception as e:
                    print(f"Error in cursor monitor: {str(e)}")
                
                time.sleep(0.5)  # Check every 500ms to reduce CPU usage
        
        # Start monitoring in a separate thread
        threading.Thread(target=monitor_cursor, daemon=True).start()
    
    def handle_ai_completion(self, completion: str):
        """Handle AI completion result."""
        if not completion:
            return
            
        # Create completion widget
        completion_widget = QWidget()
        completion_layout = QVBoxLayout()
        completion_layout.setContentsMargins(10, 5, 10, 5)
        
        # Add completion text
        completion_label = QLabel(completion)
        completion_label.setStyleSheet("""
            QLabel {
                color: #aeefff;
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                font-size: 14px;
                margin-bottom: 5px;
            }
        """)
        completion_label.setWordWrap(True)
        completion_layout.addWidget(completion_label)
        
        # Add copy button
        copy_button = QPushButton("Copy")
        copy_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        copy_button.clicked.connect(lambda: QApplication.clipboard().setText(completion))
        completion_layout.addWidget(copy_button)
        
        completion_widget.setLayout(completion_layout)
        
        # Clear existing completions
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget and isinstance(widget, QWidget) and widget.property("is_completion"):
                widget.deleteLater()
        
        # Mark as completion widget
        completion_widget.setProperty("is_completion", True)
        
        # Add to content layout at the top
        self.content_layout.insertWidget(0, completion_widget)
        
        # Make sure the completion is visible
        self.scroll.verticalScrollBar().setValue(0)
        completion_widget.show()
        
        # Add a small delay before removing the completion
        QTimer.singleShot(30000, lambda: completion_widget.deleteLater())  # Increased to 30 seconds 