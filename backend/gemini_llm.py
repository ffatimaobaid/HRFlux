import os
from config import get_current_api_key, rotate_api_key
from langchain_core.messages import SystemMessage, HumanMessage
import json
import os
from embedder import model  # For embeddings
import numpy as np
import time
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

def query_gemini_with_retry(context_chunks, question, model_name="gemini-2.0-flash", chat_history=None, hr_knowledge=None, max_retries=5):
    """
    Query Gemini/Google LLM with retry logic and error handling.
    """
    # System prompt remains same
    system_prompt = f"""
    You are HRFLUX AI assistant. 
    Context: {context_chunks}
    HR Knowledge: {hr_knowledge}
    """
    
    for attempt in range(max_retries):
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.3,
                google_api_key=os.getenv("GOOGLE_API_KEY") or get_current_api_key(),
                max_tokens=500
            )
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=question)
            ]
            
            response = llm.invoke(messages)
            if response and hasattr(response, 'content'):
                return response.content.strip(), True
            else:
                return "Gemini AI returned an empty response. Let's try once more.", False

        except Exception as e:
            error_str = str(e)
            print(f"Gemini Attempt {attempt + 1}/{max_retries} failed: {error_str}")
            
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                return f"Gemini Error: {error_str}", False

def query_gemini(context_chunks, question, model_name="gemini-2.5-flash", chat_history=None, hr_knowledge=None):
    """Wrapper for backward compatibility"""
    # Force use of config key if env is missing
    from config import GEMINI_API_KEY
    if not os.getenv("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
        
    response, success = query_gemini_with_retry(context_chunks, question, model_name, chat_history, hr_knowledge)
    return response
