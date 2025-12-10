import os

# Multiple Gemini API keys for rotation
GEMINI_API_KEYS = [
    "AIzaSyCOJcyvJAQcK8a5VjVLENxzeTUwJMmsisc",
    "AIzaSyAcPIaR02vF_zApBYPm_z8yi7gH6VD0IUI",
    "AIzaSyA0_lc-IaJSGBv_CjfcnYGd9SksNkvAERg"
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