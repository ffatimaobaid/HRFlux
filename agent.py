import logging
import sys
from rag import retrieve_context
from gemini_llm import query_gemini, classify_and_extract_leave, FAQ_QUESTIONS, get_similar_questions
from db import save_log, get_recent_history

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

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
    from workflow_engine import LeaveWorkflowEngine
    from db_schema_v2 import get_employee, get_leave_balance
    WORKFLOW_ENGINE_AVAILABLE = True
except ImportError:
    WORKFLOW_ENGINE_AVAILABLE = False
    print("⚠️ Workflow engine not available. Using legacy leave request handling.")

def run_agent(user, question, model_name="models/gemini-1.5-flash", context_chunks=None):
    # Get recent chat history for conversation continuity
    chat_history = get_recent_history(user)

    # Use Gemini to classify and extract intent + leave info
    intent_result = classify_and_extract_leave(question, model_name)

    if intent_result.get("is_leave_request", False):
        start = intent_result.get("start_date")
        end = intent_result.get("end_date")
        leave_type = intent_result.get("leave_type", "casual").lower()
        reason = intent_result.get("reason") or question

        if start and end:
            # Use workflow engine if available
            if WORKFLOW_ENGINE_AVAILABLE:
                # Get employee by username
                employee = get_employee(username=user)
                if employee:
                    employee_id = employee['employee_id']
                    
                    # Submit through workflow engine
                    result = LeaveWorkflowEngine.submit_leave_request(
                        employee_id=employee_id,
                        leave_type=leave_type,
                        start_date=start,
                        end_date=end,
                        reason=reason
                    )
                    
                    if result['success']:
                        # Get updated balance
                        balances = get_leave_balance(employee_id)
                        answer = f"{result['message']}\n\nYour current leave balances:\n" + \
                                f"• Casual: {balances['casual']} days\n" + \
                                f"• Sick: {balances['sick']} days\n" + \
                                f"• Annual: {balances['annual']} days"
                    else:
                        answer = f"❌ {result['message']}"
                else:
                    answer = "Could not find your employee record. Please contact HR."
            else:
                # Fallback to old method
                from db import save_leave_request
                save_leave_request(user, leave_type, start, end, reason)
                answer = f"Your leave request from {start} to {end} has been submitted."
            
            save_log(user, question, answer)
            return answer, []
        else:
            # Let Gemini respond naturally when dates are unclear
            context = retrieve_context("how to apply for leave or mention correct format")
            # Extract only text from context tuples
            context_texts = [chunk[0] if isinstance(chunk, tuple) else chunk for chunk in context]
            answer = query_gemini(context_texts, question, model_name, chat_history)
            save_log(user, question, answer)
            return answer, []

    # Check if asking about leave balance
    if any(keyword in question.lower() for keyword in ['leave balance', 'how many leaves', 'remaining leaves', 'available leaves']):
        logger.info(f"Processing leave balance request from user: {user}")
        
        # Try with workflow engine first
        if WORKFLOW_ENGINE_AVAILABLE:
            logger.info("Workflow engine is available, attempting to fetch leave balance...")
            try:
                employee = get_employee(username=user)
                if employee:
                    logger.info(f"Found employee: {employee}")
                    balances = get_leave_balance(employee['employee_id'])
                    logger.info(f"Retrieved leave balances: {balances}")
                    if balances:
                        answer = format_leave_balance_response(balances)
                        save_log(user, question, answer)
                        return answer, []
                    else:
                        logger.warning("No leave balances found for employee")
                else:
                    logger.warning(f"No employee found with username: {user}")
            except Exception as e:
                logger.error(f"Error in workflow engine leave balance check: {str(e)}", exc_info=True)
        
        # Fallback to direct database query
        logger.info("Attempting direct database query...")
        try:
            from db import get_leave_balance as get_legacy_leave_balance
            logger.info(f"Calling get_legacy_leave_balance for user: {user}")
            balances = get_legacy_leave_balance(user)
            logger.info(f"Direct query result: {balances}")
            
            if balances:
                answer = format_leave_balance_response(balances)
                save_log(user, question, answer)
                return answer, []
            else:
                logger.warning("No leave balances found in direct query")
                answer = "I couldn't find your leave balance. Please contact HR to check your leave balance."
                
        except Exception as e:
            logger.error(f"Error in direct leave balance query: {str(e)}", exc_info=True)
            answer = "I encountered an error while fetching your leave balance. Please try again later or contact HR."
        
        save_log(user, question, answer)
        return answer, []
    
    # Not a leave request — use provided or retrieved document context
    if context_chunks is None:
        context_chunks = retrieve_context(question)

    if not context_chunks:
        # Always show suggestions for any unanswered question
        answer = (
            "Sorry, I couldn't find information related to that in the document.\n\nDid you mean:"
        )
        similar = get_similar_questions(question, FAQ_QUESTIONS, top_n=3)
        save_log(user, question, answer)
        return answer, similar

    # Extract only text if context is in (text, score) form
    context_texts = [chunk[0] if isinstance(chunk, tuple) else chunk for chunk in context_chunks]
    answer = query_gemini(context_texts, question, model_name, chat_history)

    # Check for fallback answers and provide suggestions
    fallback_phrases = [
        "I'm here to help with HR policy-related questions only.",
        "Sorry, I couldn't find information related to that in the document.",
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
    # Lowercase answer for case-insensitive matching
    answer_lower = answer.lower()
    if any(phrase in answer_lower for phrase in fallback_phrases) or len(answer_lower) < 50:
        similar = get_similar_questions(question, FAQ_QUESTIONS, top_n=3)
        save_log(user, question, answer)
        return answer, similar

    save_log(user, question, answer)
    return answer, []
