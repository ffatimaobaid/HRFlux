import json
import logging
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Import existing backend operations
try:
    from workflow_engine import LeaveWorkflowEngine
    from db_schema_v2 import get_employee, get_leave_balance
    from hr_knowledge_base import get_hr_procedure
    from rag import retrieve_context
except ImportError as e:
    logger.error(f"Failed to import backend modules for LeaveBot Tools: {e}")

@tool
def tool_get_leave_balance(username: str) -> str:
    """
    Fetch the available leave balances (casual, sick, annual) for a given employee username.
    Use this to check if an employee has enough leave balance before applying.
    """
    try:
        emp = get_employee(username=username)
        if not emp:
            return json.dumps({"error": f"Employee record not found for username '{username}'"})
        
        balances = get_leave_balance(emp['employee_id'])
        if not balances:
            return json.dumps({"error": "Leave balance record not found."})
            
        return json.dumps({
            "casual": balances.get('casual', 0),
            "sick": balances.get('sick', 0),
            "annual": balances.get('annual', 0),
            "total_available": balances.get('casual', 0) + balances.get('sick', 0) + balances.get('annual', 0)
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def tool_get_leave_history(username: str) -> str:
    """
    Fetch the recent leave history and upcoming scheduled leaves for a given employee username.
    Use this to analyze past leave patterns or check for overlapping dates.
    """
    try:
        emp = get_employee(username=username)
        if not emp:
            return json.dumps({"error": "Employee record not found."})
            
        from workflow_engine import get_employee_leave_history
        # Fetch up to 10 recent leaves to give good context for advisory
        leaves = get_employee_leave_history(emp['employee_id'], limit=10)
        
        if not leaves:
            return json.dumps({"message": "No leave history found."})
            
        history = []
        for l in leaves:
            history.append({
                "leave_id": l[0],
                "type": l[2],
                "start_date": l[3],
                "end_date": l[4],
                "total_days": l[5],
                "status": l[7],
                "reason": l[6]
            })
        return json.dumps({"history": history})
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def tool_get_employee_profile(username: str) -> str:
    """
    Fetch the HR profile of the employee including department, role, and manager.
    Use this to understand contextual rules (e.g., Sales department might have different blackout periods).
    """
    try:
        emp = get_employee(username=username)
        if not emp:
            return json.dumps({"error": "Employee record not found."})
        
        return json.dumps({
            "employee_id": emp['employee_id'],
            "full_name": emp['full_name'],
            "department": emp['department'],
            "designation": emp['designation'],
            "joining_date": emp['joining_date']
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def tool_search_hr_policy(query: str) -> str:
    """
    Search the company HR knowledge base and PDF policy documents using RAG.
    Use this to check leave accrual rules, expiry policies, or blackout periods.
    """
    try:
        # First check hardcoded procedures for quick wins
        procedure = get_hr_procedure(query)
        if procedure and not procedure.startswith("I couldn't find a specific step-by-step procedure"):
            # If we got a good hit from the hardcoded base, return it
            pass
        
        # Always supplement with Hybrid RAG
        context_chunks = retrieve_context(query, top_k=3)
        return json.dumps({
            "policy_excerpts": context_chunks if context_chunks else ["No specific policy documents found."]
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def tool_submit_leave_request(username: str, leave_type: str, start_date: str, end_date: str, reason: str) -> str:
    """
    Submit a formal leave application to the HR system.
    Requires: username, leave_type ('casual', 'sick', or 'annual'), start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), and a reason.
    Only call this if the user has EXPLICITLY confirmed they want to apply for these dates.
    """
    try:
        emp = get_employee(username=username)
        if not emp:
            return json.dumps({"error": "Employee record not found. Cannot apply."})
            
        # Call the workflow engine directly
        result = LeaveWorkflowEngine.submit_leave_request(
            employee_id=emp['employee_id'],
            leave_type=leave_type.lower(),
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )
        
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})

# List of all tools to bind to the LeaveBot
leave_bot_tools = [
    tool_get_leave_balance,
    tool_get_leave_history,
    tool_get_employee_profile,
    tool_search_hr_policy,
    tool_submit_leave_request
]
