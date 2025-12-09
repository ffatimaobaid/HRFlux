import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = "queries.db"

def init_db():
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
    c = conn.cursor()
    
    # First check the new employees table
    c.execute("SELECT * FROM employees WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    
    # If not found, check the old users table for backward compatibility
    if not user:
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
    
    conn.close()
    return user is not None
