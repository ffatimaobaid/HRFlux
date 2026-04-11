from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from db_schema_v2 import get_employee, get_leave_balance
from db import save_log


class BaseHRAgent(ABC):
    """
    Base class for all HRFlux agents.

    All concrete agents share:
    - Common constructor signature
    - Standard response format
    - Employee context helper
    - Interaction logging
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
        Process an employee query and return a structured response.

        Must return a dict produced by `format_response`.
        """
        raise NotImplementedError

    # Shared helpers

    def format_response(
        self,
        message: str,
        status: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Standard response envelope for all agents.
        """
        return {
            "message": message,
            "status": status,
            "data": data or {},
            "agent": self.agent_name,
        }

    def get_employee_context(self, employee_id: str) -> Dict[str, Any]:
        """
        Fetch basic employee context (profile + leave balance).

        Returns an empty dict if the employee is not found.
        """
        profile = get_employee(employee_id=employee_id)
        if not profile:
            return {}

        balances = get_leave_balance(employee_id) or {}

        return {
            "employee_id": employee_id,
            "full_name": profile.get("full_name"),
            "department": profile.get("department"),
            "designation": profile.get("designation"),
            "joining_date": profile.get("joining_date"),
            "salary": profile.get("salary"),
            "leave_balance": {
                "casual": balances.get("casual", 0),
                "sick": balances.get("sick", 0),
                "annual": balances.get("annual", 0),
            },
        }

    def log_interaction(
        self,
        employee_id: str,
        query: str,
        response_message: str,
    ) -> None:
        """
        Persist a simple interaction log.

        We map employee_id to the existing `logs.user` column.
        """
        try:
            save_log(str(employee_id), query, response_message)
        except Exception:
            # Logging failures must never break the main flow.
            pass

