from supervisor_workflow import hrflux_agent
from langchain_core.messages import HumanMessage

import time
import os

print("--- Testing Conversational Memory & Agent Collaboration ---")
# Use a consistent thread_id to test memory
config = {"configurable": {"thread_id": "test_thread_01"}}

def chat(q):
    print(f"\nUser: {q}")
    # Invoke the agent using the strict setup needed by create_react_agent
    input_message = HumanMessage(content=q)
    result = hrflux_agent.invoke({"messages": [input_message]}, config)
    # create_react_agent appends messages to state["messages"]
    print("Agent:", result["messages"][-1].content)
    # Pause between queries to avoid Groq rate limits, though they are usually high
    time.sleep(3)

# Turn 1: Policy Question
chat("Can you tell me the policy on taking Casual Leaves?")

# Turn 2: Follow-up memory + Profile lookup
chat("Okay, how many do I currently have left? My username is EMP00001.")

# Turn 3: Document Drafting Tool
chat("Please draft an NOC for a Schengen Visa for me based on my profile.")

# Turn 4: Escalation Tool requirement
chat("I want to escalate an issue regarding my payroll.")

# Turn 5: Escalation Follow-up 
chat("My overtime wasn't paid. Just me. It's high urgency.")
