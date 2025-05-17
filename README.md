# UltimateOverlay

A lightweight, context-aware overlay application that displays shortcuts, syntax, or functions for the active application or programming language on your screen. Designed to be human-friendly, easily maintainable, and user extensible.

## Features
- Always-on-top, resizable, scrollable overlay
- Detects the active window/app and the file extension to infer the programming language
- Displays relevant shortcuts or syntax based on context
- Press Ctrl to switch between the function/knowledge tab (default) and the shortcut tab (while holding Ctrl)
- Manual Home/Read buttons to lock the overlay to the home page or return to context-aware mode
- Easy to extend via simple config files structure

## Project Structure
```
UltimateOverlay/
│
├── main.py                # Entry point, starts the overlay
├── overlay/               # Overlay window and UI logic
│   ├── __init__.py
│   ├── window.py          # Overlay window class
│   └── controller.py      # Handles UI updates, context switching
│
├── context/               # Context detection and shortcut logic
│   ├── __init__.py
│   ├── detector.py        # Detects active app/window
│   └── shortcuts.py       # Loads and manages shortcuts/syntax per app
│
├── resources/             # Icons, images, etc.
│
├── config/                # User-editable config files
│   ├── shortcuts.json     # Mapping of app names to shortcuts/syntax
│   └── knowledge.json     # Mapping of app names/languages to basic knowledge
│
├── utils/                 # Utility functions
│   └── __init__.py
│
├── requirements.txt       # Python dependencies
└── README.md              # Project overview and setup
```

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python main.py
   ```

## Usage
- **Resizable & Scrollable:** Drag the window edges/corners to resize. Scroll if content is long.
- **Home/Read Buttons:**
  - Click **Home** to lock the overlay to the home page (menu: Settings, Reload, About).
  - Click **Read** to return to context-aware mode (showing shortcuts or knowledge for the active app/language).
- **Ctrl Key:**
  - Hold Ctrl to show shortcuts for the focused app.
  - Release Ctrl to show basic knowledge for the detected programming language (by file extension or app name).
- **Focus:**
  - The overlay will not update with app/language info while locked on the home page.

## Configuration
- Edit `config/shortcuts.json` to add or modify shortcuts for different applications.
- Edit `config/knowledge.json` to add or modify basic knowledge for different apps or programming languages (e.g., Python, SQL, R).

## License
This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).

- **No commercial use is permitted.**
- **Attribution is required:** If you use or modify this project, you must credit the original author: Jacquart08 (https://github.com/Jacquart08)

See the LICENSE file for full details. 