import streamlit as st
from agent import run_agent
from db import init_db, save_chat_message, get_recent_history, cleanup_old_sessions, delete_user_history, init_user_table, signup_user, login_user
from context_cache import add_to_cache, get_recent_context
import json
import os
import datetime
import traceback
from auth_manager import auth_manager
from guardrails import ContentFilter, InputValidator, SecurityLogger

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
    css_path = os.path.join(os.path.dirname(__file__), "styles", "welcome.css")
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass  # CSS file not found, continue without custom styles
except Exception as e:
    st.warning(f"Could not load CSS: {e}")

try:
    css_path = os.path.join(os.path.dirname(__file__), "styles", "login.css")
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

try:
    css_path = os.path.join(os.path.dirname(__file__), "styles", "chat.css")
    with open(css_path) as f:
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
        template_path = os.path.join(os.path.dirname(__file__), "templates", "welcome.html")
        with open(template_path, "r", encoding="utf-8") as f:
            welcome_html = f.read()
    except FileNotFoundError:
        welcome_html = ""
    except Exception as e:
        st.warning(f"Could not load welcome template: {e}")
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
                    st.error("Invalid email or password")

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

    from db import get_employee_tasks, add_employee_task, update_employee_task_status
    from db_schema_v2 import get_employee
    from notification_service import generate_creative_notification
    
    employee_data = get_employee(username=user)
    emp_id = employee_data['employee_id'] if employee_data else None
    employee_name = employee_data['full_name'] if employee_data else user

    # Top Navigation / Notification Bar
    nav_col1, nav_col2, nav_col3 = st.columns([6, 1, 1])
    with nav_col1:
        st.title("HR Assistant & Productivity Dashboard")
        
    with nav_col2:
        # Notifications Popover
        pending_tasks = []
        immediate_tasks = []
        upcoming_tasks = []
        if emp_id:
            all_pending = [t for t in get_employee_tasks(emp_id) if t['status'] == 'pending']
            
            import datetime
            today_str = str(datetime.date.today())
            
            # Split tasks
            for t in all_pending:
                if t['deadline'] and t['deadline'] <= today_str:
                    immediate_tasks.append(t)
                else:
                    upcoming_tasks.append(t)
            
            pending_tasks = all_pending # all of them
            
        # The red icon bubble only counts immediate items
        badge_count = len(immediate_tasks)
        
        with st.popover(f"🔔 Notifications ({badge_count})"):
            if immediate_tasks:
                st.write("**🚨 Due Today / Overdue:**")
                # Separate meetings from other tasks
                immediate_meetings = [t for t in immediate_tasks if t['event_type'] == 'meeting']
                immediate_other = [t for t in immediate_tasks if t['event_type'] != 'meeting']
                
                # Show meetings first with special icon
                for t in immediate_meetings:
                    st.error(f"🤝 {t['title']} (Meeting - Due: {t['deadline']})")
                
                # Show other tasks
                for t in immediate_other:
                    st.error(f"- {t['title']} (Due: {t['deadline']})")
                
                # Only toast for immediate tasks
                if "notification_shown" not in st.session_state:
                    st.session_state.notification_shown = True
                    notif = generate_creative_notification(employee_name, immediate_tasks)
                    st.toast(notif, icon="🚨")
                    st.success(f"**AI Motivation:** {notif}")
            else:
                st.write("No tasks due today! 🎉")
                # Ensure we don't trigger the toast over and over when they have 0
                st.session_state.notification_shown = True

            if upcoming_tasks:
                st.write("---")
                st.write("**📅 Upcoming Tasks:**")
                # Separate meetings from other tasks
                upcoming_meetings = [t for t in upcoming_tasks if t['event_type'] == 'meeting']
                upcoming_other = [t for t in upcoming_tasks if t['event_type'] != 'meeting']
                
                # Show meetings first with special icon
                if upcoming_meetings:
                    st.write("**🤝 Upcoming Meetings:**")
                    for t in upcoming_meetings[:3]: # limit to next 3 meetings
                        st.info(f"🤝 {t['title']} (Meeting - {t['deadline']})")
                
                # Show other tasks
                if upcoming_other:
                    st.write("**📋 Other Tasks:**")
                    for t in upcoming_other[:3]: # limit to next 3 other tasks
                        st.info(f"- {t['title']} (Due: {t['deadline']})")
                
    with nav_col3:
        if st.button("Clear Chat", help="Clear conversation history"):
            st.session_state.chat_history = []
            delete_user_history(user)
            st.rerun()

    # Load selected model silently
    model = "models/gemini-1.5-flash"
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            try:
                config = json.load(f)
                model = config.get("model", model)
            except json.JSONDecodeError:
                pass

    # Main Dashboard Layout
    main_col1, main_col2 = st.columns([1.2, 1])

    with main_col1:
        st.subheader("🤖 Chat Assistant")
        
        # Chat history container
        chat_container = st.container(height=500)
        
        # Load previous chat history from DB into session state
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = get_recent_history(user)

        # Render all previous chat messages (always show, not just when sending)
        with chat_container:
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
                with st.chat_message("user"):
                    st.markdown(q)
                with st.chat_message("assistant"):
                    st.markdown(a)
                    fallback_phrases = [
                        "i'm here to help with hr policy-related questions only.",
                        "sorry, i couldn't find information related to that in the document.",
                        "does not specify",
                        "couldn't find",
                        "not available"
                    ]
                    answer_lower = a.lower()
                    if suggestions or any(phrase in answer_lower for phrase in fallback_phrases):
                        st.markdown("**Did you mean:**")
                        if not suggestions:
                            from gemini_llm import FAQ_QUESTIONS
                            fallback_suggestions = FAQ_QUESTIONS[:3]
                        else:
                            fallback_suggestions = suggestions
                        
                        if 'button_counter' not in st.session_state:
                            st.session_state.button_counter = 0
                        
                        for i, sug in enumerate(fallback_suggestions):
                            st.session_state.button_counter += 1
                            key = f"sug_btn_{st.session_state.button_counter}"
                            if st.button(sug, key=key):
                                st.session_state["pending_question"] = sug
                                st.rerun()

    from auth_manager import auth_manager
    from guardrails import ContentFilter, InputValidator, SecurityLogger

    # Input box for new user question
    if "pending_question" in st.session_state:
        question = st.session_state.pop("pending_question")
    else:
        question = st.chat_input("Ask about HR policies...", key="main_chat_input")
        
    if question:
        print(f"DEBUG: Processing question: {question}")
        # Apply content filtering and validation
        sanitized_question = ContentFilter.sanitize_input(question)
        content_filter = ContentFilter.filter_content(question)
        print(f"DEBUG: Content filter result: {content_filter}")
        
        if not content_filter['allowed']:
            SecurityLogger.log_security_event('content_blocked', {
                'original_question': question,
                'sanitized_question': sanitized_question,
                'filter_results': content_filter
            }, user)
            
            st.error("❌ Inappropriate content detected. Please rephrase your question.")
            st.write("**Issues found:**")
            for warning in content_filter['warnings']:
                st.write(f"- {warning}")
            st.stop()
        
        print("DEBUG: Content allowed, processing...")
        # Display user message immediately
        with chat_container:
            with st.chat_message("user"):
                st.markdown(sanitized_question)
            
            # Show typing indicator
            with st.chat_message("assistant"):
                st.write("Thinking...")
        
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
        print(f"DEBUG: Generated answer: {answer}")

        # Save to DB and context cache
        save_chat_message(user, question, answer, important=is_important)
        add_to_cache(user, question, answer)

        # Update chat history in session
        st.session_state.chat_history.append((question, answer, suggestions))
        
        # Display assistant's response
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(answer)
                
                # Check if there's a document response to handle
                if hasattr(st.session_state, 'last_document_response'):
                    document_response = st.session_state.last_document_response
                    
                    if document_response.get("status") == "success":
                        # Handle document display and download
                        pdf_path = document_response.get('pdf_path', '')
                        document_type = document_response.get('document_type', 'Document')
                        document_title = document_response.get('title', 'Document')
                        
                        if pdf_path and os.path.exists(pdf_path):
                            # Use enhanced PDF display
                            try:
                                from pdf_display_utils import enhanced_pdf_display
                                enhanced_pdf_display(pdf_path, document_title)
                            except ImportError:
                                # Fallback to simple display
                                st.info("📄 PDF Document Generated")
                                
                                # Create two columns for view and download
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    # Simple preview using popover
                                    with st.popover("👁️ View PDF", use_container_width=True):
                                        try:
                                            import base64
                                            with open(pdf_path, "rb") as pdf_file:
                                                base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
                                            
                                            # Simple iframe embed
                                            pdf_display = f'''
                                            <iframe src="data:application/pdf;base64,{base64_pdf}" 
                                                    width="100%" height="500px" type="application/pdf">
                                            </iframe>
                                            '''
                                            st.markdown(pdf_display, unsafe_allow_html=True)
                                            st.info("📄 PDF Preview - Scroll to view full document")
                                            
                                        except Exception as e:
                                            st.error(f"Error displaying PDF: {str(e)}")
                                            st.write(f"📁 File: {os.path.basename(pdf_path)}")
                                            st.write(f"📊 Size: {os.path.getsize(pdf_path)} bytes")
                                
                                with col2:
                                    # Download Button
                                    try:
                                        with open(pdf_path, 'rb') as pdf_file:
                                            pdf_data = pdf_file.read()
                                        
                                        filename = os.path.basename(pdf_path)
                                        st.download_button(
                                            label=f"📥 Download {document_type}",
                                            data=pdf_data,
                                            file_name=filename,
                                            mime="application/pdf",
                                            key=f"download_{filename}_{datetime.now().timestamp()}",
                                            use_container_width=True
                                        )
                                        
                                        # Show file info
                                        st.write(f"📄 {document_title}")
                                        st.write(f"📊 {os.path.getsize(pdf_path):,} bytes")
                                        
                                    except Exception as e:
                                        st.error(f"Error preparing download: {str(e)}")
                        
                        else:
                            st.error("❌ PDF file not found. Please try generating the document again.")
                        
                        # Clear the document response after handling
                        del st.session_state.last_document_response
                
                # Show suggestions if available
                if suggestions:
                    st.markdown("**Did you mean:**")
                    for i, sug in enumerate(suggestions):
                        # Create unique key using index
                        if st.button(sug, key=f"suggestion_{i}_{sug}"):
                            st.session_state["pending_question"] = sug
                            st.rerun()
        
        print("DEBUG: About to rerun...")
        # Rerun to display the updated chat history
        st.rerun()

    with main_col2:
        st.subheader("📅 My Calendar & Tasks")
        
        if not emp_id:
            st.warning("Please switch to an employee account to use the calendar.")
        else:
            tasks = get_employee_tasks(emp_id)
            
            # Simple form to add task
            with st.expander("➕ Add New Event", expanded=False):
                with st.form("add_task_form"):
                    t_title = st.text_input("Title")
                    t_desc = st.text_area("Description")
                    t_type = st.selectbox("Type", ["task", "event", "deadline", "meeting"])
                    t_date = st.date_input("Date/Deadline")
                    t_start_time = st.time_input("Start Time", value=None)
                    t_end_time = st.time_input("End Time", value=None)
                    
                    if st.form_submit_button("Add to Calendar"):
                        if t_title:
                            # Use the enhanced function that supports time
                            from meeting_tools import add_employee_task_with_time
                            start_str = str(t_start_time).replace(" datetime.time(", "").replace(")", "") if t_start_time else None
                            end_str = str(t_end_time).replace(" datetime.time(", "").replace(")", "") if t_end_time else None
                            
                            if start_str and end_str:
                                start_str = f"{start_str.split(':')[0]}:{start_str.split(':')[1]}"
                                end_str = f"{end_str.split(':')[0]}:{end_str.split(':')[1]}"
                            
                            success = add_employee_task_with_time(
                                emp_id, t_title, t_desc, str(t_date), t_type, 
                                start_str, end_str
                            )
                            if success:
                                st.success("Added!")
                                st.rerun()
                            else:
                                st.error("Failed to add event.")
                        else:
                            st.error("Title is required.")

            # Calendar view state management
            if 'calendar_view' not in st.session_state:
                st.session_state.calendar_view = 'month'
            if 'selected_date' not in st.session_state:
                st.session_state.selected_date = None

            # Add date selector for day view
            if st.session_state.calendar_view == 'day' and st.session_state.selected_date:
                col_back, col_date = st.columns([1, 3])
                with col_back:
                    if st.button("← Back to Month", key="back_to_month"):
                        st.session_state.calendar_view = 'month'
                        st.session_state.selected_date = None
                        st.rerun()
                with col_date:
                    st.subheader(f"📅 Schedule for {st.session_state.selected_date}")

            # Remove the separate date picker since we want calendar to be clickable

            try:
                from streamlit_calendar import calendar
                
                # Filter events for selected date if in day view
                if st.session_state.calendar_view == 'day' and st.session_state.selected_date:
                    day_events = []
                    
                    # Debug: Show all tasks for this employee
                    st.write(f"🔍 Debug: Total tasks for employee: {len(tasks)}")
                    st.write(f"🔍 Debug: Selected date: {st.session_state.selected_date}")
                    
                    for t in tasks:
                        st.write(f"🔍 Task: {t['title']} | Date: {t['deadline']} | Start: {t.get('start_time')} | End: {t.get('end_time')}")
                        
                        if t['deadline'] == st.session_state.selected_date:
                            color = "#3788d8" # default blue
                            if t['status'] == 'completed':
                                color = "#28a745" # green
                            elif t['event_type'] == 'deadline':
                                color = "#dc3545" # red
                            elif t['event_type'] == 'meeting':
                                color = "#ffc107" # yellow
                            
                            # Create event with time information if available
                            event_title = f"{'✅ ' if t['status']=='completed' else ''}{t['title']}"
                            event_data = {
                                "title": event_title,
                                "start": st.session_state.selected_date,
                                "color": color
                            }
                            
                            # Add time information if available
                            if t.get('start_time'):
                                # Combine date and time for proper calendar display with seconds
                                start_datetime = f"{st.session_state.selected_date}T{t['start_time']}:00"
                                event_data["start"] = start_datetime
                                st.write(f"⏰ Event start set to: {start_datetime}")
                                
                                if t.get('end_time'):
                                    end_datetime = f"{st.session_state.selected_date}T{t['end_time']}:00"
                                    event_data["end"] = end_datetime
                                    st.write(f"⏰ Event end set to: {end_datetime}")
                                else:
                                    # Default 1-hour duration if no end time
                                    start_parts = t['start_time'].split(':')
                                    start_hour = int(start_parts[0])
                                    start_min = int(start_parts[1])
                                    end_hour = (start_hour + 1) % 24
                                    end_datetime = f"{st.session_state.selected_date}T{end_hour:02d}:{start_min:02d}:00"
                                    event_data["end"] = end_datetime
                                    st.write(f"⏰ Default end set to: {end_datetime}")
                            else:
                                st.write(f"⚠️ No start_time for event: {t['title']}")
                            
                            day_events.append(event_data)
                            st.write(f"✅ Added event: {event_data}")
                    
                    st.write(f"📅 Final day_events: {day_events}")
                    
                    # Show day view with time slots - simplified configuration
                    day_options = {
                        "initialView": "timeGridDay",
                        "height": 450,
                        "slotMinTime": "08:00",
                        "slotMaxTime": "18:00",
                        "allDaySlot": False
                    }
                    
                    # Add a back button above the calendar
                    col_back, col_title = st.columns([1, 3])
                    with col_back:
                        if st.button("← Back to Month", key="back_to_month_2", use_container_width=True):
                            st.session_state.calendar_view = 'month'
                            st.session_state.selected_date = None
                            st.rerun()
                    with col_title:
                        st.subheader(f"📅 Schedule for {st.session_state.selected_date}")
                    
                    # Debug: Show what events we're creating
                    if len(day_events) == 0:
                        st.info(f"No events scheduled for {st.session_state.selected_date}")
                        
                        # Add a test event to verify calendar works
                        test_event = {
                            "title": "Test Meeting (2:00-3:00 PM)",
                            "start": f"{st.session_state.selected_date}T14:00:00",
                            "end": f"{st.session_state.selected_date}T15:00:00",
                            "color": "#ff6b6b"
                        }
                        st.write("🧪 Adding test event to verify calendar works...")
                        day_events.append(test_event)
                    else:
                        st.write(f"📅 Found {len(day_events)} events for {st.session_state.selected_date}")
                    
                    # Show final events for debugging
                    st.write("🔍 Final events being sent to calendar:")
                    for i, event in enumerate(day_events):
                        st.write(f"  {i+1}. {event['title']}: {event.get('start', 'No start')} - {event.get('end', 'No end')}")
                    
                    # Try the calendar with minimal configuration
                    try:
                        calendar(events=day_events, options=day_options)
                        st.success("✅ Calendar rendered successfully!")
                    except Exception as e:
                        st.error(f"❌ Calendar error: {e}")
                        st.write("🔧 Trying alternative display...")
                        
                        # Fallback: Show events as a simple list
                        st.write("### Events as List:")
                        for event in day_events:
                            start_time = event.get('start', 'All day')
                            if 'T' in start_time:
                                time_part = start_time.split('T')[1][:5]
                                st.write(f"- **{event['title']}** at {time_part}")
                            else:
                                st.write(f"- **{event['title']}** (All day)")
                else:
                    # Format events for streamlit-calendar (month view)
                    calendar_events = []
                    for t in tasks:
                        color = "#3788d8" # default blue
                        if t['status'] == 'completed':
                            color = "#28a745" # green
                        elif t['event_type'] == 'deadline':
                            color = "#dc3545" # red
                        elif t['event_type'] == 'meeting':
                            color = "#ffc107" # yellow
                            
                        # Calendar needs start date, we use deadline as start for tasks for simplicity
                        dt_val = t['deadline']
                        if not dt_val:
                            import datetime
                            dt_val = str(datetime.date.today())
                        
                        # Create event with time information if available
                        event_title = f"{'✅ ' if t['status']=='completed' else ''}{t['title']}"
                        event_data = {
                            "title": event_title,
                            "start": dt_val,
                            "color": color,
                            "url": f"?date={dt_val}"  # Custom URL to trigger date selection
                        }
                        
                        # Add time information if available
                        if t.get('start_time'):
                            # Combine date and time for proper calendar display
                            start_datetime = f"{dt_val}T{t['start_time']}"
                            event_data["start"] = start_datetime
                            
                            if t.get('end_time'):
                                end_datetime = f"{dt_val}T{t['end_time']}"
                                event_data["end"] = end_datetime
                            else:
                                # Default 1-hour duration if no end time
                                start_parts = t['start_time'].split(':')
                                start_hour = int(start_parts[0])
                                start_min = int(start_parts[1])
                                end_hour = (start_hour + 1) % 24
                                end_datetime = f"{dt_val}T{end_hour:02d}:{start_min:02d}"
                                event_data["end"] = end_datetime
                        
                        calendar_events.append(event_data)
                    
                    # Check URL parameters for date selection
                    query_params = st.query_params
                    if 'date' in query_params:
                        selected_date = query_params['date']
                        st.session_state.calendar_view = 'day'
                        st.session_state.selected_date = selected_date
                        # Clear the query param
                        st.query_params.clear()
                        st.rerun()
                    
                    calendar_options = {
                        "headerToolbar": {
                            "left": "today prev,next",
                            "center": "title",
                            "right": ""
                        },
                        "initialView": "dayGridMonth",
                        "height": 450,
                        "slotMinTime": "08:00:00",
                        "slotMaxTime": "18:00:00",
                        "allDaySlot": False,
                        "navLinks": True,
                        "eventClick": "function(info) { window.location.href = '?date=' + info.event.startStr.split('T')[0]; }",
                        "dateClick": "function(info) { window.location.href = '?date=' + info.dateStr; }"
                    }
                    
                    calendar(events=calendar_events, options=calendar_options)
            except ImportError:
                st.warning("Please install streamlit-calendar using `pip install streamlit-calendar` to view the graphical calendar.")
                
            # Quick actions area below calendar
            st.write("---")
            st.subheader("Action Items")
            pending = [t for t in tasks if t['status'] == 'pending']
            
            if not pending:
                st.write("No pending action items.")
            else:
                for t in pending[:5]: # show up to 5
                    if st.button(f"Mark Complete: {t['title']}", key=f"complete_{t['id']}", use_container_width=True):
                        update_employee_task_status(t['id'], 'completed')
                        st.rerun()
