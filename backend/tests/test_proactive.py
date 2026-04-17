
import sys
import os
sys.path.append(os.getcwd())
from proactive_notif import ProactiveNotifEngine

def test_notifs():
    # Test for a mock employee ID
    # Note: This depends on the DB state. 
    # Since we can't easily mock the DB connection in the script without more boilerplate, 
    # we'll just check if the class loads and the method runs.
    try:
        notifs = ProactiveNotifEngine.get_smart_notifications("EMP00001")
        print(f"Successfully fetched {len(notifs)} notifications.")
        for n in notifs:
            print(f"- [{n['type'].upper()}] {n['title']}: {n['message']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_notifs()
