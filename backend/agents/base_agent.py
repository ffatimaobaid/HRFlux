from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from db_schema_v2 import get_employee, get_leave_balance
from db import save_log

logger = logging.getLogger(__name__)

class BaseHRAgent(ABC):
    """
    🏛️ HRFlux Unified Agent Interface (Foundation Class)
    
    BaseHRAgent serves as the architectural blueprint for all specialized 
    HRFlux agents. It enforces a standardized communication protocol 
    (the 'handle' method) while providing shared access to core HR data 
    and auditing layers.
    
    SHARED INFRASTRUCTURE:
    - Standard Response Enveloping (Consistent JSON outputs)
    - Identity-Preserving Logging (Interaction auditing)
    - Reusable Employee Context (Automated profile hydration)
    - Pluggable LLM/VectorStore integration
    """

    def __init__(
        self,
        agent_name: str,
        db_session: Optional[Any] = None,
        vector_store: Optional[Any] = None,
        llm: Optional[Any] = None,
    ) -> None:
        self.agent_name = agent_name
        self.db_session = db_session
        self.vector_store = vector_store
        self.llm = llm

    @abstractmethod
    def handle(
        self, query: str, employee_id: str, session_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        [ABSTRACT] The core reasoning cycle for the agent.
        Must be implemented by every specialized specialist bot.
        """
        raise NotImplementedError

    # --- Shared Utility Core ---

    def format_response(
        self,
        message: str,
        status: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Normalizes the response format for the frontend and Supervisor consumption.
        """
        return {
            "message": message,
            "status": status,
            "data": data or {},
            "agent": self.agent_name,
            "metadata": {
                "engine": "HRFlux-v2",
                "department": self.agent_name.replace("Bot", ""),
                "processed_at": logging.Formatter("%(asctime)s").format(logging.makeLogRecord({}))
            }
        }

    def get_employee_context(self, employee_id: str) -> Dict[str, Any]:
        """
        Hydrates the agent with localized employee data before reasoning.
        """
        profile = get_employee(employee_id=employee_id)
        if not profile: return {}

        balances = get_leave_balance(employee_id) or {}
        return {
            "employee_id": employee_id,
            "full_name": profile.get("full_name"),
            "department": profile.get("department"),
            "designation": profile.get("designation"),
            "joining_date": profile.get("joining_date"),
            "leave_balance": balances
        }

    def log_interaction(
        self,
        employee_id: str,
        query: str,
        response_message: str,
    ) -> None:
        """
        Ensures every agent interaction is recorded for the Admin Audit Trail.
        """
        try:
            save_log(str(employee_id), query, response_message)
        except Exception as e:
            logger.warning(f"Audit Logging Failed for {self.agent_name}: {e}")
