
import sys
import os
import json
from datetime import datetime

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from supervisor_workflow import invoke_agent_legacy
from langchain_core.messages import HumanMessage

def test_leave_flow():
    user = "tom.dev"
    # Current date is April 9, 2026 (Thursday)
    
    # Simulate first message: "apply for leave on tuesday"
    print("\n--- TURN 1: 'apply for leave on tuesday' ---")
    state1 = {
        "messages": [HumanMessage(content="apply for leave on tuesday")],
        "username": user
    }
    
    # We call the agent
    # Note: supervisor_workflow.py now uses datetime.now() inside invoke_agent_legacy
    # Since today's real date (system time) is April 9, 2026, it should work.
    
    result1 = invoke_agent_legacy(state1)
    print(f"Assistant: {result1['messages'][-1].content}")
    
    # Simulate second message: provide type and reason
    print("\n--- TURN 2: 'casual', 'i will be out of station' ---")
    query2 = "casual, i will be out of station"
    state2 = {
        "messages": [HumanMessage(content=query2)],
        "username": user
    }
    
    result2 = invoke_agent_legacy(state2)
    print(f"Assistant: {result2['messages'][-1].content}")

if __name__ == "__main__":
    test_leave_flow()
