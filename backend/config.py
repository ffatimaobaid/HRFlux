import os

# Multiple Groq API keys for rotation
GROQ_API_KEYS = [
    "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", #shayane1296
    "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", #shayane947
    "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", #shayaneUni
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
    
    # Find the working key (The one we know is active)
    working_key = "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"
    
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

# --- GEMINI KEY ROTATION (MIRRORED LOGIC) ---
GEMINI_API_KEYS = [
    "AQ.Ab8RN6JPI9DskmmW9X7wDODvt3-qU9oEgcQbAEG_EFLqD0Vtog",
    "AIzaSyDOEdBEO1YBrEXnxnHzcpaKzFoE163cW0M",
    "AIzaSyDJgn14PJaB1zu0B2kedhhs8fX6cAlfHLc", # active
]
gemini_current_key_index = 0

def get_current_gemini_key():
    """Get the current Gemini API key"""
    return GEMINI_API_KEYS[gemini_current_key_index]

def rotate_gemini_key():
    """Rotate to the next Gemini API key"""
    global gemini_current_key_index
    gemini_current_key_index = (gemini_current_key_index + 1) % len(GEMINI_API_KEYS)
    print(f"🔄 Rotated to Gemini Key: {get_current_gemini_key()[:8]}...")
    return get_current_gemini_key()

def is_gemini_key_available(api_key):
    """Health check for Gemini key"""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
        llm.invoke("test")
        return True
    except Exception as e:
        msg = str(e).lower()
        if "rate" in msg or "quota" in msg:
            print(f"🚫 Gemini Key rate limited: {api_key[:8]}...")
            return False
        return True # Other error, but key might be ok

def set_working_gemini_key_first():
    """Prioritize the primary working Gemini key"""
    global gemini_current_key_index, GEMINI_API_KEYS
    working_key = "AQ.Ab8RN6JPI9DskmmW9X7wDODvt3-qU9oEgcQbAEG_EFLqD0Vtog"
    
    if working_key in GEMINI_API_KEYS:
        if working_key != GEMINI_API_KEYS[0]:
            GEMINI_API_KEYS.remove(working_key)
            GEMINI_API_KEYS.insert(0, working_key)
            gemini_current_key_index = 0
            print(f"✅ Working Gemini key moved to first position: {working_key[:8]}...")
    else:
        print("ℹ️ Working Gemini key already in first position or not found")

# Optional: Manual trigger for prioritization if needed
def prioritize_all_keys():
    try:
        test_and_set_working_key()
        set_working_gemini_key_first()
    except Exception as e:
        print(f"⚠️ Could not prioritize working keys: {e}")

# Legacy compatibility
GROQ_API_KEY = get_current_api_key()
# Gemini API Key (Fallback)
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_API_KEY = get_current_gemini_key()

# RAG debug / traceability: show top source files under answers when True
SHOW_SOURCES = True

# --- OLLAMA CLOUD CONFIGURATION ---
OLLAMA_API_KEY = "562e9779746d42349683337d650a683f.ioKlEqIee834Qi-13tEHQXEU"
OLLAMA_MODEL = "qwen3-vl:235b-cloud"
OLLAMA_BASE_URL = "https://ollama.com"