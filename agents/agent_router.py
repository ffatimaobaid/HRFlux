from __future__ import annotations

from typing import Any, Dict, List

from langchain_groq import ChatGroq

from config import get_current_api_key


CLASSIFIER_SYSTEM_PROMPT = """
You are an HR query classifier. Classify the user query into exactly one of these categories:
- LEAVE: anything about leave requests, leave balance, applying for leave, leave status
- POLICY: questions about HR policies, rules, benefits, working hours, dress code, salary structure
- DOCUMENT: requests for NOC, experience letter, salary certificate, approval memos
- ESCALATION: complaints, sensitive issues, things the bot cannot handle, requests to talk to HR

Return ONLY the category word, nothing else.
""".strip()


CATEGORY_TO_KEY = {
    "LEAVE": "leave",
    "POLICY": "policy",
    "DOCUMENT": "docu",
    "ESCALATION": "escalation",
}


class AgentRouter:
    """
    LLM-based intent router that delegates queries to the appropriate agent.

    `agents` is a dict with keys: "leave", "policy", "docu", "escalation".
    """

    def __init__(self, agents: Dict[str, Any], llm: ChatGroq | None = None) -> None:
        self.agents = agents
        # Allow passing an LLM instance from outside; otherwise create a default one.
        self.llm = llm or ChatGroq(
            model_name="llama-3.3-70b-versatile",
            temperature=0,
            groq_api_key=get_current_api_key(),
        )

    def _classify(self, query: str) -> str:
        """
        Use the LLM to classify the query into one of the four categories.
        Falls back to ESCALATION on error.
        """
        try:
            messages = [
                {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ]
            result = self.llm.invoke(messages)
            raw = (result.content or "").strip().upper()
            # Take the first word and map to known category
            category = raw.split()[0] if raw else "ESCALATION"
            if category not in CATEGORY_TO_KEY:
                category = "ESCALATION"
            return category
        except Exception:
            return "ESCALATION"

    def route(
        self,
        query: str,
        employee_id: str,
        session_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Route the query to the appropriate agent and return its structured response.
        """
        category = self._classify(query)
        agent_key = CATEGORY_TO_KEY.get(category, "escalation")
        agent = self.agents.get(agent_key)

        if agent is None:
            # Absolute fallback if the agent config is incomplete
            return {
                "message": "Routing error: no agent configured for this query. Please contact HR.",
                "status": "error",
                "data": {"category": category},
                "agent": "Router",
            }

        return agent.handle(query=query, employee_id=employee_id, session_history=session_history)

