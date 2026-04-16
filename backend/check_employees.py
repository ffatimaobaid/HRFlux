import sqlite3
import os

DB_PATH = "queries.db"

def check_employees():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT employee_id, full_name, manager_id FROM employees")
    rows = c.fetchall()
    conn.close()
    
    print(f"📋 Found {len(rows)} employees:")
    for row in rows:
        print(f"   - {row[0]}: {row[1]} (Reports to: {row[2]})")

if __name__ == "__main__":
    check_employees()
