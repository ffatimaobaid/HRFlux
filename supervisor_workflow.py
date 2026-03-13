"""
Central HR Assistant Workflow
Replaces the old Router with a single ReAct Language Agent equipped with tools.
This allows the agent to combine Knowledge, Leave requests, and Escalations seamlessly with memory.
"""

from typing import Annotated, Sequence, TypedDict, Literal, Optional
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
import logging

from config import get_current_api_key
from leave_bot_tools import leave_bot_tools
from escalation_tools import escalation_bot_tools
from docu_tools import docu_bot_tools

logger = logging.getLogger(__name__)

# Compile all tools into one master list
master_tools = []
master_tools.extend(leave_bot_tools)
master_tools.extend(escalation_bot_tools)
master_tools.extend(docu_bot_tools)

def get_llm():
    """Returns a fresh Groq LLM instance bound to the API key."""
    return ChatGroq(
        model_name="llama-3.3-70b-versatile",
        temperature=0.2, # Low temperature for operational accuracy
        groq_api_key=get_current_api_key()
    )

# The core prompt acts as the brain of the assistant
SYSTEM_PROMPT = """
You are the HRFlux Central Assistant. You help employees with HR policies, leave applications, document drafting, and escalations.

RULES:
1. Operational Actions (Leaves & Tickets):
   - You MUST check leave balances (`tool_get_leave_balance`) BEFORE submitting a leave request.
   - You MUST ask the user for ALL missing parameters before filing an escalation ticket (Category, Description, Parties Involved, Urgency). Do not call `tool_file_escalation` until you have these details from the user.

2. Policy Queries:
   - Use `tool_search_hr_policy` to look up rules, timings, and guidelines before answering.

3. Document Generation:
   - Use `tool_draft_document` when asked to create formal letters. Ask for specifics if not provided.

4. Collaboration & Style:
   - Focus on answering the user's questions proactively. Do NOT reply that you are unable to help if you have a tool available.
   - Combine information when necessary (e.g., check policy THEN check leave balance).
   - Be completely professional. Do not use emojis. Provide concise answers.
   - IMPORTANT: The username is provided explicitly in the user's message (e.g., "User 'john_doe' asks: ..."). Always extract that exact username for your tool calls.
"""

def setup_hrflux_agent():
    """Builds and returns the interactive agent with Memory."""
    memory = MemorySaver()
    llm = get_llm()
    
    # State modifier dynamically injects the system prompt with the username context
    def state_modifier(state):
        # We assume 'username' is pushed into the final query string, 
        # or we just rely on the tool profile fetch for specific user details.
        # But we still enforce a strict agent persona.
        return [SystemMessage(content=SYSTEM_PROMPT.replace("{username}", "Active Employee"))] + state["messages"]

    agent_graph = create_react_agent(
        llm,
        tools=master_tools,
        checkpointer=memory,
        prompt=SYSTEM_PROMPT
    )
    
    return agent_graph

# Global instance
hrflux_agent = setup_hrflux_agent()

# If other modules need compatibility, we provide a wrapper
class AgentStateShim(TypedDict):
    messages: Sequence[BaseMessage]
    username: str
    chat_history_str: str

def invoke_agent_legacy(state: AgentStateShim):
    """
    Adapter for older files (like agent.py) that still call invoke(state) without threaded config.
    """
    query = state['messages'][-1].content
    user = state.get("username", "Unknown")
    
    config = {"configurable": {"thread_id": f"thread_{user}"}}
    
    # Send only the latest human message, rely on checkpointer for history
    input_message = HumanMessage(content=f"User '{user}' says: {query}")
    
    result = hrflux_agent.invoke({"messages": [input_message]}, config)
    
    # Return the format that agent.py expects
    return {"messages": result["messages"]}
