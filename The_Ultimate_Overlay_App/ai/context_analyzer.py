"""
Context analyzer for determining the current context and appropriate AI features.
"""
from typing import Dict, Any, Optional, List
import re
from .config import AIConfig

class ContextAnalyzer:
    """Analyzes the current context to determine appropriate AI features."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.current_context: Dict[str, Any] = {
            'type': None,  # 'code', 'text', 'web', etc.
            'language': None,  # programming language if code
            'content': None,  # current content
            'cursor_position': None,  # cursor position
            'selection': None  # selected text if any
        }
    
    def analyze_context(self, 
                       content: str, 
                       cursor_position: int, 
                       selection: Optional[str] = None,
                       file_extension: Optional[str] = None,
                       app_name: Optional[str] = None) -> Dict[str, Any]:
        """Analyze the current context and determine appropriate features."""
        self.current_context.update({
            'content': content,
            'cursor_position': cursor_position,
            'selection': selection
        })
        
        # Determine context type
        if file_extension:
            self._analyze_file_context(file_extension)
        elif app_name:
            self._analyze_app_context(app_name)
        else:
            self._analyze_general_context(content)
        
        return self.current_context
    
    def _analyze_file_context(self, file_extension: str) -> None:
        """Analyze context based on file extension."""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.go': 'go',
            '.rs': 'rust',
            '.ts': 'typescript'
        }
        
        language = extension_map.get(file_extension.lower())
        if language:
            self.current_context.update({
                'type': 'code',
                'language': language
            })
        else:
            self.current_context.update({
                'type': 'text',
                'language': None
            })
    
    def _analyze_app_context(self, app_name: str) -> None:
        """Analyze context based on application name."""
        # Map common applications to context types
        app_map = {
            'chrome': 'web',
            'firefox': 'web',
            'edge': 'web',
            'code': 'code',
            'pycharm': 'code',
            'sublime': 'code',
            'notepad++': 'text',
            'word': 'text',
            'excel': 'spreadsheet'
        }
        
        context_type = app_map.get(app_name.lower(), 'general')
        self.current_context.update({
            'type': context_type,
            'language': None
        })
    
    def _analyze_general_context(self, content: str) -> None:
        """Analyze context based on content."""
        # Check for code-like patterns
        code_patterns = [
            r'def\s+\w+\s*\(',  # Python function
            r'function\s+\w+\s*\(',  # JavaScript function
            r'class\s+\w+',  # Class definition
            r'import\s+\w+',  # Import statement
            r'#include\s+<',  # C++ include
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, content):
                self.current_context.update({
                    'type': 'code',
                    'language': None  # Language detection would need more context
                })
                return
        
        self.current_context.update({
            'type': 'text',
            'language': None
        })
    
    def get_available_features(self) -> List[str]:
        """Get list of available AI features for current context."""
        features = []
        
        if not self.current_context['type']:
            return features
        
        if self.current_context['type'] == 'code':
            if self.config.enable_code_completion:
                features.append('code_completion')
            if self.config.enable_learning_suggestions:
                features.append('learning_suggestions')
        
        elif self.current_context['type'] == 'web':
            if self.config.enable_text_suggestions:
                features.append('text_suggestions')
            if self.config.enable_translation:
                features.append('translation')
            if self.config.enable_learning_suggestions:
                features.append('learning_suggestions')
        
        else:  # text, general, etc.
            if self.config.enable_text_suggestions:
                features.append('text_suggestions')
            if self.config.enable_translation:
                features.append('translation')
        
        return features 