# The Ultimate Overlay - Technical Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [AI Integration](#ai-integration)
5. [User Interface](#user-interface)
6. [Text Selection and Analysis](#text-selection-and-analysis)
7. [Function Documentation](#function-documentation)
8. [Plugin Interactions](#plugin-interactions)
9. [Customizing the AI Model](#customizing-the-ai-model)

## Project Overview

The Ultimate Overlay is a desktop application that provides context-sensitive information and AI assistance through an overlay window that stays on top of other applications. The application monitors the user's active window and selected text to provide contextual information and AI-powered analysis when needed.

Key features include:
- Always-on-top overlay window
- Context-sensitive shortcuts and information based on the active application
- Text selection monitoring 
- AI-powered text analysis using a local GPT-2 model
- Application-specific home screens (Excel, Word, browsers, etc.)

## Project Structure

The project is organized into several modules:

```
The_Ultimate_Overlay_App/
├── ai/                        # AI-related functionality
│   ├── config.py              # AI configuration settings
│   ├── completion.py          # Text completion logic
│   ├── completion_system.py   # Completion system interface
│   ├── context_analyzer.py    # Context analysis for AI features
│   ├── model_manager.py       # Model loading and management
│   └── model_downloader.py    # Model download functionality
├── overlay/                   # Overlay UI components
│   ├── ai_widget.py           # AI widget for the overlay
│   ├── window.py              # Main overlay window implementation
│   └── controller.py          # Controller logic
├── utils/                     # Utility functions
├── resources/                 # Application resources
├── config/                    # Configuration files
├── context/                   # Context-specific code
├── models/                    # Local model storage
└── main.py                    # Application entry point
```

### Key Files and Their Purposes

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `main.py` | Application entry point | `OverlayWindow()` |
| `overlay/window.py` | Main UI implementation | `OverlayWindow`, `MovableOverlayWidget` |
| `overlay/ai_widget.py` | AI interface component | `AIWidget` |
| `ai/config.py` | AI configuration | `AIConfig` |
| `ai/model_manager.py` | Model lifecycle management | `ModelManager` |
| `ai/completion.py` | Text analysis logic | `CompletionSystem` |
| `ai/context_analyzer.py` | Context-aware features | `ContextAnalyzer` |

## Core Components

### Main Application (`The_Ultimate_Overlay_App/main.py`)

The entry point of the application that initializes and runs the overlay window.

```python
# main.py (lines 11-15)
if __name__ == "__main__":
    window = OverlayWindow()
    window.run()
```

### Overlay Window (`The_Ultimate_Overlay_App/overlay/window.py`)

The `MovableOverlayWidget` class (lines 155-1138) implements the main overlay UI with the following key features:

- Stays on top of other windows (`__init__()` method, lines 157-301)
- Provides Home, Read, and AI toggle buttons (lines 214-254)
- Monitors cursor position and selected text (`_monitor_function()`, lines 903-937)
- Displays context-specific information based on the active application (`update_overlay()`, lines 579-829)
- Shows AI analysis when text is selected and AI is enabled (`display_ai_content()`, lines 1038-1046)

The `OverlayWindow` class (lines 146-154) initializes the Qt application and the overlay widget.

### AI Widget (`The_Ultimate_Overlay_App/overlay/ai_widget.py`)

The `AIWidget` class (lines 17-441) manages the AI functionality in the overlay UI:

- Toggles AI functionality on/off (`toggle_ai()`, lines 263-274)
- Handles model downloading and loading (`start_download()`, lines 171-189; `start_loading()`, lines 275-290)
- Manages AI state (enabled, loading, downloading)
- Processes text explanation requests (`request_explanation()`, lines 365-382)
- Displays AI status and progress (`setup_ui()`, lines 62-121)

## AI Integration

The AI system is designed to analyze selected text and provide insights using a local GPT-2 model.

### AI Configuration (`The_Ultimate_Overlay_App/ai/config.py`)

The `AIConfig` class (lines 17-119) manages all AI-related settings:

- Model paths and configuration (lines 26-36)
- Memory optimization settings (lines 67-78)
- Generation parameters (temperature, top_p, etc.) (lines 38-42)
- Model verification and logging (lines 36-52)

Key configuration parameters include:
```python
# Model settings (lines 26-36)
self.model_name = "gpt2"
self.model_path = os.path.join(MODELS_DIR, "gpt2")
self.context_window = 512
self.max_length = 100

# Generation settings (lines 38-42)
self.temperature = 0.7
self.top_p = 0.9
self.repetition_penalty = 1.2

# Memory settings (lines 44-46)
self.low_cpu_mem_usage = True
self.torch_dtype = "float32"
```

The configuration automatically adapts to the available system resources:
```python
# Set memory limits based on available RAM (lines 49-61)
try:
    import psutil
    available_ram = psutil.virtual_memory().available
    ram_gb = available_ram / (1024 * 1024 * 1024)
    if ram_gb > 8:
        ram_limit = "4GB"
    elif ram_gb > 4:
        ram_limit = "2GB"
    else:
        ram_limit = "1GB"
    self.max_memory = {0: ram_limit}
except Exception as e:
    # Fallback to conservative limit
    self.max_memory = {0: "2GB"}
```

### Model Management (`The_Ultimate_Overlay_App/ai/model_manager.py`)

The `ModelManager` class (lines 16-280) handles model lifecycle:

- Loading and unloading the model (`load_model()`, lines 90-168; `unload_model()`, lines 171-193)
- Memory optimization and cleanup (`_cleanup_memory()`, lines 46-88)
- Model offloading for reduced memory usage
- Text completion generation (`get_completion()`, lines 220-280)

The model loading process includes several optimizations:
```python
# Load model with CPU optimizations (lines 113-125)
load_args = {
    "device_map": "cpu",
    "low_cpu_mem_usage": self.config.low_cpu_mem_usage,
    "torch_dtype": torch.float32,
    "local_files_only": True,
    "use_cache": False,
    "offload_folder": self.config.offload_folder,
    "max_memory": self.config.max_memory
}
```

### Completion System (`The_Ultimate_Overlay_App/ai/completion_system.py` & `The_Ultimate_Overlay_App/ai/completion.py`)

These components handle the text analysis pipeline:

- `CompletionSystem` in `completion_system.py` (lines 14-30) provides the main interface
- `CompletionSystem` in `completion.py` (lines 14-148) handles context-aware processing

The `CompletionSystem` in completion.py provides context-aware prompt generation based on the type of content:
```python
# completion.py (lines 97-129)
def _generate_prompt(self, context: Dict[str, Any], features: List[str]) -> str:
    prompt_parts = []
    
    if context['type'] == 'code':
        if 'code_completion' in features:
            prompt_parts.append(f"Complete the following {context['language']} code:")
            prompt_parts.append(context['content'])
    elif context['type'] == 'web':
        if 'text_suggestions' in features:
            prompt_parts.append("Suggest improvements for the following text:")
            prompt_parts.append(context['content'])
    else:  # text, general
        if 'text_suggestions' in features:
            prompt_parts.append("Suggest improvements for the following text:")
            prompt_parts.append(context['content'])
    
    return "\n".join(prompt_parts)
```

### Context Analyzer (`The_Ultimate_Overlay_App/ai/context_analyzer.py`)

The `ContextAnalyzer` class (lines 8-144) determines the appropriate AI features based on the current context:

- Detecting content type (`analyze_context()`, lines 18-42)
- Identifying programming languages (`_analyze_file_context()`)
- Determining available AI features (`get_available_features()`, lines 115-144)
- Analyzing text selection

## User Interface

### Main Overlay UI

The main overlay contains:
- Top button bar (Home, Read, AI) (`overlay/window.py`, lines 214-254)
- Context label showing current application (line 262)
- Search bar (lines 265-269)
- Content area for shortcuts or AI content (lines 271-278)

### AI Content Display

When AI is enabled and text is selected, the overlay shows:
- Title with the selected text
- AI-generated analysis
- Copy and clear buttons

The AI content is displayed in a dedicated container with custom styling:
```python
# overlay/window.py (lines 1047-1080)
# Create container for AI content
ai_container = QWidget()
ai_layout = QVBoxLayout(ai_container)
ai_layout.setContentsMargins(10, 10, 10, 10)

# Title with selected text
title_label = QLabel(f"<b>AI Analysis of:</b> {query_text}")
title_label.setStyleSheet("color: #ffffff; font-size: 14px;")

# AI response content
content_label = QLabel(self.ai_content)
content_label.setStyleSheet("""
    color: #aeefff; 
    background-color: #2d2d2d;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 10px;
    font-size: 13px;
""")
```

### Application-Specific Home Screens

The overlay provides different home screens based on the active application:
- Excel: Formula shortcuts, functions (`add_excel_home()`, lines 386-428)
- Word: Formatting shortcuts (`add_word_home()`, lines 429-449)
- Browser: Web shortcuts (`add_browser_home()`, lines 450-492)
- Steam: Game shortcuts (`add_steam_home()`, lines 493-535)
- Generic: Generic shortcuts (`add_generic_home()`, lines 536-578)

## Text Selection and Analysis

The text selection and analysis feature is a core functionality that monitors user-selected text and provides AI-powered analysis when the AI feature is enabled.

### Text Selection Monitoring

Text selection monitoring is controlled by the AI toggle button:

```python
# overlay/window.py (line 250)
# Connect AI button toggle to text monitoring
self.ai_widget.toggle_button.toggled.connect(self.toggle_text_monitoring)
```

The monitoring is implemented as a background thread that only runs when AI is enabled:

```python
# overlay/window.py (lines 878-885)
def toggle_text_monitoring(self, enabled):
    """Toggle text selection monitoring based on AI button state"""
    if enabled:
        self._start_cursor_monitor()
    else:
        self._stop_cursor_monitor()
```

When enabled, the monitor continuously checks for selected text:

```python
# overlay/window.py (lines 903-937)
def _monitor_function(self):
    """Monitor cursor position and selected text."""
    last_selection = None
    while not self._stop_monitor:
        try:
            # Get selected text from active window
            selected_text = self._get_selected_text()
            
            # Process only if selection changed and not empty
            if selected_text and selected_text != last_selection:
                # Store the selected text
                self.selected_text = selected_text
                
                # Get context information
                context = {
                    'cursor_pos': QCursor.pos(),
                    'app_name': window_info.get('app_name'),
                    'window_title': window_info.get('window_title'),
                    'file_extension': window_info.get('file_extension')
                }
                
                # Request explanation
                self.ai_widget.request_explanation(selected_text, context, self.selected_text)
            
            last_selection = selected_text
            time.sleep(0.2)  # Reduce CPU usage
        except Exception as e:
            logger.error(f"Error in cursor monitor: {str(e)}")
```

### Text Selection Detection

The application uses multiple approaches to detect selected text across different applications:

1. **Windows API Standard Edit Controls**: Uses `EM_GETSEL` and `WM_GETTEXT` to get selection boundaries and text.
   ```python
   # overlay/window.py (lines 983-995)
   start, end = win32gui.SendMessage(hwnd, win32con.EM_GETSEL, 0, 0)
   if start != end:  # There is a selection
       length = win32gui.SendMessage(hwnd, win32con.WM_GETTEXTLENGTH, 0, 0)
       buffer = win32gui.PyMakeBuffer(length + 1)
       win32gui.SendMessage(hwnd, win32con.WM_GETTEXT, length + 1, buffer)
       text = buffer.tobytes().decode('utf-8', errors='ignore')
       return text[start:end]
   ```

2. **UI Automation**: For modern applications that don't expose selection through standard APIs.
   ```python
   # overlay/window.py (lines 999-1017)
   import uiautomation as auto
   control = auto.ControlFromHandle(hwnd)
   if control:
       # Try to get selection using UI Automation
       selection = None
       if hasattr(control, 'GetSelection'):
           selection = control.GetSelection()
       elif hasattr(control, 'GetSelectionPattern'):
           pattern = control.GetSelectionPattern()
           if pattern:
               selection = pattern.GetSelection()
   ```

3. **Fallback Method**: Gets the entire window text as a last resort.
   ```python
   # overlay/window.py (lines 1020-1024)
   text = win32gui.GetWindowText(hwnd)
   if text:
       return text.strip() or None
   ```

### AI Analysis Processing

When text is selected, the analysis process follows these steps:

1. **Request Explanation**: The selected text and context are passed to the AI widget.
   ```python
   # overlay/window.py (line 924)
   self.ai_widget.request_explanation(selected_text, context, self.selected_text)
   ```

2. **Process Request**: The request is queued and processed in the main thread.
   ```python
   # overlay/ai_widget.py (lines 383-409)
   def _process_explanation_request(self):
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
   ```

3. **Generate Explanation**: The AI model processes the text in a background thread.
   ```python
   # overlay/ai_widget.py (lines 411-441)
   def _generate_explanation(self, selected_text, context=None, query_text=None):
       # Generate completion using the model
       completion = self.completion_system.get_completion(
           text=selected_text,
           context=context
       )
       
       # Update UI from the main thread
       if completion:
           self.completion_ready.emit(completion, query_text)
   ```

4. **Display Results**: The results are displayed in the overlay UI.
   ```python
   # overlay/window.py (lines 1038-1046)
   def display_ai_content(self, completion, query=None):
       self.ai_content = completion
       self.selected_text = query if query else self.selected_text
       self.update_overlay()
   ```

## Function Documentation

### Overlay Window Functions

#### `OverlayWindow.run()` (`overlay/window.py` line 151)
Starts the Qt application and shows the overlay window.

#### `MovableOverlayWidget.__init__()` (`overlay/window.py` lines 157-301)
Initializes the overlay widget with UI components and starts monitoring threads.

#### `MovableOverlayWidget.toggle_text_monitoring(enabled)` (`overlay/window.py` lines 878-885)
Toggles text selection monitoring based on AI button state.

#### `MovableOverlayWidget._start_cursor_monitor()` (`overlay/window.py` lines 886-895)
Starts a background thread to monitor cursor position and text selection.

#### `MovableOverlayWidget._monitor_function()` (`overlay/window.py` lines 903-937)
Background thread function that monitors selected text and triggers AI analysis.

#### `MovableOverlayWidget._get_selected_text()` (`overlay/window.py` lines 960-978)
Gets the currently selected text from the active window using Windows API.

#### `MovableOverlayWidget._get_selection_direct(hwnd)` (`overlay/window.py` lines 979-1037)
Gets selected text directly from a window handle using multiple methods.

#### `MovableOverlayWidget._get_window_info()` (`overlay/window.py` lines 938-959)
Gets information about the current active window, including title and app name.

#### `MovableOverlayWidget.detect_language_by_extension(window_title)` (`overlay/window.py` lines 326-341)
Detects programming language based on file extension in window title.

#### `MovableOverlayWidget.detect_app_by_name(window_title)` (`overlay/window.py` lines 342-359)
Detects the active application based on window title patterns.

#### `MovableOverlayWidget.display_ai_content(completion, query)` (`overlay/window.py` lines 1038-1046)
Displays AI-generated content in the overlay UI.

#### `MovableOverlayWidget.display_ai_content_ui()` (`overlay/window.py` lines 1047-1133)
Creates and displays the UI components for AI content.

#### `MovableOverlayWidget.update_overlay()` (`overlay/window.py` lines 579-829)
Updates the overlay content based on the current context and mode.

#### `MovableOverlayWidget.create_app_home(app_name)` (`overlay/window.py` lines 360-385)
Creates the application-specific home screen.

### AI Widget Functions

#### `AIWidget.__init__(parent)` (`overlay/ai_widget.py` lines 25-61)
Initializes the AI widget with state variables and UI components.

#### `AIWidget.setup_ui()` (`overlay/ai_widget.py` lines 62-121)
Sets up the UI components for the AI widget.

#### `AIWidget.refresh_model_status()` (`overlay/ai_widget.py` lines 122-157)
Checks model status and updates UI accordingly.

#### `AIWidget.toggle_ai()` (`overlay/ai_widget.py` lines 263-274)
Toggles AI features on/off, handling state management.

#### `AIWidget.start_loading()` (`overlay/ai_widget.py` lines 275-290)
Starts loading the AI model in a background thread.

#### `AIWidget._load_thread()` (`overlay/ai_widget.py` lines 291-303)
Background thread function for loading the model.

#### `AIWidget.start_download()` (`overlay/ai_widget.py` lines 171-189)
Starts downloading the AI model in a background thread.

#### `AIWidget._download_thread()` (`overlay/ai_widget.py` lines 190-210)
Background thread function for downloading the model.

#### `AIWidget.request_explanation(selected_text, context, query_text)` (`overlay/ai_widget.py` lines 365-382)
Requests an AI explanation for the selected text with proper error handling.

#### `AIWidget._process_explanation_request()` (`overlay/ai_widget.py` lines 383-409)
Processes explanation requests in the main thread.

#### `AIWidget._generate_explanation(selected_text, context, query_text)` (`overlay/ai_widget.py` lines 411-441)
Generates an explanation using the model and updates the UI with the result.

### Model Management Functions

#### `ModelManager.__init__(config)` (`ai/model_manager.py` lines 19-45)
Initializes the model manager with configuration and sets up offload directory.

#### `ModelManager._cleanup_memory()` (`ai/model_manager.py` lines 46-88)
Cleans up memory and temporary files.

#### `ModelManager.load_model()` (`ai/model_manager.py` lines 90-168)
Loads the model in a background thread with memory optimization.

#### `ModelManager.unload_model()` (`ai/model_manager.py` lines 171-193)
Unloads the model and cleans up resources.

#### `ModelManager.is_model_available()` (`ai/model_manager.py` lines 195-203)
Checks if the model is available for use.

#### `ModelManager.get_completion(prompt, context)` (`ai/model_manager.py` lines 220-280)
Generates a completion for the given prompt using the loaded model.

### Completion System Functions

#### `CompletionSystem.__init__(config)` (`ai/completion.py` lines 16-28)
Initializes the completion system with configuration and components.

#### `CompletionSystem.start()` (`ai/completion.py` lines 30-40)
Starts the completion system.

#### `CompletionSystem.stop()` (`ai/completion.py` lines 42-54)
Stops the completion system.

#### `CompletionSystem._process_queue()` (`ai/completion.py` lines 56-66)
Processes completion requests from the queue.

#### `CompletionSystem.get_completion(text, context)` (`ai/completion_system.py` lines 19-27)
Gets a completion for the given text using the model manager.

#### `CompletionSystem._generate_prompt(context, features)` (`ai/completion.py` lines 97-129)
Generates an appropriate prompt based on context and available features.

## Plugin Interactions

The Ultimate Overlay interfaces with various applications through plugin-like integrations that detect and interact with specific applications.

### Application Detection

The system detects active applications through window title analysis:

```python
# overlay/window.py (lines 342-359)
def detect_app_by_name(self, window_title):
    app_to_lang = {
        'Excel': ['excel', 'spreadsheet'],
        'Word': ['word', 'document'],
        'Browser': ['chrome', 'firefox', 'edge', 'opera', 'safari'],
        'Steam': ['steam'],
        'VSCode': ['visual studio code', 'vscode'],
        'NotePad': ['notepad'],
        'PyCharm': ['pycharm']
    }
    
    if window_title:
        title_lower = window_title.lower()
        for app, keywords in app_to_lang.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return app
    return None
```

### Excel Integration

The Excel integration provides formula shortcuts and functions:

```python
# overlay/window.py (lines 386-428)
def add_excel_home(self, layout):
    functions_group = QGroupBox("Excel Functions")
    functions_layout = QVBoxLayout()
    
    # Excel functions organized by category
    excel_functions = {
        "Math": ["SUM", "AVERAGE", "COUNT", "MAX", "MIN", "ROUND"],
        "Text": ["CONCATENATE", "LEFT", "RIGHT", "MID", "TRIM", "SUBSTITUTE"],
        "Lookup": ["VLOOKUP", "HLOOKUP", "INDEX", "MATCH", "INDIRECT"],
        "Date": ["TODAY", "NOW", "DATE", "MONTH", "YEAR", "WEEKDAY"]
    }
    
    # Add function groups
    for category, funcs in excel_functions.items():
        cat_label = QLabel(f"<b>{category}</b>")
        cat_label.setStyleSheet("color: #ffffff; background-color: #3d3d3d; padding: 3px;")
        functions_layout.addWidget(cat_label)
        
        for func in funcs:
            # Create row with function and description
            # ...
```

### Word Integration

The Word integration provides formatting shortcuts:

```python
# overlay/window.py (lines 429-449)
def add_word_home(self, layout):
    style_group = QGroupBox("Word Formatting")
    style_layout = QVBoxLayout()
    
    # Word formatting shortcuts
    word_shortcuts = [
        {"shortcut": "Ctrl+B", "description": "Bold text"},
        {"shortcut": "Ctrl+I", "description": "Italic text"},
        {"shortcut": "Ctrl+U", "description": "Underline text"},
        # ...
    ]
```

### Browser Integration

The browser integration provides web shortcuts and search suggestions:

```python
# overlay/window.py (lines 450-492)
def add_browser_home(self, layout):
    web_group = QGroupBox("Browser Shortcuts")
    web_layout = QVBoxLayout()
    
    # Browser shortcuts
    browser_shortcuts = [
        {"shortcut": "Ctrl+T", "description": "New tab"},
        {"shortcut": "Ctrl+W", "description": "Close tab"},
        # ...
    ]
```

### Steam Integration

The Steam integration provides game shortcuts and hints:

```python
# overlay/window.py (lines 493-535)
def add_steam_home(self, layout):
    game_group = QGroupBox("Steam Shortcuts")
    game_layout = QVBoxLayout()
    
    # Steam shortcuts
    steam_shortcuts = [
        {"shortcut": "Shift+Tab", "description": "Toggle Steam overlay"},
        {"shortcut": "F12", "description": "Take screenshot"},
        {"shortcut": "Ctrl+R", "description": "Refresh friends list"},
        {"shortcut": "Ctrl+Tab", "description": "Switch between Steam windows"},
        {"shortcut": "Ctrl+B", "description": "View broadcast"},
        {"shortcut": "Ctrl+P", "description": "Pause download"},
        {"shortcut": "Ctrl+E", "description": "View news"},
        {"shortcut": "Ctrl+I", "description": "View inventory"}
    ]
    
    # Add shortcuts to layout
    for shortcut_info in steam_shortcuts:
        # Create row with shortcut and description
        # ...
```

### Plugin Interaction with AI

The plugins interact with the AI system through context analysis:

1. **Context Detection**: The application detects the active application context (`overlay/window.py` lines 919-923).
   ```python
   window_info = self._get_window_info()
   context = {
       'app_name': window_info.get('app_name'),
       'window_title': window_info.get('window_title'),
       'file_extension': window_info.get('file_extension')
   }
   ```

2. **Context Analysis**: The `ContextAnalyzer` uses this information to determine the appropriate AI features (`ai/context_analyzer.py` lines 18-42).
   ```python
   def analyze_context(self, content, cursor_position, selection, file_extension, app_name):
       # Update context with current info
       self.current_context.update({
           'content': content,
           'cursor_position': cursor_position,
           'selection': selection
       })
       
       # Determine context type based on application or file extension
       if file_extension:
           self._analyze_file_context(file_extension)
       elif app_name:
           self._analyze_app_context(app_name)
   ```

3. **Feature Selection**: Based on the context, different AI features are enabled (`ai/context_analyzer.py` lines 115-144).

4. **Prompt Generation**: The completion system generates appropriate prompts based on the detected context (`ai/completion.py` lines 97-129).

## Customizing the AI Model

The application is designed to work with a local GPT-2 model by default, but it can be customized to use different models.

### Model Location

The model is stored in the `models/gpt2` directory relative to the project root. The `AIConfig` class in `ai/config.py` sets the absolute path to the model directory:

```python
# ai/config.py (lines 26-33)
# Set absolute path to model directory
self.model_path = os.path.join(MODELS_DIR, "gpt2")
```

### Changing the Model

To use a different model:

1. Download or train your model and save it in the `models/` directory
2. Modify `AIConfig` in `ai/config.py` to point to your model:

```python
# Change the model name (line 26)
self.model_name = "your_model_name"  
# Update the model path (line 29)
self.model_path = os.path.join(MODELS_DIR, "your_model_name")
```

3. Adjust model parameters as needed:

```python
# Model parameters (lines 34-35)
self.context_window = 1024  # Adjust based on model capability
self.max_length = 200  # Adjust generation length
```

4. Optimize memory settings based on your hardware:

```python
# Memory settings (lines 44-46, 50-60)
self.torch_dtype = "float16"  # Use float16 for more efficient processing
self.max_memory = {0: "8GB"}  # Adjust based on available RAM
```

The model is loaded in `ModelManager.load_model()` function in `ai/model_manager.py` (lines 90-168). 