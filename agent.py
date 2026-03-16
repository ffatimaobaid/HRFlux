import logging
import sys
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
    """Validate if question is HR-related."""
    prohibited_topics = [
        'tesla', 'elon musk', 'spacex', 'amazon', 'apple', 'google', 'microsoft',
        'celebrity', 'ceo', 'owner', 'ownership', 'who is', 'what is',
        'general knowledge', 'trivia', 'news', 'politics', 'technology',
        'science', 'history', 'geography', 'sports', 'entertainment'
    ]
    
    question_lower = question.lower()
    
    # Check for prohibited topics
    for topic in prohibited_topics:
        if topic in question_lower:
            return False, f"This appears to be about {topic}, which is outside my HR domain. I can only help with HR-related questions such as policies, leave requests, benefits, and company procedures."
    
    # Check if it's a simple greeting vs HR question
    simple_greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon']
    if question_lower.strip() in simple_greetings and len(question.split()) <= 2:
        return True, "Hello! How can I help you with HR-related matters today?"
    
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
            return {
                "answer": error_message,
                "suggestions": []
            }
        
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
        
        # Log it
        save_log(user, question, final_answer)
        
        # Determine suggestions based on the final answer
        suggestions = []
        if "I'm here to help with HR-related" in final_answer or "completely unrelated" in final_answer:
            suggestions = get_similar_questions(question, FAQ_QUESTIONS, top_n=3)
        
        return final_answer, suggestions
        
    except Exception as e:
        logger.error(f"Error during unified assistant invocation: {e}", exc_info=True)
        fallback_msg = f"I'm sorry, I encountered an internal error. Please try again later. ({str(e)})"
        save_log(user, question, fallback_msg)
        return fallback_msg, [] # Return empty suggestions on error
