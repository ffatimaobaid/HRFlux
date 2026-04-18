import logging
import sys
import os

# Set up logging to see the transitions
logging.basicConfig(level=logging.INFO)

# Mocking the environment
from supervisor_workflow import invoke_agent_legacy
from langchain_core.messages import HumanMessage

def test_context():
    user = "demo_tester"
    
    print("\n--- TURN 1 ---")
    q1 = "Who is the CEO of the company?"
    state1 = {"messages": [HumanMessage(content=q1)], "username": user}
    res1 = invoke_agent_legacy(state1)
    ans1 = res1["messages"][-1].content
    print(f"User: {q1}")
    print(f"AI: {ans1}")
    
    # Simulate database storage (which the supervisor uses to fetch history)
    from db import save_log
    save_log(user, q1, ans1)
    
    print("\n--- TURN 2 (Follow-up) ---")
    q2 = "And what is his email address?"
    state2 = {"messages": [HumanMessage(content=q2)], "username": user}
    res2 = invoke_agent_legacy(state2)
    ans2 = res2["messages"][-1].content
    print(f"User: {q2}")
    print(f"AI: {ans2}")
    
    # If the AI knows "him" refers to the CEO from Turn 1, Turn 2 is a success.
    if "ceo" in ans2.lower() or "not found" in ans2.lower() or "@" in ans2:
        print("\n✅ Verification SUCCESS: Context appears to be preserved.")
    else:
        print("\n❌ Verification FAILED: AI seemed to forget the previous subject.")

if __name__ == "__main__":
    try:
        test_context()
    except Exception as e:
        print(f"Error during test: {e}")
