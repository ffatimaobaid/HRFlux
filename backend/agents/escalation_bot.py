from __future__ import annotations

import random
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from langchain_groq import ChatGroq
from config import get_current_api_key
from db_schema_v2 import DB_PATH

from .base_agent import BaseHRAgent
from .prompts import ESCALATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# --- Domain Constants ---
CATEGORY_COMPLAINT = "COMPLAINT"
CATEGORY_PAYROLL = "PAYROLL_ISSUE"
CATEGORY_HARASSMENT = "HARASSMENT"
CATEGORY_POLICY = "POLICY_DISPUTE"
CATEGORY_TECHNICAL = "TECHNICAL"
CATEGORY_GENERAL = "GENERAL"

class EscalationBot(BaseHRAgent):
    """
    🏢 HRFlux EscalationSpecialist (Alpha-Grade Agent)
    
    The EscalationBot is the system's 'Sentiment and Triage' specialist. 
    It is designed to handle high-friction, sensitive, or complex HR issues 
    that require human intervention.
    
    KEY CAPABILITIES:
    - Intent Categorization: Identifies whether an issue is Harassment, Payroll, or a Policy Dispute.
    - Automated Ticketing: Generates unique tracking IDs and logs them into SQLite.
    - Smart Triage: Assigns the correct HR Officer based on the category of the grievance.
    - Status Monitoring: Checks for duplicate or overdue tickets using SLA logic.
    """

    def __init__(
        self,
        agent_name: str = "EscalationBot",
        db_session: Any = None,
        vector_store: Any = None,
        llm: Any = None,
    ) -> None:
        super().__init__(agent_name, db_session, vector_store, llm)
        self.categorizer_llm = llm or ChatGroq(
            model_name="llama-3.3-70b-versatile",
            temperature=0,
            groq_api_key=get_current_api_key(),
        )

    def handle(
        self, query: str, employee_id: str, session_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Main entry point for handling sensitive grievances.
        """
        category = self._categorize_issue(query)
        summary = self._generate_summary(query, session_history)
        officer = self._get_assigned_officer(category)

        # Check for duplicate ticket to avoid spamming the HR team
        existing_ticket = self._find_recent_ticket(employee_id, category)
        if existing_ticket:
            ticket_id = existing_ticket["ticket_id"]
            msg = (
                f"You already have an open ticket [{ticket_id}] for this category. "
                "Please wait for the assigned officer to respond."
            )
            self.log_interaction(employee_id, query, msg)
            return self.format_response(
                msg,
                "duplicate",
                {
                    "ticket_id": ticket_id,
                    "category": category,
                    "assigned_to": existing_ticket["assigned_to"],
                },
            )

        ticket_id = self._create_ticket(employee_id, category, summary, officer)
        sla_hours = self._get_sla_hours(category)

        # Critical Priority Handling
        if category == CATEGORY_HARASSMENT:
            prefix = (
                "🚨 This matter is being treated with the highest priority and sensitivity. "
                "Your ticket has been escalated to senior HR management immediately.\n\n"
            )
        else:
            prefix = ""

        msg = (
            prefix
            + "I have recorded your concern. It has been escalated to the appropriate department.\n"
            f"🎫 **Ticket ID**: {ticket_id}\n"
            f"📋 **Category**: {category}\n"
            f"👤 **Assigned to**: {officer}\n"
            f"⏰ **Response SLA**: {sla_hours} hours\n\n"
            "An HR representative will contact you shortly."
        )

        self.log_interaction(employee_id, query, msg)
        return self.format_response(
            msg,
            "escalated",
            {
                "ticket_id": ticket_id,
                "category": category,
                "assigned_officer": officer,
                "sla_hours": sla_hours,
            },
        )

    # --- Core Intelligence Logic ---

    def _categorize_issue(self, query: str) -> str:
        """Determines the specific HR domain for the escalation."""
        prompt = (
            "Categorize this HR issue into one of: COMPLAINT, PAYROLL_ISSUE, HARASSMENT, "
            "POLICY_DISPUTE, TECHNICAL, GENERAL\n"
            f"Query: {query}\n"
            "Return ONLY the category word."
        )
        try:
            result = self.categorizer_llm.invoke(prompt)
            raw = (getattr(result, "content", None) or str(result)).strip().upper()
            category = raw.split()[0] if raw else CATEGORY_GENERAL
            valid_categories = {
                CATEGORY_COMPLAINT, CATEGORY_PAYROLL, CATEGORY_HARASSMENT,
                CATEGORY_POLICY, CATEGORY_TECHNICAL, CATEGORY_GENERAL
            }
            return category if category in valid_categories else CATEGORY_GENERAL
        except Exception:
            return CATEGORY_GENERAL

    def _get_assigned_officer(self, category: str) -> str:
        """Maps issues to specific HR contacts."""
        fallback = {
            CATEGORY_HARASSMENT: "Senior HR Manager <senior.hr@company.com>",
            CATEGORY_PAYROLL: "Payroll Officer <payroll@company.com>",
            CATEGORY_COMPLAINT: "HR Officer <hr@company.com>",
            CATEGORY_POLICY: "HR Policy Specialist <policy.hr@company.com>",
            CATEGORY_TECHNICAL: "IT Support <it.support@company.com>",
            CATEGORY_GENERAL: "HR Helpdesk <helpdesk@company.com>",
        }

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("SELECT name, email FROM hr_officers WHERE category = ? LIMIT 1", (category,))
            row = c.fetchone()
            if row:
                return f"{row[0]} <{row[1]}>"
        except Exception:
            pass
        finally:
            conn.close()

        return fallback.get(category, fallback[CATEGORY_GENERAL])

    def _create_ticket(self, employee_id: str, category: str, summary: str, assigned_to: str) -> str:
        """Registers a new escalation in the database."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        ticket_id = f"HRF-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        try:
            c.execute(
                """
                INSERT INTO escalations (ticket_id, employee_id, category, summary, assigned_to, status)
                VALUES (?, ?, ?, ?, ?, 'OPEN')
                """,
                (ticket_id, employee_id, category, summary, assigned_to),
            )
            conn.commit()
            return ticket_id
        except Exception:
            conn.rollback()
            return ticket_id
        finally:
            conn.close()

    def _generate_summary(self, query: str, session_history: List[Dict[str, str]]) -> str:
        """Creates a professional summary for the ticket."""
        history_text = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in session_history[-10:]
        )
        prompt = (
            f"{ESCALATION_SYSTEM_PROMPT}\n\n"
            "Create a neutral 2-sentence summary of this employee's issue.\n"
            f"QUERY: {query}\n"
            f"HISTORY: {history_text}\n"
        )
        try:
            result = self.categorizer_llm.invoke(prompt)
            return (getattr(result, "content", None) or str(result)).strip()
        except Exception:
            return query

    def _get_sla_hours(self, category: str) -> int:
        """Determines Response Time Resolution (SLA)."""
        sla_map = {
            CATEGORY_HARASSMENT: 4,
            CATEGORY_PAYROLL: 24,
            CATEGORY_COMPLAINT: 48,
            CATEGORY_POLICY: 48,
            CATEGORY_TECHNICAL: 24
        }
        return sla_map.get(category, 72)

    def _find_recent_ticket(self, employee_id: str, category: str) -> Optional[Dict[str, Any]]:
        """Prevents duplicate ticketing."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                "SELECT ticket_id, assigned_to, created_at FROM escalations "
                "WHERE employee_id = ? AND category = ? AND status = 'OPEN' ORDER BY created_at DESC",
                (employee_id, category),
            )
            row = c.fetchone()
            if row:
                created_dt = datetime.fromisoformat(row[2]) if row[2] else datetime.now()
                if created_dt >= datetime.now() - timedelta(hours=48):
                    return {"ticket_id": row[0], "assigned_to": row[1]}
        except Exception:
            pass
        finally:
            conn.close()
        return None

    # --- Administrative Methods ---

    def resolve_ticket(self, ticket_id: str, resolution_note: str) -> bool:
        """Closes a pending escalation."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                "UPDATE escalations SET status = 'RESOLVED', resolution_note = ?, resolved_at = ? "
                "WHERE ticket_id = ? AND status = 'OPEN'",
                (resolution_note, datetime.now().isoformat(), ticket_id),
            )
            conn.commit()
            return c.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()
