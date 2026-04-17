import sys
import os

# Add the current directory to path
sys.path.append(os.getcwd())

from rag import ingest_document

def verify():
    test_file = os.path.join("policy_docs", "PPIT Assignment 2.pdf")
    if not os.path.exists(test_file):
        print(f"File not found: {test_file}")
        return
    
    print(f"--- Verifying Ingestion for {test_file} ---")
    try:
        num_chunks, avg_tokens, doc_id = ingest_document(test_file)
        print(f"--- RESULTS ---")
        print(f"Chunks: {num_chunks}")
        print(f"Avg Tokens: {avg_tokens}")
        print(f"Doc ID: {doc_id}")
    except Exception as e:
        print(f"--- FAILED ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
