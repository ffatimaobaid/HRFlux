import os
from config import get_current_gemini_key, rotate_gemini_key
from langchain_core.messages import SystemMessage, HumanMessage
import json
import os
from embedder import model  # For embeddings
import numpy as np
import time
# import requests (No longer needed, using urllib for robustness)
from langchain_google_genai import ChatGoogleGenerativeAI

# FAQ Questions for suggestions
FAQ_QUESTIONS = [
    "What are the office timings?",
    "How do I apply for leave?",
    "What is the dress code?",
    "What is the company's dress code policy?",
    "How do I apply for casual leave?",
    "What is the workflow for leave approval?",
    "How does the HR escalation system work?",
    "What are the different types of leaves available?",
    "Who is my manager?",
    "What is my current leave balance?",
    "How do I report a grievance?",
    "What document templates are available?",
    "Is health insurance covered by the company?"
]

# Global cache for embeddings
CACHED_FAQ_EMBEDDINGS = None

def get_similar_questions(user_query, faq_questions=FAQ_QUESTIONS, top_n=3):
    """
    Find most similar FAQ questions using cosine similarity.
    Lazy-loads embeddings on first use.
    """
    global CACHED_FAQ_EMBEDDINGS
    
    if not model:
        return faq_questions[:top_n]
        
    try:
        # Lazy initialization
        if CACHED_FAQ_EMBEDDINGS is None:
            print("📊 Initializing FAQ knowledge base (this happens once)...")
            CACHED_FAQ_EMBEDDINGS = model.encode(faq_questions)
            
        query_emb = model.encode([user_query])
        similarities = np.dot(CACHED_FAQ_EMBEDDINGS, query_emb.T).flatten()
        top_indices = np.argsort(similarities)[-top_n:][::-1]
        return [faq_questions[i] for i in top_indices]
    except Exception as e:
        print(f"Warning in suggestion engine: {e}")
        return faq_questions[:top_n]

def query_ollama(messages):
    """
    Directly query Ollama API via urllib (OpenAI-compatible / Native).
    Used as a tertiary fallback. Robustly handles SSL and environment issues.
    """
    import urllib.request
    import urllib.error
    import ssl
    import json
    from config import OLLAMA_API_KEY, OLLAMA_MODEL, OLLAMA_BASE_URL

    print(f"🤖 Attempting query via Ollama ({OLLAMA_MODEL})...")
    
    # Disable SSL verification for maximum compatibility with local/tunneled Ollama instances
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Map LangChain message types to OpenAI format
    formatted_messages = []
    for m in messages:
        role = "user"
        if hasattr(m, "type"):
            role = "system" if m.type == "system" else "assistant" if m.type == "ai" else "user"
        formatted_messages.append({"role": role, "content": m.content})
    
    # Normalize the base URL
    base = OLLAMA_BASE_URL.rstrip('/')
    if base.endswith('/api'):
        base = base[:-4].rstrip('/')

    # --- TRY OPENAI-COMPATIBLE ENDPOINT FIRST ---
    openai_url = f"{base}/v1/chat/completions"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": formatted_messages,
        "temperature": 0.3,
        "stream": False
    }

    try:
        print(f"📡 HRFLUX Fallback: Sending query to Ollama OpenAI endpoint ({openai_url})...")
        req = urllib.request.Request(openai_url, data=json.dumps(payload).encode(), headers=headers, method='POST')
        with urllib.request.urlopen(req, context=ctx, timeout=180) as response:
            result = json.loads(response.read().decode())
            if "choices" in result:
                return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ Ollama OpenAI endpoint failed: {e}. Trying native endpoint...")

    # --- TRY NATIVE OLLAMA ENDPOINT AS SECONDARY ---
    native_url = f"{base}/api/chat"
    native_payload = {
        "model": OLLAMA_MODEL,
        "messages": formatted_messages,
        "stream": False,
        "options": {"temperature": 0.3}
    }

    try:
        print(f"🔄 Trying native Ollama endpoint ({native_url})...")
        req = urllib.request.Request(native_url, data=json.dumps(native_payload).encode(), headers=headers, method='POST')
        with urllib.request.urlopen(req, context=ctx, timeout=180) as response:
            result = json.loads(response.read().decode())
            if "message" in result:
                return result["message"]["content"].strip()
            else:
                raise Exception(f"Unexpected native Ollama response format: {result}")
    except Exception as e:
        print(f"❌ All Ollama endpoints failed: {e}")
        raise e

def query_gemini_with_retry(context_chunks, question, model_name="gemini-2.0-flash", chat_history=None, hr_knowledge=None, max_retries=5):
    """
    Query LLM with Groq prioritization (key rotation built-in) and fallback to Gemini.
    """
    from prompts import SYSTEM_PROMPT
    system_prompt = f"""
    {SYSTEM_PROMPT}
    
    Current Database Context: 
    {context_chunks}
    
    HR Knowledge & Procedures: 
    {hr_knowledge}
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question)
    ]

    # --- ATTEMPT 1: GROQ (WITH KEY ROTATION) ---
    try:
        from chat_groq_with_retry import create_chat_groq_with_retry
        print("🤖 Attempting query via Groq (Primary)...")
        # Instantiate Groq with its built-in key rotation capability
        llm_groq = create_chat_groq_with_retry(
            model_name="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=500
        )
        response = llm_groq.invoke(messages)
        if response and hasattr(response, 'content'):
            return response.content.strip(), True
    except Exception as e:
        print(f"⚠️ Groq exhaustive rotation failed: {e}. Falling back to Gemini...")

    # --- ATTEMPT 2: GEMINI (FALLBACK) ---
    print(f"🤖 Falling back to Gemini ({model_name})...")
    for attempt in range(max_retries):
        try:
            llm_gemini = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.3,
                google_api_key=get_current_gemini_key(),
                max_tokens=500,
                max_retries=1 # Disable aggressive internal retries
            )
            response = llm_gemini.invoke(messages)
            if response and hasattr(response, 'content'):
                return response.content.strip(), True
            else:
                return "Gemini AI returned an empty response. Let's try once more.", False
        except Exception as e:
            error_str = str(e)
            print(f"Gemini Attempt {attempt + 1}/{max_retries} failed: {error_str}")
            
            # Check for Gemini specific rate limits
            if "429" in error_str or "quota" in error_str.lower() or "limit" in error_str.lower():
                if attempt < max_retries - 1:
                    print(f"🔄 Gemini quota hit, rotating key...")
                    rotate_gemini_key()
                    time.sleep(2)
                    continue
            
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                print(f"⚠️ Gemini exhausted. Final fallback to Ollama...")
                try:
                    ollama_response = query_ollama(messages)
                    return ollama_response, True
                except Exception as ollama_e:
                    return f"All LLMs (Groq, Gemini, Ollama) failed. Ollama error: {ollama_e}", False

class ChatGoogleGenerativeAIWithRotation(ChatGoogleGenerativeAI):
    """Subclass that always uses the current Gemini key from rotation."""
    def invoke(self, *args, **kwargs):
        from config import get_current_gemini_key
        self.google_api_key = get_current_gemini_key()
        # Ensure we don't do aggressive internal retries when quota is hit
        if hasattr(self, 'max_retries'):
            self.max_retries = 1
        return super().invoke(*args, **kwargs)

def query_gemini(context_chunks, question, model_name="gemini-2.0-flash", chat_history=None, hr_knowledge=None):
    """Wrapper for backward compatibility"""
    # Force use of config key if env is missing
    from config import GEMINI_API_KEY
    if not os.getenv("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
        
    response, success = query_gemini_with_retry(context_chunks, question, model_name, chat_history, hr_knowledge)
    return response
