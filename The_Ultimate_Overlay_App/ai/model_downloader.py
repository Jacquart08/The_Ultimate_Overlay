"""
Model downloader for handling model installation.
"""
import os
import sys
import logging
from typing import Optional, Callable
from transformers import AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import snapshot_download, HfFolder
from tqdm import tqdm
from .config import AIConfig

logger = logging.getLogger(__name__)

class ModelDownloader:
    """Handles downloading and installation of AI models."""
    
    def __init__(self, config):
        self.config = config
        self.download_progress = None
    
    def is_model_installed(self) -> bool:
        """Check if the model is already installed."""
        model_path = self.config.model_path
        
        if not os.path.exists(model_path):
            logger.info(f"Model directory does not exist: {model_path}")
            return False
            
        # Check for essential files
        required_files = [
            'config.json',
            'tokenizer.json',
            'tokenizer_config.json',
            'special_tokens_map.json'
        ]
        
        # Check for model files (either safetensors or pytorch format)
        model_files = [
            'model.safetensors.index.json',  # Safetensors format
            'pytorch_model.bin.index.json'   # PyTorch format
        ]
        
        # Check each required file
        for file in required_files:
            file_path = os.path.join(model_path, file)
            if not os.path.exists(file_path):
                logger.info(f"Required file not found: {file_path}")
                return False
        
        # Check for at least one model format
        has_model = False
        for model_file in model_files:
            if os.path.exists(os.path.join(model_path, model_file)):
                has_model = True
                break
                
        if not has_model:
            logger.info("No model files found")
            return False
                
        logger.info(f"Model is already installed at: {model_path}")
        return True
    
    def download_model(self, progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """Download and install the model."""
        try:
            if self.is_model_installed():
                logger.info("Model is already installed, skipping download")
                if progress_callback:
                    progress_callback(100)  # Signal completion
                return True
                
            logger.info(f"Starting model download to: {self.config.model_path}")
            
            # Create model directory if it doesn't exist
            os.makedirs(self.config.model_path, exist_ok=True)
            
            # Create progress bar
            progress_bar = tqdm(total=100, desc="Downloading model")
            
            def update_progress(progress: int):
                progress_bar.update(progress - progress_bar.n)
                if progress_callback:
                    progress_callback(progress)
            
            # Download model files
            snapshot_download(
                repo_id=self.config.model_name,
                local_dir=self.config.model_path,
                local_dir_use_symlinks=False,
                tqdm_class=tqdm
            )
            
            # Verify download
            if not self.is_model_installed():
                logger.error("Model files not found after download")
                return False
                
            logger.info("Model downloaded successfully")
            progress_bar.close()
            return True
            
        except Exception as e:
            logger.error(f"Error downloading model: {str(e)}")
            return False 