from __future__ import annotations

from typing import Any, Dict

from langchain_groq import ChatGroq

from config import get_current_api_key
from vector_store import get_or_create_collection

from .leave_bot import LeaveBot
from .policy_bot import PolicyBot
from .docu_bot import DocuBot
from .escalation_bot import EscalationBot


def create_agents(
    db_session: Any = None,
    vector_store: Any = None,
    llm: Any = None,
    embeddings: Any = None,
) -> Dict[str, Any]:
    """
    Instantiate all HRFlux agents with shared dependencies.

    Returns:
        {
          "leave": LeaveBot(...),
          "policy": PolicyBot(...),
          "docu": DocuBot(...),
          "escalation": EscalationBot(...),
        }
    """
    # Lazy defaults
    llm = llm or ChatGroq(
        model_name="llama-3.3-70b-versatile",
        temperature=0.2,
        groq_api_key=get_current_api_key(),
    )

    # For PolicyBot we expect a vector store / collection.
    vector_store = vector_store or get_or_create_collection()

    agents = {
        "leave": LeaveBot(agent_name="LeaveBot", db_session=db_session, vector_store=None, llm=llm),
        "policy": PolicyBot(
            agent_name="PolicyBot",
            db_session=db_session,
            vector_store=vector_store,
            llm=llm,
            embeddings=embeddings,
        ),
        "docu": DocuBot(agent_name="DocuBot", db_session=db_session, vector_store=None, llm=llm),
        "escalation": EscalationBot(
            agent_name="EscalationBot", db_session=db_session, vector_store=None, llm=llm
        ),
    }
    return agents

