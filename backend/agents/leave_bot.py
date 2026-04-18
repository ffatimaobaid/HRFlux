from __future__ import annotations

import re
import sqlite3
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

from db_schema_v2 import DB_PATH, get_leave_balance, update_leave_balance
from workflow_engine import LeaveWorkflowEngine, get_employee_leave_history

from .base_agent import BaseHRAgent
from .prompts import LEAVE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# --- Intent Identifiers ---
INTENT_CHECK_BALANCE = "CHECK_BALANCE"
INTENT_APPLY_LEAVE = "APPLY_LEAVE"
INTENT_CHECK_STATUS = "CHECK_STATUS"
INTENT_CANCEL_LEAVE = "CANCEL_LEAVE"

class LeaveBot(BaseHRAgent):
    """
    🏝️ HRFlux LeaveSpecialist (Alpha-Grade Agent)
    
    The LeaveBot is the system's operational expert for time-off management.
    It combines natural language understanding with strict database logic
    to manage the lifecycle of an employee's leave requests.
    
    KEY CAPABILITIES:
    - Real-time Balance Lookups: Precision queries into SQLite leave tables.
    - Application Processing: Automated validation of dates and balance sufficiency.
    - Historical Auditing: Retrieval of past leave entries for transparency.
    - Lifecycle Management: Cancellations and automated balance restorations.
    """

    def __init__(
        self,
        agent_name: str = "LeaveBot",
        db_session: Any = None,
        vector_store: Any = None,
        llm: Any = None,
    ) -> None:
        super().__init__(agent_name, db_session, vector_store, llm)

    def handle(
        self, query: str, employee_id: str, session_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Processes leave queries by performing slot extraction followed by logical execution.
        """
        # Step 1: Intelligent Slot Extraction (NLP)
        intent, slots = self._extract_intent_and_slots(query)

        # Step 2: Intent Dispatching
        if intent == INTENT_CHECK_BALANCE:
            message, data = self._check_balance(employee_id)
            self.log_interaction(employee_id, query, message)
            return self.format_response(message, "success", data)

        if intent == INTENT_APPLY_LEAVE:
            return self._process_application(employee_id, query, slots)

        if intent == INTENT_CHECK_STATUS:
            message, data = self._check_status(employee_id)
            self.log_interaction(employee_id, query, message)
            return self.format_response(message, "success", data)

        if intent == INTENT_CANCEL_LEAVE:
            return self._process_cancellation(employee_id, query, slots)

        # Fallback for uncertain intents
        msg = (
            "I'm LeaveBot. I can assist you with balance inquiries, leave applications, "
            "and history checks. Could you please clarify your request?"
        )
        return self.format_response(msg, "uncertain", {"detected_intent": intent})

    # --- Core Operational Methods ---

    def _check_balance(self, employee_id: str) -> Tuple[str, Dict[str, Any]]:
        """Retrieves and formats leave distribution for an employee."""
        balances = get_leave_balance(employee_id)
        if not balances:
            return "Unable to locate leave record. Please verify your ID with HR.", {}

        msg = (
            "📊 **Current Leave Distribution**:\n"
            f"• Annual: {balances.get('annual', 0)} days\n"
            f"• Sick: {balances.get('sick', 0)} days\n"
            f"• Casual: {balances.get('casual', 0)} days"
        )
        return msg, {"leave_balance": balances}

    def _process_application(self, employee_id: str, query: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        """Validates and submits a formal leave request."""
        missing = []
        if not slots.get("leave_type"): missing.append("leave type")
        if not slots.get("start_date") or not slots.get("end_date"): missing.append("period dates")

        if missing:
            msg = f"To finalize your request, I need: {', '.join(missing)}."
            return self.format_response(msg, "need_more_info")

        if not self._dates_are_valid(slots["start_date"], slots["end_date"]):
            return self.format_response("Invalid date range. End date must be after start date.", "error")

        # Logical Execution via Workflow Engine
        validation = LeaveWorkflowEngine.validate_leave_request(
            employee_id, slots["leave_type"], slots["start_date"], slots["end_date"]
        )
        if not validation.get("valid"):
            return self.format_response(validation.get("message", "Insufficient balance."), "error")

        result = LeaveWorkflowEngine.submit_leave_request(
            employee_id, slots["leave_type"], slots["start_date"], slots["end_date"], slots.get("reason", "N/A")
        )
        
        msg = f"✅ Success! Your {slots['leave_type']} leave request has been submitted (ID: {result.get('request_id')})."
        return self.format_response(msg, "success", {"request_id": result.get("request_id")})

    def _process_cancellation(self, employee_id: str, query: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        """Reverses a pending or approved leave request."""
        req_id = slots.get("request_id")
        if not req_id:
            return self.format_response("Please provide the ID of the request you wish to cancel.", "need_more_info")

        conn = sqlite3.connect(DB_PATH)
        try:
            c = conn.cursor()
            c.execute("SELECT status, leave_type, total_days FROM leave_requests_v2 WHERE id = ? AND employee_id = ?", (req_id, employee_id))
            row = c.fetchone()
            if not row: return self.format_response("Request not found.", "error")
            
            status, l_type, days = row
            if status.lower() not in ("pending", "approved"):
                return self.format_response(f"Request {req_id} is '{status}' and cannot be altered.", "error")

            c.execute("UPDATE leave_requests_v2 SET status = 'cancelled' WHERE id = ?", (req_id,))
            conn.commit()
            
            # Restore balance if it was already marked as approved
            if status.lower() == "approved":
                b = get_leave_balance(employee_id) or {}
                update_leave_balance(employee_id, l_type, b.get(l_type, 0) + int(days), f"Cancelled ID: {req_id}")

            return self.format_response(f"Request {req_id} has been successfully cancelled.", "success")
        except Exception as e:
            return self.format_response(f"Cancellation failure: {str(e)}", "error")
        finally:
            conn.close()

    def _check_status(self, employee_id: str) -> Tuple[str, Dict[str, Any]]:
        """Retrieves recent request history."""
        history = get_employee_leave_history(employee_id, limit=3)
        if not history: return "No recent leave activity found.", {}

        lines = ["📅 **Recent Leave History**:"]
        for r in history:
            lines.append(f"- ID {r[0]}: {r[2]} ({r[3]} to {r[4]}) → **{r[7]}**")
        return "\n".join(lines), {"history": history}

    # --- Intelligence Helpers ---

    def _extract_intent_and_slots(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """A lightweight NLU pass to identify parameters."""
        q = query.lower()
        slots: Dict[str, Any] = {}
        
        # Intent Heuristics
        if any(k in q for k in ["balance", "remaining", "how many"]): intent = INTENT_CHECK_BALANCE
        elif any(k in q for k in ["apply", "request", "take"]): intent = INTENT_APPLY_LEAVE
        elif any(k in q for k in ["history", "status", "pending"]): intent = INTENT_CHECK_STATUS
        elif any(k in q for k in ["cancel", "delete", "withdraw"]): intent = INTENT_CANCEL_LEAVE
        else: intent = "UNKNOWN"

        # Parameter Extraction (Leave Type)
        for lt in ["annual", "sick", "casual"]:
            if lt in q: slots["leave_type"] = lt
            
        # Parameter Extraction (ID)
        m = re.search(r"\b(\d+)\b", q)
        if m: slots["request_id"] = int(m.group(1))

        # Parameter Extraction (Dates: YYYY-MM-DD)
        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", q)
        if dates: slots["start_date"] = dates[0]
        if len(dates) > 1: slots["end_date"] = dates[1]

        return intent, slots

    def _dates_are_valid(self, start: str, end: str) -> bool:
        """Structural validation of date strings."""
        try:
            s_dt = datetime.strptime(start, "%Y-%m-%d")
            e_dt = datetime.strptime(end, "%Y-%m-%d")
            return e_dt >= s_dt
        except Exception:
            return False
