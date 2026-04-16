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
        max_tokens=4096,
    )
    memory = MemorySaver()
    agent = create_react_agent(
        llm,
        tools=admin_bot_tools,
        checkpointer=memory,
        prompt=ADMIN_SYSTEM_PROMPT,
    )
    return agent


# Singleton agent instances
_admin_agent = None
_admin_gemini_agent = None

def _get_agent():
    global _admin_agent
    if _admin_agent is None:
        _admin_agent = _build_agent()
    return _admin_agent

def _get_gemini_agent():
    global _admin_gemini_agent
    if _admin_gemini_agent is None:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from config import get_current_gemini_key, GEMINI_MODEL
        from gemini_llm import ChatGoogleGenerativeAIWithRotation
        
        llm = ChatGoogleGenerativeAIWithRotation(
            model=GEMINI_MODEL,
            temperature=0.1,
            google_api_key=get_current_gemini_key(),
            max_tokens=4096
        )
        memory = MemorySaver()
        _admin_gemini_agent = create_react_agent(
            llm,
            tools=admin_bot_tools,
            checkpointer=memory,
            prompt=ADMIN_SYSTEM_PROMPT,
        )
    return _admin_gemini_agent


# ---------------------------------------------------------------------------
# Public Interface
# ---------------------------------------------------------------------------

def invoke_admin_agent(query: str, thread_id: str = "admin_session") -> str:
    """
    Invoke the admin bot with a natural-language query.
    Returns the agent's response as a plain string.
    """
    config = {"configurable": {"thread_id": thread_id}}
    input_messages = {"messages": [HumanMessage(content=query)]}
    
    try:
        # PRIMARY: Groq
        agent = _get_agent()
        result = agent.invoke(input_messages, config=config)
        return result["messages"][-1].content or "Action completed."
        
    except Exception as e:
        logger.warning(f"Admin Groq Agent failed: {e}. Trying Gemini Fallback...")
        
        # SECONDARY: Gemini with rotation
        try:
            from config import rotate_gemini_key
            gemini_agent = _get_gemini_agent()
            
            for attempt in range(2):  # Try with rotation
                try:
                    result = gemini_agent.invoke(input_messages, config=config)
                    return result["messages"][-1].content or "Action completed via Gemini."
                except Exception as gem_e:
                    if ("quota" in str(gem_e).lower() or "429" in str(gem_e)) and attempt < 1:
                        logger.warning("Admin Gemini quota hit, rotating key...")
                        rotate_gemini_key()
                        continue
                    raise gem_e
            
        except Exception as gem_final_e:
            logger.error(f"Admin Gemini Agent failed (all attempts): {gem_final_e}")
            
            # FINAL FALLBACK: Simple text query to Ollama or Gemini (No Tools)
            try:
                from gemini_llm import query_gemini
                fallback_response = query_gemini([], f"ADMIN REQUEST: {query}\n(System note: Groq and Gemini Agent both failed. User is an ADMIN. Use your internal knowledge or suggest manual check.)")
                return f"⚠️ (Partial Service) {fallback_response}"
            except Exception as final_e:
                return f"❌ All Admin AI services (Groq/Gemini/Ollama) are currently unavailable. Error: {str(e)}"
