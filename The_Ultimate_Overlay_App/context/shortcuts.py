import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'shortcuts.json')

_shortcuts = None

def load_shortcuts():
    global _shortcuts
    if _shortcuts is None:
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                _shortcuts = json.load(f)
        except Exception:
            _shortcuts = {}
    return _shortcuts

def get_shortcuts_for_app(window_title):
    shortcuts = load_shortcuts()
    window_title_lower = window_title.lower() if window_title else ""
    for app_name, app_shortcuts in shortcuts.items():
        if app_name.lower() in window_title_lower:
            return app_shortcuts
    return [] 