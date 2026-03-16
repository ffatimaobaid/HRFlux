from langchain_groq import ChatGroq
from config import get_current_api_key, rotate_api_key
from langchain_core.messages import SystemMessage, HumanMessage
import json
from embedder import model  # For embeddings
import numpy as np
import time

# List of FAQ/reference questions for suggestions
FAQ_QUESTIONS = [
    "What is the leave policy?",
    "What are the office timings?",
    "How do I apply for leave?",
    "What is the dress code?",
    "Can I work remotely?",
    "What is the policy on freelancing?",
    "What is the process for reporting tardiness?",
    "Can I accept gifts from clients?",
    "What is the sick leave policy?",
    "How do I report a rule violation?",
    "How do I submit documents to HR?",
    "What is the salary advance process?",
    "When will I get my payslip?",
    "What is the performance review process?",
    "How do I request reimbursement?",
    "What is the resignation process?",
    "What are the working hours?",
    "How do I check my leave balance?",
    "What benefits am I eligible for?",
    "How do I report a safety issue?",
]

def get_similar_questions(user_query, faq_questions=FAQ_QUESTIONS, top_n=3):
    query_emb = model.encode([user_query])
    faq_embs = model.encode(faq_questions)

    print(f"User query embedding shape: {query_emb.shape}")
    print(f"FAQ embeddings shape: {faq_embs.shape}")

    query_norm = np.linalg.norm(query_emb[0])
    faq_norms = np.linalg.norm(faq_embs, axis=1)

    print(f"User query norm: {query_norm}")
    print(f"FAQ norms: {faq_norms}")

    epsilon = 1e-10
    sims = np.dot(faq_embs, query_emb[0]) / (faq_norms * query_norm + epsilon)
    print(f"Similarity scores: {sims}")

    top_indices = np.argsort(sims)[::-1][:top_n]
    print(f"Top indices: {top_indices}")

    return [faq_questions[i] for i in top_indices]


def query_gemini_with_retry(context_chunks, question, model_name="llama-3.3-70b-versatile", chat_history=None, hr_knowledge=None, max_retries=5):
    """Query Groq with automatic key rotation on quota limits"""
    
    # Build history string
    if chat_history:
        formatted = [
            f"User: {q}\nAssistant: {a}"
            for q, a in chat_history[-5:]
            if q.strip() and a.strip()
        ]
        history_str = "\n".join(formatted) if formatted else "No prior exchanges available."
    else:
        history_str = "No prior exchanges available."

    # Build context text
    context_text = "\n\n".join(context_chunks) if context_chunks else "No specific document content available."
    
    # Add HR knowledge if provided
    hr_knowledge_text = ""
    if hr_knowledge:
        hr_knowledge_text = f"\n\nGeneral HR Knowledge:\n{hr_knowledge}"

    system_prompt = f"""
You are a professional, helpful HR assistant with comprehensive knowledge of HR policies and procedures.

Responsibilities:
- Answer HR-related questions using uploaded documents first, then your general HR knowledge
- Provide practical, actionable guidance for common HR procedures
- If documents don't contain the answer, use your HR expertise to help with HR-related queries
- Maintain conversation context and reference previous interactions when relevant
- No emojis, maintain professional tone
- If completely unrelated to HR: "I'm here to help with HR-related questions only."
- Office timings must include Mon–Thu & Friday details when relevant

Guidelines for unseen queries:
- For procedural questions (how to apply, submit, request): Provide step-by-step guidance
- For policy questions: Explain standard HR practices and procedures
- For specific company details: If not in documents, provide general HR guidelines
- Always consider conversation history for context and follow-ups

---

Conversation History:
{history_str}

---

HR Policy Document (Uploaded):
{context_text}
{hr_knowledge_text}
"""
    
    for attempt in range(max_retries):
        try:
            # Create fresh ChatGroq instance for each attempt with current API key
            llm = ChatGroq(
                temperature=0.3, 
                model_name=model_name,
                groq_api_key=get_current_api_key(),
                max_tokens=400
            )
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=question)
            ]
            response = llm.invoke(messages)
            return response.content.strip(), True  # Success
            
        except Exception as e:
            error_str = str(e)
            print(f"Attempt {attempt + 1}/{max_retries}: {error_str}")
            
            # Check if it's a quota/rate limit error - updated detection
            is_rate_limit = (
                "429" in error_str or 
                "quota" in error_str.lower() or 
                "rate limit" in error_str.lower() or
                "rate_limit_exceeded" in error_str or
                "tokens per day" in error_str or
                "Need more tokens" in error_str
            )
            
            if is_rate_limit:
                if attempt < max_retries - 1:
                    print(f"🔄 API quota reached, rotating to next key...")
                    print(f"🔑 Current key before rotation: {get_current_api_key()[:8]}...{get_current_api_key()[-4:]}")
                    
                    rotate_api_key()
                    new_key = get_current_api_key()
                    print(f"🔑 New key after rotation: {new_key[:8]}...{new_key[-4:]}")
                    print(f"🆕 Will create fresh ChatGroq instance with new key")
                    
                    time.sleep(3)  # Brief pause before retry
                    continue
                else:
                    print("❌ All API keys have reached their limits.")
                    return "All API keys have reached their limits. Please try again later.", False
            else:
                # Other errors, don't retry with key rotation
                print(f"❌ Non-rate-limit error: {error_str}")
                return f"An unexpected error occurred: {error_str}", False
    
    return "Failed after all retry attempts.", False


def query_gemini(context_chunks, question, model_name="llama-3.3-70b-versatile", chat_history=None, hr_knowledge=None):
    """Wrapper for backward compatibility"""
    response, success = query_gemini_with_retry(context_chunks, question, model_name, chat_history, hr_knowledge)
    return response
