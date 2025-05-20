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
        self._offload_dir = os.path.join(os.path.dirname(self.config.model_path), "offload")
        
    def _cleanup_memory(self):
        """Clean up memory and temporary files."""
        # Clear Python garbage collector
        gc.collect()
        
        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # Clear offload directory
        if os.path.exists(self._offload_dir):
            try:
                shutil.rmtree(self._offload_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up offload directory: {e}")
        
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
                
                # Create offload directory
                os.makedirs(self._offload_dir, exist_ok=True)
                
                # Load tokenizer first
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.config.model_path,
                    use_fast=True  # Use fast tokenizer for better performance
                )
                self._loading_progress = 30
                
                # Load model with CPU optimizations
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.config.model_path,
                    device_map="cpu",
                    low_cpu_mem_usage=True,
                    torch_dtype=torch.float32,  # Use float32 for CPU
                    max_memory=self.config.max_memory,
                    offload_folder=self._offload_dir  # Enable offloading to disk
                )
                
                # Set model to evaluation mode
                self.model.eval()
                
                self._loading_progress = 100
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading model: {str(e)}")
                self.model = None
                self.tokenizer = None
                with self._lock:
                    self._loading = False
                    self._loading_progress = 0
                return
            
            with self._lock:
                self._loading = False
                self._loading_progress = 0
        
        threading.Thread(target=_load, daemon=True).start()
    
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
                    max_new_tokens=self.config.max_length,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    do_sample=True,
                    num_return_sequences=1,
                    pad_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.2,  # Prevent repetitive text
                    no_repeat_ngram_size=3,  # Prevent repeating phrases
                    num_beams=1,  # Use greedy search to save memory
                    early_stopping=False  # Disable early stopping since we're using greedy search
                )
                
                completion = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                
                # Return only the new text
                new_text = completion[len(prompt):].strip()
                if new_text:
                    return new_text
                return None
                
        except Exception as e:
            logger.error(f"Error generating completion: {str(e)}")
            return None 