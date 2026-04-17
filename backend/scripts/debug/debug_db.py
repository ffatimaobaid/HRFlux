import sqlite3
import pandas as pd

def check_db():
    try:
        conn = sqlite3.connect("queries.db")
        
        print("--- Recent Leave Requests ---")
        df = pd.read_sql_query("SELECT * FROM leave_requests_v2 ORDER BY id DESC LIMIT 5", conn)
        print(df)
        
        print("\n--- Employees ---")
        df_emp = pd.read_sql_query("SELECT employee_id, username, full_name, manager_id FROM employees LIMIT 10", conn)
        print(df_emp)
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
