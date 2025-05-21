"""
Configuration settings for the AI module.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import os
import tempfile

# Get the absolute path to the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class AIConfig:
    """Configuration for AI features."""
    
    def __init__(self):
        # Model settings - Using a tiny model
        self.model_name = "gpt2"  # Tiny model (124M parameters)
        self.model_path = os.path.join("models", "gpt2")
        self.context_window = 512  # Smaller context window
        self.max_length = 100  # Limit response length
        
        # Generation settings
        self.temperature = 0.7
        self.top_p = 0.9
        self.repetition_penalty = 1.2
        self.no_repeat_ngram_size = 3
        
        # Memory settings
        self.low_cpu_mem_usage = True
        self.torch_dtype = "float32"  # Use float32 for better compatibility
        self.max_memory = {0: "2GB"}  # More reasonable memory limit
        
        # Offload settings
        try:
            home_dir = os.path.expanduser("~")
            self.offload_folder = os.path.join(home_dir, ".ultimate_overlay", "offload")
            os.makedirs(self.offload_folder, exist_ok=True)
            self.offload_state_dict = True
        except Exception as e:
            import tempfile
            self.offload_folder = os.path.join(tempfile.gettempdir(), "ultimate_overlay_offload")
            os.makedirs(self.offload_folder, exist_ok=True)
            self.offload_state_dict = True
        
        # Feature settings - Minimal settings
        self.enabled = True
        self.code_languages = []
        self.batch_size = 1
        self.max_memory = {0: "128MB"}  # Very low memory limit
        self.num_threads = 1  # Single thread
        self.use_cache = False  # Disable caching to save memory
    
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