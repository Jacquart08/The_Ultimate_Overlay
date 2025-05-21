"""
Configuration settings for the AI module.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import os
import tempfile
import logging

logger = logging.getLogger(__name__)

# Get the absolute path to the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class AIConfig:
    """Configuration for AI features."""
    
    def __init__(self):
        logger.info("Initializing AIConfig")
        try:
            # Model settings - Using a tiny model
            self.model_name = "gpt2"  # Tiny model (124M parameters)
            
            # Set up model path
            try:
                # First try in the project's models directory
                self.model_path = os.path.join(PROJECT_ROOT, "models", "gpt2")
                if not os.path.exists(self.model_path):
                    # If not found, try in user's home directory
                    home_dir = os.path.expanduser("~")
                    self.model_path = os.path.join(home_dir, ".ultimate_overlay", "models", "gpt2")
                    if not os.path.exists(self.model_path):
                        # Create the directory
                        os.makedirs(self.model_path, exist_ok=True)
                        logger.info(f"Created model directory at: {self.model_path}")
            except Exception as e:
                logger.error(f"Error setting up model path: {str(e)}")
                # Fallback to temp directory
                self.model_path = os.path.join(tempfile.gettempdir(), "ultimate_overlay", "models", "gpt2")
                os.makedirs(self.model_path, exist_ok=True)
                logger.info(f"Using fallback model directory at: {self.model_path}")
            
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
                logger.info(f"Using offload directory at: {self.offload_folder}")
            except Exception as e:
                logger.warning(f"Could not create offload directory in home: {str(e)}")
                self.offload_folder = os.path.join(tempfile.gettempdir(), "ultimate_overlay_offload")
                os.makedirs(self.offload_folder, exist_ok=True)
                self.offload_state_dict = True
                logger.info(f"Using fallback offload directory at: {self.offload_folder}")
            
            # Feature settings - Minimal settings
            self.enabled = True
            self.code_languages = []
            self.batch_size = 1
            self.max_memory = {0: "128MB"}  # Very low memory limit
            self.num_threads = 1  # Single thread
            self.use_cache = False  # Disable caching to save memory
            
            logger.info("AIConfig initialization completed")
            
        except Exception as e:
            logger.error(f"Error in AIConfig.__init__: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    @classmethod
    def load(cls, config_path: str = "config/ai_config.json") -> 'AIConfig':
        """Load configuration from JSON file."""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_dict = json.load(f)
                return cls(**config_dict)
            return cls()
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {str(e)}")
            return cls()
    
    def save(self, config_path: str = "config/ai_config.json") -> None:
        """Save configuration to JSON file."""
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(self.__dict__, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {str(e)}")
    
    def update(self, **kwargs) -> None:
        """Update configuration settings."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
        except Exception as e:
            logger.error(f"Error updating config: {str(e)}") 