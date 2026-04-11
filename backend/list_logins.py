import sqlite3

conn = sqlite3.connect('queries.db')
c = conn.cursor()

c.execute("SELECT employee_id, username, full_name, department, designation FROM employees WHERE status='active' ORDER BY employee_id")
employees = c.fetchall()

print("\n" + "="*60)
print("AVAILABLE LOGIN CREDENTIALS")
print("="*60)
print("\nAll passwords are: password123\n")

for emp in employees:
    emp_id, username, full_name, dept, designation = emp
    print(f"{username:20s} | {full_name:25s} | {designation}")

print("\n" + "="*60)
print(f"Total: {len(employees)} employees")
print("="*60)

conn.close()
