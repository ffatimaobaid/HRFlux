import os

# Multiple Groq API keys for rotation
GROQ_API_KEYS = [
    "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",
    "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"
]

# Current key index for rotation
current_key_index = 0

def get_current_api_key():
    """Get the current API key"""
    return GROQ_API_KEYS[current_key_index]

def rotate_api_key():
    """Rotate to the next API key"""
    global current_key_index
    current_key_index = (current_key_index + 1) % len(GROQ_API_KEYS)
    return GROQ_API_KEYS[current_key_index]

def reset_key_rotation():
    """Reset to first API key"""
    global current_key_index
    current_key_index = 0

# Legacy compatibility
GROQ_API_KEY = get_current_api_key()
#3rd API AIzaSyCZvWDk9ydZNBeSRasZrpcE6Q8kJ2Zrmdk

# RAG debug / traceability: show top source files under answers when True
SHOW_SOURCES = True