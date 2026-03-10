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

def run_agent(user, question, model_name="models/gemini-1.5-flash", context_chunks=None):
    # Get recent chat history for conversation continuity
    chat_history = get_recent_history(user)

    # --- STATUS CHECK INTENT DETECTION ---
    status_keywords = ["status", "approved", "rejected", "application", "request", "ticket", "complaint", "what happened", "my leave", "update on"]
    if any(k in question.lower() for k in status_keywords):
        logger.info(f"Status check detected for user: {user}")
        user_status_context = "User's Recent Activity Status:\n"
        
        if WORKFLOW_ENGINE_AVAILABLE:
            # 1. Fetch Leave Requests
            try:
                # We need to get employee_id first
                emp = get_employee(username=user)
                if emp:
                    # workflow_engine doesn't have a direct 'get_history' by id exposed as static, 
                    # but checks 'get_employee_leave_history' at module level
                    from workflow_engine import get_employee_leave_history
                    leaves = get_employee_leave_history(emp['employee_id'], limit=3)
                    if leaves:
                        user_status_context += "\nRecent Leave Requests:\n"
                        for l in leaves:
                            # l: id, emp_id, type, start, end, days, reason, status, approver, approved_at, comments, ...
                            lid, ltype, start, end, status, comments = l[0], l[2], l[3], l[4], l[7], l[10]
                            user_status_context += f"- Leave ({ltype}) from {start} to {end}: {status.upper()}"
                            if status in ['approved', 'rejected'] and comments:
                                user_status_context += f" (Admin Note: {comments})"
                            user_status_context += "\n"
                    else:
                        user_status_context += "\nNo recent leave requests found.\n"
            except Exception as e:
                logger.error(f"Error fetching leave status: {e}")

            # 2. Fetch Escalations
            try:
                escalations = ChatEscalationEngine.get_user_escalations(user, limit=3)
                if escalations:
                    user_status_context += "\nRecent Support Escalations:\n"
                    for esc in escalations:
                        # esc: reason, status, resolution_notes, date, resolved_at
                        user_status_context += f"- Ticket ({esc['reason']}): {esc['status'].upper()}"
                        if esc['status'] == 'resolved' and esc['resolution_notes']:
                            user_status_context += f" (Resolution: {esc['resolution_notes']})"
                        user_status_context += "\n"
                else:
                    user_status_context += "\nNo recent escalations found.\n"
            except Exception as e:
                logger.error(f"Error fetching escalation status: {e}")
        
        # Inject this context into the chunks
        if context_chunks is None:
            context_chunks = []
        context_chunks.append(user_status_context)
        print(f"DEBUG: Injected Status Context:\n{user_status_context}")


    # ===== NEW LANGGRAPH LOGIC START =====
    from supervisor_workflow import hrflux_agent
    from langchain_core.messages import HumanMessage, AIMessage
    
    # Build history_str for prompt injection
    history_str = ""
    if chat_history:
        formatted = [f"User: {q}\nAI: {a}" for q, a in chat_history[-5:] if q and a and q.strip() and a.strip()]
        if formatted:
            history_str = "\n".join(formatted)
        else:
            history_str = "No prior exchanges."
            
    # Combine status context with question if available
    if context_chunks:
        question_with_context = f"Internal Context (Status/History):\n{chr(10).join(context_chunks)}\n\nUser Question:\n{question}"
    else:
        question_with_context = question
        
    state = {
        "messages": [HumanMessage(content=question_with_context)],
        "username": user,
        "chat_history_str": history_str,
    }
    
    logger.info(f"Invoking hrflux_agent for user {user}")
    try:
        result = hrflux_agent.invoke(state)
        answer = result["messages"][-1].content
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Error invoking hrflux_agent: {e}")
        answer = "I'm sorry, an internal error occurred while processing your request."
        
    suggestions = []
    if "I'm here to help with HR-related" in answer or "completely unrelated" in answer:
        from gemini_llm import get_similar_questions, FAQ_QUESTIONS
        suggestions = get_similar_questions(question, FAQ_QUESTIONS, top_n=3)
        
    from db import save_log
    save_log(user, question, answer)
    return answer, suggestions
