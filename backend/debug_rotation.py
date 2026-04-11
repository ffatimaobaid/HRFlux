"""
Test the key rotation logic to see if it's working properly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import GROQ_API_KEYS, get_current_api_key, rotate_api_key, reset_key_rotation

def test_rotation_debug():
    """Debug the key rotation to see what's happening."""
    print("🔍 Key Rotation Debug Test")
    print("=" * 40)
    
    print(f"📋 Total keys: {len(GROQ_API_KEYS)}")
    for i, key in enumerate(GROQ_API_KEYS):
        masked = key[:8] + "..." + key[-4:]
        print(f"   Key {i+1}: {masked}")
    
    # Reset to start
    reset_key_rotation()
    print(f"\n🔄 Reset to: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
    
    # Test manual rotation
    print(f"\n🔄 Testing manual rotation...")
    for i in range(6):  # Rotate through twice
        current = get_current_api_key()
        print(f"Before rotation {i+1}: {current[:8]}...{current[-4:]} (index: {GROQ_API_KEYS.index(current)})")
        
        rotate_api_key()
        new_key = get_current_api_key()
        print(f"After rotation {i+1}:  {new_key[:8]}...{new_key[-4:]} (index: {GROQ_API_KEYS.index(new_key)})")
        
        if current == new_key:
            print("❌ ERROR: Same key after rotation!")
        else:
            print("✅ Key rotated successfully")
        print()
    
    # Test the actual rotation logic
    print("🔧 Testing rotation logic...")
    reset_key_rotation()
    
    for i in range(len(GROQ_API_KEYS)):
        key = get_current_api_key()
        index = GROQ_API_KEYS.index(key)
        print(f"Step {i+1}: Key {index+1} - {key[:8]}...{key[-4:]}")
        rotate_api_key()
    
    print(f"\n🎯 Final state: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")

if __name__ == "__main__":
    test_rotation_debug()
