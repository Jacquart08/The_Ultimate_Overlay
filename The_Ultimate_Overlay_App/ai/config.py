"""
Configuration settings for the AI module.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import os

# Get the absolute path to the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class AIConfig:
    """Configuration for AI features."""
    
    def __init__(self):
        # Model settings
        self.model_name = "codellama/CodeLlama-7b-hf"
        self.model_path = os.path.join(PROJECT_ROOT, "models", "codellama-7b")
        self.quantization = "none"  # No quantization for CPU
        
        # Feature settings
        self.enabled = True
        self.max_length = 15  # Further reduced for better performance
        self.temperature = 0.2  # Lower temperature for more focused completions
        self.top_p = 0.95
        self.code_languages = []
        self.context_window = 128  # Further reduced context window
        
        # Performance settings
        self.device = "cpu"
        self.batch_size = 1  # Process one completion at a time
        self.max_memory = {0: "1GB"}  # Further reduced memory limit
    
    @classmethod
    def load(cls, config_path: str = "config/ai_config.json") -> 'AIConfig':
        """Load configuration from JSON file."""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
            return cls(**config_dict)
        return cls()
    
    def save(self, config_path: str = "config/ai_config.json") -> None:
        """Save configuration to JSON file."""
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(self.__dict__, f, indent=4)
    
    def update(self, **kwargs) -> None:
        """Update configuration settings."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value) 