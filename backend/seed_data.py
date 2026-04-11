"""
Seed Data Script for HRFlux
Populates the database with sample employee records, leave balances, and test data
"""

from db_schema_v2 import create_enhanced_schema, migrate_existing_data, add_employee
from datetime import datetime, timedelta
import random

def seed_employees():
    """Create sample employee records with hierarchical structure."""
    
    print("📝 Creating sample employees...")
    
    # CEO (no manager)
    add_employee(
        employee_id="EMP00001",
        username="john.ceo",
        password="password123",
        full_name="John Smith",
        email="john.smith@company.com",
        department="Executive",
        designation="CEO",
        joining_date="2015-01-15",
        manager_id=None,
        salary=150000
    )
    
    # HR Manager (reports to CEO)
    add_employee(
        employee_id="EMP00002",
        username="sarah.hr",
        password="password123",
        full_name="Sarah Johnson",
        email="sarah.johnson@company.com",
        department="Human Resources",
        designation="HR Manager",
        joining_date="2016-03-20",
        manager_id="EMP00001",
        salary=85000
    )
    
    # IT Manager (reports to CEO)
    add_employee(
        employee_id="EMP00003",
        username="mike.it",
        password="password123",
        full_name="Mike Williams",
        email="mike.williams@company.com",
        department="Information Technology",
        designation="IT Manager",
        joining_date="2016-06-10",
        manager_id="EMP00001",
        salary=90000
    )
    
    # Sales Manager (reports to CEO)
    add_employee(
        employee_id="EMP00004",
        username="emily.sales",
        password="password123",
        full_name="Emily Davis",
        email="emily.davis@company.com",
        department="Sales",
        designation="Sales Manager",
        joining_date="2017-02-14",
        manager_id="EMP00001",
        salary=80000
    )
    
    # HR Team Members (report to HR Manager)
    add_employee(
        employee_id="EMP00005",
        username="david.hr",
        password="password123",
        full_name="David Brown",
        email="david.brown@company.com",
        department="Human Resources",
        designation="HR Executive",
        joining_date="2018-05-01",
        manager_id="EMP00002",
        salary=55000
    )
    
    add_employee(
        employee_id="EMP00006",
        username="lisa.hr",
        password="password123",
        full_name="Lisa Anderson",
        email="lisa.anderson@company.com",
        department="Human Resources",
        designation="Recruitment Specialist",
        joining_date="2019-08-15",
        manager_id="EMP00002",
        salary=52000
    )
    
    # IT Team Members (report to IT Manager)
    add_employee(
        employee_id="EMP00007",
        username="tom.dev",
        password="password123",
        full_name="Tom Wilson",
        email="tom.wilson@company.com",
        department="Information Technology",
        designation="Senior Developer",
        joining_date="2018-01-20",
        manager_id="EMP00003",
        salary=75000
    )
    
    add_employee(
        employee_id="EMP00008",
        username="anna.dev",
        password="password123",
        full_name="Anna Martinez",
        email="anna.martinez@company.com",
        department="Information Technology",
        designation="Full Stack Developer",
        joining_date="2019-11-05",
        manager_id="EMP00003",
        salary=68000
    )
    
    add_employee(
        employee_id="EMP00009",
        username="james.devops",
        password="password123",
        full_name="James Taylor",
        email="james.taylor@company.com",
        department="Information Technology",
        designation="DevOps Engineer",
        joining_date="2020-03-12",
        manager_id="EMP00003",
        salary=72000
    )
    
    # Sales Team Members (report to Sales Manager)
    add_employee(
        employee_id="EMP00010",
        username="robert.sales",
        password="password123",
        full_name="Robert Garcia",
        email="robert.garcia@company.com",
        department="Sales",
        designation="Sales Executive",
        joining_date="2018-09-01",
        manager_id="EMP00004",
        salary=58000
    )
    
    add_employee(
        employee_id="EMP00011",
        username="maria.sales",
        password="password123",
        full_name="Maria Rodriguez",
        email="maria.rodriguez@company.com",
        department="Sales",
        designation="Account Manager",
        joining_date="2019-04-18",
        manager_id="EMP00004",
        salary=62000
    )
    
    add_employee(
        employee_id="EMP00012",
        username="chris.sales",
        password="password123",
        full_name="Chris Lee",
        email="chris.lee@company.com",
        department="Sales",
        designation="Sales Representative",
        joining_date="2020-07-22",
        manager_id="EMP00004",
        salary=50000
    )
    
    # Marketing Team (report to CEO for now)
    add_employee(
        employee_id="EMP00013",
        username="jennifer.marketing",
        password="password123",
        full_name="Jennifer White",
        email="jennifer.white@company.com",
        department="Marketing",
        designation="Marketing Specialist",
        joining_date="2019-10-30",
        manager_id="EMP00001",
        salary=60000
    )
    
    # Finance Team (report to CEO)
    add_employee(
        employee_id="EMP00014",
        username="william.finance",
        password="password123",
        full_name="William Thompson",
        email="william.thompson@company.com",
        department="Finance",
        designation="Finance Manager",
        joining_date="2017-05-12",
        manager_id="EMP00001",
        salary=88000
    )
    
    add_employee(
        employee_id="EMP00015",
        username="sophia.finance",
        password="password123",
        full_name="Sophia Clark",
        email="sophia.clark@company.com",
        department="Finance",
        designation="Accountant",
        joining_date="2020-01-08",
        manager_id="EMP00014",
        salary=55000
    )
    
    print("✅ Created 15 sample employees with manager hierarchy")


def seed_sample_leave_requests():
    """Create some sample leave requests for testing workflow."""
    import sqlite3
    
    print("📝 Creating sample leave requests...")
    
    conn = sqlite3.connect("queries.db")
    c = conn.cursor()
    
    # Sample leave requests
    sample_requests = [
        # Pending requests
        ("EMP00007", "casual", "2025-01-15", "2025-01-17", 3, "Family event", "pending"),
        ("EMP00008", "sick", "2024-12-20", "2024-12-22", 3, "Medical appointment", "pending"),
        ("EMP00010", "annual", "2025-02-10", "2025-02-14", 5, "Vacation", "pending"),
        
        # Approved requests (past)
        ("EMP00011", "casual", "2024-11-05", "2024-11-06", 2, "Personal work", "approved"),
        ("EMP00012", "sick", "2024-10-15", "2024-10-16", 2, "Flu", "approved"),
        
        # Rejected request
        ("EMP00009", "casual", "2024-12-25", "2024-12-27", 3, "Holiday travel", "rejected"),
    ]
    
    for req in sample_requests:
        try:
            c.execute("""
                INSERT INTO leave_requests_v2 
                (employee_id, leave_type, start_date, end_date, total_days, reason, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, req)
        except Exception as e:
            print(f"⚠️ Warning: Could not insert sample request: {e}")
    
    conn.commit()
    conn.close()
    
    print("✅ Created sample leave requests")


def seed_attendance_records():
    """Create sample attendance records for the past week."""
    import sqlite3
    from datetime import datetime, timedelta
    
    print("📝 Creating sample attendance records...")
    
    conn = sqlite3.connect("queries.db")
    c = conn.cursor()
    
    # Get all employees
    c.execute("SELECT employee_id FROM employees WHERE status = 'active'")
    employees = [row[0] for row in c.fetchall()]
    
    # Create attendance for last 5 working days
    today = datetime.now()
    statuses = ['present', 'present', 'present', 'present', 'late', 'present']
    
    for i in range(5):
        date = (today - timedelta(days=i+1)).strftime('%Y-%m-%d')
        for emp_id in employees:
            status = random.choice(statuses)
            check_in = "09:00:00" if status == 'present' else "09:45:00"
            check_out = "18:00:00"
            
            try:
                c.execute("""
                    INSERT INTO attendance 
                    (employee_id, date, check_in_time, check_out_time, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (emp_id, date, check_in, check_out, status))
            except:
                pass  # Skip if duplicate
    
    conn.commit()
    conn.close()
    
    print("✅ Created sample attendance records")


def main():
    """Main seed data function."""
    print("=" * 60)
    print("🌱 HRFlux Database Seeding Script")
    print("=" * 60)
    
    # Step 1: Create schema
    print("\n1️⃣ Creating enhanced database schema...")
    create_enhanced_schema()
    
    # Step 2: Migrate existing data
    print("\n2️⃣ Migrating existing data...")
    migrate_existing_data()
    
    # Step 3: Seed employees
    print("\n3️⃣ Seeding sample employees...")
    seed_employees()
    
    # Step 4: Seed leave requests
    print("\n4️⃣ Seeding sample leave requests...")
    seed_sample_leave_requests()
    
    # Step 5: Seed attendance
    print("\n5️⃣ Seeding sample attendance records...")
    seed_attendance_records()
    
    print("\n" + "=" * 60)
    print("✅ Database seeding complete!")
    print("=" * 60)
    print("\n📊 Summary:")
    print("  - 15 employees created with manager hierarchy")
    print("  - Leave balances: Casual (10), Sick (10), Annual (14)")
    print("  - Sample leave requests created (pending, approved, rejected)")
    print("  - Attendance records for last 5 days")
    print("\n🔐 Sample Login Credentials:")
    print("  - CEO: john.ceo / password123")
    print("  - HR Manager: sarah.hr / password123")
    print("  - IT Manager: mike.it / password123")
    print("  - Developer: tom.dev / password123")
    print("  - Sales: robert.sales / password123")
    print("=" * 60)

if __name__ == "__main__":
    main()
