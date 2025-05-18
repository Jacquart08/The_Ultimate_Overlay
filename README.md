# UltimateOverlay

A lightweight, context-aware overlay application that displays shortcuts, syntax, or functions for the active application or programming language on your screen. Designed to be human-friendly, easily maintainable, and user extensible.

## How it works ?

When runing the App, the overlay will show up somewhere. Just resize it and put it anywhere you want on the screen.
You then have 2 button Home will be you dashboard (WIP), and Read. When pressing the read button you will activate the awareness mode. This mode will automatically detect the application you are using and, if applicable, the file extension you are looking at (It only works when the window is curently focused by windows). 
Now regarding the app you are on, or the file extension it will provide you by default some knowledge about the programming language you are on (and it change automatically when switching from one file to another). If not applicable a custonizable dashboard will appear (WIP). It even detect the language in your web browser if the extension is in the URL.
Now you can also press ctrl and it will then display some shortcuts based on the app you are on (it no longer read the file extension).
You also have at your disposal a search bar in order for you to filter the results (when the knwledge base will be big enough).

## Features
- Always-on-top, resizable, scrollable overlay
- Detects the active window/app and the file extension to infer the programming language
- Displays relevant shortcuts or syntax based on context
- Press Ctrl to switch between the function/knowledge tab (default) and the shortcut tab (while holding Ctrl)
- Manual Home/Read buttons to lock the overlay to the home page or return to context-aware mode
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
- **New format for knowledge.json:**
  - Each entry should have a `title`, a `summary`, a `description`, and (optionally) a `code` field. Example:
    ```json
    {
      "title": "for",
      "summary": "Loop range",
      "description": "For loop.",
      "code": "for i in range(10):"
    }
    ```
  - The tooltip will show the description and, if present, the code block.

## License
This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).

- **No commercial use is permitted.**
- **Attribution is required:** If you use or modify this project, you must credit the original author: Jacquart08 (https://github.com/Jacquart08)

See the LICENSE file for full details. 
