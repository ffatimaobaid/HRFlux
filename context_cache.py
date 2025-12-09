# context_cache.py

import sqlite3
from datetime import datetime, timedelta

# Initialize or connect to the SQLite DB
conn = sqlite3.connect('query_cache.db', check_same_thread=False)
cursor = conn.cursor()

# Create the table if not exists
cursor.execute('''
CREATE TABLE IF NOT EXISTS query_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    question TEXT,
    answer TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

def add_to_cache(user_id, question, answer):
    cursor.execute(
        "INSERT INTO query_cache (user_id, question, answer, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, question, answer, datetime.now())
    )
    conn.commit()

def get_recent_context(user_id, hours=24):
    cutoff = datetime.now() - timedelta(hours=hours)
    cursor.execute(
        "SELECT question, answer FROM query_cache WHERE user_id = ? AND timestamp >= ? ORDER BY timestamp ASC",
        (user_id, cutoff)
    )
    return cursor.fetchall()
