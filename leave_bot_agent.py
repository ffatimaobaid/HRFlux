import os
import json
import logging
from typing import List, Optional

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

# Local imports
from config import get_current_api_key
from leave_bot_tools import leave_bot_tools

logger = logging.getLogger(__name__)

# --- State Schema ---
class LeaveBotState(TypedDict):
    messages: List[BaseMessage]
    username: str
    employee_id: str

# --- System Prompt ---
# This prompt instructs the agent to act as BOTH an operational assistant and an advisory assistant. 
LEAVEBOT_SYSTEM_PROMPT = """
You are the HRFlux LeaveBot, a specialized AI agent responsible for managing and advising on employee leave requests and policies.

Your capabilities include:
1. Operational Tasks: You can check leave balances, view leave history, and submit formal leave requests using your tools.
2. Advisory Tasks: You must act as an intelligent counselor. When a user asks questions like "Is December a good month to take leave?" or "Will I have enough leave for a 2-week vacation?", you MUST NOT guess. Instead, you MUST use your tools to:
   - Search the HR policy (tool_search_hr_policy) for blackout dates, accrual rules, or department-specific constraints.
   - Check the user's specific past usage (tool_get_leave_history).
   - Check the user's current balance (tool_get_leave_balance).
   - Check their employee profile (tool_get_employee_profile) to see what department they are in.
   - CHECK THE CALENDAR (`tool_get_employee_calendar`) to see if they have overlapping overlapping tasks, meetings, or deadlines during the requested leave period.

RULES:
- Always fetch the user's profile first if you need context to answer a personalized advisory question.
- Do NOT hallucinate policies. Always call `tool_search_hr_policy` if asked about rules, blackout periods, or carrying forward balances.
- STRICT REQUIREMENT: If the user provides dates or asks to take leave, you MUST FIRST call `tool_get_employee_calendar` to check for overlapping deadlines. You CANNOT skip this step. If you do not call the calendar tool, you have failed.
- If there is a deadline, meeting, or important task overlapping with their requested leave dates, strongly WARN the user and advise them to reconsider or secure coverage. However, DO NOT hard-block the submission. If they insist, allow them to submit the request.
- If the user explicitly asks to apply for leave, use `tool_submit_leave_request`, but only AFTER checking their balance using `tool_get_leave_balance` to ensure they have enough days! Don't let them apply for leaves they don't have.
- If a query is NOT related to leaves, time off, or attendance, state that you are the LeaveBot and cannot help with that query.
- Maintain a polite, professional, and helpful HR persona.

The current user is: {username}
"""

def get_llm():
    """Returns the configured Gemini LLM bound with tools."""
    # Find the user's selected model from config, fallback to flash
    model_name = "gemini-1.5-flash"
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            # Extact 'gemini-1.5-flash' from 'models/gemini-1.5-flash'
            model_string = config.get("model", "models/gemini-1.5-flash")
            model_name = model_string.split("/")[-1] if "/" in model_string else model_string
    except Exception:
        pass
        
    llm = ChatGroq(
        model_name="llama-3.3-70b-versatile",
        groq_api_key=get_current_api_key(),
        temperature=0.2 # Lower temperature for procedural adherence
    )
    # Bind the tools to the model natively
    return llm.bind_tools(leave_bot_tools)


def leave_bot_node(state: LeaveBotState):
    """The main reasoning node that invokes the LLM."""
    username = state.get("username", "Unknown User")
    messages = state["messages"]

    # Inject the system prompt at the beginning if it's not already there
    system_msg = SystemMessage(content=LEAVEBOT_SYSTEM_PROMPT.format(username=username))
    
    # Check if the first message is already our system message
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [system_msg] + messages
    else:
        # Update it just in case username changed
        messages[0] = system_msg
        
    # Create a sanitized copy of messages for the LLM to avoid google-genai crashes
    # The API requires all parts to have non-empty text.
    sanitized_messages = []
    for msg in messages:
        # Create a copy to avoid mutating the actual graph state
        msg_copy = msg.copy()
        if not msg_copy.content:
            msg_copy.content = " "
        sanitized_messages.append(msg_copy)

    llm_with_tools = get_llm()
    
    logger.info(f"LeaveBot generating response for user '{username}' with {len(sanitized_messages)} messages context.")
    response = llm_with_tools.invoke(sanitized_messages)
    
    return {"messages": [response]}


def compile_leave_bot_graph():
    """
    Compiles the LangGraph StateGraph for the standalone LeaveBot.
    This creates a ReAct style agent loop.
    """
    builder = StateGraph(LeaveBotState)

    # Add the reasoning node
    builder.add_node("leave_bot", leave_bot_node)
    
    # Add the tool execution node
    tool_node = ToolNode(leave_bot_tools)
    builder.add_node("tools", tool_node)

    # Define the execution flow
    builder.add_edge(START, "leave_bot")
    
    # The tools_condition routing checks if the LLM output requested a tool call.
    # If yes -> route to 'tools' node. If no -> route to END.
    builder.add_conditional_edges("leave_bot", tools_condition)
    
    # After a tool is done, we MUST go back to the reasoning node to interpret the tool output
    builder.add_edge("tools", "leave_bot")

    return builder.compile()

# Singleton graph instance to be imported by supervisor_workflow
leave_bot_agent = compile_leave_bot_graph()
