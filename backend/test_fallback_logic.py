import sys
import os
from langchain_core.messages import HumanMessage

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from gemini_llm import query_ollama
    print("Testing query_ollama from gemini_llm.py...")
    
    messages = [HumanMessage(content="Hi, respond with SUCCESS.")]
    response = query_ollama(messages)
    print(f"Response: {response}")
    if "SUCCESS" in response.upper():
        print("✅ query_ollama is working correctly!")
    else:
        print("⚠️ query_ollama returned an unexpected response.")
except Exception as e:
    print(f"❌ query_ollama failed: {e}")
