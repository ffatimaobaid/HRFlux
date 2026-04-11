from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import random
import sqlite3

from langchain_groq import ChatGroq

from config import get_current_api_key
from db_schema_v2 import DB_PATH

from .base_agent import BaseHRAgent
from .prompts import ESCALATION_SYSTEM_PROMPT


CATEGORY_COMPLAINT = "COMPLAINT"
CATEGORY_PAYROLL = "PAYROLL_ISSUE"
CATEGORY_HARASSMENT = "HARASSMENT"
CATEGORY_POLICY = "POLICY_DISPUTE"
CATEGORY_TECHNICAL = "TECHNICAL"
CATEGORY_GENERAL = "GENERAL"


class EscalationBot(BaseHRAgent):
    """
    EscalationBot – handles sensitive/unresolved issues and creates HR tickets.
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
        category = self._categorize_issue(query)
        summary = self._generate_summary(query, session_history)
        officer = self._get_assigned_officer(category)

        # Duplicate ticket check
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

        if category == CATEGORY_HARASSMENT:
            prefix = (
                "This matter is being treated with the highest priority and sensitivity. "
                "Your ticket has been escalated to senior HR management.\n\n"
            )
        else:
            prefix = ""

        msg = (
            prefix
            + "I understand your concern and I've escalated this to our HR team.\n"
            f"🎫 Ticket ID: {ticket_id}\n"
            f"📋 Category: {category}\n"
            f"👤 Assigned to: {officer}\n"
            f"⏰ Expected response within: {sla_hours} hours\n"
            "You'll receive a follow-up from HR soon. Is there anything else I can help you with?"
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

    # --- Core categorization and ticket flow ---

    def _categorize_issue(self, query: str) -> str:
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
            if category not in {
                CATEGORY_COMPLAINT,
                CATEGORY_PAYROLL,
                CATEGORY_HARASSMENT,
                CATEGORY_POLICY,
                CATEGORY_TECHNICAL,
                CATEGORY_GENERAL,
            }:
                return CATEGORY_GENERAL
            return category
        except Exception:
            return CATEGORY_GENERAL

    def _get_assigned_officer(self, category: str) -> str:
        """
        Look up officer from hr_officers table if available, otherwise return a default mapping.
        """
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
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS hr_officers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    name TEXT,
                    email TEXT
                )
                """
            )
            c.execute(
                "SELECT name, email FROM hr_officers WHERE category = ? LIMIT 1",
                (category,),
            )
            row = c.fetchone()
            if row:
                name, email = row
                return f"{name} <{email}>"
        finally:
            conn.close()

        return fallback.get(category, fallback[CATEGORY_GENERAL])

    def _create_ticket(self, employee_id: str, category: str, summary: str, assigned_to: str) -> str:
        """
        Create a ticket in the `escalations` table and return its ticket_id.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        ticket_id = f"HRF-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        try:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS escalations (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ticket_id TEXT UNIQUE,
                  employee_id TEXT,
                  category TEXT,
                  summary TEXT,
                  assigned_to TEXT,
                  status TEXT DEFAULT 'OPEN',
                  resolution_note TEXT,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  resolved_at DATETIME
                )
                """
            )
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
        """
        Use LLM to summarize the issue from the conversation.
        """
        history_text = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in session_history[-10:]
        )
        prompt = (
            f"{ESCALATION_SYSTEM_PROMPT}\n\n"
            "Create a 2-3 sentence neutral summary of the employee's issue based on the query "
            "and the recent conversation.\n\n"
            f"QUERY:\n{query}\n\n"
            f"HISTORY:\n{history_text}\n"
        )
        try:
            result = self.categorizer_llm.invoke(prompt)
            return (getattr(result, "content", None) or str(result)).strip()
        except Exception:
            return query

    def _get_sla_hours(self, category: str) -> int:
        if category == CATEGORY_HARASSMENT:
            return 4
        if category == CATEGORY_PAYROLL:
            return 24
        if category == CATEGORY_COMPLAINT:
            return 48
        if category == CATEGORY_POLICY:
            return 48
        if category == CATEGORY_TECHNICAL:
            return 24
        return 72

    def _find_recent_ticket(self, employee_id: str, category: str) -> Optional[Dict[str, Any]]:
        """
        Find an open ticket for the same employee & category within the last 48 hours.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                """
                SELECT ticket_id, assigned_to, created_at
                FROM escalations
                WHERE employee_id = ? AND category = ? AND status = 'OPEN'
                ORDER BY created_at DESC
                """,
                (employee_id, category),
            )
            row = c.fetchone()
            if not row:
                return None
            ticket_id, assigned_to, created_at = row
            # SQLite stores created_at as text in ISO format by default
            try:
                created_dt = datetime.fromisoformat(created_at)
            except Exception:
                created_dt = datetime.now()
            if created_dt >= datetime.now() - timedelta(hours=48):
                return {"ticket_id": ticket_id, "assigned_to": assigned_to}
            return None
        except Exception:
            return None
        finally:
            conn.close()

    # --- Admin methods ---

    def get_open_tickets(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                """
                SELECT ticket_id, employee_id, category, summary, assigned_to, status, created_at
                FROM escalations
                WHERE status = 'OPEN'
                ORDER BY created_at DESC
                """
            )
            rows = c.fetchall()
            return [
                {
                    "ticket_id": r[0],
                    "employee_id": r[1],
                    "category": r[2],
                    "summary": r[3],
                    "assigned_to": r[4],
                    "status": r[5],
                    "created_at": r[6],
                }
                for r in rows
            ]
        finally:
            conn.close()

    def resolve_ticket(self, ticket_id: str, resolution_note: str) -> bool:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                """
                UPDATE escalations
                SET status = 'RESOLVED',
                    resolution_note = ?,
                    resolved_at = ?
                WHERE ticket_id = ? AND status = 'OPEN'
                """,
                (resolution_note, datetime.now().isoformat(), ticket_id),
            )
            conn.commit()
            return c.rowcount > 0
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_tickets_by_employee(self, employee_id: str) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                """
                SELECT ticket_id, category, summary, assigned_to, status, created_at, resolved_at
                FROM escalations
                WHERE employee_id = ?
                ORDER BY created_at DESC
                """,
                (employee_id,),
            )
            rows = c.fetchall()
            return [
                {
                    "ticket_id": r[0],
                    "category": r[1],
                    "summary": r[2],
                    "assigned_to": r[3],
                    "status": r[4],
                    "created_at": r[5],
                    "resolved_at": r[6],
                }
                for r in rows
            ]
        finally:
            conn.close()

    def get_overdue_tickets(self) -> List[Dict[str, Any]]:
        """
        Tickets where created_at + SLA hours < NOW() and status='OPEN'.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                """
                SELECT ticket_id, employee_id, category, summary, assigned_to, status, created_at
                FROM escalations
                WHERE status = 'OPEN'
                """
            )
            rows = c.fetchall()
            overdue: List[Dict[str, Any]] = []
            for r in rows:
                ticket_id, employee_id, category, summary, assigned_to, status, created_at = r
                try:
                    created_dt = datetime.fromisoformat(created_at)
                except Exception:
                    created_dt = datetime.now()
                sla_hours = self._get_sla_hours(category)
                if created_dt + timedelta(hours=sla_hours) < datetime.now():
                    overdue.append(
                        {
                            "ticket_id": ticket_id,
                            "employee_id": employee_id,
                            "category": category,
                            "summary": summary,
                            "assigned_to": assigned_to,
                            "status": status,
                            "created_at": created_at,
                        }
                    )
            return overdue
        finally:
            conn.close()

