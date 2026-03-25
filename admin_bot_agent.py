"""
Admin Bot Agent
LangGraph ReAct agent for the HRFLUX Admin chatbot.
Equipped with admin-level tools and a strict admin-domain system prompt.
"""

import logging
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from chat_groq_with_retry import create_chat_groq_with_retry
from admin_bot_tools import admin_bot_tools

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

ADMIN_SYSTEM_PROMPT = """
You are HRFlux AdminBot, an intelligent assistant exclusively for HR administrators.
You have access to live HR system data via tools. Use them to answer questions accurately.

YOUR CAPABILITIES:
- View and act on pending leave requests (approve / reject)
- View and resolve HR escalations
- Look up employee profiles and full employee list
- Retrieve chatbot query logs for auditing
- List indexed HR policy documents
- Give a live dashboard summary of KPIs

RULES:
1. Always call a tool to get live data rather than guessing or making up numbers.
2. When asked to approve/reject a leave or resolve an escalation, confirm the action in your reply.
3. If the admin asks about a specific employee, use tool_get_employee_profile with their username or ID.
4. For a general overview/summary, call tool_get_dashboard_stats first.
5. Present data in a clean, readable format — use bullet points and headings where helpful.
6. You are restricted to HR administration topics only. Politely decline anything unrelated.
7. Be concise and professional. Avoid unnecessary padding.
""".strip()

# ---------------------------------------------------------------------------
# Agent Setup
# ---------------------------------------------------------------------------

def _build_agent():
    """Build and return the admin ReAct agent with memory."""
    llm = create_chat_groq_with_retry(
        model_name="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=1024,
    )
    memory = MemorySaver()
    agent = create_react_agent(
        llm,
        tools=admin_bot_tools,
        checkpointer=memory,
        prompt=ADMIN_SYSTEM_PROMPT,
    )
    return agent


# Singleton agent instance
_admin_agent = None

def _get_agent():
    global _admin_agent
    if _admin_agent is None:
        _admin_agent = _build_agent()
    return _admin_agent


# ---------------------------------------------------------------------------
# Public Interface
# ---------------------------------------------------------------------------

def invoke_admin_agent(query: str, thread_id: str = "admin_session") -> str:
    """
    Invoke the admin bot with a natural-language query.
    Returns the agent's response as a plain string.

    Args:
        query: Admin's question or command.
        thread_id: Conversation thread ID for memory continuity (default: one shared admin session).
    """
    try:
        agent = _get_agent()
        config = {"configurable": {"thread_id": thread_id}}
        result = agent.invoke(
            {"messages": [HumanMessage(content=query)]},
            config=config,
        )
        last_message = result["messages"][-1]
        return last_message.content or "I completed the action but have nothing further to add."
    except Exception as e:
        logger.error(f"AdminBot error: {e}", exc_info=True)
        return f"⚠️ AdminBot encountered an error: {str(e)}"
