import sys
import os
import json
import urllib.request
import urllib.error
import ssl

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ollama_direct():
    print("🔍 Verifying Ollama Key and Connection...")
    print("=" * 50)
    
    try:
        from config import OLLAMA_API_KEY, OLLAMA_MODEL, OLLAMA_BASE_URL
    except ImportError:
        print("❌ Error: Could not import configuration from config.py")
        return

    # Normalize base URL
    base = OLLAMA_BASE_URL.rstrip('/')
    print(f"📍 Endpoint: {base}")
    print(f"🤖 Model:    {OLLAMA_MODEL}")
    
    if OLLAMA_API_KEY:
        masked_key = f"{OLLAMA_API_KEY[:8]}...{OLLAMA_API_KEY[-4:]}"
        print(f"🔑 Key:      {masked_key}")
    else:
        print("🔑 Key:      MISSING")

    # Disable SSL verification for testing if needed (common in some corporate environments)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json"
    }

    # Test 1: OpenAI-compatible endpoint
    openai_url = f"{base}/v1/chat/completions"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": "Respond with the word 'SUCCESS' if you hear me."}],
        "temperature": 0.1,
        "stream": False
    }

    print(f"\n📡 [Test 1] Attempting OpenAI-compatible endpoint: {openai_url}")
    try:
        req = urllib.request.Request(openai_url, data=json.dumps(payload).encode(), headers=headers, method='POST')
        with urllib.request.urlopen(req, context=ctx, timeout=180) as response:
            status = response.getcode()
            body = response.read().decode()
            print(f"✅ Status Code: {status}")
            result = json.loads(body)
            if "choices" in result:
                answer = result['choices'][0]['message']['content'].strip()
                print(f"💬 Answer: {answer}")
                if "SUCCESS" in answer.upper():
                    print("✨ TEST 1 RESULT: SUCCESS")
                return
    except urllib.error.HTTPError as e:
        print(f"⚠️ Test 1 failed with HTTP Error {e.code}: {e.reason}")
        if e.code == 404:
            print("   👉 This is normal if the provider doesn't support the OpenAI endpoint.")
        elif e.code == 401:
            print("   👉 Unauthorized: Check your OLLAMA_API_KEY.")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")

    # Test 2: Native Ollama endpoint
    native_payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": "Respond with the word 'SUCCESS' if you hear me."}],
        "stream": False,
        "options": {"temperature": 0.1}
    }
    native_url = f"{base}/api/chat"
    print(f"\n📡 [Test 2] Attempting Native Ollama endpoint: {native_url}")
    try:
        req = urllib.request.Request(native_url, data=json.dumps(native_payload).encode(), headers=headers, method='POST')
        with urllib.request.urlopen(req, context=ctx, timeout=180) as response:
            status = response.getcode()
            body = response.read().decode()
            print(f"✅ Status Code: {status}")
            result = json.loads(body)
            if "message" in result:
                answer = result['message']['content'].strip()
                print(f"💬 Answer: {answer}")
                if "SUCCESS" in answer.upper():
                    print("✨ TEST 2 RESULT: SUCCESS")
                return
            else:
                print(f"❓ Unexpected format: {result}")
    except urllib.error.HTTPError as e:
        print(f"❌ Test 2 failed with HTTP Error {e.code}: {e.reason}")
        if e.code == 401:
            print("   👉 Unauthorized: Check your OLLAMA_API_KEY.")
        error_body = e.read().decode()
        print(f"   📄 Error Content: {error_body}")
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")

    print("\n总结 (Summary):")
    print("❌ Failed to establish connection to Ollama API.")
    print("1. Please check if OLLAMA_BASE_URL is correct (e.g., https://your-provider.com).")
    print("2. Verify that OLLAMA_MODEL exists on the provider.")
    print("3. Ensure OLLAMA_API_KEY is valid.")

if __name__ == "__main__":
    test_ollama_direct()
