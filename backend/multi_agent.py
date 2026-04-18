from __future__ import annotations

import operator
import logging
import json
from typing import Annotated, Any, Dict, List, Sequence, TypedDict, Literal

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.tools import tool

from config import get_current_api_key
from agents.agent_router import CLASSIFIER_SYSTEM_PROMPT

# Import the root-level specialist graphs
from leave_bot_agent import leave_bot_agent
from policy_bot_agent import policy_bot_agent
from docu_bot_agent import docu_bot_agent
from escalation_bot_agent import escalation_bot_agent

logger = logging.getLogger(__name__)

# --- Graph State Definition ---
class AgentState(TypedDict):
    """
    The state shared between nodes in the Multi-Agent graph.
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    employee_id: str
    username: str

# --- Specialist Tools (The 'Act' part of ReAct) ---

@tool
def call_leave_bot(query: str, username: str):
    """Call the LeaveBot Specialist for queries about annual leave, medical leave, balance checks, or applications."""
    logger.info(f"Delegating to LeaveBot: {query}")
    result = leave_bot_agent.invoke({"messages": [HumanMessage(content=query)], "username": username})
    return result["messages"][-1].content

@tool
def call_policy_bot(query: str, username: str):
    """Call the PolicyBot Specialist for questions about company guidelines, HR rules, or employee benefits."""
    logger.info(f"Delegating to PolicyBot: {query}")
    result = policy_bot_agent.invoke({"messages": [HumanMessage(content=query)], "username": username})
    return result["messages"][-1].content

@tool
def call_docu_bot(query: str, username: str):
    """Call the DocuBot Specialist for generating NOCs, Salary Certificates, or Experience Letters."""
    logger.info(f"Delegating to DocuBot: {query}")
    result = docu_bot_agent.invoke({"messages": [HumanMessage(content=query)], "username": username})
    return result["messages"][-1].content

@tool
def call_escalation_bot(query: str, username: str):
    """Call the EscalationBot Specialist for formal complaints, sensitive issues, or requests to talk to HR."""
    logger.info(f"Delegating to EscalationBot: {query}")
    result = escalation_bot_agent.invoke({"messages": [HumanMessage(content=query)], "username": username})
    return result["messages"][-1].content

# --- Node Implementation ---

def supervisor_node(state: AgentState):
    """
    The ReAct Supervisor Brain.
    It Razona (Reasons) about the query and decides which specialists to Act (Call).
    """
    llm = ChatGroq(
        model_name="llama-3.3-70b-versatile",
        temperature=0,
        groq_api_key=get_current_api_key(),
    )
    
    # Bind the specialist tools to the supervisor
    tools = [call_leave_bot, call_policy_bot, call_docu_bot, call_escalation_bot]
    llm_with_tools = llm.bind_tools(tools)
    
    # Enforce Persona: The Supervisor is a high-level HR Orchestrator
    system_message = {
        "role": "system",
        "content": (
            "You are the HRFlux Multi-Agent Supervisor. Your goal is to help employees by delegating "
            "tasks to the correct specialist bots. \n"
            "1. REASON about the user's request.\n"
            "2. ACT by calling the appropriate specialist tool if necessary.\n"
            "3. If a tool brings back information, summarize it professionally for the user.\n"
            f"Active Employee: {state.get('username', 'Unknown')}"
        )
    }
    
    messages = [system_message] + list(state["messages"])
    
    response = llm_with_tools.invoke(messages)
    
    return {"messages": [response]}

def call_tools_node(state: AgentState):
    """
    The node that executes the specialist tool calls.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    if not last_message.tool_calls:
        return {"messages": []}
    
    results = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        # Inject username into all specialist calls
        tool_args["username"] = state.get("username", "Active Employee")
        
        # Execute tool
        mapping = {
            "call_leave_bot": call_leave_bot,
            "call_policy_bot": call_policy_bot,
            "call_docu_bot": call_docu_bot,
            "call_escalation_bot": call_escalation_bot,
        }
        
        func = mapping.get(tool_name)
        if func:
            output = func.invoke(tool_args)
            results.append(ToolMessage(
                tool_call_id=tool_call["id"],
                content=output
            ))
            
    return {"messages": results}

# --- Router Logic ---

def should_continue(state: AgentState):
    """Determines if the graph should finish or execute tools."""
    messages = state["messages"]
    last_message = messages[-1]
    
    if last_message.tool_calls:
        return "tools"
    return END

# --- Graph Construction ---

def create_hrflux_multi_agent_graph():
    """
    Builds the state-of-the-art ReAct Multi-Agent Supervisor Graph.
    """
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("tools", call_tools_node)
    
    # Set Entry Point
    workflow.set_entry_point("supervisor")
    
    # Add Conditional Edges
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    
    # Transitions from Tools always go back to Supervisor for summary
    workflow.add_edge("tools", "supervisor")
    
    return workflow.compile()

# Final Global Instance
hrflux_multi_agent = create_hrflux_multi_agent_graph()

if __name__ == "__main__":
    print("--- HRFLUX ReAct Multi-Agent Orchestrator ---")
    
    test_state = {
        "messages": [HumanMessage(content="What is my leave balance? Also, show me the maternity leave policy.")],
        "username": "DemoUser"
    }
    
    # We use a recursion limit to prevent infinite loops in demo
    for output in hrflux_multi_agent.stream(test_state, {"recursion_limit": 10}):
        for key, value in output.items():
            print(f"\n--- Node: {key} ---")
            msg = value["messages"][-1]
            if isinstance(msg, AIMessage) and msg.tool_calls:
                print(f"Decision: Calling Specialists - {msg.tool_calls}")
            else:
                print(f"Content: {msg.content[:200]}...")
