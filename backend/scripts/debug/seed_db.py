import sqlite3
from db_schema_v2 import create_enhanced_schema, migrate_existing_data

def seed_db():
    create_enhanced_schema()
    
    conn = sqlite3.connect('queries.db')
    c = conn.cursor()

    # Insert employee data directly with balances
    c.execute("""
    INSERT OR IGNORE INTO employees 
    (employee_id, username, password, full_name, email, department, designation, joining_date, casual_leave_balance, sick_leave_balance, annual_leave_balance) 
    VALUES 
    ('EMP00001', 'admin', 'admin', 'Admin User', 'admin@company.com', 'HR', 'Admin', '2024-01-01', 5, 10, 18),
    ('EMP00002', 'john', 'password123', 'John Doe', 'john@company.com', 'IT', 'Developer', '2024-02-15', 5, 10, 14),
    ('EMP00003', 'sarah', 'password123', 'Sarah Smith', 'sarah@company.com', 'Sales', 'Manager', '2023-11-01', 5, 10, 14)
    """)

    conn.commit()
    print("Database seeded successfully with 'admin', 'john', and 'sarah'.")
    conn.close()

if __name__ == "__main__":
    seed_db()
