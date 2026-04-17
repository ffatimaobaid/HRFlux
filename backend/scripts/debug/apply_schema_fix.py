from db_schema_v2 import create_enhanced_schema
try:
    create_enhanced_schema()
    print("Schema updated successfully.")
except Exception as e:
    print(f"Error: {e}")
