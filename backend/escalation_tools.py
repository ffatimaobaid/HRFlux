import json
import logging
import sqlite3
import random
from datetime import datetime
from typing import Optional
from langchain_core.tools import tool

from db_schema_v2 import DB_PATH
from db import get_recent_history
from summarizer import generate_escalation_summary

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
    File a formal HR escalation or complaint ticket on behalf of the employee.
    This stores the ticket in the HR system and assigns it to the correct HR officer.
    
    CRITICAL: You MUST NOT call this tool until you have explicitly asked the user 
    for all of the required parameters:
    - incident_category: One of COMPLAINT, HARASSMENT, PAYROLL_ISSUE, POLICY_DISPUTE, TECHNICAL, GENERAL
    - incident_description: A detailed summary of what happened
    - parties_involved: Who was involved? (if none, use "None")
    - urgency_level: One of Low, Medium, High, Critical
    
    If any of these are missing from the conversation, ASK THE USER FIRST. Do not invent answers.
    """
    from db_schema_v2 import get_employee
    
    try:
        emp = get_employee(employee_id=username) or get_employee(username=username)
        employee_id = emp['employee_id'] if emp else None
        
        category = incident_category.upper()
        if category not in CATEGORY_MAP:
            category = "GENERAL"
            
        officer = CATEGORY_MAP[category]
        ticket_id = f"HRF-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        
        full_description = (
            f"Category: {category}\n"
            f"Urgency: {urgency_level.upper()}\n"
            f"Parties Involved: {parties_involved}\n"
            f"Details: {incident_description}"
        )
        
        # 1. Fetch recent history for summarization
        history_tuples = get_recent_history(username, limit=5)
        
        # 2. Generate AI Context Summary
        summary = generate_escalation_summary(username, incident_description, history_tuples)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 3. Store in chat_escalations
        c.execute("""
            INSERT INTO chat_escalations 
            (employee_id, username, query, full_history, reason, sensitivity_score, status, conversation_summary)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (
            employee_id,
            username,
            incident_description,          # The core incident text
            full_description,              # Full structured breakdown
            f"[{ticket_id}] {category} - {urgency_level.upper()} urgency. Assigned to: {officer}",
            1.0 if urgency_level.upper() in ("HIGH", "CRITICAL") else 0.5,
            summary
        ))
        
        db_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return json.dumps({
            "status": "success",
            "message": f"Your HR ticket has been filed successfully and assigned to {officer}.",
            "ticket_id": ticket_id,
            "db_id": db_id,
            "assigned_officer": officer,
            "category": category,
            "urgency": urgency_level.upper(),
            "note": "You can check your ticket status by asking 'show my escalations'."
        })
        
    except Exception as e:
        logger.error(f"Failed to file escalation: {e}")
        return json.dumps({"error": str(e)})


@tool
def tool_get_my_escalations(username: str) -> str:
    """
    Retrieve the status of all HR escalation tickets filed by this employee.
    Use this when the employee asks about their complaint status, ticket status,
    or wants to see their open/resolved escalations.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT reason, status, resolution_notes, created_at, resolved_at
            FROM chat_escalations
            WHERE username = ?
            ORDER BY created_at DESC
            LIMIT 10
        """, (username,))
        
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            return json.dumps({
                "message": "You have no escalation tickets on record."
            })
        
        tickets = []
        for r in rows:
            tickets.append({
                "reason_summary": r[0],
                "status": r[1],
                "resolution_notes": r[2] or "Pending HR review",
                "filed_at": r[3],
                "resolved_at": r[4] or "Not yet resolved"
            })
        
        return json.dumps({
            "total": len(tickets),
            "tickets": tickets
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch escalations for {username}: {e}")
        return json.dumps({"error": str(e)})


escalation_bot_tools = [tool_file_escalation, tool_get_my_escalations]
