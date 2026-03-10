import streamlit as st
from agent import run_agent
from db import init_db, save_chat_message, get_recent_history, cleanup_old_sessions, delete_user_history, init_user_table, signup_user, login_user
from context_cache import add_to_cache, get_recent_context
import json
import os
import datetime
import traceback
import re

st.set_page_config(page_title="HR Chatbot", layout="centered")

@st.cache_data(ttl=3600*24)
def generate_alternative_queries(query):
    """
    Generate alternative search queries using Gemini to improve hybrid retrieval.
    This replaces hardcoded synonym dictionaries.
    """
    from gemini_llm import query_gemini
    try:
        # We ask Gemini to rewrite the query using standard HR terminology
        prompt = (
            f"Generate 3 alternative search queries for the user question: '{query}'. "
            "Use standard HR terminology and synonyms. "
            "Output only the 3 alternatives separated by pipes (|). No other text."
        )
        # Use a fast model if possible to avoid latency
        response = query_gemini([], prompt)
        
        # Parse response
        # Expected format: "Alternative 1 | Alternative 2 | Alternative 3"
        alternatives = [alt.strip() for alt in response.split('|') if alt.strip()]
        
        # Ensure we don't have duplicates or empty strings
        unique_alts = list(set([query] + alternatives))
        return unique_alts
        
    except Exception as e:
        print(f"Error generating alternative queries: {e}")
        return [query]

# Initialize DB and user table
init_db()
init_user_table()
cleanup_old_sessions(retention_hours=24)

# Global styles: custom CSS + Bootstrap
try:
    with open("styles/welcome.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

try:
    with open("styles/login.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

try:
    with open("styles/chat.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.markdown(
    """
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
      crossorigin="anonymous"
    />
    """,
    unsafe_allow_html=True,
)

if "welcome_done" not in st.session_state:
    st.session_state.welcome_done = False

if not st.session_state.welcome_done:
    try:
        with open("templates/welcome.html", "r", encoding="utf-8") as f:
            welcome_html = f.read()
    except FileNotFoundError:
        welcome_html = ""

    if welcome_html:
        st.markdown(welcome_html, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Continue", use_container_width=True):
            st.session_state.welcome_done = True
            st.rerun()

    st.stop()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "show_signup" not in st.session_state:
    st.session_state.show_signup = False

if not st.session_state.logged_in:
    # Two-column layout styled via styles/login.css
    st.markdown('<div class="login-page"><div class="login-card">', unsafe_allow_html=True)
    col_left, col_right = st.columns([3, 2])

    # LOGIN VIEW
    if not st.session_state.show_signup:
        with col_left:
            st.markdown(
                """
                <div class="login-left-header">
                  <div class="login-logo-mark">
                    <img src="https://dummyimage.com/120x60/000/fff&text=HRFLUX" alt="HRFLUX logo" />
                    <p class="login-logo-text">HRFLUX</p>
                  </div>
                  <h2 class="login-heading">Welcome back</h2>
                  <p class="login-subtext">AI-powered HR assistant, tailored to your workplace.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown('<p class="login-field-label">Email</p>', unsafe_allow_html=True)
            login_user_input = st.text_input("Email", key="login_user", placeholder="Enter your email")

            st.markdown('<p class="login-field-label">Password</p>', unsafe_allow_html=True)
            login_pass_input = st.text_input(
                "Password",
                type="password",
                key="login_pass",
                placeholder="Enter your password",
            )

            st.markdown('<p class="login-forgot"><span>Forgot your password?</span></p>', unsafe_allow_html=True)

            if st.button("Login"):
                if login_user(login_user_input, login_pass_input):
                    st.session_state.logged_in = True
                    st.session_state.user = login_user_input
                    st.success("Logged in!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

            if st.button("Don't have an account? Sign Up", key="go_to_signup"):
                st.session_state.show_signup = True
                st.rerun()

        with col_right:
            st.markdown(
                """
                <div class="login-right-card">
                  <div class="login-hero-icon">🤖</div>
                  <h3>AI-Powered HR Tailored for You.</h3>
                  <p>Get instant answers to HR questions, policies, and workplace queries.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # SIGNUP VIEW
    else:
        with col_left:
            st.markdown(
                """
                <div class="login-left-header">
                  <div class="login-logo-mark">
                    <img src="https://dummyimage.com/120x60/000/fff&text=HRFLUX" alt="HRFLUX logo" />
                    <p class="login-logo-text">HRFLUX</p>
                  </div>
                  <h2 class="login-heading">Create your account</h2>
                  <p class="login-subtext">Sign up to start using your AI-powered HR assistant.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown('<p class="login-field-label">New Username</p>', unsafe_allow_html=True)
            signup_user_input = st.text_input("New Username", key="signup_user")

            st.markdown('<p class="login-field-label">New Password</p>', unsafe_allow_html=True)
            signup_pass_input = st.text_input("New Password", type="password", key="signup_pass")

            if st.button("Create account"):
                if signup_user(signup_user_input, signup_pass_input):
                    st.success("Signup successful! Please login.")
                    st.session_state.show_signup = False
                    st.rerun()
                else:
                    st.error("Username already exists.")

            if st.button("Already have an account? Login", key="back_to_login"):
                st.session_state.show_signup = False
                st.rerun()

        with col_right:
            st.markdown(
                """
                <div class="login-right-card">
                  <div class="login-hero-icon">👥</div>
                  <h3>Welcome to HRFLUX.</h3>
                  <p>Create your account to personalize your HR experience.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()
else:
    user = st.session_state.user

    # Full-screen purple background, simple layout
    st.markdown(
        """
        <style>
        .stApp {
            background: #e3e6ff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

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

    for chat_entry in st.session_state.chat_history:
        if len(chat_entry) == 3:
            q, a, suggestions = chat_entry
        else:
            q, a = chat_entry
            suggestions = []
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
