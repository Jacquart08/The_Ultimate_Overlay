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
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

class AIConfig:
    """Configuration for AI features."""
    
    def __init__(self):
        # Model settings - Using local model
        self.model_name = "gpt2"  # The model name (for reference)
        
        # Set absolute path to model directory
        self.model_path = os.path.join(MODELS_DIR, "gpt2")
        logger.info(f"Model path set to: {self.model_path}")
        
        # Verify model path exists
        if os.path.exists(self.model_path):
            logger.info(f"Found model at: {self.model_path}")
            # List model files
            if os.path.isdir(self.model_path):
                files = os.listdir(self.model_path)
                logger.info(f"Model directory contains {len(files)} files")
                for file in files:
                    if file.endswith('.bin'):
                        logger.info(f"Found model file: {file}")
        else:
            logger.warning(f"Model path does not exist: {self.model_path}")
            logger.warning(f"Current working directory: {os.getcwd()}")
            logger.warning(f"Project root: {PROJECT_ROOT}")
            # Try to find alternate model location
            alt_path = os.path.abspath("models/gpt2")
            logger.warning(f"Trying alternate path: {alt_path}")
            if os.path.exists(alt_path):
                self.model_path = alt_path
                logger.info(f"Using alternate model path: {self.model_path}")
        
        # Model parameters
        self.context_window = 512
        self.max_length = 100  # Limit response length
        
        # Generation settings
        self.temperature = 0.7
        self.top_p = 0.9
        self.repetition_penalty = 1.2
        self.no_repeat_ngram_size = 3
        
        # Memory settings - Optimized for local use
        self.low_cpu_mem_usage = True
        self.torch_dtype = "float32"  # Use float32 for better compatibility
        
        # Set memory limits based on available RAM
        try:
            import psutil
            available_ram = psutil.virtual_memory().available
            ram_gb = available_ram / (1024 * 1024 * 1024)
            if ram_gb > 8:
                ram_limit = "4GB"  # Higher limit for systems with more RAM
            elif ram_gb > 4:
                ram_limit = "2GB"  # Medium limit
            else:
                ram_limit = "1GB"  # Lower limit for systems with less RAM
            self.max_memory = {0: ram_limit}
            logger.info(f"Set memory limit to {ram_limit} based on {ram_gb:.2f}GB available RAM")
        except Exception as e:
            # Fallback to conservative limit
            self.max_memory = {0: "2GB"}
            logger.warning(f"Error detecting RAM, using default 2GB limit: {str(e)}")
        
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
        
        # Feature settings - Optimized for performance
        self.enabled = True
        self.code_languages = ["python", "javascript", "html", "css", "sql", "r", "java", "c", "cpp"]
        self.batch_size = 1
        self.num_threads = 2  # Use 2 threads for better performance
        self.use_cache = True  # Enable caching for better performance
    
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