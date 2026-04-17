import os
import json
from langchain_core.messages import HumanMessage
from leave_bot_agent import leave_bot_agent

# Use a test employee that we know exists from seed_data.py
TEST_USER = "john.ceo" 

print("====================================")
print(f"Testing Advanced LeaveBot for user: {TEST_USER}")
print("====================================")

def run_test_case(name, query):
    print(f"\n--- Test Case: {name} ---")
    print(f"Query: {query}")
    
    state = {
        "messages": [HumanMessage(content=query)],
        "username": TEST_USER,
        "employee_id": "EMP00001"
    }
    
    try:
        result = leave_bot_agent.invoke(state)
        final_answer = result["messages"][-1].content
        print("\nFinal Answer:\n", final_answer)
        
        # Check if the agent actually used tools (length of history > 2)
        tool_calls = [msg for msg in result["messages"] if hasattr(msg, "tool_calls") and msg.tool_calls]
        if tool_calls:
            print(f"\n[Tools Called]: {', '.join([tc['name'] for msg in tool_calls for tc in msg.tool_calls])}")
        else:
            print("\n[Tools Called]: None")
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")

if __name__ == "__main__":
    # 1. Test basic operational capability (Balance)
    run_test_case("Check Balance", "What is my current leave balance?")
    
    # 2. Test simple application (Operational)
    run_test_case("Apply for Leave", "Please apply for 1 day of casual leave for tomorrow. Reason: personal work.")
    
    # 3. Test complex advisory reasoning (Requires history + balance check)
    run_test_case("Complex Advisory Request", "Do I have enough leave for a 12-day vacation? Please advise based on my history and balance.")
