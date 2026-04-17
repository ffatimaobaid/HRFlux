"""
Check current Groq configuration and key setup.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import GROQ_API_KEYS, get_current_api_key, rotate_api_key, reset_key_rotation
    
    print("🔍 Groq Configuration Check")
    print("=" * 40)
    
    print(f"📋 Total API keys: {len(GROQ_API_KEYS)}")
    
    if len(GROQ_API_KEYS) == 0:
        print("❌ No API keys configured!")
    else:
        for i, key in enumerate(GROQ_API_KEYS):
            masked = key[:8] + "..." + key[-4:]
            print(f"   Key {i+1}: {masked}")
        
        print(f"\n🔑 Current key: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
        
        # Test rotation
        print("\n🔄 Testing rotation...")
        for i in range(3):
            rotate_api_key()
            current = get_current_api_key()
            print(f"   Rotation {i+1}: {current[:8]}...{current[-4:]}")
        
        reset_key_rotation()
        print(f"\n🔄 Reset to: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
        
        print("\n✅ Configuration looks good!")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n💡 If the configuration is good but you still see rate limits,")
print("   the issue might be:")
print("   1. All keys have reached their limits")
print("   2. The retry logic isn't triggering properly")
print("   3. The error detection isn't working")
