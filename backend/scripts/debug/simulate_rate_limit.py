"""
Test to see if key rotation is actually being triggered during rate limit errors.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import GROQ_API_KEYS, get_current_api_key, rotate_api_key, reset_key_rotation

def simulate_rate_limit_scenario():
    """Simulate what happens when a rate limit occurs."""
    print("🚨 Simulating Rate Limit Scenario")
    print("=" * 50)
    
    # Start with first key
    reset_key_rotation()
    original_key = get_current_api_key()
    print(f"🔑 Starting with: {original_key[:8]}...{original_key[-4:]}")
    
    # Simulate the error detection logic
    error_message = "I'm sorry, I encountered an internal error. Please try again later. (Error code: 429 - {'error': {'message': 'Rate limit reached for model llama-3.3-70b-versatile in organization org_01k7vddsgdfwxt45cq24skxkbn service tier on_demand on tokens per day (TPD): Limit 100000, Used 98003, Requested 2863. Please try again in 12m28.223999999s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}})"
    
    print(f"\n🔍 Testing error detection...")
    print(f"Error message: {error_message[:100]}...")
    
    # Check if our error detection would catch this
    is_rate_limit = (
        "429" in error_message or 
        "quota" in error_message.lower() or 
        "rate limit" in error_message.lower() or 
        "limit" in error_message.lower() or
        "rate_limit_exceeded" in error_message or
        "tokens per day" in error_message or
        "Need more tokens" in error_message
    )
    
    print(f"🎯 Rate limit detected: {is_rate_limit}")
    
    if is_rate_limit:
        print(f"\n🔄 Simulating key rotation...")
        
        # Simulate multiple attempts
        for attempt in range(3):
            print(f"\n--- Attempt {attempt + 1} ---")
            current_key = get_current_api_key()
            print(f"Current key: {current_key[:8]}...{current_key[-4:]}")
            
            if attempt < 2:  # Simulate rotation for first 2 attempts
                print("🔄 Rotating to next key...")
                rotate_api_key()
                new_key = get_current_api_key()
                print(f"New key: {new_key[:8]}...{new_key[-4:]}")
                
                if current_key == new_key:
                    print("❌ ERROR: Rotation failed - same key!")
                else:
                    print("✅ Rotation successful")
            else:
                print("❌ All keys exhausted")
    
    print(f"\n🎯 Final key: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
    
    # Test the actual rotation function
    print(f"\n🔧 Testing rotate_api_key() function...")
    reset_key_rotation()
    
    for i in range(len(GROQ_API_KEYS)):
        key = get_current_api_key()
        print(f"Rotation {i+1}: {key[:8]}...{key[-4:]}")
        rotate_api_key()

if __name__ == "__main__":
    simulate_rate_limit_scenario()
