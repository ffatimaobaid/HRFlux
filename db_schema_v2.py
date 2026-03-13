import sqlite3
from datetime import datetime
import os

DB_PATH = "queries.db"

def create_enhanced_schema():
    """
    Create enhanced database schema for HRFlux Module 1 & 2.
    Includes employee profiles, leave balances, attendance, and approval workflows.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # ========== EMPLOYEES TABLE ==========
    c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            designation TEXT NOT NULL,
            joining_date TEXT NOT NULL,
            manager_id TEXT,
            casual_leave_balance INTEGER DEFAULT 10,
            sick_leave_balance INTEGER DEFAULT 10,
            annual_leave_balance INTEGER DEFAULT 14,
            salary REAL,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'terminated')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
        )
    """)
    
    # ========== ENHANCED LEAVE REQUESTS TABLE ==========
    c.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            leave_type TEXT NOT NULL CHECK(leave_type IN ('casual', 'sick', 'annual', 'emergency')),
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_days INTEGER NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'cancelled')),
            approver_id TEXT,
            approved_at DATETIME,
            approval_comments TEXT,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (approver_id) REFERENCES employees(employee_id)
        )
    """)
    
    # ========== ATTENDANCE TABLE ==========
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            date TEXT NOT NULL,
            check_in_time TEXT,
            check_out_time TEXT,
            status TEXT NOT NULL CHECK(status IN ('present', 'absent', 'late', 'half_day', 'on_leave')),
            remarks TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(employee_id, date),
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        )
    """)
    
    # ========== LEAVE BALANCE HISTORY TABLE ==========
    c.execute("""
        CREATE TABLE IF NOT EXISTS leave_balance_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            balance_before INTEGER,
            balance_after INTEGER,
            change_amount INTEGER,
            reason TEXT,
            related_request_id INTEGER,
            changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (related_request_id) REFERENCES leave_requests_v2(id)
        )
    """)
    
    # ========== WORKFLOW ESCALATIONS TABLE ==========
    c.execute("""
        CREATE TABLE IF NOT EXISTS workflow_escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            request_type TEXT NOT NULL,
            escalated_to TEXT,
            escalated_from TEXT,
            reason TEXT,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'resolved', 'cancelled')),
            escalated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved_at DATETIME,
            FOREIGN KEY (request_id) REFERENCES leave_requests_v2(id)
        )
    """)
    
    # ========== CHAT ESCALATIONS TABLE (New) ==========
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            username TEXT,
            query TEXT,
            full_history TEXT,
            reason TEXT,
            sensitivity_score REAL,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'resolved', 'cancelled')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved_at DATETIME,
            resolution_notes TEXT
        )
    """)
    
    # ========== EMPLOYEE TASKS TABLE (New) ==========
    c.execute("""
        CREATE TABLE IF NOT EXISTS employee_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            deadline TEXT,
            event_type TEXT CHECK(event_type IN ('task', 'event', 'deadline', 'meeting')),
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'completed', 'cancelled')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("Enhanced database schema created successfully!")


def migrate_existing_data():
    """
    Migrate data from old tables to new enhanced schema.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Check if old users table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if c.fetchone():
            # Migrate users to employees table
            c.execute("""
                INSERT OR IGNORE INTO employees (employee_id, username, password, full_name, email, department, designation, joining_date)
                SELECT 
                    'EMP' || substr('00000' || rowid, -5),
                    username,
                    password,
                    username,
                    username || '@company.com',
                    'General',
                    'Employee',
                    date('now')
                FROM users
            """)
            print("Migrated users to employees table")
        
        # Check if old leave_requests table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leave_requests'")
        if c.fetchone():
            # Migrate old leave requests to new table
            c.execute("""
                INSERT OR IGNORE INTO leave_requests_v2 
                (employee_id, leave_type, start_date, end_date, total_days, reason, status, submitted_at)
                SELECT 
                    (SELECT employee_id FROM employees WHERE username = lr.user LIMIT 1),
                    CASE 
                        WHEN type IS NULL OR type = 'general' THEN 'casual'
                        ELSE type
                    END,
                    start_date,
                    end_date,
                    julianday(end_date) - julianday(start_date) + 1,
                    reason,
                    status,
                    timestamp
                FROM leave_requests lr
                WHERE EXISTS (SELECT 1 FROM employees WHERE username = lr.user)
            """)
            print("Migrated leave requests to enhanced table")
        
        conn.commit()
    except Exception as e:
        print(f"Migration warning: {e}")
        conn.rollback()
    finally:
        conn.close()


def add_employee(employee_id, username, password, full_name, email, department, 
                designation, joining_date, manager_id=None, salary=None):
    """
    Add a new employee to the database.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO employees 
            (employee_id, username, password, full_name, email, department, designation, 
             joining_date, manager_id, salary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (employee_id, username, password, full_name, email, department, 
              designation, joining_date, manager_id, salary))
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        print(f"Error adding employee: {e}")
        return False
    finally:
        conn.close()


def get_employee(employee_id=None, username=None):
    """
    Retrieve employee information by ID or username.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if employee_id:
        c.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
    elif username:
        c.execute("SELECT * FROM employees WHERE username = ?", (username,))
    else:
        return None
    
    row = c.fetchone()
    conn.close()
    
    if row:
        columns = ['employee_id', 'username', 'password', 'full_name', 'email', 
                  'department', 'designation', 'joining_date', 'manager_id',
                  'casual_leave_balance', 'sick_leave_balance', 'annual_leave_balance',
                  'salary', 'status', 'created_at']
        return dict(zip(columns, row))
    return None


def get_leave_balance(employee_id):
    """
    Get current leave balances for an employee.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT casual_leave_balance, sick_leave_balance, annual_leave_balance
        FROM employees WHERE employee_id = ?
    """, (employee_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            'casual': row[0],
            'sick': row[1],
            'annual': row[2]
        }
    return None


def update_leave_balance(employee_id, leave_type, new_balance, reason=None, request_id=None):
    """
    Update leave balance and record history.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Get current balance
        balance_field = f"{leave_type}_leave_balance"
        c.execute(f"SELECT {balance_field} FROM employees WHERE employee_id = ?", (employee_id,))
        old_balance = c.fetchone()[0]
        
        # Update balance
        c.execute(f"""
            UPDATE employees 
            SET {balance_field} = ?
            WHERE employee_id = ?
        """, (new_balance, employee_id))
        
        # Record history
        change_amount = new_balance - old_balance
        c.execute("""
            INSERT INTO leave_balance_history 
            (employee_id, leave_type, balance_before, balance_after, change_amount, reason, related_request_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (employee_id, leave_type, old_balance, new_balance, change_amount, reason, request_id))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating leave balance: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_all_employees():
    """
    Retrieve all active employees.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM employees WHERE status = 'active' ORDER BY full_name")
    rows = c.fetchall()
    conn.close()
    
    columns = ['employee_id', 'username', 'password', 'full_name', 'email', 
              'department', 'designation', 'joining_date', 'manager_id',
              'casual_leave_balance', 'sick_leave_balance', 'annual_leave_balance',
              'salary', 'status', 'created_at']
    
    return [dict(zip(columns, row)) for row in rows]


if __name__ == "__main__":
    print("Creating enhanced database schema...")
    create_enhanced_schema()
    print("Migrating existing data...")
    migrate_existing_data()
    print("Database setup complete!")
