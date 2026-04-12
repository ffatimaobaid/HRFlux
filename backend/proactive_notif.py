import sqlite3
from datetime import datetime, date
import os
import json
import concurrent.futures
from gemini_llm import query_gemini

DB_PATH = "queries.db"

class ProactiveNotifEngine:
    @staticmethod
    def get_smart_notifications(employee_id):
        """
        Gathers intelligent notifications for a specific employee.
        Returns a list of dicts: {type, title, message, action_label, action_params}
        """
        from notifications import NotificationManager
        employee_id = NotificationManager._resolve_user_id(employee_id)
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        notifications = []
        today_str = date.today().isoformat()
        
        # 1. Check Attendance (Removed as requested)
            
        # 2. Check Tasks / Deadlines
        c.execute("""
            SELECT id, title, deadline FROM employee_tasks 
            WHERE employee_id = ? AND status = 'pending' 
            AND deadline <= ?
        """, (employee_id, today_str))
        tasks = c.fetchall()
        for t in tasks:
            urgency = "TODAY" if t['deadline'] == today_str else "SOON"
            notifications.append({
                "id": t['id'],  # Unique task ID
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
                    "id": 1001,  # Fixed ID for leave balance
                    "type": "info",
                    "title": "Leave Balance Notice",
                    "message": f"Your {', '.join(low_balances)} leave balance is running low. Plan your time accordingly.",
                    "action_label": "Check Balances",
                    "action_id": "view_leaves"
                })

        # 4. Fetch persistent unread notifications
        c.execute("""
            SELECT id, type, title, message 
            FROM notifications 
            WHERE user_id = ? AND status = 'unread'
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC
        """, (employee_id, datetime.now().isoformat()))
        persistent = [dict(r) for r in c.fetchall()]
        
        # Merge and prioritize status updates to the top (Approved or Rejected)
        p_status = [n for n in persistent if "Approved" in n['title'] or "Rejected" in n['title']]
        p_other = [n for n in persistent if "Approved" not in n['title'] and "Rejected" not in n['title']]
        
        # Combine: Status updates first, then urgent tasks/balances, then others
        notifications = p_status + notifications + p_other

        # 5. Content Insights (Fallback if nothing else)
        if not notifications:
            notifications.append({
                "id": 1002,
                "type": "success",
                "title": "Daily Tip",
                "message": "You are all caught up! Remember to take 5-minute breaks every hour for better focus.",
                "action_label": "Wellness Policy",
                "action_id": "view_policy_wellness"
            })

        conn.close()
        
        # 5. AI Spicing (Creative Content Layer)
        return ProactiveNotifEngine._spice_up_notifications(notifications)

    @staticmethod
    def _spice_up_notifications(notifications):
        """
        Uses Gemini to rewrite notification text into something more creative and engaging.
        """
        if not notifications:
            return []

        try:
            # We only spice up a limited number to keep it fast
            to_spice = notifications[:3]
            remaining = notifications[3:]
            
            prompt = f"""
            You are a creative HR assistant named HRFLUX. 
            Rewrite the following HR notifications to be more engaging and friendly.
            Strictly do NOT use any emojis in the title or message.
            Keep the tone professional and supportive.
            Keep the core meaning and any specific data (dates, IDs, task names) exactly the same.
            
            Notifications to rewrite:
            {[{ 'id': n['id'], 'title': n['title'], 'message': n['message'] } for n in to_spice]}
            
            Return ONLY a JSON array of objects with 'id', 'title', and 'message' keys.
            Do not include any other text or markdown formatting.
            """
            
            import re
            import ast
            def strip_emojis(text):
                return re.sub(r'[^\x00-\x7F]+', '', text).strip()

            response = query_gemini("", prompt, model_name="gemini-1.5-flash")
            
            clean_response = response.strip()
            # Standard cleanup
            if "```json" in clean_response:
                clean_response = clean_response.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_response:
                clean_response = clean_response.split("```")[1].split("```")[0].strip()
            
            # Extract array part
            match = re.search(r'(\[.*\])', clean_response, re.DOTALL)
            if match:
                clean_response = match.group(1)
            
            try:
                spiced_data = json.loads(clean_response)
            except:
                try:
                    # Fallback to ast for single quotes or Python-like format
                    spiced_data = ast.literal_eval(clean_response)
                except:
                    print(f"⚠️ Both json and ast failed to parse: {clean_response[:100]}")
                    return notifications

            # Map spiced content back to original notifications
            if not isinstance(spiced_data, list):
                return notifications
                
            spiced_map = {item.get('id'): item for item in spiced_data if isinstance(item, dict) and 'id' in item}
            
            for notif in to_spice:
                nid = notif.get('id')
                if nid in spiced_map:
                    notif['title'] = strip_emojis(spiced_map[nid].get('title', notif['title']))
                    notif['message'] = strip_emojis(spiced_map[nid].get('message', notif['message']))
            
            return to_spice + remaining
            
        except Exception as e:
            print(f"⚠️ Notification spicing failed: {e}. Returning static content.")
            return notifications
