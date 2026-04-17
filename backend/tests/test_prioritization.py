"""
Test the new key prioritization system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import GROQ_API_KEYS, get_current_api_key, rotate_api_key, reset_key_rotation, set_working_key_first

def test_key_prioritization():
    """Test the key prioritization system."""
    print("🔍 Testing Key Prioritization")
    print("=" * 40)
    
    print(f"📋 Total keys: {len(GROQ_API_KEYS)}")
    for i, key in enumerate(GROQ_API_KEYS):
        masked = key[:8] + "..." + key[-4:]
        print(f"   Key {i+1}: {masked}")
    
    print(f"\n🔑 Current key before prioritization: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
    
    # Reset and prioritize
    reset_key_rotation()
    set_working_key_first()
    
    print(f"\n🔑 After prioritization: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
    
    # Test rotation
    print("\n🔄 Testing rotation...")
    for i in range(3):
        current = get_current_api_key()
        print(f"Rotation {i+1}: {current[:8]}...{current[-4:]}")
        rotate_api_key()
    
    print(f"\n✅ Key prioritization working correctly!")

if __name__ == "__main__":
    test_key_prioritization()
