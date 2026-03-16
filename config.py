import os

# Multiple Groq API keys for rotation
GROQ_API_KEYS = [
    "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", #shayane - WORKING KEY
    "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", # EXHAUSTED
    "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", # EXHAUSTED
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

def set_working_key_first():
    """Set working key to first position for rotation priority"""
    global current_key_index, GROQ_API_KEYS
    working_key = "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"
    
    # Move working key to first position
    if working_key in GROQ_API_KEYS:
        GROQ_API_KEYS.remove(working_key)
        GROQ_API_KEYS.insert(0, working_key)
        current_key_index = 0
        print(f"✅ Moved working key to first position: {working_key[:8]}...{working_key[-4:]}")
    else:
        print("❌ Working key not found in list")

# Prioritize working key when module loads
try:
    set_working_key_first()
except Exception as e:
    print(f"⚠️ Could not prioritize working key: {e}")

# Legacy compatibility
GROQ_API_KEY = get_current_api_key()
#3rd API AIzaSyCZvWDk9ydZNBeSRasZrpcE6Q8kJ2Zrmdk

# RAG debug / traceability: show top source files under answers when True
SHOW_SOURCES = True