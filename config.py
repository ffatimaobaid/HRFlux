import os

# Multiple Gemini API keys for rotation
GEMINI_API_KEYS = [
    "AIzaSyCZvWDk9ydZNBeSRasZrpcE6Q8kJ2Zrmdk",
    "AIzaSyDQDG3BnXlzBkCv6yQ54y8skC3UgMR9LmM",
    "AIzaSyAg5CkvHJZJxXpjkYPueG2xO-5PZdypcF8"
]

# Current key index for rotation
current_key_index = 0

def get_current_api_key():
    """Get the current API key"""
    return GEMINI_API_KEYS[current_key_index]

def rotate_api_key():
    """Rotate to the next API key"""
    global current_key_index
    current_key_index = (current_key_index + 1) % len(GEMINI_API_KEYS)
    return GEMINI_API_KEYS[current_key_index]

def reset_key_rotation():
    """Reset to first API key"""
    global current_key_index
    current_key_index = 0

# Legacy compatibility
GEMINI_API_KEY = get_current_api_key()
#3rd API AIzaSyCZvWDk9ydZNBeSRasZrpcE6Q8kJ2Zrmdk

# RAG debug / traceability: show top source files under answers when True
SHOW_SOURCES = True