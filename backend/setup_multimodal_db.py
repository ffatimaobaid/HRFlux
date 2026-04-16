import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "queries.db")

def setup_db():
    print(f"🔧 Setting up Multimodal RAG database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create multimodal_files table
    c.execute("""
        CREATE TABLE IF NOT EXISTS multimodal_files (
            doc_id TEXT PRIMARY KEY,
            filename TEXT,
            file_path TEXT,
            file_type TEXT,
            file_size INTEGER,
            total_chunks INTEGER,
            processing_results TEXT,
            uploaded_by TEXT,
            upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Multimodal database setup complete.")

if __name__ == "__main__":
    setup_db()
