"""
Completion system for handling AI completions.
"""
import logging
from typing import Optional, Dict, Any
from .config import AIConfig
from .model_manager import ModelManager
from .completion import CompletionSystem as BaseCompletionSystem

logger = logging.getLogger(__name__)

class CompletionSystem:
    """System for handling AI completions."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.model_manager = ModelManager(config)
        self.base_system = BaseCompletionSystem(config)
    
    def get_completion(self, text: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Get a completion for the given text."""
        if not self.model_manager.is_model_available():
            logger.warning("Model not available for completion")
            return None
            
        try:
            return self.model_manager.get_completion(text, context)
        except Exception as e:
            logger.error(f"Error getting completion: {str(e)}")
            return None 