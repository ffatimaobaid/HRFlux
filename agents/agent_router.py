from __future__ import annotations

from typing import Any, Dict, List

from langchain_groq import ChatGroq

from config import get_current_api_key


CLASSIFIER_SYSTEM_PROMPT = """
You are an HR query classifier for a company HR assistant. Classify the user query into exactly one of these categories:
- LEAVE: anything about leave requests, leave balance, applying for leave, leave status
- POLICY: questions about HR policies, rules, benefits, working hours, dress code, salary structure
- DOCUMENT: requests for NOC, experience letter, salary certificate, approval memos
- ESCALATION: complaints, sensitive issues, things the bot cannot handle, requests to talk to HR
- OFF_TOPIC: anything NOT related to HR — general knowledge, news, science, coding, math, weather,
  celebrity questions, jokes, recipes, or any topic outside of employment and workplace matters.
  Greetings like "hi" or "hello" should be classified as POLICY (handled naturally), not OFF_TOPIC.

Return ONLY the category word, nothing else.
""".strip()

OFF_TOPIC_MESSAGE = (
    "I'm HRFLUX, your dedicated HR assistant. I can only help with HR-related topics such as:\n"
    "• 🏖️ Leave requests and balance\n"
    "• 📋 HR policies, benefits, and company rules\n"
    "• 📄 Official documents (NOC, experience letter, salary certificate)\n"
    "• 🚨 Employee grievances and escalations\n\n"
    "Please ask me something related to your workplace or HR matters!"
)

CATEGORY_TO_KEY = {
    "LEAVE": "leave",
    "POLICY": "policy",
    "DOCUMENT": "docu",
    "ESCALATION": "escalation",
    "OFF_TOPIC": None,   # handled specially — no agent
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
        Non-HR (OFF_TOPIC) queries are rejected here with a polite explanation.
        """
        category = self._classify(query)

        # Reject off-topic queries immediately
        if category == "OFF_TOPIC":
            return {
                "message": OFF_TOPIC_MESSAGE,
                "status": "off_topic",
                "data": {"category": category},
                "agent": "Router",
            }

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

