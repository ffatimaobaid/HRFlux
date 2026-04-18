from __future__ import annotations

import logging
from typing import List, Optional, Sequence, Annotated
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from chat_groq_with_retry import create_chat_groq_with_retry
from escalation_tools import escalation_bot_tools

logger = logging.getLogger(__name__)

# --- Encapsulated System Prompt ---
ESCALATION_SYSTEM_PROMPT = """
AGENT_IDENTITY: HRFlux CrisisResolution (Level 2)
ROLE: Sentiment-Aware Triage and Escalation Specialist.
CORE_MANDATES:
1. Sentiment Analysis: Detect and de-escalate frustration or workplace grievances.
2. Triage & Routing: Summarize complex issues for HR Business Partners.
3. Confidentiality: Maintain the highest standards of privacy.
BEHAVIOR_RULES:
- Empathetic but neutral professional language.
- DO NOT promise specific outcomes.
""".strip()

# --- State Schema ---
class EscalationBotState(TypedDict):
    """The State shared across EscalationBot nodes."""
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]
    username: str

# --- Node Implementation ---

def escalation_bot_node(state: EscalationBotState):
    """The core reasoning node for the Crisis & Escalation Specialist."""
    llm = create_chat_groq_with_retry(
        model_name="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=4096,
    )
    llm_with_tools = llm.bind_tools(escalation_bot_tools)
    
    messages = list(state["messages"])
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages.insert(0, SystemMessage(content=ESCALATION_SYSTEM_PROMPT))
        
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# --- Graph Assembly ---

def compile_escalation_bot_graph():
    workflow = StateGraph(EscalationBotState)
    workflow.add_node("escalation_bot", escalation_bot_node)
    workflow.add_node("tools", ToolNode(escalation_bot_tools))
    workflow.add_edge(START, "escalation_bot")
    workflow.add_conditional_edges("escalation_bot", tools_condition)
    workflow.add_edge("tools", "escalation_bot")
    return workflow.compile()

escalation_bot_agent = compile_escalation_bot_graph()

def invoke_escalation_agent(query: str, username: str = "Active Employee") -> str:
    state = {"messages": [HumanMessage(content=query)], "username": username}
    result = escalation_bot_agent.invoke(state)
    return result["messages"][-1].content
