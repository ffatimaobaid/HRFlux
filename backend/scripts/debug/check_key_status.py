"""
Check which Groq API key is currently being used.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import GROQ_API_KEYS, get_current_api_key, rotate_api_key, reset_key_rotation
    
    print("🔍 Current Groq API Key Status")
    print("=" * 40)
    
    print(f"📋 Total API keys: {len(GROQ_API_KEYS)}")
    
    for i, key in enumerate(GROQ_API_KEYS):
        masked = key[:8] + "..." + key[-4:]
        print(f"   Key {i+1}: {masked}")
    
    current_key = get_current_api_key()
    print(f"\n🔑 Currently using: {current_key[:8]}...{current_key[-4:]}")
    
    # Find which key index this is
    try:
        key_index = GROQ_API_KEYS.index(current_key)
        print(f"📍 Key index: {key_index + 1} of {len(GROQ_API_KEYS)}")
    except ValueError:
        print("❌ Current key not found in the list!")
    
    # Test rotation to see if it works
    print(f"\n🔄 Testing rotation...")
    original_key = current_key
    
    for i in range(3):
        rotate_api_key()
        new_key = get_current_api_key()
        print(f"   Rotation {i+1}: {new_key[:8]}...{new_key[-4:]}")
        
        if new_key == original_key:
            print("⚠️ Same key appearing in rotation - might be an issue")
    
    # Reset
    reset_key_rotation()
    print(f"\n🔄 Reset to: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n💡 If all keys show rate limits immediately, it might be:")
print("   1. All keys genuinely hit their daily limits")
print("   2. The rotation isn't working properly")
print("   3. There's a caching issue")
