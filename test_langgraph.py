from supervisor_workflow import hrflux_agent
from langchain_core.messages import HumanMessage

def test_query(q):
    print(f"\n--- Testing Query: {q} ---")
    state = {
        "messages": [HumanMessage(content=q)],
        "username": "EMP00001",
        "chat_history_str": "No prior exchanges."
    }
    result = hrflux_agent.invoke(state)
    print("Final Agent Response:", result["messages"][-1].content)

test_query("I want to apply for 2 days of sick leave tomorrow.")
test_query("What is the dress code?")
test_query("Please generate a salary certificate for me.")
test_query("My manager is harassing me, I need help.")
