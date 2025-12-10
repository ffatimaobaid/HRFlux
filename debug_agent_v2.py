import os
import sys
import unittest.mock
sys.modules['streamlit'] = unittest.mock.MagicMock()

from agent import run_agent, normalize_date
from db_schema_v2 import get_employee
import sqlite3

# Test normalization directly
print(f"Testing normalize_date('15 dec'): {normalize_date('15 dec')}")
print(f"Testing normalize_date('2025-01-01'): {normalize_date('2025-01-01')}")

def debug_run():
    user = "tom.dev"
    # Query with natural language date
    question = "I want to apply for casual leave from 15 dec to 17 dec for personal reasons"
    print(f"\nQuestion: {question}")
    
    try:
        answer, suggestions = run_agent(user, question, model_name="models/gemini-2.5-flash")
        print(f"\nAgent Answer:\n{answer}")
    except Exception as e:
        print(f"Error running agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_run()
