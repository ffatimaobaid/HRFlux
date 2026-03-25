import logging
import sys
from typing import Optional
from rag import retrieve_context
from gemini_llm import query_gemini, FAQ_QUESTIONS, get_similar_questions
from db import save_log, get_recent_history, get_document_filenames_by_ids
from hr_knowledge_base import get_hr_procedure, format_hr_response
from vector_store import search_sources
from config import SHOW_SOURCES
from dateutil import parser as date_parser
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def normalize_date(date_str):
    """
    Normalize date string to YYYY-MM-DD format using dateutil.
    Handles '15 dec', 'next monday', etc.
    """
    try:
        if not date_str:
            return None
        # Parse date (fuzzy=True allows skipping extra text if any)
        dt = date_parser.parse(date_str, fuzzy=True)
        
        # If year seems to be default (1900) or past, and user said "15 dec",
        # dateutil defaults to current year or 1900 depending on version.
        # Let's ensure if it's in the past relative to today, we might mean next year?
        # For simplicity, we assume generic parsing is 'current year' usually.
        # But if it defaults to 1900, fix it.
        if dt.year == 1900:
             dt = dt.replace(year=datetime.now().year)
             
        # If date is in the past (e.g. Dec 15 when today is Dec 10 2025), keep logic simple.
        # Ideally compare with today.
        
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
        logger.warning(f"Date parsing failed for '{date_str}': {e}")
        return date_str # Return original if parse fails, let validator catch it

def format_leave_balance_response(balances):
    """Helper function to format leave balance response"""
    return (
        "Your current leave balances:\n" +
        f"• Casual Leave: {balances.get('casual', 0)} days\n" +
        f"• Sick Leave: {balances.get('sick', 0)} days\n" +
        f"• Annual Leave: {balances.get('annual', 0)} days\n" +
        f"Total Available: {balances.get('casual', 0) + balances.get('sick', 0) + balances.get('annual', 0)} days"
    )

# Import new workflow engine and database functions
try:
    from workflow_engine import LeaveWorkflowEngine, ChatEscalationEngine
    from db_schema_v2 import get_employee, get_leave_balance
    WORKFLOW_ENGINE_AVAILABLE = True
except ImportError:
    WORKFLOW_ENGINE_AVAILABLE = False
    print("Workflow engine not available. Using legacy leave request handling.")

def validate_hr_query(question: str) -> tuple[bool, Optional[str]]:
    """
    Validate whether the question is HR-related using a Groq LLM classifier.
    Returns (is_valid, optional_message).
    """
    # Short-circuit for simple greetings — always allow
    simple_greetings = {'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening'}
    if question.lower().strip() in simple_greetings:
        return True, None

    try:
        from chat_groq_with_retry import create_chat_groq_with_retry

        llm = create_chat_groq_with_retry(
            model_name="llama-3.3-70b-versatile",
            temperature=0,
            max_tokens=10   # We only need one word back
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a query classifier for a company HR chatbot. "
                    "Determine if the user query is HR-related or not.\n\n"
                    "HR topics include: leave requests, attendance, salary, payroll, policies, "
                    "benefits, onboarding, offboarding, grievances, performance reviews, "
                    "document requests (NOC, experience letter, salary certificate), "
                    "company rules, and general workplace/employment matters.\n\n"
                    "Non-HR topics include: general knowledge, science, math, coding, news, "
                    "weather, celebrity gossip, sports, recipes, jokes, and anything not related "
                    "to employment or the workplace.\n\n"
                    "Reply with ONLY one word — HR or NON_HR."
                )
            },
            {"role": "user", "content": question},
        ]

        result = llm.invoke(messages)
        classification = (result.content or "").strip().upper()

        if classification.startswith("NON_HR"):
            refusal = (
                "I'm HRFLUX, your dedicated HR assistant. I can only help with HR-related topics such as:\n"
                "• 🏖️ Leave requests and balance\n"
                "• 📋 HR policies, benefits, and company rules\n"
                "• 📄 Official documents (NOC, experience letter, salary certificate)\n"
                "• 🚨 Employee grievances and escalations\n\n"
                "Please ask me something related to your workplace or HR matters!"
            )
            return False, refusal

    except Exception as e:
        logger.warning(f"HR query classifier failed, allowing query through: {e}")

    return True, None

def run_agent(user, question, model_name="models/gemini-1.5-flash", context_chunks=None):
    # Import the new shim for our unified LangGraph assistant
    from supervisor_workflow import invoke_agent_legacy
    
    # Save the user query to standard DB logging if needed
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Validate the query first
        is_valid, error_message = validate_hr_query(question)
        
        if not is_valid:
            print(f"DEBUG: Query validation failed: {error_message}")
            return error_message, []
        
        # The legacy shim expects a state dict with 'messages' and 'username'
        from langchain_core.messages import HumanMessage
        state = {
            "messages": [HumanMessage(content=question)],
            "username": user
        }
        
        # Invoke the LangGraph agent with an automatic retry for intermittent Groq tool-use parse errors
        result = None
        for attempt in range(3):
            try:
                result = invoke_agent_legacy(state)
                break
            except Exception as e:
                if 'tool_use_failed' in str(e) or 'invalid_request_error' in str(e):
                    if attempt < 2:
                        logger.warning(f"Groq tool parsing failed (Attempt {attempt+1}/3). Retrying...")
                        continue
                raise e
        
        # Extract the final answer
        final_answer = result["messages"][-1].content
        
        # Check if the response contains JSON (document generation)
        suggestions = []
        try:
            # Try to parse JSON response for document generation
            if "{" in final_answer and "}" in final_answer:
                import json
                import os
                # Extract JSON from the response
                json_start = final_answer.find("{")
                json_end = final_answer.rfind("}") + 1
                json_str = final_answer[json_start:json_end]
                
                response_data = json.loads(json_str)
                
                # Handle document generation response
                if response_data.get("status") == "success":
                    document_title = response_data.get("title", "Document")
                    document_type = response_data.get("document_type", "Document")
                    employee_data = response_data.get("employee_data", {})
                    pdf_path = response_data.get("pdf_path", "")
                    
                    # Create user-friendly message with download info
                    user_message = f"✅ **{document_title}** has been generated successfully!\n\n"
                    user_message += f"**Document Details:**\n"
                    user_message += f"• Type: {document_type}\n"
                    user_message += f"• Employee: {employee_data.get('Employee Name', 'N/A')}\n"
                    user_message += f"• ID: {employee_data.get('Employee ID', 'N/A')}\n"
                    user_message += f"• Designation: {employee_data.get('Designation', 'N/A')}\n\n"
                    
                    # Add download information
                    if pdf_path and os.path.exists(pdf_path):
                        # Store the full response data for download handling
                        try:
                            import streamlit as st
                            st.session_state.last_document_response = response_data
                        except:
                            pass  # Streamlit not available in this context
                        
                        user_message += f"📥 **Download Available:** Your document has been generated and is ready for download.\n\n"
                        user_message += f"💡 **Where to find it:** The PDF has been saved to your documents folder."
                    else:
                        user_message += f"⚠️ **Note:** PDF file generation completed. Check your documents folder."
                    
                    user_message += f"\n\nYour document has been personalized with your employee data and is ready for use."
                    
                    final_answer = user_message
                    
                elif response_data.get("status") == "error":
                    error_msg = response_data.get("error", "Unknown error occurred")
                    final_answer = f"❌ **Document Generation Failed:**\n\n{error_msg}\n\nPlease try again or contact HR support."
                
        except (json.JSONDecodeError, Exception):
            # Not a JSON response, handle normally
            pass
        
        # Log it
        save_log(user, question, final_answer)
        
        # Determine suggestions based on the final answer
        if "I'm here to help with HR-related" in final_answer or "completely unrelated" in final_answer:
            suggestions = get_similar_questions(question, FAQ_QUESTIONS, top_n=3)
        
        return final_answer, suggestions
        
    except Exception as e:
        logger.error(f"Error during unified assistant invocation: {e}", exc_info=True)
        fallback_msg = f"I'm sorry, I encountered an internal error. Please try again later. ({str(e)})"
        save_log(user, question, fallback_msg)
        return fallback_msg, [] # Return empty suggestions on error
