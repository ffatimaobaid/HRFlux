"""
Debug test to see what's happening with the "hi" input.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import run_agent

def test_hi_input():
    """Test what happens when we send 'hi' as input."""
    print("🔍 Testing 'hi' input to agent")
    print("=" * 50)
    
    # Test with different users to see if username extraction is the issue
    test_users = ["admin", "tom.dev", "john.doe", "unknown"]
    
    for user in test_users:
        print(f"\n👤 Testing with user: {user}")
        print("-" * 30)
        
        try:
            result = run_agent(user, "hi")
            print(f"✅ Agent response: {result}")
            
            # Check if response contains meeting scheduling
            response_str = str(result)
            if "scheduling a meeting" in response_str.lower():
                print("⚠️ MEETING SCHEDULING DETECTED!")
            elif "escalated" in response_str.lower():
                print("⚠️ ESCALATION DETECTED!")
            elif "leave" in response_str.lower():
                print("⚠️ LEAVE REQUEST DETECTED!")
            else:
                print("✅ NORMAL RESPONSE")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 30)

if __name__ == "__main__":
    test_hi_input()
