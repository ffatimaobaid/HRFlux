import json
import logging
import sqlite3
import random
from datetime import datetime, timedelta
from typing import Optional
from langchain_core.tools import tool

from db_schema_v2 import DB_PATH

logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    "COMPLAINT": "HR Officer <hr@company.com>",
    "PAYROLL_ISSUE": "Payroll Officer <payroll@company.com>",
    "HARASSMENT": "Senior HR Manager <senior.hr@company.com>",
    "POLICY_DISPUTE": "HR Policy Specialist <policy.hr@company.com>",
    "TECHNICAL": "IT Support <it.support@company.com>",
    "GENERAL": "HR Helpdesk <helpdesk@company.com>",
}

@tool
def tool_file_escalation(
    username: str, 
    incident_category: str, 
    incident_description: str, 
    parties_involved: str,
    urgency_level: str
) -> str:
    """
    File a formal HR escalation or complaint ticket.
    
    CRITICAL: You MUST NOT call this tool until you have explicitly asked the user 
    for all of the required parameters:
    - incident_category (e.g., COMPLAINT, HARASSMENT, PAYROLL_ISSUE)
    - incident_description (A detailed summary of what happened)
    - parties_involved (Who was involved? If none, put "None")
    - urgency_level (Low, Medium, High, Critical)
    
    If any of these are missing from the conversation, ASK THE USER FIRST. Do not invent answers.
    """
    from db_schema_v2 import get_employee
    
    try:
        emp = get_employee(username=username)
        employee_id = emp['employee_id'] if emp else "UNKNOWN"
        
        category = incident_category.upper()
        if category not in CATEGORY_MAP:
            category = "GENERAL"
            
        summary = f"[{urgency_level.upper()}] Parties: {parties_involved}\nDetails: {incident_description}"
        officer = CATEGORY_MAP[category]
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        ticket_id = f"HRF-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        c.execute("""
            INSERT INTO workflow_escalations 
            (request_id, request_type, escalated_to, escalated_from, reason, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (0, category, officer, employee_id, summary, "pending"))
        
        conn.commit()
        conn.close()
        
        return json.dumps({
            "status": "success",
            "message": "Ticket filed successfully.",
            "ticket_id": ticket_id,
            "assigned_officer": officer,
            "category": category
        })
        
    except Exception as e:
        logger.error(f"Failed to file escalation: {e}")
        return json.dumps({"error": str(e)})

escalation_bot_tools = [tool_file_escalation]
