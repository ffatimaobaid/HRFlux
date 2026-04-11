import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "queries.db"

def init_db():
    # Initialize the enhanced schema which includes all tables
    from db_schema_v2 import create_enhanced_schema, migrate_existing_data
    
    # Create all tables including the enhanced ones
    create_enhanced_schema()
    
    # Migrate any existing data and ensure time fields are added
    migrate_existing_data()
    
    # Also create the legacy tables for backwards compatibility
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            question TEXT,
            answer TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT,
            uploaded_at TEXT,
            avg_tokens REAL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT,
            text TEXT,
            embedding BLOB
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            type TEXT,
            start_date TEXT,
            end_date TEXT,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def init_user_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_document_metadata(doc_id, filename, avg_tokens):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO documents (id, filename, uploaded_at, avg_tokens) VALUES (?, ?, ?, ?)",
              (doc_id, filename, datetime.now().isoformat(), avg_tokens))
    conn.commit()
    conn.close()


def delete_document_metadata(doc_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()


def get_all_documents():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM documents")
    rows = c.fetchall()
    conn.close()
    return rows


def get_document_filenames_by_ids(doc_ids):
    """Return filenames for a list of document IDs (for debug/source display)."""
    if not doc_ids:
        return []

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        placeholders = ",".join(["?"] * len(doc_ids))
        c.execute(f"SELECT id, filename FROM documents WHERE id IN ({placeholders})", doc_ids)
        rows = c.fetchall()
    finally:
        conn.close()

    id_to_name = {doc_id: filename for doc_id, filename in rows}
    # Preserve input order, fall back to doc_id if filename missing
    return [id_to_name.get(d, d) for d in doc_ids]


def add_document_chunks(doc_id, chunks, embeddings=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for i, chunk in enumerate(chunks):
        embedding = embeddings[i] if embeddings else None
        c.execute(
            "INSERT INTO document_chunks (doc_id, text, embedding) VALUES (?, ?, ?)",
            (doc_id, chunk, embedding)
        )
    conn.commit()
    conn.close()


def get_all_chunks():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT text FROM document_chunks ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def save_log(user, question, answer):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO logs (user, question, answer) VALUES (?, ?, ?)", (user, question, answer))
    conn.commit()
    conn.close()


def get_logs(user=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if user:
        c.execute("SELECT * FROM logs WHERE user = ? ORDER BY timestamp DESC", (user,))
    else:
        c.execute("SELECT * FROM logs ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def save_leave_request(user, leave_type, start_date, end_date, reason):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO leave_requests (user, type, start_date, end_date, reason)
        VALUES (?, ?, ?, ?, ?)
    """, (user, leave_type, start_date, end_date, reason))
    conn.commit()
    conn.close()


def save_chat_message(user, question, answer, important=False):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO logs (user, question, answer, timestamp)
                 VALUES (?, ?, ?, ?)""",
              (user, question, answer, datetime.now()))
    conn.commit()
    conn.close()


def get_recent_history(user, limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT question, answer FROM logs
        WHERE user = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (user, limit))
    rows = c.fetchall()
    conn.close()
    return rows[::-1]


def get_recent_context(user, hours=24):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    cutoff_time = datetime.now() - timedelta(hours=hours)
    c.execute("""
        SELECT question, answer FROM logs
        WHERE user = ? AND timestamp > ?
        ORDER BY timestamp ASC
    """, (user, cutoff_time.isoformat()))
    context = c.fetchall()
    conn.close()
    return context


def update_user_session(user):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO user_sessions (user) VALUES (?)", (user,))
    conn.commit()
    conn.close()


def cleanup_old_sessions(retention_hours=24):
    cutoff = datetime.now() - timedelta(hours=retention_hours)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff.isoformat(),))
    conn.commit()
    conn.close()


def delete_user_history(user):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM logs WHERE user = ?", (user,))
    conn.commit()
    conn.close()


def signup_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    # Use Row factory to handle results by name more easily
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. First, authenticate the user. Check both tables.
    authenticated = False
    
    # Check employees table
    c.execute("SELECT employee_id FROM employees WHERE username = ? AND password = ?", (username, password))
    if c.fetchone():
        authenticated = True
    
    # If not found, check legacy users table
    if not authenticated:
        c.execute("SELECT username FROM users WHERE username = ? AND password = ?", (username, password))
        if c.fetchone():
            authenticated = True
    
    if authenticated:
        # 2. Get the full employee record for the authenticated user
        c.execute("SELECT * FROM employees WHERE username = ?", (username,))
        emp_row = c.fetchone()
        
        conn.close()
        
        if emp_row:
            return dict(emp_row)
        else:
            # User exists in legacy table but not in employees table
            # Return a minimal dict but don't point to EMP001 (Test Employee)
            return {
                'username': username, 
                'employee_id': f'TEMP_{username}', 
                'full_name': username,
                'email': f'{username}@hrflux.ai',
                'department': 'General',
                'designation': 'Employee',
                'joining_date': '2024-01-01',
                'casual_leave_balance': 0,
                'sick_leave_balance': 0,
                'annual_leave_balance': 0,
                'status': 'active'
            }
            
    conn.close()
    return None


def add_employee_task(employee_id, title, description, deadline, event_type, status='pending'):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO employee_tasks (employee_id, title, description, deadline, event_type, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (employee_id, title, description, deadline, event_type, status))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding task: {e}")
        return False
    finally:
        conn.close()

def get_employee_tasks(employee_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM employee_tasks WHERE employee_id = ? ORDER BY COALESCE(deadline, '9999-12-31') ASC", (employee_id,))
    rows = c.fetchall()
    conn.close()
    
    columns = ['id', 'employee_id', 'title', 'description', 'deadline', 'event_type', 'status', 'created_at']
    return [dict(zip(columns, row)) for row in rows]

def update_employee_task_status(task_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("UPDATE employee_tasks SET status = ? WHERE id = ?", (status, task_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()
