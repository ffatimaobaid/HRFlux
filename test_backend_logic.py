import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from agent import run_agent

user = "test_user"
question = "List all categories shown in the 'Employee Relations & Risk Management' pie chart."

print(f"Testing question: {question}")
answer, suggestions = run_agent(user, question)

print("\n--- ANSWER ---")
print(answer)
print("\n--- SUGGESTIONS ---")
print(suggestions)
