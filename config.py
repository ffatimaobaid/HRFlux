import os

# Multiple Groq API keys for rotation
GROQ_API_KEYS = [
    "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",
    "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", #shayane - WORKING KEY
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

def get_next_available_key():
    """Find the next available key that hasn't hit the limit"""
    global current_key_index
    
    # Try current key first
    current_key = get_current_api_key()
    if is_key_available(current_key):
        return current_key
    
    # Try all other keys
    for i in range(len(GROQ_API_KEYS)):
        key = GROQ_API_KEYS[i]
        if is_key_available(key):
            current_key_index = i
            return key
    
    # No available keys found
    return None

def is_key_available(api_key):
    """Check if a key is available (not rate limited)"""
    try:
        # Make a simple test call to check if key is working
        from chat_groq_with_retry import create_chat_groq_with_retry
        
        llm = create_chat_groq_with_retry(
            model_name="llama-3.3-70b-versible",
            temperature=0.2,
            api_key=api_key
        )
        
        # Simple test message
        test_response = llm.invoke("test")
        return True
    except Exception as e:
        # Check if it's a rate limit error
        error_msg = str(e).lower()
        rate_limit_indicators = [
            "rate limit", "limit exceeded", "quota exceeded", 
            "too many requests", "service tier", "upgrade"
        ]
        
        if any(indicator in error_msg for indicator in rate_limit_indicators):
            print(f"🚫 Key rate limited: {api_key[:20]}...")
            return False
        else:
            # Other error, but key might still work
            print(f"⚠️ Key test failed (not rate limit): {api_key[:20]}...")
            return True

def smart_rotate_on_rate_limit():
    """Smart rotation that tries all keys before failing"""
    global current_key_index
    
    original_index = current_key_index
    attempts = 0
    
    while attempts < len(GROQ_API_KEYS):
        current_key = get_current_api_key()
        
        if is_key_available(current_key):
            print(f"✅ Using available key: {current_key[:20]}...")
            return current_key
        
        # Try next key
        print(f"🔄 Key {current_key[:20]}... rate limited, trying next...")
        rotate_api_key()
        attempts += 1
    
    # All keys exhausted, reset to original
    current_key_index = original_index
    print("❌ All API keys are rate limited")
    return None

def set_working_key_first():
    """Set working key to first position for rotation priority"""
    global current_key_index, GROQ_API_KEYS
    
    # Find the working key (marked with WORKING KEY comment)
    working_key = None
    for i, key in enumerate(GROQ_API_KEYS):
        if "#shayane - WORKING KEY" in str(GROQ_API_KEYS[i]) or i == 1:  # Index 1 is the working key
            working_key = GROQ_API_KEYS[i]
            break
    
    if working_key and working_key != GROQ_API_KEYS[0]:
        # Remove working key from its current position
        GROQ_API_KEYS.remove(working_key)
        # Insert at first position
        GROQ_API_KEYS.insert(0, working_key)
        # Reset index to 0 since working key is now first
        current_key_index = 0
        print(f"✅ Working key moved to first position: {working_key[:20]}...")
    else:
        print("ℹ️ Working key already in first position or not found")

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