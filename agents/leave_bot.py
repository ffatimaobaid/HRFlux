from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import sqlite3

from db_schema_v2 import DB_PATH, get_leave_balance, update_leave_balance
from workflow_engine import LeaveWorkflowEngine, get_employee_leave_history

from .base_agent import BaseHRAgent
from .prompts import LEAVE_SYSTEM_PROMPT


INTENT_CHECK_BALANCE = "CHECK_BALANCE"
INTENT_APPLY_LEAVE = "APPLY_LEAVE"
INTENT_CHECK_STATUS = "CHECK_STATUS"
INTENT_CANCEL_LEAVE = "CANCEL_LEAVE"


class LeaveBot(BaseHRAgent):
    """
    LeaveBot – handles all leave-related queries.
    """

    def __init__(
        self,
        agent_name: str = "LeaveBot",
        db_session: Any = None,
        vector_store: Any = None,
        llm: Any = None,
    ) -> None:
        super().__init__(agent_name, db_session, vector_store, llm)

    # Public entrypoint

    def handle(
        self, query: str, employee_id: str, session_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Main handler. Performs lightweight intent + slot extraction and dispatches
        to internal methods, returning a standardized response dict.
        """
        # Basic intent + slot extraction
        intent, slots = self._extract_intent_and_slots(query)

        # Enrich with employee context (not strictly required but may be useful later)
        context = self.get_employee_context(employee_id)

        if intent == INTENT_CHECK_BALANCE:
            message, data = self._check_balance(employee_id)
            self.log_interaction(employee_id, query, message)
            return self.format_response(message, "success", data)

        if intent == INTENT_APPLY_LEAVE:
            missing = []
            leave_type = slots.get("leave_type")
            start_date = slots.get("start_date")
            end_date = slots.get("end_date")
            reason = slots.get("reason") or "Not specified"

            if not leave_type:
                missing.append("leave type (annual, sick, or casual)")
            if not start_date or not end_date:
                missing.append("start and end dates")

            if missing:
                msg = (
                    "To apply for leave I need a bit more information: "
                    + ", ".join(missing)
                    + "."
                )
                self.log_interaction(employee_id, query, msg)
                return self.format_response(msg, "need_more_info", {"missing": missing})

            # Basic past-date check
            if not self._dates_are_valid(start_date, end_date):
                msg = "Your end date must be on or after the start date, and dates cannot be in the distant past."
                self.log_interaction(employee_id, query, msg)
                return self.format_response(msg, "error")

            message, data = self._apply_leave(
                employee_id, leave_type=leave_type, start_date=start_date, end_date=end_date, reason=reason
            )
            self.log_interaction(employee_id, query, message)
            return self.format_response(message, data.get("status", "success"), data)

        if intent == INTENT_CHECK_STATUS:
            message, data = self._check_status(employee_id)
            self.log_interaction(employee_id, query, message)
            return self.format_response(message, "success", data)

        if intent == INTENT_CANCEL_LEAVE:
            request_id = slots.get("request_id")
            if not request_id:
                msg = "Please provide the leave request ID you want to cancel."
                self.log_interaction(employee_id, query, msg)
                return self.format_response(msg, "need_more_info")

            message, data = self._cancel_leave(employee_id, request_id)
            self.log_interaction(employee_id, query, message)
            status = "success" if data.get("cancelled") else "error"
            return self.format_response(message, status, data)

        # Fallback – could not confidently classify
        msg = (
            "I'm LeaveBot and I can help with leave balances, applying for leave, "
            "checking leave status, or cancelling a leave request. Could you please rephrase your request?"
        )
        self.log_interaction(employee_id, query, msg)
        return self.format_response(msg, "uncertain", {"detected_intent": intent})

    # --- Intent & slot extraction ---

    def _extract_intent_and_slots(self, query: str) -> Tuple[str, Dict[str, Any]]:
        q = query.lower()
        slots: Dict[str, Any] = {}

        # Simple intent heuristics
        if any(k in q for k in ["balance", "how many days", "remaining leave", "leaves left"]):
            intent = INTENT_CHECK_BALANCE
        elif any(k in q for k in ["apply for leave", "apply leave", "request leave", "book leave"]):
            intent = INTENT_APPLY_LEAVE
        elif any(k in q for k in ["status", "approved", "rejected", "pending"]) and "leave" in q:
            intent = INTENT_CHECK_STATUS
        elif any(k in q for k in ["cancel", "withdraw"]) and "leave" in q:
            intent = INTENT_CANCEL_LEAVE
        else:
            # Weak guess based on presence of keywords
            if "leave" in q and any(k in q for k in ["from", "to"]):
                intent = INTENT_APPLY_LEAVE
            else:
                intent = "UNKNOWN"

        # Leave type
        if "annual" in q:
            slots["leave_type"] = "annual"
        elif "sick" in q:
            slots["leave_type"] = "sick"
        elif "casual" in q:
            slots["leave_type"] = "casual"

        # Request ID (for cancellation)
        m = re.search(r"\b(\d+)\b", q)
        if m:
            slots["request_id"] = int(m.group(1))

        # Naive date extraction: expect YYYY-MM-DD
        date_matches = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", q)
        if len(date_matches) >= 1:
            slots["start_date"] = date_matches[0]
        if len(date_matches) >= 2:
            slots["end_date"] = date_matches[1]

        # Reason fallback – crude extraction after "because" or "for"
        reason_match = re.search(r"\b(because|for)\b(.+)", q)
        if reason_match:
            slots["reason"] = reason_match.group(2).strip()

        return intent, slots

    # --- Core capabilities ---

    def _check_balance(self, employee_id: str) -> Tuple[str, Dict[str, Any]]:
        balances = get_leave_balance(employee_id)
        if not balances:
            return "I couldn't find your leave balance. Please contact HR.", {"leave_balance": {}}

        msg = (
            "Here is your current leave balance:\n"
            f"- Annual: {balances.get('annual', 0)} days\n"
            f"- Sick: {balances.get('sick', 0)} days\n"
            f"- Casual: {balances.get('casual', 0)} days"
        )
        return msg, {"leave_balance": balances}

    def _apply_leave(
        self,
        employee_id: str,
        leave_type: str,
        start_date: str,
        end_date: str,
        reason: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Submit a leave request using the existing workflow engine.
        """
        # Validate balance using the workflow engine helper
        validation = LeaveWorkflowEngine.validate_leave_request(employee_id, leave_type, start_date, end_date)
        if not validation.get("valid"):
            return validation.get("message", "You do not have enough balance for this leave."), {
                "status": "insufficient_balance",
                "details": validation,
            }

        result = LeaveWorkflowEngine.submit_leave_request(
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
        )

        if not result.get("success"):
            return result.get("message", "Failed to submit leave request."), {
                "status": "error",
                "details": result,
            }

        msg = result.get("message", "Your leave request has been submitted.")
        data = {
            "status": "pending",
            "request_id": result.get("request_id"),
            "details": result,
        }
        return msg, data

    def _check_status(self, employee_id: str) -> Tuple[str, Dict[str, Any]]:
        history = get_employee_leave_history(employee_id, limit=5)
        if not history:
            return "You don't have any recent leave requests.", {"requests": []}

        lines = ["Here are your recent leave requests:"]
        requests_data = []
        for row in history:
            # id, employee_id, leave_type, start_date, end_date, total_days, reason, status, approver_id, approved_at, comments, submitted_at
            (
                req_id,
                emp_id,
                leave_type,
                start_date,
                end_date,
                total_days,
                reason,
                status,
                approver_id,
                approved_at,
                comments,
                submitted_at,
            ) = row
            line = f"- ID {req_id}: {leave_type} from {start_date} to {end_date} ({status})"
            lines.append(line)
            requests_data.append(
                {
                    "id": req_id,
                    "leave_type": leave_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_days": total_days,
                    "status": status,
                    "reason": reason,
                }
            )

        return "\n".join(lines), {"requests": requests_data}

    def _cancel_leave(self, employee_id: str, request_id: int) -> Tuple[str, Dict[str, Any]]:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                """
                SELECT id, employee_id, leave_type, total_days, status
                FROM leave_requests_v2
                WHERE id = ?
                """,
                (request_id,),
            )
            row = c.fetchone()
            if not row:
                return "No leave request found with that ID.", {"cancelled": False}

            _id, emp_id, leave_type, total_days, status = row
            if str(emp_id) != str(employee_id):
                return "You can only cancel your own leave requests.", {"cancelled": False}

            if status.lower() not in ("pending", "approved"):
                return f"Leave request {request_id} is already {status} and cannot be cancelled.", {
                    "cancelled": False
                }

            # Update status to cancelled
            c.execute(
                """
                UPDATE leave_requests_v2
                SET status = 'cancelled'
                WHERE id = ?
                """,
                (request_id,),
            )
            conn.commit()

            # Optionally restore balance if it had already been deducted on approval.
            # We conservatively restore only if it was approved.
            if status.lower() == "approved":
                balances = get_leave_balance(employee_id) or {}
                current = balances.get(leave_type, 0)
                new_balance = current + int(total_days or 0)
                update_leave_balance(
                    employee_id,
                    leave_type=leave_type,
                    new_balance=new_balance,
                    reason=f"Leave cancelled - Request ID: {request_id}",
                    request_id=request_id,
                )

            msg = f"Leave request {request_id} has been cancelled."
            return msg, {"cancelled": True, "request_id": request_id}
        except Exception as e:
            conn.rollback()
            return f"Failed to cancel leave request: {e}", {"cancelled": False}
        finally:
            conn.close()

    # --- Utilities ---

    def _dates_are_valid(self, start_date: str, end_date: str) -> bool:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if end < start:
                return False
            # Allow slightly backdated requests; hard validation can be tightened later.
            return True
        except ValueError:
            return False

