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
    # Adapter for older files (like agent.py)
    query = state['messages'][-1].content
    user = state.get("username", "Unknown")
    
    config = {"configurable": {"thread_id": f"thread_{user}"}}
    
    # ALWAYS pull the most recent context from SQLite to bypass memory wipes from server reloads
    history_text = "No previous history."
    try:
        from db import get_recent_history
        # Limit to 3 most recent QA pairs to avoid enormous context
        recent = get_recent_history(user, limit=3)
        if recent:
            history_text = ""
            for q, a in recent:
                history_text += f"\nUser: {q}\nAI: {a}\n"
    except Exception as e:
        logger.warning(f"Failed to fetch DB history for thread_{user}: {e}")

    # Send only the latest human message with current context (Date/Time/Day) AND recent DB history
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    day_str = now.strftime("%A")
    time_str = now.strftime("%H:%M:%S")
    
    contextual_prompt = (
        f"Current Context: User: '{user}', Date: {date_str}, Day: {day_str}, Time: {time_str}\n\n"
        f"--- Previous Recent Chat History ---\n{history_text}\n----------------------------------\n\n"
        f"User Question: {query}"
    )
    
    input_message = HumanMessage(content=contextual_prompt)
    
    try:
        # PRIMARY: Attempt Groq Agent invocation
        result = hrflux_agent.invoke({"messages": [input_message]}, config)
    except Exception as e:
        logger.warning(f"Groq primary assistant failed: {e}. Falling back to Smart Gemini Agent...")
        
        # FALLBACK: Use the full-featured Gemini Agent Graph with tool parity
        try:
            # We must use a unique thread ID for Gemini to avoid state collisions if needed, 
            # but usually thread_{user} is fine as it's separate from Groq's local memory object.
            
            # ATTEMPT FALLBACK WITH ROTATION support
            from config import get_current_gemini_key
            for attempt in range(2): # Try rotation if needed
                try:
                    result = gemini_agent.invoke({"messages": [input_message]}, config)
                    break 
                except Exception as gem_e:
                    if ("quota" in str(gem_e).lower() or "429" in str(gem_e)) and attempt < 1:
                        logger.warning(f"Gemini quota hit, rotating key...")
                        rotate_gemini_key()
                        # We need to recreate the agent/llm if we want to update the key immediately
                        # but ChatGoogleGenerativeAI might need a fresh instance.
                        # For now, let's just use the fallback shim if the graph fails.
                        continue
                    raise gem_e

        except Exception as gemini_e:
            logger.error(f"Critical Fallback Failure (Gemini Agent): {gemini_e}")
            # Final secondary fallback to raw Gemini text (very robust)
            try:
                from gemini_llm import query_gemini
                fallback_answer = query_gemini([], f"User '{user}' asks: {query} (Note: System context: Date={date_str}, Day={day_str})")
                from langchain_core.messages import AIMessage
                result = {"messages": [HumanMessage(content=query), AIMessage(content=fallback_answer)]}
            except Exception as final_e:
                logger.error(f"Total System Failure: {final_e}")
                raise e # Re-raise original Groq error
    
    # Return the format that agent.py expects
    return {"messages": result["messages"]}
