# UltimateOverlay

A lightweight, context-aware overlay application that displays shortcuts, syntax, or functions for the active application or programming language on your screen. Designed to be human-friendly, easily maintainable, and user extensible.

## Features
- Always-on-top, resizable, scrollable overlay
- Detects the active window/app and the file extension to infer the programming language
- Displays relevant shortcuts or syntax based on context
- Press Ctrl to switch between the function/knowledge tab (default) and the shortcut tab (while holding Ctrl)
- Manual Home/Read buttons to lock the overlay to the home page or return to context-aware mode
- **AI-Powered Completions**: Context-aware code completions using CodeLlama (optional)
- **Compact, modern overlay UI** (shows only names, details on hover)
- **Rich tooltips**: Mouse over any item to see a description and (if available) a code example in a code block
- **Search/filter bar**: Quickly filter functions/shortcuts by name or summary
- **Favorites/pinning**: Star your favorite items to keep them at the top (persisted in `config/favorites.json`)
- **Copy to clipboard**: Instantly copy code or shortcut with one click
- **Quick doc links**: Open official documentation for any function/shortcut with one click (web globe icon)
- **Context display**: Shows current app/file and detected language at the top, always visible
- **Highlight on hover**: Rows are visually highlighted for clarity
- Easy to extend via simple config files structure

## Project Structure
```
UltimateOverlay/
│
├── main.py                # Entry point, starts the overlay
├── overlay/               # Overlay window and UI logic
│   ├── __init__.py
│   └── window.py          # Main overlay window class and logic
│
├── context/               # Context detection and shortcut logic
│   ├── __init__.py
│   ├── detector.py        # Detects active app/window
│   └── shortcuts.py       # Loads and manages shortcuts/syntax per app
│
├── ai/                    # AI-related functionality
│   ├── __init__.py
│   ├── config.py          # AI model configuration
│   └── model_manager.py   # Manages AI model loading and inference
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
- **AI Completions:**
  - Toggle AI features using the AI button in the top-right corner
  - Completions will appear at the top of the overlay when available
  - Click the copy button to copy the completion to clipboard
- **Focus:**
  - The overlay will not update with app/language info while locked on the home page.
- **Context Bar:**
  - The top of the overlay always shows the current app/file and detected language, even when the overlay is focused.
- **Search/Filter:**
  - Use the search bar to filter the list in real time by name or summary.
- **Favorites/Pinning:**
  - Click the star icon to pin/unpin an item. Favorites always appear at the top and are saved in `config/favorites.json`.
- **Copy to Clipboard:**
  - Click the green copy icon to copy the code (for knowledge) or shortcut (for shortcuts) to the clipboard.
- **Quick Documentation:**
  - Click the blue globe icon to open the official documentation for the function/shortcut in your browser.
- **Highlight on Hover:**
  - Rows are visually highlighted when hovered for better focus.

## Configuration
- Edit `config/shortcuts.json` to add or modify shortcuts for different applications.
- Edit `config/knowledge.json` to add or modify basic knowledge for different apps or programming languages (e.g., Python, SQL, R).
- **Favorites:**
  - Your pinned items are saved in `config/favorites.json` and persist between sessions.
- **AI Configuration:**
  - AI features are optional and can be toggled on/off
  - The model will be downloaded automatically on first use
  - Memory usage is optimized for CPU-only systems

## License
This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).

- **No commercial use is permitted.**
- **Attribution is required:** If you use or modify this project, you must credit the original author: Jacquart08 (https://github.com/Jacquart08)

See the LICENSE file for full details. 
