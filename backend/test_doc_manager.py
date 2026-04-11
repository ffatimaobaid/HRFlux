import requests
import os

BASE_URL = "http://localhost:8000"

def test_document_manager():
    print("--- Testing Document Manager API ---")
    
    # 1. Login to get token
    login_data = {"username": "ADMIN", "password": "ADMIN"}
    try:
        res = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        token = res.json().get("token")
        print(f"✅ Login successful. Token: {token[:10]}...")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 2. List documents
    try:
        res = requests.get(f"{BASE_URL}/api/admin/documents", headers=headers)
        print(f"✅ List documents: {res.status_code}")
        print(f"   Response: {res.json()}")
    except Exception as e:
        print(f"❌ List documents failed: {e}")

    # 3. Upload a test document
    test_file_path = "test_policy.txt"
    with open(test_file_path, "w") as f:
        f.write("This is a test policy about remote work. Remote work is allowed 2 days a week.")
        
    try:
        with open(test_file_path, "rb") as f:
            files = {"file": ("test_policy.txt", f, "text/plain")}
            res = requests.post(f"{BASE_URL}/api/admin/documents/upload", headers=headers, files=files)
            print(f"✅ Upload document: {res.status_code}")
            print(f"   Response: {res.json()}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

if __name__ == "__main__":
    test_document_manager()
