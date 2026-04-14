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
    
    # Add time fields to employee_tasks table if they don't exist
    add_time_fields_to_tasks(conn, c)
    
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
            conversation_summary TEXT,
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
            start_time TEXT,
            end_time TEXT,
            event_type TEXT CHECK(event_type IN ('task', 'event', 'deadline', 'meeting')),
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'completed', 'cancelled')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        )
    """)
    
    # ========== MULTI-MODAL RAG TABLES (New) ==========
    c.execute("""
        CREATE TABLE IF NOT EXISTS multimodal_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER,
            total_chunks INTEGER DEFAULT 0,
            processing_results TEXT,
            uploaded_by TEXT,
            upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_searched TIMESTAMP,
            search_count INTEGER DEFAULT 0,
            tags TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS multimodal_search_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            query_type TEXT,
            results_count INTEGER,
            search_time_ms REAL,
            searched_by TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ========== NOTIFICATIONS TABLE (New) ==========
    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('info', 'warning', 'success', 'critical')),
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'unread' CHECK(status IN ('unread', 'read', 'dismissed', 'escalated')),
            priority INTEGER DEFAULT 0,
            action_id TEXT,
            action_params TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME
        )
    """)

    # ========== ANNOUNCEMENTS TABLE (New) ==========
    c.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            priority TEXT DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high')),
            created_by TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES employees(employee_id)
        )
    """)
    
    # ========== SECURITY AUDIT LOGS TABLE (New) ==========
    c.execute("""
        CREATE TABLE IF NOT EXISTS security_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            action TEXT NOT NULL,
            target_id TEXT,
            ip_address TEXT,
            status TEXT DEFAULT 'success',
            metadata TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ========== SLA RULES TABLE (New) ==========
    c.execute("""
        CREATE TABLE IF NOT EXISTS sla_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT UNIQUE NOT NULL, -- 'leave', 'escalation', 'document'
            warning_hours INTEGER DEFAULT 24,
            critical_hours INTEGER DEFAULT 48,
            esc_target_role TEXT DEFAULT 'HR'
        )
    """)

    # Seed default SLA rules
    sla_defaults = [
        ('leave', 24, 48, 'HR_MANAGER'),
        ('escalation', 12, 24, 'ADMIN'),
        ('document', 48, 72, 'HR_ADMIN')
    ]
    for task, warn, crit, role in sla_defaults:
        c.execute("INSERT OR IGNORE INTO sla_rules (task_type, warning_hours, critical_hours, esc_target_role) VALUES (?, ?, ?, ?)",
                  (task, warn, crit, role))
    
    conn.commit()
    conn.close()
    print("Enhanced database schema created successfully!")

def seed_default_users(conn, c):
    """Seed the database with default users if they don't exist."""
    users_to_seed = [
        ('EMP001', 'test_user', 'password123', 'Test Employee', 'test@hrflux.ai', 'Engineering', 'Developer', '2024-01-01', 50000),
        ('ADM001', 'ADMIN', 'ADMIN', 'System Administrator', 'admin@hrflux.ai', 'HR', 'Admin', '2023-01-01', 100000)
    ]
    
    for emp_id, uname, pwd, name, email, dept, desig, join_date, sal in users_to_seed:
        c.execute("SELECT 1 FROM employees WHERE username = ?", (uname,))
        if not c.fetchone():
            c.execute("""
                INSERT INTO employees 
                (employee_id, username, password, full_name, email, department, designation, joining_date, salary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (emp_id, uname, pwd, name, email, dept, desig, join_date, sal))
            print(f"Seeded user: {uname}")

def add_time_fields_to_tasks(conn, c):
    """
    Add start_time and end_time fields to employee_tasks table for better time tracking.
    This function is called during schema creation to ensure time fields are always available.
    """
    try:
        # Check if columns already exist
        c.execute("PRAGMA table_info(employee_tasks)")
        columns = [row[1] for row in c.fetchall()]
        
        if 'start_time' not in columns:
            c.execute("""
                ALTER TABLE employee_tasks 
                ADD COLUMN start_time TEXT
            """)
            print("Added start_time column to employee_tasks table")
        
        if 'end_time' not in columns:
            c.execute("""
                ALTER TABLE employee_tasks 
                ADD COLUMN end_time TEXT
            """)
            print("Added end_time column to employee_tasks table")
        
        conn.commit()
        
    except Exception as e:
        print(f"Warning: Could not add time fields to employee_tasks table: {e}")
        # Don't rollback the entire transaction for this optional enhancement


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
        
        # Ensure default users exist
        seed_default_users(conn, c)
        
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
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Check if employees table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employees'")
        table_exists = c.fetchone()
        
        if not table_exists:
            print("Employees table does not exist, returning empty list")
            return []
        
        c.execute("SELECT * FROM employees WHERE status = 'active' ORDER BY full_name")
        rows = c.fetchall()
        conn.close()
        
        columns = ['employee_id', 'username', 'password', 'full_name', 'email', 
                  'department', 'designation', 'joining_date', 'manager_id',
                  'casual_leave_balance', 'sick_leave_balance', 'annual_leave_balance',
                  'salary', 'status', 'created_at']
        
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error in get_all_employees: {e}")
        return []


if __name__ == "__main__":
    print("Creating enhanced database schema...")
    create_enhanced_schema()
    print("Migrating existing data...")
    migrate_existing_data()
    print("Database setup complete!")
