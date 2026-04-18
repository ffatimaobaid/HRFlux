import json
import logging
from typing import List, Dict, Any
from langchain_core.tools import tool
from rag import retrieve_context

logger = logging.getLogger(__name__)

@tool
def tool_search_hr_policy(query: str) -> str:
    """
    Search the company HR policy handbook and knowledge base for answers.
    Use this for any questions about rules, benefits, working hours, 
    holidays, or general company procedures.
    """
    try:
        # retrieve_context returns (answer, chunks) or similar depending on implementation
        # Looking at rag.py, it's a hybrid search.
        from vector_store import search_sources
        results = search_sources(query, limit=4)
        
        if not results:
            return "No specific policy information found for this query in the official handbook."
            
        context_parts = []
        for r in results:
            src = r.get("metadata", {}).get("doc_id", "Unknown Document")
            txt = r.get("content", "")
            context_parts.append(f"[Source: {src}]\n{txt}")
            
        return "\n\n".join(context_parts)
    except Exception as e:
        logger.error(f"Policy search failed: {e}")
        return f"Error accessing policy database: {str(e)}"

policy_bot_tools = [tool_search_hr_policy]
