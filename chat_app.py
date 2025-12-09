import streamlit as st
from agent import run_agent
from db import init_db, save_chat_message, get_recent_history, cleanup_old_sessions, delete_user_history, init_user_table, signup_user, login_user
from context_cache import add_to_cache, get_recent_context
import json
import os
import datetime
import traceback
import re

HR_SYNONYMS = {
    "leave": ["vacation", "absence", "time off", "holiday"],
    "absent": ["not present", "missing", "away"],
    "policy": ["rule", "guideline", "regulation"],
    "salary": ["pay", "wage", "compensation"],
    "late": ["tardy", "delayed", "not on time"],
    "gift": ["present", "reward", "incentive"],
    # Add more as needed
}

def expand_query_with_synonyms(query):
    expanded = [query]
    for word, synonyms in HR_SYNONYMS.items():
        if re.search(rf"\b{word}\b", query, re.IGNORECASE):
            for syn in synonyms:
                # Replace the word with the synonym in the query
                expanded.append(re.sub(rf"\b{word}\b", syn, query, flags=re.IGNORECASE))
    return expanded

# Initialize DB and user table
init_db()
init_user_table()
cleanup_old_sessions(retention_hours=24)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Login or Signup")
    tab1, tab2 = st.tabs(["Login", "Signup"])

    with tab1:
        login_user_input = st.text_input("Username", key="login_user")
        login_pass_input = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            if login_user(login_user_input, login_pass_input):
                st.session_state.logged_in = True
                st.session_state.user = login_user_input
                st.success("Logged in!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab2:
        signup_user_input = st.text_input("New Username", key="signup_user")
        signup_pass_input = st.text_input("New Password", type="password", key="signup_pass")
        if st.button("Signup"):
            if signup_user(signup_user_input, signup_pass_input):
                st.success("Signup successful! Please login.")
            else:
                st.error("Username already exists.")
    st.stop()
else:
    user = st.session_state.user
    st.set_page_config(page_title="HR Chatbot", layout="centered")
    st.title("HR Assistant Chatbot")

    # Load selected model silently
    model = "models/gemini-1.5-flash"
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            try:
                config = json.load(f)
                model = config.get("model", model)
            except json.JSONDecodeError:
                pass

    # Clear chat button (UI + DB)
    if st.button("Clear Chat"):
        st.session_state.chat_history = []
        delete_user_history(user)  # ✅ Clear from DB
        st.rerun()

    # Load previous chat history from DB into session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = get_recent_history(user)

    # Input box for new user question
    # Check for a pending question from a suggestion button
    if "pending_question" in st.session_state:
        question = st.session_state.pop("pending_question")
    else:
        question = st.chat_input("Ask about HR policies...")
    if question:
        try:
            # Get recent context (24 hours) for chat continuity (not for retrieval)
            context = get_recent_context(user)

            # Generate answer and suggestions (let run_agent handle retrieval and query expansion)
            answer, suggestions = run_agent(user, question, model)
            print("Suggestions returned from run_agent:", suggestions)
        except Exception:
            traceback.print_exc()
            answer = "Sorry, something went wrong while processing your request."
            suggestions = []

        is_important = "leave" in question.lower()

        # Save to DB and context cache
        save_chat_message(user, question, answer, important=is_important)
        add_to_cache(user, question, answer)

        # Update chat history in session
        st.session_state.chat_history.append((question, answer, suggestions))

    # Render all previous chat messages
    # Ensure all chat history entries have 3 elements (q, a, suggestions)
    for i in range(len(st.session_state.chat_history)):
        if len(st.session_state.chat_history[i]) == 2:
            q, a = st.session_state.chat_history[i]
            st.session_state.chat_history[i] = (q, a, [])

    for q, a, suggestions in st.session_state.chat_history:
        print("Rendering suggestions in chat history:", suggestions)
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            st.markdown(a)
            # Show suggestion buttons if present or if answer contains fallback phrases
            fallback_phrases = [
                "i'm here to help with hr policy-related questions only.",
                "sorry, i couldn't find information related to that in the document.",
                "does not specify",
                "couldn't find",
                "not available",
                "no information",
                "not provided",
                "not mentioned",
                "unknown",
                "not stated",
                "not clear",
                "not sure",
                "unable to find",
                "no details"
            ]
            answer_lower = a.lower()
            if suggestions or any(phrase in answer_lower for phrase in fallback_phrases):
                st.markdown("**Did you mean:**")
                # If suggestions empty, show FAQ_QUESTIONS as fallback suggestions
                if not suggestions:
                    from gemini_llm import FAQ_QUESTIONS
                    fallback_suggestions = FAQ_QUESTIONS[:3]
                else:
                    fallback_suggestions = suggestions
                
                # Initialize button counter if not exists
                if 'button_counter' not in st.session_state:
                    st.session_state.button_counter = 0
                
                for i, sug in enumerate(fallback_suggestions):
                    # Use global counter for truly unique keys
                    st.session_state.button_counter += 1
                    key = f"sug_btn_{st.session_state.button_counter}"
                    if st.button(sug, key=key):
                        st.session_state["pending_question"] = sug
                        st.rerun()
