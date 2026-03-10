from typing import Annotated, Sequence, TypedDict, Literal, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
import json
import logging
from config import get_current_api_key

logger = logging.getLogger(__name__)

# 1. State Schema
class AgentState(TypedDict):
    """
    State schema tracking conversation history and routing logic.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next_agent: Optional[str]
    employee_id: Optional[str]
    username: Optional[str]
    chat_history_str: Optional[str]
    reason: Optional[str] # Used for passing extracted reasoning across nodes

# 2. Structured Output for Router
class RouteDecision(BaseModel):
    next_agent: Literal["LeaveBot", "PolicyBot", "DocuBot", "EscalationBot"] = Field(
        description="The agent to route the user's query to."
    )
    reason: str = Field(description="Why this route was chosen.")

# 3. Router Node
def router_node(state: AgentState):
    """The Supervisor that analyzes intent and assigns the next agent."""
    messages = state["messages"]
    logger.info("Router Node: Analyzing intent...")
    
    # Needs a fresh LLM instance since the API key might rotate
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        temperature=0,
        google_api_key=get_current_api_key()
    )
    
    structured_llm = llm.with_structured_output(RouteDecision)
    
    system_prompt = """You are the HRFlux Routing Supervisor.
Your job is to read the latest user message and decide which specialized agent should handle it based on these strict guidelines:

- **LeaveBot**: ANY question or request related to taking time off, checking leave balances, sick leave, annual leave, or reporting absences/tardiness.
- **PolicyBot**: General questions about company guidelines, office timings, dress code, WFH policies, and other standard FAQs.
- **DocuBot**: Explicit requests to generate, draft, or write official employment documents like NOCs, Experience Letters, or Salary Certificates.
- **EscalationBot**: If the user mentions sensitive topics (harassment, discrimination, salary dispute, whistleblowing), explicitly asks to speak to human HR/manager, or if the user asks for their personal profile details (my ID, my joining date, my manager).

Output the designated next_agent and your reasoning.
"""
    
    try:
        decision = structured_llm.invoke([
            {"role": "system", "content": system_prompt},
            messages[-1] 
        ])
        
        logger.info(f"Router Decision: {decision.next_agent} - {decision.reason}")
        return {"next_agent": decision.next_agent, "reason": decision.reason}
    except Exception as e:
        logger.error(f"Router explicitly failed, falling back to EscalationBot: {e}")
        return {"next_agent": "EscalationBot", "reason": "Routing LLM failed to parse constraints"}

# 4. Conditional Edge Function
def route_to_worker(state: AgentState):
    return state.get("next_agent", "EscalationBot")

# 5. Worker Bots

def leave_bot(state: AgentState):
    logger.info("Executing advanced LeaveBot agent logic...")
    
    # Import the compiled LangGraph agent we just created
    from leave_bot_agent import leave_bot_agent
    
    query = state["messages"][-1].content
    user = state.get("username", "Unknown")
    
    # We must pass down the username so the LeaveBot can query the DB properly
    sub_state = {
        "messages": [HumanMessage(content=query)],
        "username": user,
        "employee_id": state.get("employee_id", "")
    }
    
    try:
        # Invoke the sub-graph
        result = leave_bot_agent.invoke(sub_state)
        # The result messages contain the entire agent loop history. The last message is the final answer.
        final_answer = result["messages"][-1].content
        return {"messages": [AIMessage(content=final_answer)]}
    except Exception as e:
        logger.error(f"Advanced LeaveBot agent failed: {e}")
        import traceback
        traceback.print_exc()
        return {"messages": [AIMessage(content="I encountered an internal error checking your leave information. Please contact HR support.")]}


def policy_bot(state: AgentState):
    logger.info("Executing PolicyBot logic...")
    query = state["messages"][-1].content
    history_str = state.get("chat_history_str", "No prior exchanges.")
    
    from rag import retrieve_context
    from gemini_llm import query_gemini
    from config import SHOW_SOURCES
    from hr_knowledge_base import get_hr_procedure, format_hr_response
    
    # 1. Check strict procedure matches
    hr_knowledge = None
    hr_matches = get_hr_procedure(query)
    if hr_matches:
        hr_knowledge = format_hr_response(hr_matches)
        
    # 2. Vector DB Context
    context_chunks = retrieve_context(query)
    
    # 3. Query Gemini
    answer = query_gemini(
        context_chunks=context_chunks if context_chunks else [],
        question=query,
        model_name="models/gemini-2.0-flash",
        chat_history=None, # In supervisor, we might format this differently or rely on state
        hr_knowledge=hr_knowledge
    )
    
    return {"messages": [AIMessage(content=answer)]}


def docu_bot(state: AgentState):
    logger.info("Executing DocuBot logic...")
    query = state["messages"][-1].content
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=get_current_api_key())
    prompt = f"Draft an official HR document based on this request: '{query}'. Use a professional template format with placeholders like [Date], [Employee Name], etc. if specific details aren't provided. Do not invent company names, just use HRFlux."
    
    ans = llm.invoke(prompt).content
    return {"messages": [AIMessage(content=ans)]}


def escalation_bot(state: AgentState):
    logger.info("Executing EscalationBot logic...")
    query = state["messages"][-1].content
    user = state.get("username", "Unknown")
    history_str = state.get("chat_history_str", "")
    reason = state.get("reason", "Sensitive query or manual review requested")
    
    # Check Profile Intent First (as a sub-rule of Escalation)
    profile_keywords = ["my profile", "my details", "my info", "who is my manager", "my department", "my designation", "my role", "my employee id", "my salary", "my joining date"]
    if any(k in query.lower() for k in profile_keywords):
        from db_schema_v2 import get_employee
        emp = get_employee(username=user)
        if emp:
            manager_info = "N/A"
            if emp.get('manager_id'):
                mgr = get_employee(employee_id=emp['manager_id'])
                if mgr:
                    manager_info = f"{mgr.get('full_name')} ({emp.get('manager_id')})"
            ans = (
                f"### 👤 {emp.get('full_name')} (You)\n\n"
                f"**Employee ID:** `{emp.get('employee_id')}`\n"
                f"**Department:** {emp.get('department')}\n"
                f"**Designation:** {emp.get('designation')}\n"
                f"**Manager:** {manager_info}\n"
                f"**Joining Date:** {emp.get('joining_date')}\n"
                f"**Email:** {emp.get('email')}\n"
            )
            return {"messages": [AIMessage(content=ans)]}
            
    # Actually Escalate
    try:
        from workflow_engine import ChatEscalationEngine
        ChatEscalationEngine.submit_chat_escalation(
            username=user,
            query=query,
            full_history=history_str,
            reason=reason,
            sensitivity_score=1.0
        )
        ans = "⚠️ I have escalated your query to a human HR officer. They will review your case and get back to you shortly."
    except ImportError:
        ans = "I have noted your request for manual review. Please contact HR directly at hr@company.com."
        
    return {"messages": [AIMessage(content=ans)]}

# 6. Build Graph
workflow = StateGraph(AgentState)

workflow.add_node("Router", router_node)
workflow.add_node("LeaveBot", leave_bot)
workflow.add_node("PolicyBot", policy_bot)
workflow.add_node("DocuBot", docu_bot)
workflow.add_node("EscalationBot", escalation_bot)

workflow.add_edge(START, "Router")

workflow.add_conditional_edges(
    "Router",
    route_to_worker,
    {
        "LeaveBot": "LeaveBot",
        "PolicyBot": "PolicyBot",
        "DocuBot": "DocuBot",
        "EscalationBot": "EscalationBot"
    }
)

workflow.add_edge("LeaveBot", END)
workflow.add_edge("PolicyBot", END)
workflow.add_edge("DocuBot", END)
workflow.add_edge("EscalationBot", END)

hrflux_agent = workflow.compile()
