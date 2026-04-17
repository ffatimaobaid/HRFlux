"""
Quick test to verify Groq key rotation is working with the new error detection.
"""

from groq_client import create_groq_client
from config import GROQ_API_KEYS, get_current_api_key, rotate_api_key, reset_key_rotation
from langchain_core.messages import HumanMessage

def test_enhanced_key_rotation():
    """Test the enhanced key rotation with better error detection."""
    print("🧪 Testing Enhanced Groq Key Rotation...")
    print("=" * 60)
    
    # Show all keys
    print(f"📋 Total API keys: {len(GROQ_API_KEYS)}")
    for i, key in enumerate(GROQ_API_KEYS):
        masked = key[:8] + "..." + key[-4:]
        print(f"   Key {i+1}: {masked}")
    
    print(f"\n🔑 Starting with key: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
    
    # Test with a simple query
    client = create_groq_client(temperature=0.1)
    
    try:
        print("\n🤖 Testing query...")
        messages = [HumanMessage(content="What is 2+2? Just give the number.")]
        response = client.invoke(messages)
        print(f"✅ Response: {response.content}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test manual rotation
    print("\n🔄 Testing manual rotation...")
    original_key = get_current_api_key()
    rotate_api_key()
    new_key = get_current_api_key()
    
    print(f"🔑 Before: {original_key[:8]}...{original_key[-4:]}")
    print(f"🔑 After:  {new_key[:8]}...{new_key[-4:]}")
    
    if original_key != new_key:
        print("✅ Manual rotation works!")
    else:
        print("❌ Manual rotation failed!")
    
    # Test with rotated key
    try:
        print("\n🤖 Testing query with rotated key...")
        messages = [HumanMessage(content="What is 3+3? Just give the number.")]
        response = client.invoke(messages)
        print(f"✅ Response: {response.content}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Reset
    reset_key_rotation()
    print(f"\n🔄 Reset to: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
    
    print("\n" + "=" * 60)
    print("🎉 Enhanced key rotation test complete!")
    print("\n💡 If you see rate limit errors, the rotation should now work!")
    print("   Watch for the 🔄 and 🔑 symbols in the output.")

if __name__ == "__main__":
    test_enhanced_key_rotation()
