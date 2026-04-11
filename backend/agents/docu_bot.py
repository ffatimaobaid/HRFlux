from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import sqlite3

from db_schema_v2 import DB_PATH, get_employee

from .base_agent import BaseHRAgent
from .prompts import DOCUMENT_SYSTEM_PROMPT


DOC_TYPE_NOC = "NOC"
DOC_TYPE_EXPERIENCE = "EXPERIENCE_LETTER"
DOC_TYPE_SALARY = "SALARY_CERTIFICATE"
DOC_TYPE_LEAVE_APPROVAL = "LEAVE_APPROVAL"


class DocuBot(BaseHRAgent):
    """
    DocuBot – generates standard HR documents (NOC, experience letters, salary certificates, leave approvals).
    """

    def __init__(
        self,
        agent_name: str = "DocuBot",
        db_session: Any = None,
        vector_store: Any = None,
        llm: Any = None,
    ) -> None:
        super().__init__(agent_name, db_session, vector_store, llm)

    def handle(
        self, query: str, employee_id: str, session_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        doc_type = self._identify_document_type(query)

        if doc_type is None:
            msg = (
                "I can generate: NOC, Experience Letter, Salary Certificate, and Leave Approval Letter. "
                "Which one do you need?"
            )
            self.log_interaction(employee_id, query, msg)
            return self.format_response(msg, "need_more_info", {"available_types": ["NOC", "Experience Letter", "Salary Certificate", "Leave Approval Letter"]})

        extra_info, missing = self._collect_missing_info(doc_type, query, session_history)
        if missing:
            msg = "I need a bit more information: " + ", ".join(missing) + "."
            self.log_interaction(employee_id, query, msg)
            return self.format_response(msg, "need_more_info", {"missing": missing, "doc_type": doc_type})

        employee_data = self._fetch_employee_data(employee_id)
        if not employee_data:
            msg = "I couldn't find your employee record. Please contact HR."
            self.log_interaction(employee_id, query, msg)
            return self.format_response(msg, "error")

        document_text = self._generate_document(doc_type, employee_data, extra_info)
        preview_msg = (
            f"Your {doc_type.replace('_', ' ').title()} has been generated! Here's a preview:\n\n"
            f"{document_text}\n\n"
            "Would you like me to save this as a PDF?"
        )
        self.log_interaction(employee_id, query, preview_msg)

        return self.format_response(preview_msg, "success", {"doc_type": doc_type, "document_text": document_text})

    # --- Internal helpers ---

    def _identify_document_type(self, query: str) -> Optional[str]:
        q = query.lower()
        if "noc" in q or "no objection" in q:
            return DOC_TYPE_NOC
        if "experience letter" in q or "experience certificate" in q:
            return DOC_TYPE_EXPERIENCE
        if "salary certificate" in q or ("salary" in q and "certificate" in q):
            return DOC_TYPE_SALARY
        if "leave approval" in q or ("approve" in q and "leave" in q):
            return DOC_TYPE_LEAVE_APPROVAL
        return None

    def _collect_missing_info(
        self,
        doc_type: str,
        query: str,
        session_history: List[Dict[str, str]],
    ) -> (Dict[str, Any], List[str]):
        """
        Collect required fields from query + history.
        """
        q = query.lower()
        history_text = " ".join(m.get("content", "").lower() for m in session_history)
        combined = q + " " + history_text

        extra: Dict[str, Any] = {}
        missing: List[str] = []

        def extract_purpose(text: str) -> Optional[str]:
            # Very light-weight heuristic for purposes
            for kw in ["visa", "bank loan", "loan", "rental", "rent", "embassy"]:
                if kw in text:
                    return kw
            return None

        def extract_addressed_to(text: str) -> Optional[str]:
            # Look for "to <entity>" pattern
            return None  # Keep simple for now; HR can edit manually later.

        if doc_type in (DOC_TYPE_NOC, DOC_TYPE_SALARY):
            purpose = extract_purpose(combined)
            if purpose:
                extra["purpose"] = purpose
            else:
                missing.append("purpose (e.g., bank loan, visa application)")
            addr = extract_addressed_to(combined)
            if addr:
                extra["addressed_to"] = addr
            else:
                missing.append("addressee (e.g., bank name, embassy)")

        if doc_type == DOC_TYPE_EXPERIENCE:
            addr = extract_addressed_to(combined)
            extra["addressed_to"] = addr or "Whom It May Concern"

        if doc_type == DOC_TYPE_LEAVE_APPROVAL:
            # Expect a request id somewhere in text
            import re

            m = re.search(r"\b(\d+)\b", combined)
            if m:
                extra["request_id"] = int(m.group(1))
            else:
                missing.append("leave request ID to approve")

        return extra, missing

    def _fetch_employee_data(self, employee_id: str) -> Optional[Dict[str, Any]]:
        emp = get_employee(employee_id=employee_id)
        if not emp:
            return None

        return {
            "name": emp.get("full_name"),
            "designation": emp.get("designation"),
            "department": emp.get("department"),
            "joining_date": emp.get("joining_date"),
            "salary": emp.get("salary"),
            "employee_id": emp.get("employee_id"),
            "company_name": "HRFlux",  # Can be customized later
        }

    def _generate_document(
        self,
        doc_type: str,
        employee_data: Dict[str, Any],
        extra_info: Dict[str, Any],
    ) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        name = employee_data["name"]
        designation = employee_data["designation"]
        department = employee_data["department"]
        joining_date = employee_data["joining_date"]
        salary = employee_data.get("salary", "N/A")
        employee_id = employee_data["employee_id"]
        company_name = employee_data["company_name"]

        addressed_to = extra_info.get("addressed_to", "TO WHOM IT MAY CONCERN")
        purpose = extra_info.get("purpose", "the stated purpose")

        if doc_type == DOC_TYPE_NOC:
            return (
                f"{addressed_to}\n"
                f"Date: {today}\n\n"
                f"This is to certify that {name}, holding the position of {designation} in the\n"
                f"{department} department at {company_name}, has been a valued employee since {joining_date}.\n"
                f"This No Objection Certificate is issued upon the employee's request for the purpose of {purpose}.\n"
                f"{company_name} has no objection to this matter.\n\n"
                f"Sincerely,\n"
                f"HR Department\n"
                f"{company_name}"
            )

        if doc_type == DOC_TYPE_EXPERIENCE:
            return (
                f"{addressed_to}\n"
                f"Date: {today}\n\n"
                f"This is to certify that {name} (Employee ID: {employee_id}) has been employed\n"
                f"with {company_name} as {designation} in the {department} department since {joining_date}.\n"
                f"During their tenure, they have demonstrated professionalism and dedication to their responsibilities.\n"
                f"We wish them success in their future endeavors.\n\n"
                f"HR Department\n"
                f"{company_name}"
            )

        if doc_type == DOC_TYPE_SALARY:
            return (
                f"{addressed_to}\n"
                f"Date: {today}\n\n"
                f"This is to certify that {name}, employed as {designation} at {company_name}\n"
                f"since {joining_date}, draws a monthly salary of PKR {salary}.\n"
                f"This certificate is issued upon request for {purpose} purposes.\n\n"
                f"HR Department\n"
                f"{company_name}"
            )

        if doc_type == DOC_TYPE_LEAVE_APPROVAL:
            req_id = extra_info.get("request_id", "N/A")
            return (
                f"To Whom It May Concern\n"
                f"Date: {today}\n\n"
                f"This is to confirm that the leave request (ID: {req_id}) submitted by {name},\n"
                f"{designation} in the {department} department at {company_name}, has been approved.\n\n"
                f"HR Department\n"
                f"{company_name}"
            )

        # Fallback
        return "Document type not supported."

    def _ensure_generated_docs_dir(self) -> str:
        base = os.path.join(os.getcwd(), "generated_docs")
        os.makedirs(base, exist_ok=True)
        return base

    def _save_as_pdf(self, document_text: str, doc_type: str, employee_id: str) -> str:
        """
        Save the document as a PDF. Falls back to a .txt file if PDF libraries are unavailable.
        """
        directory = self._ensure_generated_docs_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_type = doc_type.lower()

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas

            file_path = os.path.join(directory, f"{employee_id}_{safe_type}_{timestamp}.pdf")
            c = canvas.Canvas(file_path, pagesize=A4)
            width, height = A4
            y = height - 72  # 1 inch margin
            for line in document_text.splitlines():
                c.drawString(72, y, line)
                y -= 14
                if y < 72:
                    c.showPage()
                    y = height - 72
            c.save()
            return file_path
        except Exception:
            # Fallback to plain text
            file_path = os.path.join(directory, f"{employee_id}_{safe_type}_{timestamp}.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(document_text)
            return file_path

    def _log_document_request(self, employee_id: str, doc_type: str, file_path: str) -> None:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS document_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id TEXT,
                    doc_type TEXT,
                    file_path TEXT,
                    requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'GENERATED'
                )
                """
            )
            c.execute(
                """
                INSERT INTO document_requests (employee_id, doc_type, file_path, status)
                VALUES (?, ?, ?, 'GENERATED')
                """,
                (employee_id, doc_type, file_path),
            )
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()

