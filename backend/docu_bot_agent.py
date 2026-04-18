from __future__ import annotations

import logging
from typing import List, Optional, Sequence, Annotated
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from chat_groq_with_retry import create_chat_groq_with_retry
from docu_tools import docu_bot_tools

logger = logging.getLogger(__name__)

# --- Encapsulated System Prompt ---
DOCUMENT_SYSTEM_PROMPT = """
AGENT_IDENTITY: HRFlux DocumentArchitect v1.5
ROLE: Official Document Generator and Templating Specialist.
CORE_MANDATES:
1. Template Precision: Generate high-fidelity drafts for NOCs, Experience Letters, and Salary Certificates.
2. Data Validation: Ensure all PII and employee variables are localized before finalizing.
3. Logical Reasoning: Understand the 'Purpose' of the document to adjust tone.
BEHAVIOR_RULES:
- Formal, high-authority diplomatic tone.
- Request missing parameters immediately rather than assuming defaults.
""".strip()

# --- State Schema ---
class DocuBotState(TypedDict):
    """The State shared across DocuBot nodes."""
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]
    username: str

# --- Node Implementation ---

def docu_bot_node(state: DocuBotState):
    """The core reasoning node for the Document Specialist."""
    llm = create_chat_groq_with_retry(
        model_name="llama-3.3-70b-versatile",
        temperature=0,
        max_tokens=4096,
    )
    llm_with_tools = llm.bind_tools(docu_bot_tools)
    
    messages = list(state["messages"])
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages.insert(0, SystemMessage(content=DOCUMENT_SYSTEM_PROMPT))
        
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# --- Graph Assembly ---

def compile_docu_bot_graph():
    workflow = StateGraph(DocuBotState)
    workflow.add_node("docu_bot", docu_bot_node)
    workflow.add_node("tools", ToolNode(docu_bot_tools))
    workflow.add_edge(START, "docu_bot")
    workflow.add_conditional_edges("docu_bot", tools_condition)
    workflow.add_edge("tools", "docu_bot")
    return workflow.compile()

docu_bot_agent = compile_docu_bot_graph()

def invoke_docu_agent(query: str, username: str = "Active Employee") -> str:
    state = {"messages": [HumanMessage(content=query)], "username": username}
    result = docu_bot_agent.invoke(state)
    return result["messages"][-1].content
