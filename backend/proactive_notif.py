
import sqlite3
from datetime import datetime, date
import os

DB_PATH = "queries.db"

class ProactiveNotifEngine:
    @staticmethod
    def get_smart_notifications(employee_id):
        """
        Gathers intelligent notifications for a specific employee.
        Returns a list of dicts: {type, title, message, action_label, action_params}
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        notifications = []
        today_str = date.today().isoformat()
        
        # 1. Check Attendance
        c.execute("SELECT check_in_time FROM attendance WHERE employee_id = ? AND date = ?", (employee_id, today_str))
        attendance = c.fetchone()
        if not attendance or not attendance['check_in_time']:
            notifications.append({
                "type": "warning",
                "title": "Clock-in Reminder",
                "message": "You haven't checked in for today yet. Stay compliant with the attendance policy!",
                "action_label": "Check In Now",
                "action_id": "check_in"
            })
            
        # 2. Check Tasks / Deadlines
        c.execute("""
            SELECT title, deadline FROM employee_tasks 
            WHERE employee_id = ? AND status = 'pending' 
            AND deadline <= ?
        """, (employee_id, today_str))
        tasks = c.fetchall()
        for t in tasks:
            urgency = "TODAY" if t['deadline'] == today_str else "SOON"
            notifications.append({
                "type": "critical" if urgency == "TODAY" else "info",
                "title": f"Deadline Alert: {urgency}",
                "message": f"Your task '{t['title']}' is due {t['deadline'].split('-')[-1]}. Don't miss it!",
                "action_label": "View Tasks",
                "action_id": "view_tasks"
            })
            
        # 3. Check Leave Balances
        c.execute("""
            SELECT casual_leave_balance, sick_leave_balance, annual_leave_balance 
            FROM employees WHERE employee_id = ?
        """, (employee_id,))
        emp = c.fetchone()
        if emp:
            low_balances = []
            if emp['casual_leave_balance'] < 2: low_balances.append("Casual")
            if emp['sick_leave_balance'] < 2: low_balances.append("Sick")
            
            if low_balances:
                notifications.append({
                    "type": "info",
                    "title": "Leave Balance Notice",
                    "message": f"Your {', '.join(low_balances)} leave balance is running low. Plan your time accordingly.",
                    "action_label": "Check Balances",
                    "action_id": "view_leaves"
                })

        # 4. Content Insights (Generic but smart-themed)
        # Randomly suggest a policy if no urgent notifications
        if not notifications:
            notifications.append({
                "type": "success",
                "title": "Daily Tip",
                "message": "You are all caught up! Remember to take 5-minute breaks every hour for better focus.",
                "action_label": "Wellness Policy",
                "action_id": "view_policy_wellness"
            })

        conn.close()
        return notifications
