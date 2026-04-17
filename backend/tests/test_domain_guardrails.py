"""
Test the domain guardrails implementation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import run_agent, validate_hr_query

def test_domain_guardrails():
    """Test the new domain guardrails."""
    print("🔍 Testing Domain Guardrails")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        ("hi", "Should work - simple greeting"),
        ("hello", "Should work - simple greeting"),
        ("who owns tesla", "Should be blocked - Tesla question"),
        ("what is the capital of france", "Should be blocked - general knowledge"),
        ("elon musk", "Should be blocked - celebrity topic"),
        ("tell me about spacex", "Should be blocked - other company"),
        ("what's our leave policy", "Should work - HR question"),
        ("how do i apply for leave", "Should work - HR question"),
    ]
    
    for query, expected_result in test_cases:
        print(f"\n🧪 Testing: '{query}'")
        print(f"📋 Expected: {expected_result}")
        
        try:
            result = run_agent("test_user", query)
            response = result.get("answer", "")
            
            if expected_result == "Should be blocked":
                if "outside my HR domain" in response.lower():
                    print("✅ BLOCKED - Correctly rejected")
                else:
                    print("❌ FAILED - Should have been blocked")
            elif expected_result == "Should work":
                if "hello" in response.lower() or "hi" in response.lower():
                    print("✅ ALLOWED - Correctly responded")
                else:
                    print("❌ FAILED - Wrong response")
            
            print(f"📝 Response: {response[:100]}...")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print("-" * 30)

if __name__ == "__main__":
    test_domain_guardrails()
