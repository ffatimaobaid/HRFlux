from __future__ import annotations

import logging
from typing import List, Optional, Sequence, Annotated
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from chat_groq_with_retry import create_chat_groq_with_retry
from policy_bot_tools import policy_bot_tools

logger = logging.getLogger(__name__)

# --- Encapsulated System Prompt ---
POLICY_SYSTEM_PROMPT = """
AGENT_IDENTITY: HRFlux PolicyAnalyst v3.0
ROLE: RAG-based Domain Expert for Company Regulations and Benefits.
CORE_MANDATES:
1. Grounded Analysis: Synthesize answers exclusively from retrieved vector-store context.
2. Citational Integrity: Always explicitly mention the source document.
3. Ambiguity Resolution: If context is insufficient, politely decline or suggest HR contact.
BEHAVIOR_RULES:
- Avoid hallucinations. 
- Use structured responses.
- Strictly adhere to provided knowledge snippets.
""".strip()

# --- State Schema ---
class PolicyBotState(TypedDict):
    """The State shared across PolicyBot nodes."""
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]
    username: str

# --- Node Implementation ---

def policy_bot_node(state: PolicyBotState):
    """The core reasoning node for the Policy Specialist."""
    llm = create_chat_groq_with_retry(
        model_name="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=4096,
    )
    llm_with_tools = llm.bind_tools(policy_bot_tools)
    
    messages = list(state["messages"])
    # Ensure system prompt is present
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages.insert(0, SystemMessage(content=POLICY_SYSTEM_PROMPT))
        
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# --- Graph Assembly ---

def compile_policy_bot_graph():
    workflow = StateGraph(PolicyBotState)
    workflow.add_node("policy_bot", policy_bot_node)
    workflow.add_node("tools", ToolNode(policy_bot_tools))
    workflow.add_edge(START, "policy_bot")
    workflow.add_conditional_edges("policy_bot", tools_condition)
    workflow.add_edge("tools", "policy_bot")
    return workflow.compile()

policy_bot_agent = compile_policy_bot_graph()

def invoke_policy_agent(query: str, username: str = "Active Employee") -> str:
    state = {"messages": [HumanMessage(content=query)], "username": username}
    result = policy_bot_agent.invoke(state)
    return result["messages"][-1].content
