import google.generativeai as genai
from config import GEMINI_API_KEY
import json
from embedder import model  # For embeddings
import numpy as np

genai.configure(api_key=GEMINI_API_KEY)

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


def query_gemini(context_chunks, question, model_name="models/gemini-2.5-flash", chat_history=None):

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

    # FIX: join outside the f-string (no backslashes in f-string expressions)
    context_text = "\n\n".join(context_chunks)

    prompt = f"""
You are a professional, helpful HR assistant.

Responsibilities:
- Answer only HR policy-related questions using the document.
- No emojis, no fabricated information.
- If irrelevant → respond: "I'm here to help with HR policy-related questions only."
- If no info found → say: "Sorry, I couldn't find information related to that in the document."
- Office timings must include Mon–Thu & Friday.

---

Conversation History:
{history_str}

---

HR Policy Document:
{context_text}

---

User Question:
{question}

---

Answer (based strictly on the document):
"""

    try:
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.3, "max_output_tokens": 400}
        )
        return response.text.strip()

    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "quota" in error_str.lower():
            return (
                "The chatbot has reached the usage limit for this Gemini API key.\n\n"
                "Please wait a few minutes or use a different API key."
            )
        return f"An unexpected error occurred: {error_str}"


def classify_and_extract_leave(message: str, model_name="models/gemini-2.5-flash"):
    
    prompt = (
        "You are an HR assistant.\n\n"
        "Your task is to classify the following message and extract leave request details.\n\n"
        "If the message IS a leave request, respond ONLY with:\n"
        "{\n"
        '  "is_leave_request": true,\n'
        '  "leave_type": "<sick/casual/emergency/annual/...>",\n'
        '  "start_date": "<YYYY-MM-DD or natural date>",\n'
        '  "end_date": "<YYYY-MM-DD or natural date>",\n'
        '  "reason": "<brief reason>"\n'
        "}\n\n"
        "If it is NOT a leave request, respond ONLY with:\n"
        "{\n"
        '  "is_leave_request": false\n'
        "}\n\n"
        "Strictly output valid JSON only.\n\n"
        f"Message: \"{message}\""
    )

    try:
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(prompt)
        raw_output = response.text.strip()

        try:
            return json.loads(raw_output)
        except json.JSONDecodeError:
            return {"is_leave_request": False, "error": "Gemini returned invalid JSON."}

    except Exception as e:
        return {"is_leave_request": False, "error": str(e)}
