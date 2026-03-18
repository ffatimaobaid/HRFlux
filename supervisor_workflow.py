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

from chat_groq_with_retry import create_chat_groq_with_retry
from leave_bot_tools import leave_bot_tools
from escalation_tools import escalation_bot_tools
from docu_tools import docu_bot_tools
from meeting_tools import meeting_bot_tools

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
        temperature=0.2  # Low temperature for operational accuracy
    )

# The core prompt acts as the brain of the assistant
SYSTEM_PROMPT = """
You are HRFlux Central Assistant. You help employees with HR policies, leave applications, document drafting, escalations, and meeting scheduling.

IMPORTANT: You have tools available. When users ask for documents (NOC, salary certificate, experience letter), you MUST call the tool_generate_enhanced_document function. Do NOT just respond with text.

CRITICAL DOMAIN RESTRICTION:
You are an HR ASSISTANT for this company ONLY. 
You must STRICTLY answer questions related to:
- HR policies, procedures, and benefits
- Leave requests and balance inquiries  
- Employee onboarding and training
- Company-specific information and procedures
- Document drafting and HR workflows
- Meeting scheduling and calendar management

STRICTLY PROHIBITED TOPICS:
- Questions about other companies, their leadership, or ownership (Tesla, SpaceX, Amazon, etc.)
- Celebrity gossip or entertainment industry news
- General knowledge questions outside HR domain
- Personal advice about investments, careers, or life decisions
- Technical support for non-HR software/hardware issues
- Any question not related to this company's HR functions

RESPONSE POLICY:
If asked about prohibited topics, respond: 
"I am specifically designed to help with HR-related questions for this company. 
I cannot assist with questions about [topic]. Please ask an appropriate question about HR policies, leave requests, or other HR-related matters."

If the question is HR-related but unclear, ask for clarification about the specific HR context needed.

RULES:
1. Operational Actions (Leaves, Tickets & Meetings):
   - You MUST check leave balances (`tool_get_leave_balance`) BEFORE submitting a leave request.
   - You MUST ask the user for ALL missing parameters before filing an escalation ticket (Category, Description, Parties Involved, Urgency). Do not call `tool_file_escalation` until you have these details from the user.
   - For meeting scheduling, FIRST call `tool_schedule_meeting` with just the username to understand what information is needed. Then ask the user for specific details (title, date, time, participants) before calling again with all parameters.

2. Policy Queries:
   - Use `tool_search_hr_policy` to look up rules, timings, and guidelines before answering.

3. Document Generation:
   - ALWAYS use `tool_generate_enhanced_document` for professional document generation with PDF download.
   - This automatically personalizes documents with employee data and provides download links.
   - Ask for specific requirements if needed, but don't ask for basic employee details (auto-filled).
   - NEVER use `tool_draft_document` - it's outdated and doesn't provide PDF downloads.
   - CRITICAL: When user asks for NOC, salary certificate, or experience letter, you MUST call the tool, not just respond with text.

4. Meeting Management:
   - Use `tool_schedule_meeting` to schedule meetings for employees. Always ask for meeting title and date first.
   - Use `tool_list_meetings` to show upcoming meetings.
   - Use `tool_cancel_meeting` to cancel scheduled meetings.

5. Collaboration & Style:
   - Focus on answering the user's questions proactively. Do NOT reply that you are unable to help if you have a tool available.
   - Combine information when necessary (e.g., check policy THEN check leave balance).
   - Be completely professional. Do not use emojis. Provide concise answers.
   - IMPORTANT: The username is provided explicitly in the user's message (e.g., "User 'john_doe' asks: ..."). Always extract that exact username for your tool calls.
   - MEETING SCHEDULING: When users ask to schedule meetings, guide them through the process step by step. Don't assume they know what information is needed.
   - CRITICAL: Never answer questions about other companies, celebrities, or general knowledge outside the HR domain.
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
