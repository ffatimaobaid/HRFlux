import logging
from typing import List, Tuple
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

def generate_escalation_summary(username: str, incident_description: str, history: List[Tuple[str, str]]) -> str:
    """
    Generate a targeted AI summary of the conversation history focused on the escalation topic.
    """
    if not history:
        return f"Individual Incident Report: {incident_description}"
    
    # Format history for the LLM
    formatted_history = ""
    for q, a in history:
        formatted_history += f"User: {q}\nAI: {a}\n"
        
    prompt = f"""
    You are an HR Incident Summarizer. An employee named '{username}' is escalating a workplace issue.
    
    CORE INCIDENT:
    {incident_description}
    
    RECENT CONVERSATION HISTORY:
    {formatted_history}
    ---
    TASK:
    Provide a professional, concise summary (3-5 sentences) of this incident for an HR Manager.
    Focus ONLY on the facts relevant to the grievance/complaint. 
    Do NOT include unrelated chat history or generic assistant responses.
    The summary should help the HR Manager understand the core problem and any parties involved immediately.
    Output only the summary text.
    """
    
    try:
        from supervisor_workflow import get_llm, get_gemini_llm
        # Attempt to use Groq first, then Gemini
        llm = get_llm()
        messages = [HumanMessage(content=prompt)]
        
        try:
            response = llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            logger.warning(f"Summarizer failed on Groq: {e}. Trying Gemini...")
            gemini = get_gemini_llm()
            res = gemini.invoke(messages)
            return res.content.strip()
            
    except Exception as e:
        logger.error(f"Total failure in AI summarization: {e}")
        return f"AI summarization unavailable. Core Incident: {incident_description}"
