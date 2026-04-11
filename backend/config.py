import os

# Multiple Groq API keys for rotation
GROQ_API_KEYS = [
    "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",# shayane947
    "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",#famma new
    "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", #i220487
    "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", #shayane - WORKING KEY
    "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",
    "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",#famma
    "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",#hadiamazhar662 new
    "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",#shayane new
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
        from langchain_groq import ChatGroq
        
        llm = ChatGroq(
            model_name="llama-3.3-70b-versatile",
            temperature=0.2,
            groq_api_key=api_key,
            max_retries=0
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
            # Other error, key is completely broken/invalid
            print(f"⚠️ Key test failed (invalid/broken key): {api_key[:20]}...")
            return False

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

def test_and_set_working_key():
    """Dynamically test keys on startup and set the first working one."""
    global current_key_index, GROQ_API_KEYS
    
    print("🔄 Initializing system and verifying API keys...")
    
    # Check the first key first without rearranging if it works
    if is_key_available(GROQ_API_KEYS[0]):
        print(f"✅ Primary API key is active: {GROQ_API_KEYS[0][:20]}...")
        return

    # If the first fails, dynamically find one that works
    working_key = None
    for i in range(1, len(GROQ_API_KEYS)):
        key = GROQ_API_KEYS[i]
        if is_key_available(key):
            working_key = key
            break
            
    if working_key:
        GROQ_API_KEYS.remove(working_key)
        GROQ_API_KEYS.insert(0, working_key)
        current_key_index = 0
        print(f"✅ Found working key & shifted to priority: {working_key[:20]}...")
    else:
        print("❌ WARNING: No working API keys found during startup check!")

try:
    test_and_set_working_key()
except Exception as e:
    print(f"⚠️ Could not verify keys on startup: {e}")

# Legacy compatibility
GROQ_API_KEY = get_current_api_key()
# Gemini API Key (Fallback)
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY = "AIzaSyBiVFAKx9gM_wrYNdgDRzsMwGWNyykX9zE"

# RAG debug / traceability: show top source files under answers when True
SHOW_SOURCES = True