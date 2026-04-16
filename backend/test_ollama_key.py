import sys
import os
import requests
import json

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ollama_direct():
    print("Verifying Ollama Key and Connection...")
    
    # We'll import these from config to ensure they are correctly set
    from config import OLLAMA_API_KEY, OLLAMA_MODEL
    OLLAMA_BASE_URL = "https://ollama.com/api"
    
    print(f"Endpoint: {OLLAMA_BASE_URL}")
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Key: {OLLAMA_API_KEY[:8]}...{OLLAMA_API_KEY[-4:]}")
    
    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": "Hi, are you working? Please respond with 'YES, OLLAMA IS WORKING' if you receive this."}],
        "temperature": 0.3
    }
    
    try:
        # Try OpenAI-compatible endpoint
        print(f"\nSending request to {OLLAMA_BASE_URL}/chat...")
        response = requests.post(
            f"{OLLAMA_BASE_URL}/chat",
            headers=headers,
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": "Hi, are you working?"}],
                "stream": False
            },
            timeout=30,
            verify=False
        )
            
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {response.headers}")
        
        try:
            result = response.json()
            print(f"Response received (JSON)!")
            if "choices" in result:
                print(f"Answer: {result['choices'][0]['message']['content'].strip()}")
            elif "message" in result:
                print(f"Answer: {result['message']['content'].strip()}")
            else:
                print(f"Unexpected format: {result}")
        except:
            print(f"Response was NOT JSON. First 500 chars:")
            print(response.text[:500])
            
    except Exception as e:
        print(f"Failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"📄 Response Content: {e.response.text}")

if __name__ == "__main__":
    test_ollama_direct()
