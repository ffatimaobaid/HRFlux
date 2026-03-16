"""
Centralized Groq API client with automatic key rotation and retry logic.
This module provides a unified way to handle Groq API calls with rate limit handling.
"""

import time
from typing import Any, Dict, List, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from config import get_current_api_key, rotate_api_key


class GroqClientWithRetry:
    """ChatGroq wrapper with automatic key rotation."""
    
    def __init__(self, chat_groq: ChatGroq):
        self.chat_groq = chat_groq
        self.max_retries = 5  # Increased to match number of API keys
        self.model_name = chat_groq.model_name
        self.temperature = chat_groq.temperature
        self.max_tokens = chat_groq.max_tokens
    
    def __getattr__(self, name):
        """Delegate all other attributes to the underlying ChatGroq instance."""
        return getattr(self.chat_groq, name)
    
    def _create_new_chat_groq(self, api_key: str) -> ChatGroq:
        """Create a fresh ChatGroq instance with new API key."""
        return ChatGroq(
            model_name=self.model_name,
            temperature=self.temperature,
            groq_api_key=api_key,
            max_tokens=self.max_tokens
        )
    
    def invoke(self, messages: List[BaseMessage], **kwargs) -> Any:
        """
        Invoke Groq API with automatic key rotation on rate limits.
        """
        for attempt in range(self.max_retries):
            try:
                return self.chat_groq.invoke(messages, **kwargs)
                
            except Exception as e:
                error_str = str(e)
                print(f"Groq API Attempt {attempt + 1}/{self.max_retries}: {error_str}")
                
                # Check if it's a quota/rate limit error - updated detection
                is_rate_limit = (
                    "429" in error_str or 
                    "quota" in error_str.lower() or 
                    "rate limit" in error_str.lower() or 
                    "limit" in error_str.lower() or
                    "rate_limit_exceeded" in error_str or
                    "tokens per day" in error_str or
                    "Need more tokens" in error_str
                )
                
                if is_rate_limit:
                    if attempt < self.max_retries - 1:
                        print(f"🔄 API quota reached, rotating to next key...")
                        print(f"🔑 Current key before rotation: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
                        
                        # Update the API key and create completely new ChatGroq instance
                        rotate_api_key()
                        new_key = get_current_api_key()
                        print(f"🔑 New key after rotation: {new_key[:8]}...{new_key[-4:]}")
                        
                        # IMPORTANT: Create completely new ChatGroq instance
                        self.chat_groq = self._create_new_chat_groq(new_key)
                        print(f"🆕 Created new ChatGroq instance with fresh key")
                        
                        time.sleep(3)  # Brief pause before retry
                        continue
                    else:
                        print("❌ All API keys have reached their limits.")
                        raise Exception("All API keys have reached their limits. Please try again later.")
                else:
                    # Other errors, don't retry with key rotation
                    print(f"❌ Non-rate-limit error: {error_str}")
                    raise Exception(f"Groq API error: {error_str}")
        
        raise Exception("Failed after all retry attempts.")


def create_groq_client(model_name: str = "llama-3.3-70b-versatile", 
                      temperature: float = 0.3, 
                      max_tokens: int = 400) -> GroqClientWithRetry:
    """
    Create a Groq client with retry logic.
    
    Args:
        model_name: Groq model name
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        
    Returns:
        GroqClientWithRetry instance that behaves like ChatGroq
    """
    chat_groq = ChatGroq(
        model_name=model_name,
        temperature=temperature,
        groq_api_key=get_current_api_key(),
        max_tokens=max_tokens
    )
    return GroqClientWithRetry(chat_groq)


def query_groq_with_retry(question: str, 
                         system_prompt: Optional[str] = None,
                         model_name: str = "llama-3.3-70b-versatile",
                         temperature: float = 0.3,
                         max_retries: int = 3) -> str:
    """
    Simple wrapper for single question queries.
    
    Args:
        question: The question to ask
        system_prompt: Optional system prompt
        model_name: Groq model name
        temperature: Sampling temperature
        max_retries: Maximum retry attempts
        
    Returns:
        Response as string
    """
    client = create_groq_client(model_name, temperature)
    client.max_retries = max_retries
    
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=question))
    
    response = client.invoke(messages)
    return response.content.strip()


# Legacy compatibility function
def get_groq_llm_with_retry(model_name: str = "llama-3.3-70b-versatile", 
                           temperature: float = 0.3) -> GroqClientWithRetry:
    """
    Legacy compatibility function.
    Returns a GroqClientWithRetry that can be used like the old get_groq_llm() function.
    """
    return create_groq_client(model_name, temperature)
