import os
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from config import get_current_api_key

@tool
def tool_search_hr_policy(query: str) -> str:
    """Search HR policy"""
    return "Found it."

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.2,
    groq_api_key=get_current_api_key()
)

llm_with_tools = llm.bind_tools([tool_search_hr_policy])

try:
    print("Trying llama-3.3-70b-versatile...")
    res = llm_with_tools.invoke("What is the dress code policy?")
    print("Success:")
    print(res.tool_calls)
except Exception as e:
    print(f"Error: {e}")

llm31 = ChatGroq(
    model_name="llama3-groq-70b-8192-tool-use-preview",
    temperature=0.2,
    groq_api_key=get_current_api_key()
)
llm31_with_tools = llm31.bind_tools([tool_search_hr_policy])

try:
    print("\nTrying llama3-groq-70b-8192-tool-use-preview...")
    res = llm31_with_tools.invoke("What is the dress code policy?")
    print("Success:")
    print(res.tool_calls)
except Exception as e:
    print(f"Error: {e}")
