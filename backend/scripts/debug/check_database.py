import sqlite3
import os

def check_database():
    try:
        db_path = "queries.db"
        print(f"🔍 Checking database at: {os.path.abspath(db_path)}")
        
        if not os.path.exists(db_path):
            print("❌ Database file does not exist. Creating a new one...")
            open(db_path, 'a').close()
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("\n📋 Available tables:")
        for table in tables:
            print(f"- {table[0]}")
            # Show table structure
            cursor.execute(f"PRAGMA table_info({table[0]})")
            columns = cursor.fetchall()
            print("  Columns:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        
        # Check if employees table has data
        try:
            cursor.execute("SELECT * FROM employees LIMIT 5")
            users = cursor.fetchall()
            if users:
                print("\n👤 Sample user data:")
                for user in users:
                    print(f"- {user}")
            else:
                print("\nℹ️ No users found in the employees table.")
        except Exception as e:
            print(f"\n❌ Error reading employees table: {str(e)}")
        
        # Check document_chunks for RAG data
        try:
            cursor.execute("SELECT COUNT(*) FROM document_chunks")
            count = cursor.fetchone()[0]
            print(f"\n📄 Document chunks in RAG system: {count}")
        except:
            print("\nℹ️ No document_chunks table found (this might be normal if no documents have been indexed)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database error: {str(e)}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🔍 HR Chatbot Database Checker 🔍\n" + "="*50)
    if check_database():
        print("\n✅ Database check completed successfully")
    else:
        print("\n❌ Database check encountered issues")
