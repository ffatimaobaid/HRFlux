import os
import sys

# Mock streamlit before importing agent
import unittest.mock
sys.modules['streamlit'] = unittest.mock.MagicMock()

from agent import run_agent
from db_schema_v2 import get_employee
import sqlite3

def check_latest_request():
    conn = sqlite3.connect("queries.db")
    c = conn.cursor()
    c.execute("SELECT id, employee_id, leave_type, start_date, status FROM leave_requests_v2 ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row

def debug_run():
    user = "tom.dev" # Known seeded user
    
    # 1. Check if user exists
    emp = get_employee(username=user)
    if not emp:
        print(f"❌ User {user} not found in DB! Seed data issues?")
        return

    print(f"Found user: {emp['full_name']} ({emp['employee_id']})")
    
    # 2. Simulate User Query
    question = "I want to apply for casual leave from 2025-12-20 to 2025-12-22 because I am sick"
    print(f"\nQuestion: {question}")
    
    # 3. Run Agent
    print("running agent...")
    try:
        answer, suggestions = run_agent(user, question, model_name="models/gemini-2.5-flash")
        print(f"\nAgent Answer:\n{answer}")
    except Exception as e:
        print(f"Error running agent: {e}")
        import traceback
        traceback.print_exc()

    # 4. Check Database
    print("\nChecking Database for new request...")
    latest = check_latest_request()
    if latest:
        print(f"Latest Request in DB: ID={latest[0]}, Emp={latest[1]}, Type={latest[2]}, Start={latest[3]}, Status={latest[4]}")
    else:
        print("No requests found.")

if __name__ == "__main__":
    debug_run()
