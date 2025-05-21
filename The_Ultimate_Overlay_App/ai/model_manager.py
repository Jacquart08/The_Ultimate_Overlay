"""
Model manager for handling AI model loading and unloading.
"""
import logging
import threading
from typing import Optional, Dict, Any
from transformers import AutoModelForCausalLM, AutoTokenizer
from The_Ultimate_Overlay_App.ai.config import AIConfig
import torch
import gc
import os
import shutil

logger = logging.getLogger(__name__)

class ModelManager:
    """Manages the lifecycle of the AI model."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self._loading = False
        self._lock = threading.Lock()
        self._loading_progress = 0
        
        # Set up offload directory in user's home directory
        home_dir = os.path.expanduser("~")
        self._offload_dir = os.path.join(home_dir, ".ultimate_overlay", "offload")
        self.config.offload_folder = self._offload_dir
        
        # Create offload directory with proper permissions
        try:
            os.makedirs(self._offload_dir, exist_ok=True)
            # Test write permissions
            test_file = os.path.join(self._offload_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            logger.info(f"Offload directory created and verified at: {self._offload_dir}")
        except Exception as e:
            logger.warning(f"Could not create offload directory at {self._offload_dir}: {str(e)}")
            # Fallback to system temp directory
            import tempfile
            self._offload_dir = os.path.join(tempfile.gettempdir(), "ultimate_overlay_offload")
            self.config.offload_folder = self._offload_dir
            os.makedirs(self._offload_dir, exist_ok=True)
            logger.info(f"Using fallback offload directory at: {self._offload_dir}")
        
    def _cleanup_memory(self):
        """Clean up memory and temporary files."""
        # Clear Python garbage collector
        gc.collect()
        
        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # Clean up offload directory
        if self._offload_dir and os.path.exists(self._offload_dir):
            logger.info(f"Cleaning up offload directory: {self._offload_dir}")
            try:
                # Remove files one by one to avoid permission issues
                for root, dirs, files in os.walk(self._offload_dir, topdown=False):
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
                os.makedirs(self._offload_dir, exist_ok=True)
                logger.info("Offload directory cleaned up")
            except Exception as e:
                logger.warning(f"Failed to clean up offload directory: {str(e)}")
        
        # Force garbage collection again
        gc.collect()
    
    def load_model(self):
        """Load the model in a background thread."""
        if self._loading or self.model is not None:
            return
            
        with self._lock:
            self._loading = True
            self._loading_progress = 0
            
        def _load():
            try:
                logger.info(f"Loading model from {self.config.model_path}")
                self._loading_progress = 10
                
                # Clean up memory before loading
                self._cleanup_memory()
                
                # Load tokenizer first with fallback options
                try:
                    self.tokenizer = AutoTokenizer.from_pretrained(
                        self.config.model_path,
                        use_fast=True,
                        local_files_only=True,
                        model_max_length=self.config.context_window,
                        trust_remote_code=True
                    )
                except Exception as e:
                    logger.warning(f"Failed to load tokenizer with fast mode: {str(e)}")
                    # Try with legacy mode
                    self.tokenizer = AutoTokenizer.from_pretrained(
                        self.config.model_path,
                        use_fast=False,
                        local_files_only=True,
                        model_max_length=self.config.context_window,
                        trust_remote_code=True
                    )
                
                self._loading_progress = 30
                
                # Load model with CPU optimizations
                load_args = {
                    "device_map": "cpu",
                    "low_cpu_mem_usage": self.config.low_cpu_mem_usage,
                    "torch_dtype": torch.float32,
                    "local_files_only": True,
                    "use_cache": False,
                    "offload_folder": self.config.offload_folder,
                    "max_memory": self.config.max_memory,
                    "load_in_8bit": False,
                    "load_in_4bit": False,
                    "quantization_config": None,
                    "trust_remote_code": True
                }
                
                logger.info("Loading model with configuration:")
                for key, value in load_args.items():
                    logger.info(f"  {key}: {value}")
                
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.config.model_path,
                    **load_args
                )
                
                # Set model to evaluation mode
                self.model.eval()
                
                self._loading_progress = 100
                logger.info("Model loaded successfully")
                return True
                
            except Exception as e:
                logger.error(f"Error loading model: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.model = None
                self.tokenizer = None
                with self._lock:
                    self._loading = False
                    self._loading_progress = 0
                return False
            
            finally:
                with self._lock:
                    self._loading = False
                    self._loading_progress = 0
        
        # Start loading in background thread
        thread = threading.Thread(target=_load, daemon=True)
        thread.start()
        thread.join()  # Wait for loading to complete
        return self.model is not None and self.tokenizer is not None
    
    def unload_model(self):
        """Unload the model and clean up resources."""
        with self._lock:
            if self.model is not None:
                # Move model to CPU before deletion
                if hasattr(self.model, 'to'):
                    self.model.to('cpu')
                del self.model
                self.model = None
                
            if self.tokenizer is not None:
                del self.tokenizer
                self.tokenizer = None
                
            self._loading = False
            self._loading_progress = 0
            
            # Clean up memory and temporary files
            self._cleanup_memory()
    
    def is_model_available(self) -> bool:
        """Check if the model is available for use."""
        return self.model is not None and self.tokenizer is not None
    
    def is_model_loading(self) -> bool:
        """Check if the model is currently loading."""
        return self._loading
    
    def get_loading_progress(self) -> int:
        """Get the current loading progress (0-100)."""
        return self._loading_progress
    
    def get_model(self) -> Optional[AutoModelForCausalLM]:
        """Get the loaded model."""
        return self.model
    
    def get_tokenizer(self) -> Optional[AutoTokenizer]:
        """Get the loaded tokenizer."""
        return self.tokenizer
    
    def get_completion(self, prompt: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Get a completion from the model."""
        if not self.is_model_available():
            logger.warning("Model not available for completion")
            return None
            
        try:
            # Prepare the prompt with context
            if context:
                file_ext = context.get('file_extension', '')
                app_name = context.get('app_name', '')
                if file_ext:
                    prompt = f"Language: {file_ext}\n{prompt}"
                if app_name:
                    prompt = f"Application: {app_name}\n{prompt}"
            
            # Add instruction for text generation
            prompt = f"Generate a helpful response for the following text:\n{prompt}\nResponse:"
            
            # Generate completion with CPU optimizations
            with torch.no_grad():  # Disable gradient calculation
                # Set number of threads to 1 to avoid OMP errors
                torch.set_num_threads(1)
                
                inputs = self.tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=self.config.context_window
                )
                
                # Generate with memory-efficient settings
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=100,  # Limit response length
                    temperature=0.7,  # Slightly more creative
                    top_p=0.9,  # More focused sampling
                    do_sample=True,
                    num_return_sequences=1,
                    pad_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.2,  # Prevent repetitive text
                    no_repeat_ngram_size=3,  # Prevent repeating phrases
                    num_beams=1,  # Use greedy search to save memory
                    early_stopping=False  # Disable early stopping since we're not using beam search
                )
                
                completion = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                
                # Return only the new text
                new_text = completion[len(prompt):].strip()
                if new_text:
                    logger.info(f"Generated completion: {new_text[:100]}...")
                    return new_text
                logger.warning("No new text generated")
                return None
                
        except Exception as e:
            logger.error(f"Error generating completion: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None 