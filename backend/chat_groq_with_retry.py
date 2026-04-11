"""
Custom ChatGroq class with built-in retry logic for LangGraph compatibility.
This replaces the original ChatGroq to ensure all API calls have key rotation.
"""

import time
from typing import Any, List, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage
from config import get_current_api_key, rotate_api_key


class ChatGroqWithRetry(ChatGroq):
    """ChatGroq subclass with automatic key rotation for all methods."""
    
    # Define as a class attribute or use object.__setattr__ in __init__
    rotation_max_retries: int = 5
    _original_params: dict = {}
    
    def __init__(self, *args, **kwargs):
        # Disable built-in library retries
        kwargs['max_retries'] = 0
        super().__init__(*args, **kwargs)
        
        # In Pydantic v2 (LangChain 0.3), we use object.__setattr__ for custom private attributes
        object.__setattr__(self, '_original_params', {
            'model_name': kwargs.get('model_name', 'llama-3.3-70b-versatile'),
            'temperature': kwargs.get('temperature', 0.3),
            'max_tokens': kwargs.get('max_tokens', 4096),
        })
    
    def _create_fresh_instance(self, api_key: str) -> 'ChatGroqWithRetry':
        """Create a completely fresh instance with new API key."""
        return ChatGroqWithRetry(
            model_name=self._original_params['model_name'],
            temperature=self._original_params['temperature'],
            max_tokens=self._original_params['max_tokens'],
            groq_api_key=api_key
        )
    
    def _is_rate_limit_error(self, error_str: str) -> bool:
        """Check if error is a rate limit error."""
        return (
            "429" in error_str or 
            "quota" in error_str.lower() or 
            "rate limit" in error_str.lower() or 
            "limit" in error_str.lower() or
            "rate_limit_exceeded" in error_str or
            "tokens per day" in error_str or
            "Need more tokens" in error_str
        )
    
    def _handle_rate_limit(self, attempt: int) -> bool:
        """Handle rate limit by rotating keys."""
        if attempt < self.rotation_max_retries - 1:
            print(f"🔄 API quota reached, rotating to next key...")
            print(f"🔑 Current key before rotation: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
            
            rotate_api_key()
            new_key = get_current_api_key()
            print(f"🔑 New key after rotation: {new_key[:8]}...{new_key[-4:]}")
            
            # Update this instance's API key
            self.groq_api_key = new_key
            print(f"🆕 Updated instance API key to: {self.groq_api_key[:8]}...{self.groq_api_key[-4:]}")
            
            time.sleep(3)
            return True
        else:
            print("❌ All API keys have reached their limits.")
            return False
    
    def invoke(self, input: Any, config: Optional[dict] = None, **kwargs) -> Any:
        """Override invoke with retry logic - matches LangChain signature."""
        for attempt in range(self.rotation_max_retries):
            try:
                return super().invoke(input, config, **kwargs)
            except Exception as e:
                error_str = str(e)
                print(f"ChatGroq Invoke Attempt {attempt + 1}/{self.rotation_max_retries}: {error_str}")
                
                # Enhanced rate limit detection - catch ALL possible patterns
                is_rate_limit = (
                    "429" in error_str or 
                    "quota" in error_str.lower() or 
                    "rate limit" in error_str.lower() or 
                    "limit" in error_str.lower() or
                    "rate_limit_exceeded" in error_str or
                    "tokens per day" in error_str or
                    "Need more tokens" in error_str or
                    "Upgrade to Dev Tier" in error_str or
                    "service tier on_demand" in error_str
                )
                
                print(f"🎯 Rate limit detection: {is_rate_limit}")
                
                if is_rate_limit:
                    if self._handle_rate_limit(attempt):
                        print(f"✅ Retrying with new key...")
                        time.sleep(2)  # Extra pause
                        continue
                    else:
                        print("❌ All API keys have reached their limits.")
                        raise Exception("All API keys have reached their limits. Please try again later.")
                else:
                    print(f"❌ Non-rate-limit error: {error_str}")
                    raise e
        
        raise Exception("Failed after all retry attempts.")
    
    # Don't override other methods to avoid signature conflicts
    # Let __getattr__ handle everything else


def create_chat_groq_with_retry(model_name: str = "llama-3.3-70b-versatile", 
                               temperature: float = 0.3, 
                               max_tokens: int = 4096) -> ChatGroqWithRetry:
    """Create ChatGroq instance with built-in retry logic."""
    return ChatGroqWithRetry(
        model_name=model_name,
        temperature=temperature,
        groq_api_key=get_current_api_key(),
        max_tokens=max_tokens,
        max_retries=0 # Force immediate fail for rotation
    )
