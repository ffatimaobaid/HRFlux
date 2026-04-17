import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "queries.db"

def seed_calendar_events():
    """Seed the employee_tasks table with mock events for all existing employees."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get all employees
    c.execute("SELECT employee_id FROM employees")
    employees = c.fetchall()
    
    if not employees:
        print("No employees found in the database. Please add some employees first.")
        conn.close()
        return
        
    event_types = ['task', 'event', 'deadline', 'meeting']
    titles = [
        "Project Review", "Team Sync", "Client Meeting", "Submit Expense Report", 
        "Complete Compliance Training", "1-on-1 with Manager", "Quarterly Planning", 
        "Code Review", "Update HR Policies", "Townhall Meeting"
    ]
    
    descriptions = [
        "Make sure to prepare the slides.", "Discussing Q3 goals.", 
        "Bring the updated contract.", "Required for all staff.", 
        "Deadline approaching.", "Regular catch-up.", "Please review the doc before meeting."
    ]
    
    count = 0
    today = datetime.now()
    
    for (emp_id,) in employees:
        # Generate 3-6 random events for each employee
        num_events = random.randint(3, 6)
        
        for _ in range(num_events):
            title = random.choice(titles)
            desc = random.choice(descriptions)
            event_type = random.choice(event_types)
            
            # Generate a random deadline within the next 14 days
            days_offset = random.randint(0, 14)
            deadline = (today + timedelta(days=days_offset)).strftime("%Y-%m-%d")
            
            c.execute("""
                INSERT INTO employee_tasks (employee_id, title, description, deadline, event_type, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (emp_id, title, desc, deadline, event_type, 'pending'))
            
            count += 1
            
    conn.commit()
    conn.close()
    print(f"Successfully seeded {count} mock events/tasks for {len(employees)} employees.")

if __name__ == "__main__":
    seed_calendar_events()
