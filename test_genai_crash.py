import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from config import GEMINI_API_KEY
import json

def get_llm():
    model_name = "gemini-1.5-flash"
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            model_string = config.get("model", "models/gemini-1.5-flash")
            model_name = model_string.split("/")[-1] if "/" in model_string else model_string
    except Exception:
        pass
    return ChatGoogleGenerativeAI(model=model_name, google_api_key=GEMINI_API_KEY, temperature=0.2)
    
llm = get_llm()

# Create a mock history mimicking what the graph produces during a tool call
msgs = [
    HumanMessage(content="What is my leave balance?"),
    AIMessage(content="", tool_calls=[{"name": "test_tool", "args": {}, "id": "call_123"}]),
    ToolMessage(content='{"casual": 10}', tool_call_id="call_123")
]

try:
    print("Trying without sanitization...")
    res = llm.invoke(msgs)
    print("Success:", res)
except Exception as e:
    print("Failed as expected:", type(e).__name__, str(e))

print("\n-------------------------------\n")

# Try different sanitization strategies
try:
    print("Trying string replacement sanitization...")
    sanitized = []
    for m in msgs:
        if isinstance(m, AIMessage):
            sanitized.append(AIMessage(content=" ", tool_calls=m.tool_calls))
        elif isinstance(m, ToolMessage):
            sanitized.append(ToolMessage(content=m.content or " ", tool_call_id=m.tool_call_id))
        else:
            sanitized.append(m)
            
    res = llm.invoke(sanitized)
    print("Success:", res)
except Exception as e:
    print("Failed again:", type(e).__name__, str(e))
