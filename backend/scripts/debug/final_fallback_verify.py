import sys
import os
import json

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Simple Mock for LangChain messages since they might not be in the root environment
class MockMessage:
    def __init__(self, content, m_type):
        self.content = content
        self.type = m_type

def test_final_logic():
    try:
        from gemini_llm import query_ollama
        print("🚀 Final Verification: Testing query_ollama with Mock LangChain Objects...")
        
        # Simulating the messages passed from query_gemini_with_retry
        messages = [
            MockMessage("You are a helpful HR assistant.", "system"),
            MockMessage("Hi, please answer with 'CONFIRMED' if you receive this.", "human")
        ]
        
        print(f"Format check: {[m.type for m in messages]}")
        response = query_ollama(messages)
        
        print("-" * 30)
        print(f"RESPONSE: {response}")
        print("-" * 30)
        
        if response:
            print("✅ VERIFIED: The function correctly handles mock LangChain objects and gets a response.")
        else:
            print("❌ FAILED: Received empty response.")
            
    except Exception as e:
        print(f"❌ ERROR DURING FINAL VERIFICATION: {e}")

if __name__ == "__main__":
    test_final_logic()
