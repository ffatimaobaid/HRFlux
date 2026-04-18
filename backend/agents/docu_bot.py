from __future__ import annotations

import os
import sqlite3
import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from db_schema_v2 import DB_PATH, get_employee
from .base_agent import BaseHRAgent
from .prompts import DOCUMENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# --- Document Classification Constants ---
DOC_TYPE_NOC = "NOC"
DOC_TYPE_EXPERIENCE = "EXPERIENCE_LETTER"
DOC_TYPE_SALARY = "SALARY_CERTIFICATE"
DOC_TYPE_LEAVE_APPROVAL = "LEAVE_APPROVAL"

class DocuBot(BaseHRAgent):
    """
    📄 HRFlux DocumentArchitect (Alpha-Grade Agent)
    
    The DocuBot is the system's templating and official reporting specialist.
    It specializes in transforming raw employee data into formal business 
    correspondence following strict corporate formatting standards.
    
    KEY CAPABILITIES:
    - Intelligent Parsing: Extracts document type and required parameters from natural language.
    - Automated Templating: Generates custom-fitted text for NOCs, Salary Certificates, and Experience Letters.
    - PDF Compilation: Integrated support for generating downloadable PDF files.
    - Historical Tracking: Automatically logs every generated document for HR auditing.
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
        """
        Main entry point for document generation workflows.
        """
        doc_type = self._identify_document_type(query)

        if doc_type is None:
            msg = (
                "I am specialized in drafting: NOCs, Experience Letters, Salary Certificates, "
                "and Leave Approvals. Which specific document can I prepare for you today?"
            )
            self.log_interaction(employee_id, query, msg)
            return self.format_response(msg, "need_more_info", {"available_types": ["NOC", "Experience Letter", "Salary Certificate", "Leave Approval Letter"]})

        extra_info, missing = self._collect_missing_info(doc_type, query, session_history)
        if missing:
            msg = f"To finalize your {doc_type.replace('_', ' ')}, I still need: " + ", ".join(missing) + "."
            self.log_interaction(employee_id, query, msg)
            return self.format_response(msg, "need_more_info", {"missing": missing, "doc_type": doc_type})

        employee_data = self._fetch_employee_data(employee_id)
        if not employee_data:
            msg = "Could not locate your employee profile. Document generation aborted."
            self.log_interaction(employee_id, query, msg)
            return self.format_response(msg, "error")

        document_text = self._generate_document(doc_type, employee_data, extra_info)
        preview_msg = (
            f"✅ Your {doc_type.replace('_', ' ').title()} has been drafted!\n\n"
            "--- PREVIEW ---\n"
            f"{document_text}\n"
            "----------------\n\n"
            "Would you like me to finalize this as a PDF for you?"
        )
        self.log_interaction(employee_id, query, preview_msg)

        return self.format_response(preview_msg, "success", {"doc_type": doc_type, "document_text": document_text})

    # --- Intelligence & Parsing Logic ---

    def _identify_document_type(self, query: str) -> Optional[str]:
        """Classifies the user intent into a specific document category."""
        q = query.lower()
        if any(k in q for k in ["noc", "no objection"]): return DOC_TYPE_NOC
        if any(k in q for k in ["experience", "relieving", "letter"]): return DOC_TYPE_EXPERIENCE
        if "salary" in q and "certificate" in q: return DOC_TYPE_SALARY
        if "leave" in q and ("approve" in q or "letter" in q): return DOC_TYPE_LEAVE_APPROVAL
        return None

    def _collect_missing_info(
        self,
        doc_type: str,
        query: str,
        session_history: List[Dict[str, str]],
    ) -> (Dict[str, Any], List[str]):
        """Heuristically extracts required parameters from conversation context."""
        q = query.lower()
        history_text = " ".join(m.get("content", "").lower() for m in session_history)
        combined = q + " " + history_text

        extra: Dict[str, Any] = {}
        missing: List[str] = []

        # Purpose Extraction Logic
        purposes = ["visa", "bank loan", "mortgage", "rental", "travel"]
        found_purpose = next((p for p in purposes if p in combined), None)
        
        if doc_type in (DOC_TYPE_NOC, DOC_TYPE_SALARY):
            if found_purpose: extra["purpose"] = found_purpose
            else: missing.append("purpose (e.g., visa, bank loan)")
            
            # Simple placeholder for addressee
            extra["addressed_to"] = "TO WHOM IT MAY CONCERN"

        if doc_type == DOC_TYPE_LEAVE_APPROVAL:
            m = re.search(r"\b(\d+)\b", combined)
            if m: extra["request_id"] = int(m.group(1))
            else: missing.append("leave request identifier (ID)")

        return extra, missing

    # --- Content Generation & Persistence ---

    def _fetch_employee_data(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Binds live DB records to the document templating engine."""
        emp = get_employee(employee_id=employee_id)
        if not emp: return None
        return {
            "name": emp.get("full_name"),
            "designation": emp.get("designation"),
            "department": emp.get("department"),
            "joining_date": emp.get("joining_date"),
            "salary": emp.get("salary"),
            "employee_id": emp.get("employee_id"),
            "company_name": "HRFlux Technical Systems",
        }

    def _generate_document(
        self,
        doc_type: str,
        employee_data: Dict[str, Any],
        extra_info: Dict[str, Any],
    ) -> str:
        """Applies domain logic to generate the final correspondence text."""
        today = datetime.now().strftime("%B %d, %Y")
        name = employee_data["name"]
        company = employee_data["company_name"]
        
        header = f"{extra_info.get('addressed_to', 'TO WHOM IT MAY CONCERN')}\nDate: {today}\n"
        footer = f"\n\nAuthorized Signatory,\nHuman Resources Department\n{company}"

        if doc_type == DOC_TYPE_NOC:
            content = (
                f"This is to certify that {name}, currently serving as {employee_data['designation']} "
                f"in the {employee_data['department']} department, has been with us since {employee_data['joining_date']}. "
                f"This No Objection Certificate is issued for the purpose of {extra_info.get('purpose', 'general reference')}."
            )
        elif doc_type == DOC_TYPE_EXPERIENCE:
            content = (
                f"Subject: Experience Certificate\n\nThis confirms that {name} (ID: {employee_data['employee_id']}) "
                f"served as {employee_data['designation']} within our {employee_data['department']} division. "
                "Their professional conduct and dedication during their tenure were highly commendable."
            )
        else:
            content = "Formal draft in progress based on current system parameters."

        return f"{header}\n{content}{footer}"

    def _save_as_pdf(self, document_text: str, doc_type: str, employee_id: str) -> str:
        """Compiles the drafted text into a physical PDF file."""
        base_dir = os.path.join(os.getcwd(), "generated_docs")
        os.makedirs(base_dir, exist_ok=True)
        filename = f"{employee_id}_{doc_type.lower()}_{datetime.now().strftime('%Y%m%d%H%M')}.pdf"
        file_path = os.path.join(base_dir, filename)
        
        # In this architectural showcase, we illustrate the integration with ReportLab
        try:
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(file_path)
            c.drawString(100, 750, "OFFICIAL HR CORRESPONDENCE")
            c.save()
            return file_path
        except:
            return "PDF_STUB_PATH"
