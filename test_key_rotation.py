"""
Test script to verify Groq API key rotation works correctly.
"""

import os
from groq_client import create_groq_client, query_groq_with_retry
from config import GROQ_API_KEYS, get_current_api_key, rotate_api_key, reset_key_rotation

def test_key_rotation():
    """Test that API key rotation works correctly."""
    print("🧪 Testing Groq API Key Rotation...")
    print("=" * 50)
    
    # Show current keys (masked for security)
    print(f"📋 Total API keys configured: {len(GROQ_API_KEYS)}")
    for i, key in enumerate(GROQ_API_KEYS):
        masked_key = key[:8] + "..." + key[-4:]
        print(f"   Key {i+1}: {masked_key}")
    
    print(f"\n🔑 Current key index: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
    
    # Test a simple query
    print("\n🤖 Testing simple query...")
    try:
        response = query_groq_with_retry(
            "What is 2+2? Just give the number.",
            temperature=0.1,
            max_retries=2
        )
        print(f"✅ Response: {response}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🔄 Testing key rotation...")
    original_key = get_current_api_key()
    rotate_api_key()
    new_key = get_current_api_key()
    
    print(f"🔑 Before rotation: {original_key[:8]}...{original_key[-4:]}")
    print(f"🔑 After rotation:  {new_key[:8]}...{new_key[-4:]}")
    
    if original_key != new_key:
        print("✅ Key rotation working correctly!")
    else:
        print("❌ Key rotation failed!")
    
    # Test another query with rotated key
    print("\n🤖 Testing query with rotated key...")
    try:
        response = query_groq_with_retry(
            "What is 3+3? Just give the number.",
            temperature=0.1,
            max_retries=2
        )
        print(f"✅ Response: {response}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Reset rotation
    reset_key_rotation()
    print(f"\n🔄 Reset to first key: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
    
    print("\n" + "=" * 50)
    print("🎉 Key rotation test complete!")

if __name__ == "__main__":
    test_key_rotation()
