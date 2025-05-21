"""
AI module for The Ultimate Overlay.
Handles all AI-related functionality including code completion,
text suggestions, and learning resource recommendations.
"""

from .model_manager import ModelManager
from .completion import CompletionSystem
from .context_analyzer import ContextAnalyzer
from .config import AIConfig

__all__ = ['ModelManager', 'CompletionSystem', 'ContextAnalyzer', 'AIConfig'] 