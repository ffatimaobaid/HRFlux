"""
Simple test to verify key rotation logic without API calls.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import GROQ_API_KEYS, get_current_api_key, rotate_api_key, reset_key_rotation

def test_key_rotation_logic():
    """Test the key rotation logic without API calls."""
    print("🧪 Key Rotation Logic Test")
    print("=" * 50)
    
    # Show all keys
    print(f"📋 Total API keys: {len(GROQ_API_KEYS)}")
    for i, key in enumerate(GROQ_API_KEYS):
        masked = key[:8] + "..." + key[-4:]
        print(f"   Key {i+1}: {masked}")
    
    # Test rotation
    print(f"\n🔄 Testing rotation...")
    original_key = get_current_api_key()
    print(f"Start: {original_key[:8]}...{original_key[-4:]}")
    
    # Rotate through all keys
    keys_seen = set()
    for i in range(len(GROQ_API_KEYS) * 2):  # Go through twice
        rotate_api_key()
        current_key = get_current_api_key()
        keys_seen.add(current_key)
        print(f"Rotation {i+1}: {current_key[:8]}...{current_key[-4:]}")
    
    print(f"\n📊 Results:")
    print(f"Unique keys seen: {len(keys_seen)}")
    print(f"Expected keys: {len(GROQ_API_KEYS)}")
    
    if len(keys_seen) == len(GROQ_API_KEYS):
        print("✅ Key rotation working correctly!")
    else:
        print("❌ Key rotation not working properly!")
    
    # Reset
    reset_key_rotation()
    print(f"\n🔄 Reset to: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
    
    return len(keys_seen) == len(GROQ_API_KEYS)

if __name__ == "__main__":
    success = test_key_rotation_logic()
    if success:
        print("\n✅ Key rotation logic is working!")
        print("💡 The issue might be in the API call retry logic.")
    else:
        print("\n❌ Key rotation logic has issues!")
