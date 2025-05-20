"""
Completion system for handling different types of AI completions.
"""
from typing import Dict, Any, Optional, List
from queue import Queue
from threading import Thread, Lock
import time
import logging
from .model_manager import ModelManager
from .context_analyzer import ContextAnalyzer
from .config import AIConfig

logger = logging.getLogger(__name__)

class CompletionSystem:
    """Handles different types of AI completions based on context."""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.model_manager = ModelManager(config)
        self.context_analyzer = ContextAnalyzer(config)
        self.completion_queue = Queue()
        self.is_running = False
        self.worker_thread: Optional[Thread] = None
        self.lock = Lock()
        self.last_completion_time = 0
        self.completion_cooldown = 0.5  # seconds between completions
    
    def start(self) -> None:
        """Start the completion system."""
        with self.lock:
            if self.is_running:
                return
            
            self.is_running = True
            self.worker_thread = Thread(target=self._process_queue)
            self.worker_thread.daemon = True
            self.worker_thread.start()
            logger.info("Completion system started")
    
    def stop(self) -> None:
        """Stop the completion system."""
        with self.lock:
            if not self.is_running:
                return
            
            self.is_running = False
            if self.worker_thread:
                self.worker_thread.join()
            self.model_manager.unload_model()
            logger.info("Completion system stopped")
    
    def _process_queue(self) -> None:
        """Process completion requests from the queue."""
        while self.is_running:
            try:
                if not self.completion_queue.empty():
                    request = self.completion_queue.get()
                    self._handle_completion_request(request)
                time.sleep(0.1)  # Prevent busy waiting
            except Exception as e:
                logger.error(f"Error processing completion queue: {str(e)}")
    
    def _handle_completion_request(self, request: Dict[str, Any]) -> None:
        """Handle a completion request based on context."""
        current_time = time.time()
        if current_time - self.last_completion_time < self.completion_cooldown:
            return
        
        try:
            # Analyze context
            context = self.context_analyzer.analyze_context(
                content=request.get('content', ''),
                cursor_position=request.get('cursor_position', 0),
                selection=request.get('selection'),
                file_extension=request.get('file_extension'),
                app_name=request.get('app_name')
            )
            
            # Get available features
            features = self.context_analyzer.get_available_features()
            
            if not features:
                return
            
            # Generate appropriate prompt based on context and features
            prompt = self._generate_prompt(context, features)
            
            # Get completion from model
            completion = self.model_manager.get_completion(prompt, context)
            
            if completion:
                self.last_completion_time = current_time
                # Here you would typically send the completion back to the UI
                # This will be implemented when we integrate with the overlay
                
        except Exception as e:
            logger.error(f"Error handling completion request: {str(e)}")
    
    def _generate_prompt(self, context: Dict[str, Any], features: List[str]) -> str:
        """Generate appropriate prompt based on context and features."""
        prompt_parts = []
        
        if context['type'] == 'code':
            if 'code_completion' in features:
                prompt_parts.append(f"Complete the following {context['language']} code:")
                prompt_parts.append(context['content'])
            elif 'learning_suggestions' in features:
                prompt_parts.append(f"Suggest learning resources for {context['language']}:")
                prompt_parts.append(context['content'])
        
        elif context['type'] == 'web':
            if 'text_suggestions' in features:
                prompt_parts.append("Suggest improvements for the following text:")
                prompt_parts.append(context['content'])
            elif 'translation' in features:
                prompt_parts.append("Translate the following text to English:")
                prompt_parts.append(context['content'])
            elif 'learning_suggestions' in features:
                prompt_parts.append("Suggest learning resources for the following topic:")
                prompt_parts.append(context['content'])
        
        else:  # text, general
            if 'text_suggestions' in features:
                prompt_parts.append("Suggest improvements for the following text:")
                prompt_parts.append(context['content'])
            elif 'translation' in features:
                prompt_parts.append("Translate the following text to English:")
                prompt_parts.append(context['content'])
        
        return "\n".join(prompt_parts)
    
    def request_completion(self, 
                         content: str, 
                         cursor_position: int, 
                         selection: Optional[str] = None,
                         file_extension: Optional[str] = None,
                         app_name: Optional[str] = None) -> None:
        """Request a completion based on current context."""
        request = {
            'content': content,
            'cursor_position': cursor_position,
            'selection': selection,
            'file_extension': file_extension,
            'app_name': app_name,
            'timestamp': time.time()
        }
        self.completion_queue.put(request) 