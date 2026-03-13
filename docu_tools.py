import json
import logging
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from config import get_current_api_key

logger = logging.getLogger(__name__)

@tool
def tool_draft_document(document_type: str, employee_details_str: str, specific_requirements: str) -> str:
    """
    Draft an official HR document (like an NOC, Salary Certificate, or Experience Letter).
    
    Args:
        document_type: The type of document requested (e.g., "NOC for Visa", "Salary Certificate").
        employee_details_str: Relevant employee info (name, joining date, etc.) formatted as a string.
        specific_requirements: Any specific text or address the user wants included.
        
    Returns:
        The drafted document as markdown.
    """
    try:
        llm = ChatGroq(
            temperature=0.2, 
            model_name="llama-3.3-70b-versatile",
            groq_api_key=get_current_api_key()
        )
        
        prompt = f"""
You are an expert HR Administrator.
Please draft an official {document_type} based on the following details.
Do not make up fake company names, simply use HRFlux.
Use a highly professional, pristine business letter format.

Employee Details:
{employee_details_str}

Specific Requirements:
{specific_requirements}

Output ONLY the document draft text.
"""
        response = llm.invoke(prompt)
        return json.dumps({
            "status": "success",
            "draft": response.content.strip()
        })
    except Exception as e:
        logger.error(f"Failed to draft document: {e}")
        return json.dumps({"error": str(e)})

docu_bot_tools = [tool_draft_document]
