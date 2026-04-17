import sqlite3

# Check database status
conn = sqlite3.connect('queries.db')
c = conn.cursor()

# Check tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in c.fetchall()]
print("Tables in database:", tables)

# Check employees table
if 'employees' in tables:
    c.execute("SELECT COUNT(*) FROM employees")
    count = c.fetchone()[0]
    print(f"\nEmployees in database: {count}")
    
    if count > 0:
        c.execute("SELECT employee_id, username, full_name FROM employees LIMIT 5")
        employees = c.fetchall()
        print("\nSample employees:")
        for emp in employees:
            print(f"  - {emp[0]}: {emp[1]} ({emp[2]})")
else:
    print("\n❌ 'employees' table does not exist!")

conn.close()
