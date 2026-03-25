"""
Admin Bot Tools
LangChain tools for the Admin chatbot — wraps existing DB and workflow functions.
No new DB logic here, purely adapters for the LangGraph ReAct agent.
"""

import json
from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# Leave Management Tools
# ---------------------------------------------------------------------------

@tool
def tool_get_pending_leaves() -> str:
    """
    Get all pending leave requests awaiting admin approval.
    Returns a formatted summary of each pending leave (employee, dates, reason).
    """
    try:
        from workflow_engine import LeaveWorkflowEngine
        requests = LeaveWorkflowEngine.get_pending_requests()
        if not requests:
            return "No pending leave requests at the moment."

        lines = [f"Found {len(requests)} pending leave request(s):\n"]
        for req in requests:
            req_id    = req[0]
            emp_id    = req[1]
            leave_type = req[2]
            start     = req[3]
            end       = req[4]
            days      = req[5]
            reason    = req[6]
            full_name = req[12] if len(req) > 12 else emp_id
            dept      = req[13] if len(req) > 13 else "N/A"
            lines.append(
                f"• ID #{req_id} | {full_name} ({dept}) | {leave_type.upper()} | "
                f"{start} → {end} ({days} days) | Reason: {reason}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching pending leaves: {e}"


@tool
def tool_approve_leave(request_id: int, comment: str = "Approved via Admin Chat") -> str:
    """
    Approve a specific leave request by its ID.
    Args:
        request_id: The integer ID of the leave request to approve.
        comment: Optional approval comment/note.
    """
    try:
        from workflow_engine import LeaveWorkflowEngine
        result = LeaveWorkflowEngine.approve_leave_request(request_id, "ADMIN_CHAT", comment)
        if result.get("success"):
            return f"✅ Leave request #{request_id} has been approved. Note: {comment}"
        return f"❌ Failed to approve request #{request_id}: {result.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error approving leave #{request_id}: {e}"


@tool
def tool_reject_leave(request_id: int, reason: str = "Rejected via Admin Chat") -> str:
    """
    Reject a specific leave request by its ID.
    Args:
        request_id: The integer ID of the leave request to reject.
        reason: The reason for rejection.
    """
    try:
        from workflow_engine import LeaveWorkflowEngine
        result = LeaveWorkflowEngine.reject_leave_request(request_id, "ADMIN_CHAT", reason)
        if result.get("success"):
            return f"❌ Leave request #{request_id} has been rejected. Reason: {reason}"
        return f"Failed to reject request #{request_id}: {result.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error rejecting leave #{request_id}: {e}"


# ---------------------------------------------------------------------------
# Escalation Tools
# ---------------------------------------------------------------------------

@tool
def tool_get_escalations(status_filter: str = "all") -> str:
    """
    Get HR escalations. 
    Args:
        status_filter: One of 'pending', 'resolved', or 'all' (default).
    """
    try:
        from workflow_engine import LeaveWorkflowEngine, ChatEscalationEngine

        # Workflow escalations
        all_esc = LeaveWorkflowEngine.get_all_escalations()
        if status_filter in ("pending", "resolved"):
            all_esc = [e for e in all_esc if e["status"] == status_filter]

        # Chat/Support escalations
        chat_esc = ChatEscalationEngine.get_pending_escalations()

        lines = []
        if all_esc:
            lines.append(f"=== Workflow Escalations ({len(all_esc)}) ===")
            for e in all_esc:
                lines.append(
                    f"• ID #{e['id']} | {e.get('employee_name','?')} | "
                    f"{e.get('request_type','?')} | Status: {e['status']} | "
                    f"Reason: {e.get('reason','N/A')}"
                )
        else:
            lines.append("No workflow escalations found.")

        if chat_esc:
            lines.append(f"\n=== Sensitive Chat Escalations ({len(chat_esc)}) ===")
            for c in chat_esc:
                lines.append(
                    f"• ID #{c['id']} | User: {c['username']} | "
                    f"Reason: {c['reason']} | Query: {c['query']}"
                )
        else:
            lines.append("No pending chat/sensitive escalations.")

        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching escalations: {e}"


@tool
def tool_resolve_escalation(escalation_id: int, resolution_note: str) -> str:
    """
    Resolve a workflow escalation by its ID.
    Args:
        escalation_id: The integer ID of the escalation to resolve.
        resolution_note: A note describing how the issue was resolved.
    """
    try:
        from workflow_engine import LeaveWorkflowEngine
        result = LeaveWorkflowEngine.resolve_escalation(escalation_id, resolution_note)
        if result.get("success"):
            return f"✅ Escalation #{escalation_id} marked as resolved. Note: {resolution_note}"
        return f"Failed to resolve escalation #{escalation_id}: {result.get('message', 'Unknown error')}"
    except Exception as e:
        return f"Error resolving escalation #{escalation_id}: {e}"


# ---------------------------------------------------------------------------
# Employee Tools
# ---------------------------------------------------------------------------

@tool
def tool_get_employees() -> str:
    """
    Get a list of all employees in the system with their basic information
    (name, employee ID, department, designation).
    """
    try:
        from db_schema_v2 import get_all_employees
        employees = get_all_employees()
        if not employees:
            return "No employees found in the system."

        lines = [f"Total employees: {len(employees)}\n"]
        for emp in employees:
            # get_all_employees returns dicts or tuples depending on version
            if isinstance(emp, dict):
                lines.append(
                    f"• {emp.get('full_name', 'N/A')} | ID: {emp.get('employee_id', 'N/A')} | "
                    f"Dept: {emp.get('department', 'N/A')} | Role: {emp.get('designation', 'N/A')}"
                )
            else:
                lines.append(str(emp))
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching employees: {e}"


@tool
def tool_get_employee_profile(identifier: str) -> str:
    """
    Get the detailed profile of a single employee.
    Args:
        identifier: Either the employee's username (email) or employee_id (e.g. EMP001).
    """
    try:
        from db_schema_v2 import get_employee
        # Try by username first, then by employee_id
        emp = get_employee(username=identifier) or get_employee(employee_id=identifier)
        if not emp:
            return f"No employee found for identifier '{identifier}'."
        # Mask sensitive fields
        safe = {k: v for k, v in emp.items() if k not in ("password", "password_hash")}
        lines = ["Employee Profile:"]
        for k, v in safe.items():
            lines.append(f"  {k.replace('_', ' ').title()}: {v}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching employee profile: {e}"


# ---------------------------------------------------------------------------
# Logs & Documents Tools
# ---------------------------------------------------------------------------

@tool
def tool_get_query_logs(limit: int = 20) -> str:
    """
    Get recent chatbot query logs.
    Args:
        limit: Number of recent logs to return (default 20, max 100).
    """
    try:
        from db import get_logs
        logs = get_logs()
        if not logs:
            return "No query logs found."
        limit = min(limit, 100)
        recent = logs[:limit]
        lines = [f"Showing {len(recent)} most recent query log(s):\n"]
        for log in recent:
            # log: (id, user, question, answer, timestamp)
            log_id, user, question, answer, ts = log[0], log[1], log[2], log[3], log[4]
            preview = answer[:80] + "..." if len(answer) > 80 else answer
            lines.append(f"• [{ts}] User: {user} | Q: {question} | A: {preview}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching query logs: {e}"


@tool
def tool_get_documents() -> str:
    """
    Get a list of all HR policy documents currently indexed in the knowledge base.
    """
    try:
        from db import get_all_documents
        docs = get_all_documents()
        if not docs:
            return "No documents found in the knowledge base."
        lines = [f"Indexed documents ({len(docs)}):\n"]
        for doc in docs:
            doc_id, name, uploaded_at, avg_tokens = doc[0], doc[1], doc[2], doc[3]
            lines.append(
                f"• ID {doc_id} | {name} | Uploaded: {str(uploaded_at)[:10]} | "
                f"Avg tokens/chunk: {avg_tokens:.1f}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching documents: {e}"


@tool
def tool_get_dashboard_stats() -> str:
    """
    Get a high-level dashboard summary: total employees, pending leaves,
    open escalations, and indexed documents.
    """
    try:
        from db_schema_v2 import get_all_employees
        from workflow_engine import LeaveWorkflowEngine
        from db import get_all_documents

        employees    = get_all_employees()
        pending_leaves = LeaveWorkflowEngine.get_pending_requests()
        all_esc      = LeaveWorkflowEngine.get_all_escalations()
        open_esc     = [e for e in all_esc if e["status"] == "pending"]
        docs         = get_all_documents()

        return (
            f"📊 HRFLUX Admin Dashboard Summary\n"
            f"────────────────────────────────\n"
            f"👥 Total Employees:       {len(employees)}\n"
            f"📋 Pending Leave Requests: {len(pending_leaves)}\n"
            f"🚨 Open Escalations:      {len(open_esc)}\n"
            f"📂 Indexed Documents:      {len(docs)}"
        )
    except Exception as e:
        return f"Error fetching dashboard stats: {e}"


# Expose as a list for the agent
admin_bot_tools = [
    tool_get_pending_leaves,
    tool_approve_leave,
    tool_reject_leave,
    tool_get_escalations,
    tool_resolve_escalation,
    tool_get_employees,
    tool_get_employee_profile,
    tool_get_query_logs,
    tool_get_documents,
    tool_get_dashboard_stats,
]
