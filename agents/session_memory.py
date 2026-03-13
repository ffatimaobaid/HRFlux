from __future__ import annotations

from typing import Dict, List


class SessionMemory:
    """
    In-memory per-employee session memory.

    NOTE: This is process-local and suitable for demos / single-process runs.
    For production, replace with a persistent store (Redis, DB, etc.).
    """

    def __init__(self) -> None:
        self._store: Dict[str, List[Dict[str, str]]] = {}

    def add_message(self, employee_id: str, role: str, content: str) -> None:
        history = self._store.setdefault(employee_id, [])
        history.append({"role": role, "content": content})

    def get_history(self, employee_id: str, last_n: int = 10) -> List[Dict[str, str]]:
        history = self._store.get(employee_id, [])
        if last_n <= 0:
            return list(history)
        return history[-last_n:]

    def clear(self, employee_id: str) -> None:
        self._store.pop(employee_id, None)

