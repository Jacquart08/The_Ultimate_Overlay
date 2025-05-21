"""
Model downloader for AI features.
"""
import os
import logging
import shutil
import time
import json
from pathlib import Path
from typing import Optional, Callable, Dict, List
from transformers import AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import snapshot_download, HfFolder
from tqdm import tqdm
from .config import AIConfig
import torch

logger = logging.getLogger(__name__)

class ModelDownloader:
    """Handles model downloading and initialization."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self._download_attempts = 0
        self._max_retries = 3
        self._retry_delay = 5  # seconds
        
        # Set up offload directory in user's home directory
        home_dir = os.path.expanduser("~")
        self.offload_dir = os.path.join(home_dir, ".ultimate_overlay", "offload")
        self.config.offload_folder = self.offload_dir
        
        # Create offload directory with proper permissions
        try:
            os.makedirs(self.offload_dir, exist_ok=True)
            # Test write permissions
            test_file = os.path.join(self.offload_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            logger.info(f"Offload directory created and verified at: {self.offload_dir}")
        except Exception as e:
            logger.warning(f"Could not create offload directory at {self.offload_dir}: {str(e)}")
            # Fallback to system temp directory
            import tempfile
            self.offload_dir = os.path.join(tempfile.gettempdir(), "ultimate_overlay_offload")
            self.config.offload_folder = self.offload_dir
            os.makedirs(self.offload_dir, exist_ok=True)
            logger.info(f"Using fallback offload directory at: {self.offload_dir}")
    
    def _cleanup_partial_download(self, path: str) -> None:
        """Clean up any partial downloads."""
        try:
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)
                time.sleep(1)  # Give filesystem time to clean up
        except Exception as e:
            logger.warning(f"Error cleaning up partial download: {str(e)}")
    
    def _verify_file(self, file_path: str, expected_size: Optional[int] = None) -> bool:
        """Verify a single file exists and has valid content."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return False
                
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(f"File is empty: {file_path}")
                return False
                
            if expected_size and file_size != expected_size:
                logger.error(f"File size mismatch for {file_path}: expected {expected_size}, got {file_size}")
                return False
            
            # For JSON files, verify they can be loaded
            if file_path.endswith('.json'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in {file_path}: {str(e)}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying file {file_path}: {str(e)}")
            return False
    
    def _verify_download(self, model_path: str) -> bool:
        """Verify that all required files are present and valid."""
        required_files = [
            'config.json',
            'tokenizer.json',
            'tokenizer_config.json',
            'special_tokens_map.json',
            'pytorch_model.bin',
            'vocab.json',
            'merges.txt'
        ]
        
        try:
            # Check if directory exists
            if not os.path.exists(model_path):
                logger.error(f"Model directory does not exist: {model_path}")
                return False
            
            # Log directory contents for debugging
            logger.info(f"Contents of {model_path}:")
            for root, dirs, files in os.walk(model_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    size = os.path.getsize(file_path)
                    logger.info(f"  {file_path} ({size} bytes)")
            
            # Check each required file
            missing_files = []
            invalid_files = []
            
            for file in required_files:
                # Search for the file in all subdirectories
                found = False
                for root, dirs, files in os.walk(model_path):
                    if file in files:
                        file_path = os.path.join(root, file)
                        if self._verify_file(file_path):
                            found = True
                            break
                
                if not found:
                    missing_files.append(file)
            
            if missing_files:
                logger.error(f"Missing required files: {', '.join(missing_files)}")
                return False
                
            if invalid_files:
                logger.error(f"Invalid files: {', '.join(invalid_files)}")
                return False
            
            logger.info(f"Model verification successful at: {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying download: {str(e)}")
            return False
    
    def is_model_installed(self) -> bool:
        """Check if model is installed and valid."""
        return self._verify_download(self.config.model_path)
    
    def download_model(self, progress_callback: Optional[Callable[[int], None]] = None) -> bool:
        """Download and initialize the model with robust error handling."""
        try:
            if self.is_model_installed():
                logger.info("Model is already installed and verified")
                if progress_callback:
                    progress_callback(100)
                return True
            
            logger.info(f"Starting model download to: {self.config.model_path}")
            
            # Create model directory if it doesn't exist
            os.makedirs(self.config.model_path, exist_ok=True)
            
            # Create progress bar
            progress_bar = tqdm(total=100, desc="Downloading model")
            
            def update_progress(progress: int):
                try:
                    progress_bar.update(progress - progress_bar.n)
                    if progress_callback:
                        progress_callback(progress)
                except Exception as e:
                    logger.warning(f"Error updating progress: {str(e)}")
            
            # Download model files with retry logic
            while self._download_attempts < self._max_retries:
                try:
                    # Clean up any partial downloads
                    self._cleanup_partial_download(self.config.model_path)
                    os.makedirs(self.config.model_path, exist_ok=True)
                    
                    # Download model files with explicit patterns
                    snapshot_download(
                        repo_id=self.config.model_name,
                        local_dir=self.config.model_path,
                        tqdm_class=tqdm,
                        ignore_patterns=[
                            "*.msgpack", "*.h5", "*.safetensors",
                            "*.mlpackage", "*.onnx", "*.tflite",
                            "*.bin.index.json"
                        ],
                        allow_patterns=[
                            "*.json",
                            "*.bin",
                            "*.txt",
                            "*.model",
                            "*.vocab",
                            "*.merges",
                            "*.config"
                        ],
                        token=None,  # Use anonymous access
                        local_files_only=False,  # Force download from hub
                        resume_download=True  # Allow resuming interrupted downloads
                    )
                    
                    # Update progress to 100% after download
                    update_progress(100)
                    
                    # Verify download and log any missing files
                    if not self._verify_download(self.config.model_path):
                        logger.error("Model verification failed after download")
                        # List all files in the directory
                        logger.info("Contents of model directory:")
                        for root, dirs, files in os.walk(self.config.model_path):
                            for file in files:
                                logger.info(f"  {os.path.join(root, file)}")
                        return False
                    
                    logger.info("Model downloaded and verified successfully")
                    progress_bar.close()
                    return True
                    
                except Exception as e:
                    logger.error(f"Download attempt {self._download_attempts + 1} failed: {str(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Check if we have partial files
                    if os.path.exists(self.config.model_path):
                        logger.info("Checking partial download...")
                        files = os.listdir(self.config.model_path)
                        if files:
                            logger.info(f"Found {len(files)} files in partial download: {files}")
                
                self._download_attempts += 1
                if self._download_attempts < self._max_retries:
                    logger.info(f"Retrying download in {self._retry_delay} seconds...")
                    time.sleep(self._retry_delay)
            
            logger.error("All download attempts failed")
            return False
            
        except Exception as e:
            logger.error(f"Error in download process: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        finally:
            try:
                progress_bar.close()
            except:
                pass
    
    def load_model(self) -> bool:
        """Load the model from disk with robust error handling."""
        if not self.is_model_installed():
            logger.error("Model not installed or invalid, cannot load")
            return False
            
        try:
            # Clean up any existing model and memory
            self._cleanup_model()
            
            logger.info("Loading tokenizer...")
            try:
                # First try loading with default settings
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.config.model_path,
                    use_fast=True,
                    local_files_only=True,
                    model_max_length=self.config.context_window
                )
                logger.info("Tokenizer loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load tokenizer with default settings: {str(e)}")
                # Try loading with legacy settings
                try:
                    self.tokenizer = AutoTokenizer.from_pretrained(
                        self.config.model_path,
                        use_fast=False,  # Use legacy tokenizer
                        local_files_only=True,
                        model_max_length=self.config.context_window,
                        trust_remote_code=True
                    )
                    logger.info("Tokenizer loaded successfully with legacy settings")
                except Exception as e2:
                    logger.error(f"Failed to load tokenizer with legacy settings: {str(e2)}")
                    return False
            
            logger.info("Loading model with minimal settings...")
            
            # Basic configuration without offloading
            load_args = {
                "device_map": "cpu",
                "low_cpu_mem_usage": True,
                "torch_dtype": torch.float32,
                "local_files_only": True,
                "use_cache": False,
                "offload_folder": None,  # Disable offloading
                "max_memory": {0: "512MB"},  # Limit memory usage
                "load_in_8bit": False,  # Disable 8-bit quantization
                "load_in_4bit": False,  # Disable 4-bit quantization
                "quantization_config": None,  # Disable quantization
                "trust_remote_code": True  # Allow custom model code
            }
            
            try:
                logger.info("Attempting to load model with configuration:")
                for key, value in load_args.items():
                    logger.info(f"  {key}: {value}")
                
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.config.model_path,
                    **load_args
                )
                logger.info("Model loaded successfully")
                return True
            except Exception as e:
                logger.error(f"Error loading model: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                self._cleanup_model()
                return False
            
        except Exception as e:
            logger.error(f"Error in model loading process: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._cleanup_model()
            return False
    
    def _cleanup_model(self) -> None:
        """Clean up model resources and memory."""
        try:
            logger.info("Starting model cleanup...")
            
            # Clear model and tokenizer
            if self.model is not None:
                logger.info("Cleaning up model...")
                if hasattr(self.model, 'to'):
                    self.model.to('cpu')
                del self.model
                self.model = None
                logger.info("Model cleaned up")
            
            if self.tokenizer is not None:
                logger.info("Cleaning up tokenizer...")
                del self.tokenizer
                self.tokenizer = None
                logger.info("Tokenizer cleaned up")
            
            # Clean up offload directory
            if self.offload_dir and os.path.exists(self.offload_dir):
                logger.info(f"Cleaning up offload directory: {self.offload_dir}")
                try:
                    # Remove files one by one to avoid permission issues
                    for root, dirs, files in os.walk(self.offload_dir, topdown=False):
                        for name in files:
                            try:
                                file_path = os.path.join(root, name)
                                os.remove(file_path)
                                logger.debug(f"Removed file: {file_path}")
                            except Exception as e:
                                logger.warning(f"Failed to remove file {name}: {str(e)}")
                        for name in dirs:
                            try:
                                dir_path = os.path.join(root, name)
                                os.rmdir(dir_path)
                                logger.debug(f"Removed directory: {dir_path}")
                            except Exception as e:
                                logger.warning(f"Failed to remove directory {name}: {str(e)}")
                    # Recreate the directory
                    os.makedirs(self.offload_dir, exist_ok=True)
                    logger.info("Offload directory cleaned up")
                except Exception as e:
                    logger.warning(f"Failed to clean up offload directory: {str(e)}")
            
            # Force garbage collection
            logger.info("Running garbage collection...")
            import gc
            gc.collect()
            
            # Clear CUDA cache if available
            if torch.cuda.is_available():
                logger.info("Clearing CUDA cache...")
                torch.cuda.empty_cache()
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during model cleanup: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}") 