"""
Central HR Assistant Workflow
Replaces the old Router with a single ReAct Language Agent equipped with tools.
This allows the agent to combine Knowledge, Leave requests, and Escalations seamlessly with memory.
"""

from typing import Annotated, Sequence, TypedDict, Literal, Optional
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
import logging
from datetime import datetime

from chat_groq_with_retry import create_chat_groq_with_retry
from config import get_current_gemini_key, rotate_gemini_key
from langchain_google_genai import ChatGoogleGenerativeAI
from leave_bot_tools import leave_bot_tools
from escalation_tools import escalation_bot_tools
from docu_tools import docu_bot_tools
from meeting_tools import meeting_bot_tools
from prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Compile all tools into one master list
master_tools = []
master_tools.extend(leave_bot_tools)
master_tools.extend(escalation_bot_tools)
master_tools.extend(docu_bot_tools)  # Now contains both enhanced and basic tools
master_tools.extend(meeting_bot_tools)

def get_llm():
    """Returns a fresh Groq client with retry logic."""
    return create_chat_groq_with_retry(
        model_name="llama-3.3-70b-versatile",
        temperature=0.2,  # Low temperature for operational accuracy
        max_tokens=4096
    )

def get_gemini_llm():
    """Returns a fresh Gemini client with rotation support."""
    from config import GEMINI_MODEL
    from gemini_llm import ChatGoogleGenerativeAIWithRotation
    return ChatGoogleGenerativeAIWithRotation(
        model=GEMINI_MODEL,
        temperature=0.2,
        google_api_key=get_current_gemini_key(),
        max_tokens=4096
    )

# Note: SYSTEM_PROMPT is imported from prompts.py

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

# Global instances for Groq and Gemini agents
hrflux_agent = setup_hrflux_agent()

def setup_gemini_agent():
    """Builds and returns the Gemini version of the smart agent."""
    memory = MemorySaver()
    llm = get_gemini_llm()
    
    agent_graph = create_react_agent(
        llm,
        tools=master_tools,
        checkpointer=memory,
        prompt=SYSTEM_PROMPT
    )
    return agent_graph

gemini_agent = setup_gemini_agent()

# If other modules need compatibility, we provide a wrapper
class AgentStateShim(TypedDict):
    messages: Sequence[BaseMessage]
    username: str
    chat_history_str: str

def invoke_agent_legacy(state: AgentStateShim):
    """
    Adapter for production files (like agent.py).
    Ensures context is preserved by passing proper message turns.
    """
    query = state['messages'][-1].content
    user = state.get("username", "Unknown")
    
    # Consistent thread ID for persistent memory
    config = {"configurable": {"thread_id": f"thread_{user}"}}
    
    # 1. Fetch recent history and convert to proper Message objects
    full_messages = []
    try:
        from db import get_recent_history
        from langchain_core.messages import HumanMessage, AIMessage
        
        # Hydrate context with current environment data
        now = datetime.now()
        ctx_info = f"Context: User={user}, Date={now.strftime('%Y-%m-%d')}, Day={now.strftime('%A')}, Time={now.strftime('%H:%M:%S')}"
        full_messages.append(SystemMessage(content=f"{SYSTEM_PROMPT}\n\n{ctx_info}"))

        # Fetch last 5 QA pairs to provide deep context without overloading tokens
        recent = get_recent_history(user, limit=5)
        if recent:
            # History comes in (question, answer) tuples
            for q, a in reversed(recent): # reversed because get_recent_history usually returns newest first
                if q: full_messages.append(HumanMessage(content=q))
                if a: full_messages.append(AIMessage(content=a))
    except Exception as e:
        logger.warning(f"Failed to fetch/parse DB history for thread_{user}: {e}")

    # 2. Add the current user query
    full_messages.append(HumanMessage(content=query))
    
    try:
        # PRIMARY: Attempt Groq Agent invocation with full message sequence
        result = hrflux_agent.invoke({"messages": full_messages}, config)
        
    except Exception as e:
        logger.warning(f"Groq primary assistant failed: {e}. Falling back to Smart Gemini Agent...")
        
        # FALLBACK: Use the Gemini Agent Graph with tool parity
        try:
            from config import get_current_gemini_key, rotate_gemini_key
            for attempt in range(2): 
                try:
                    result = gemini_agent.invoke({"messages": full_messages}, config)
                    break 
                except Exception as gem_e:
                    if ("quota" in str(gem_e).lower() or "429" in str(gem_e)) and attempt < 1:
                        logger.warning(f"Gemini quota hit, rotating key...")
                        rotate_gemini_key()
                        continue
                    raise gem_e

        except Exception as gemini_e:
            logger.error(f"Critical Fallback Failure (Gemini Agent): {gemini_e}")
            # Final secondary fallback to raw Gemini text
            try:
                from gemini_llm import query_gemini
                fallback_answer = query_gemini([], f"User '{user}' asks: {query} (System Context: {ctx_info})")
                from langchain_core.messages import AIMessage
                result = {"messages": full_messages + [AIMessage(content=fallback_answer)]}
            except Exception as final_e:
                logger.error(f"Total System Failure: {final_e}")
                raise e 
    
    return {"messages": result["messages"]}
