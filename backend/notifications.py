import sqlite3
import json
import logging
from datetime import datetime, timedelta

DB_PATH = "queries.db"
logger = logging.getLogger(__name__)

class NotificationManager:
    @staticmethod
    def _resolve_user_id(user_id):
        """Helper to ensure we are using employee_id, looking up by username if necessary."""
        # Common roles
        if user_id in ["ADMIN", "HR_MANAGER", "HR_ADMIN"]:
            return user_id
            
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            # First, check if it's already a valid employee_id
            c.execute("SELECT employee_id FROM employees WHERE employee_id = ?", (user_id,))
            res = c.fetchone()
            if res:
                return res[0]
            
            # If not, try looking up by username
            c.execute("SELECT employee_id FROM employees WHERE username = ?", (user_id,))
            res = c.fetchone()
            if res:
                return res[0]
            
            # Fallback to original if not found (might be a system role not in employees table)
            return user_id
        finally:
            conn.close()

    @staticmethod
    def create_notification(user_id, n_type, title, message, action_id=None, action_params=None, priority=0, expires_in_days=30):
        """Create a new persistent notification."""
        user_id = NotificationManager._resolve_user_id(user_id)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()
        
        try:
            c.execute("""
                INSERT INTO notifications (user_id, type, title, message, action_id, action_params, priority, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, n_type, title, message, action_id, json.dumps(action_params) if action_params else None, priority, expires_at))
            conn.commit()
            logger.info(f"Created {n_type} notification for {user_id}: {title}")
            return c.lastrowid
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def get_notifications(user_id, include_read=True):
        """Fetch notifications for a user."""
        user_id = NotificationManager._resolve_user_id(user_id)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        query = "SELECT * FROM notifications WHERE user_id = ? AND status != 'dismissed'"
        if not include_read:
            query += " AND status = 'unread'"
        query += " ORDER BY priority DESC, created_at DESC LIMIT 50"
        
        c.execute(query, (user_id,))
        rows = c.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            d = dict(row)
            if d['action_params']:
                try:
                    d['action_params'] = json.loads(d['action_params'])
                except:
                    pass
            result.append(d)
        return result

    @staticmethod
    def update_status(notif_id, status):
        """Update notification status: read, dismissed, escalated."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE notifications SET status = ? WHERE id = ?", (status, notif_id))
        conn.commit()
        conn.close()

    @staticmethod
    def check_slas():
        """
        Background task to check for SLA breaches in leave requests and escalations.
        Triggers new notifications for HR when a breach is detected.
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        try:
            # Get SLA rules
            c.execute("SELECT * FROM sla_rules")
            rules = {r['task_type']: r for r in c.fetchall()}
            
            # 1. Check Pending Leave Requests
            if 'leave' in rules:
                rule = rules['leave']
                # Join with employees to get manager_id
                c.execute("""
                    SELECT lr.*, e.full_name as emp_name, e.manager_id
                    FROM leave_requests_v2 lr
                    JOIN employees e ON lr.employee_id = e.employee_id
                    WHERE lr.status = 'pending'
                """)
                requests = c.fetchall()
                
                for req in requests:
                    submitted_at = datetime.fromisoformat(req['submitted_at'].replace(' ', 'T'))
                    hours_pending = (datetime.now() - submitted_at).total_seconds() / 3600
                    
                    if hours_pending > rule['critical_hours']:
                        # Critical Breach - Notify HR
                        NotificationManager.create_notification(
                            user_id=rule['esc_target_role'], # Using role name for system-wide alerts
                            n_type='critical',
                            title="SLA CRITICAL: Leave Approval",
                            message=f"Leave request ID {req['id']} for {req['emp_name']} has been pending for over {rule['critical_hours']} hours.",
                            action_id="view_pending_leaves",
                            priority=2
                        )
                    elif hours_pending > rule['warning_hours']:
                        # Warning - Notify Manager
                        if req['manager_id']:
                            NotificationManager.create_notification(
                                user_id=req['manager_id'],
                                n_type='warning',
                                title="SLA Warning: Leave Approval",
                                message=f"Leave request for {req['emp_name']} is approaching SLA limit.",
                                action_id="view_pending_leaves",
                                priority=1
                            )

            # 2. Check Chat Escalations
            if 'escalation' in rules:
                rule = rules['escalation']
                c.execute("SELECT * FROM chat_escalations WHERE status = 'pending'")
                escalations = c.fetchall()
                
                for esc in escalations:
                    created_at = datetime.fromisoformat(esc['created_at'].replace(' ', 'T'))
                    hours_pending = (datetime.now() - created_at).total_seconds() / 3600
                    
                    if hours_pending > rule['critical_hours']:
                        NotificationManager.create_notification(
                            user_id='ADMIN', # Escalation to Admin/HR
                            n_type='critical',
                            title="SLA BREACH: HR Escalation",
                            message=f"Complaints from {esc['username']} (ID: {esc['id']}) has not been resolved for {rule['critical_hours']}h.",
                            priority=2
                        )

        except Exception as e:
            logger.error(f"Error in SLA engine: {e}")
        finally:
            conn.close()
