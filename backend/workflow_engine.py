"""
Workflow Engine for HRFlux
Handles leave request approvals, balance validation, and escalations
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from db_schema_v2 import get_employee, get_leave_balance, update_leave_balance
from notifications import NotificationManager
from guardrails import ContentFilter, InputValidator, SecurityLogger

logger = logging.getLogger(__name__)

DB_PATH = "queries.db"


class LeaveWorkflowEngine:
    """
    Manages leave request workflow including validation, approvals, and escalations.
    """
    
    @staticmethod
    def calculate_leave_days(start_date, end_date):
        """Calculate number of leave days excluding weekends."""
        from datetime import datetime
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        total_days = (end - start).days + 1
        # For simplicity, returning total days (can enhance with weekend exclusion)
        return total_days
    
    
    @staticmethod
    def validate_leave_request(employee_id, leave_type, start_date, end_date, reason):
        """
        Validate if employee has sufficient leave balance with content filtering.
        
        Returns:
            dict: {'valid': bool, 'message': str, 'days_required': int, 'balance': int}
        """
        # Apply content filtering to reason
        content_filter = ContentFilter.filter_content(reason)
        if not content_filter['allowed']:
            SecurityLogger.log_security_event('inappropriate_leave_reason', {
                'employee_id': employee_id,
                'original_reason': reason,
                'sanitized_reason': content_filter['sanitized_text'],
                'filter_results': content_filter
            })
            
            return {
                'valid': False,
                'message': 'Inappropriate content detected in leave reason',
                'days_required': 0,
                'balance': 0
            }
        
        # Validate reason length and content using dictionary format
        leave_request_data = {
            'employee_id': employee_id,
            'leave_type': leave_type,
            'start_date': start_date,
            'end_date': end_date,
            'reason': content_filter['sanitized_text']
        }
        validation = InputValidator.validate_leave_request(leave_request_data)
        
        if not validation['valid']:
            SecurityLogger.log_security_event('leave_validation_failed', {
                'employee_id': employee_id,
                'validation_errors': validation['errors'],
                'sanitized_reason': content_filter['sanitized_text']
            })
            
            return validation
        
        days_required = LeaveWorkflowEngine.calculate_leave_days(start_date, end_date)
        balances = get_leave_balance(employee_id)
        
        if not balances:
            return {
                'valid': False,
                'message': 'Employee not found',
                'days_required': days_required,
                'balance': 0
            }
        
        current_balance = balances.get(leave_type, 0)
        
        if current_balance >= days_required:
            return {
                'valid': True,
                'message': f'Leave request valid. {current_balance - days_required} days will remain after approval.',
                'days_required': days_required,
                'balance': current_balance
            }
        else:
            return {
                'valid': False,
                'message': f'Insufficient {leave_type} leave balance. Required: {days_required}, Available: {current_balance}',
                'days_required': days_required,
                'balance': current_balance
            }
    
    
    @staticmethod
    def check_overlapping_requests(employee_id, start_date, end_date):
        """
        Check if employee has overlapping leave requests.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT id, start_date, end_date, status
            FROM leave_requests_v2
            WHERE employee_id = ?
            AND status IN ('pending', 'approved')
            AND (
                (start_date <= ? AND end_date >= ?) OR
                (start_date <= ? AND end_date >= ?) OR
                (start_date >= ? AND end_date <= ?)
            )
        """, (employee_id, start_date, start_date, end_date, end_date, start_date, end_date))
        
        overlapping = c.fetchall()
        conn.close()
        
        return overlapping
    
    
    @staticmethod
    def submit_leave_request(employee_id, leave_type, start_date, end_date, reason):
        """
        Submit a leave request with validation.
        
        Returns:
            dict: {'success': bool, 'message': str, 'request_id': int or None}
        """
        # Validate leave balance
        validation = LeaveWorkflowEngine.validate_leave_request(
            employee_id, leave_type, start_date, end_date, reason
        )
        
        if not validation['valid']:
            return {
                'success': False,
                'message': validation['message'],
                'request_id': None
            }
        
        # Check overlapping requests
        overlapping = LeaveWorkflowEngine.check_overlapping_requests(
            employee_id, start_date, end_date
        )
        
        if overlapping:
            return {
                'success': False,
                'message': f'You have an overlapping leave request (ID: {overlapping[0][0]})',
                'request_id': None
            }
        
        # Get manager for approval routing
        employee = get_employee(employee_id=employee_id)
        manager_id = employee.get('manager_id') if employee else None
        
        # Insert leave request
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            c.execute("""
                INSERT INTO leave_requests_v2 
                (employee_id, leave_type, start_date, end_date, total_days, reason, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """, (employee_id, leave_type, start_date, end_date, 
                  validation['days_required'], reason))
            
            request_id = c.lastrowid
            conn.commit()
            
            # Auto-route to manager if exists
            try:
                if manager_id:
                    message_text = f"Leave request submitted successfully (ID: {request_id}). Pending approval from manager."
                    # Notify Manager
                    NotificationManager.create_notification(
                        user_id=manager_id,
                        n_type="info",
                        title="New Leave Request",
                        message=f"A new {leave_type} leave request has been submitted by {employee.get('full_name', 'an employee')}.",
                        action_id="view_pending_leaves"
                    )
                else:
                    message_text = f"Leave request submitted successfully (ID: {request_id}). Pending HR approval."
                    # Notify HR Role
                    NotificationManager.create_notification(
                        user_id="HR_MANAGER",
                        n_type="info",
                        title="New Leave Request",
                        message=f"A new {leave_type} leave request for {employee.get('full_name', 'an employee')} needs approval.",
                        action_id="view_pending_leaves"
                    )
            except Exception as notif_e:
                logger.warning(f"Failed to send submission notification: {notif_e}")
                # We still consider the submission a success even if the notification fails
                if manager_id:
                    message_text = f"Leave request submitted successfully (ID: {request_id}). Manager notification pending."
                else:
                    message_text = f"Leave request submitted successfully (ID: {request_id}). HR notification pending."

            return {
                'success': True,
                'message': message_text,
                'request_id': request_id
            }
            
        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'message': f'Error submitting leave request: {str(e)}',
                'request_id': None
            }
        finally:
            conn.close()
    
    
    @staticmethod
    def approve_leave_request(request_id, approver_id, comments=None):
        """
        Approve a leave request and deduct leave balance.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            # Get request details
            c.execute("""
                SELECT employee_id, leave_type, total_days, status, start_date, end_date
                FROM leave_requests_v2 WHERE id = ?
            """, (request_id,))
            
            request = c.fetchone()
            if not request:
                return {'success': False, 'message': 'Leave request not found'}
            
            employee_id, leave_type, total_days, status, start_date, end_date = request
            
            if status != 'pending':
                return {'success': False, 'message': f'Request already {status}'}
            
            # Get current balance
            balances = get_leave_balance(employee_id)
            current_balance = balances.get(leave_type, 0)
            new_balance = current_balance - total_days
            
            if new_balance < 0:
                return {
                    'success': False,
                    'message': 'Insufficient leave balance for approval'
                }
            
            # Update request status
            c.execute("""
                UPDATE leave_requests_v2
                SET status = 'approved', 
                    approver_id = ?,
                    approved_at = ?,
                    approval_comments = ?
                WHERE id = ?
            """, (approver_id, datetime.now().isoformat(), comments, request_id))
            
            conn.commit()
            
            # Update leave balance
            update_leave_balance(
                employee_id, leave_type, new_balance,
                reason=f"Leave approved - Request ID: {request_id}",
                request_id=request_id
            )
            
            # Notify Employee
            NotificationManager.create_notification(
                user_id=employee_id,
                n_type="success",
                title="Leave Approved",
                message=f"Your {leave_type} leave from {start_date} to {end_date} has been approved.",
                priority=1
            )
            
            return {
                'success': True,
                'message': f'Leave request approved. New {leave_type} balance: {new_balance} days'
            }
            
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': f'Error approving request: {str(e)}'}
        finally:
            conn.close()
    
    
    @staticmethod
    def reject_leave_request(request_id, approver_id, comments=None):
        """
        Reject a leave request.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            # Get request details
            c.execute("""
                SELECT employee_id, leave_type, start_date, end_date, status
                FROM leave_requests_v2 WHERE id = ?
            """, (request_id,))
            
            request = c.fetchone()
            if not request:
                return {'success': False, 'message': 'Leave request not found'}
            
            employee_id, leave_type, start_date, end_date, status = request
            
            if status != 'pending':
                return {'success': False, 'message': f'Request is already {status}'}
            
            # Update status
            c.execute("""
                UPDATE leave_requests_v2 
                SET status = 'rejected', approver_id = ?, approved_at = ?, approval_comments = ?
                WHERE id = ?
            """, (approver_id, datetime.now().isoformat(), comments, request_id))
            
            conn.commit()
            
            # Notify Employee
            NotificationManager.create_notification(
                user_id=employee_id,
                n_type="warning",
                title="Leave Request Rejected",
                message=f"Your {leave_type} leave from {start_date} to {end_date} has been rejected. Reason: {comments or 'No reason provided.'}",
                priority=1
            )
            
            return {
                'success': True,
                'message': 'Leave request rejected successfully'
            }
            
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': f'Error rejecting request: {str(e)}'}
        finally:
            conn.close()
    
    
    @staticmethod
    def get_pending_requests(manager_id=None, employee_id=None):
        """
        Get pending leave requests for approval.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        if employee_id:
            # Get requests for a specific employee
            c.execute("""
                SELECT lr.*, e.full_name, e.department
                FROM leave_requests_v2 lr
                JOIN employees e ON lr.employee_id = e.employee_id
                WHERE lr.employee_id = ? AND lr.status = 'pending'
                ORDER BY lr.submitted_at DESC
            """, (employee_id,))
        elif manager_id:
            # Get requests for employees under this manager
            c.execute("""
                SELECT lr.*, e.full_name, e.department
                FROM leave_requests_v2 lr
                JOIN employees e ON lr.employee_id = e.employee_id
                WHERE e.manager_id = ? AND lr.status = 'pending'
                ORDER BY lr.submitted_at DESC
            """, (manager_id,))
        else:
            # Get all pending requests
            c.execute("""
                SELECT lr.*, e.full_name, e.department
                FROM leave_requests_v2 lr
                JOIN employees e ON lr.employee_id = e.employee_id
                WHERE lr.status = 'pending'
                ORDER BY lr.submitted_at DESC
            """)
        
        requests = c.fetchall()
        conn.close()
        return requests
    
    
    @staticmethod
    def check_and_escalate_stale_requests(days_threshold=7):
        """
        Escalate leave requests pending for more than threshold days.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days_threshold)).isoformat()
        
        # Find stale requests
        c.execute("""
            SELECT id, employee_id FROM leave_requests_v2
            WHERE status = 'pending' AND submitted_at < ?
        """, (cutoff_date,))
        
        stale_requests = c.fetchall()
        
        escalated = []
        for request_id, employee_id in stale_requests:
            # Create escalation record
            c.execute("""
                INSERT INTO workflow_escalations 
                (request_id, request_type, reason, status)
                VALUES (?, 'leave_request', 'Pending for more than 7 days', 'pending')
            """, (request_id,))
            escalated.append(request_id)
        
        conn.commit()
        conn.close()
        
        return {
            'escalated_count': len(escalated),
            'request_ids': escalated
        }


    @staticmethod
    def get_analytics():
        """
        Calculate resolution rate and average resolution time for leave requests.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            # Resolution Rate
            c.execute("SELECT COUNT(*) FROM leave_requests_v2")
            total = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM leave_requests_v2 WHERE status IN ('approved', 'rejected')")
            resolved = c.fetchone()[0]
            
            res_rate = (resolved / total * 100) if total > 0 else 0
            
            # Avg Resolution Time (only for approved/rejected)
            c.execute("""
                SELECT 
                    AVG(julianday(approved_at) - julianday(submitted_at)) 
                FROM leave_requests_v2 
                WHERE status IN ('approved', 'rejected') AND approved_at IS NOT NULL
            """)
            avg_days = c.fetchone()[0] or 0
            
            return {
                "resolution_rate": round(res_rate, 1),
                "avg_resolution_time": round(avg_days, 1)
            }
        finally:
            conn.close()


    @staticmethod
    def get_all_escalations():
        """
        Get all workflow escalations.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT we.*, lr.employee_id, e.full_name
            FROM workflow_escalations we
            JOIN leave_requests_v2 lr ON we.request_id = lr.id
            JOIN employees e ON lr.employee_id = e.employee_id
            ORDER BY we.escalated_at DESC
        """)
        
        rows = c.fetchall()
        conn.close()
        
        escalations = []
        columns = ['id', 'request_id', 'request_type', 'escalated_to', 'escalated_from', 
                   'reason', 'status', 'escalated_at', 'resolved_at', 'employee_id', 'employee_name']
        
        for row in rows:
            escalations.append(dict(zip(columns, row)))
            
        return escalations


    @staticmethod
    def resolve_escalation(escalation_id, resolution_notes):
        """
        Resolve a workflow escalation.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            c.execute("""
                UPDATE workflow_escalations
                SET status = 'resolved',
                    resolved_at = ?,
                    reason = reason || ' | Resolution: ' || ?
                WHERE id = ?
            """, (datetime.now().isoformat(), resolution_notes, escalation_id))
            
            if c.rowcount == 0:
                return {'success': False, 'message': 'Escalation not found'}
                
            conn.commit()
            return {'success': True, 'message': 'Escalation resolved successfully'}
            
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': f'Error resolving escalation: {str(e)}'}
        finally:
            conn.close()


    @staticmethod
    def get_combined_active_escalations():
        """
        Fetch both workflow escalations and chat escalations into a unified format.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 1. Fetch Workflow Escalations (Stale Leave Requests)
        c.execute("""
            SELECT we.id, e.username, we.reason, we.status, we.escalated_at, lr.employee_id
            FROM workflow_escalations we
            JOIN leave_requests_v2 lr ON we.request_id = lr.id
            JOIN employees e ON lr.employee_id = e.employee_id
            WHERE we.status = 'pending'
            ORDER BY we.escalated_at DESC
        """)
        workflow_rows = c.fetchall()
        
        # 2. Fetch Chat Escalations (Sensitive/Unresolved Queries)
        c.execute("""
            SELECT id, username, query, reason, status, created_at, employee_id, conversation_summary
            FROM chat_escalations
            WHERE status = 'pending'
            ORDER BY created_at DESC
        """)
        chat_rows = c.fetchall()
        
        conn.close()
        
        combined = []
        
        # Format Workflow Escalations
        for r in workflow_rows:
            combined.append({
                "id": f"WF-{r[0]}",
                "db_id": r[0],
                "type": "workflow",
                "source": r[1],
                "employee_id": r[5],
                "description": f"STALE REQUEST: {r[2]}",
                "status": r[3],
                "created_at": r[4],
                "conversation_summary": None # Workflows have no conversation context yet
            })
            
        # Format Chat Escalations
        for r in chat_rows:
            combined.append({
                "id": f"CH-{r[0]}",
                "db_id": r[0],
                "type": "chat",
                "source": r[1],
                "employee_id": r[6],
                "description": f"SENSITIVE QUERY: {r[3]}",
                "query": r[2],
                "status": r[4],
                "created_at": r[5],
                "conversation_summary": r[7]
            })
            
        # Sort by date
        combined.sort(key=lambda x: x['created_at'], reverse=True)
        return combined


def get_employee_leave_history(employee_id, limit=10):
    """Get leave request history for an employee."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT * FROM leave_requests_v2
        WHERE employee_id = ?
        ORDER BY submitted_at DESC
        LIMIT ?
    """, (employee_id, limit))
    
    history = c.fetchall()
    conn.close()
    return history


class ChatEscalationEngine:
    """
    Manages escalations for sensitive or unresolved chat queries.
    """
    
    @staticmethod
    def submit_chat_escalation(username, query, full_history, reason, sensitivity_score=0.0, conversation_summary=None):
        """
        Escalate a chat query to HR.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            # Get employee_id if exists
            c.execute("SELECT employee_id FROM employees WHERE username = ?", (username,))
            res = c.fetchone()
            employee_id = res[0] if res else None
            
            # Format history as string if list
            if isinstance(full_history, list):
                # Handle tuples (query, answer, suggestions) or (query, answer)
                formatted_history = []
                for item in full_history:
                    q = item[0]
                    a = item[1]
                    formatted_history.append(f"User: {q}\\nAI: {a}")
                history_str = "\\n".join(formatted_history)
            else:
                history_str = str(full_history)

            c.execute("""
                INSERT INTO chat_escalations 
                (employee_id, username, query, full_history, reason, sensitivity_score, status, conversation_summary)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (employee_id, username, query, history_str, reason, sensitivity_score, conversation_summary))
            
            escalation_id = c.lastrowid
            conn.commit()
            
            return {
                'success': True,
                'message': 'Query escalated to HR successfully',
                'escalation_id': escalation_id
            }
            
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': f'Error escalating query: {str(e)}'}
        finally:
            conn.close()

    @staticmethod
    def get_pending_escalations():
        """Get all pending chat escalations."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT * FROM chat_escalations 
            WHERE status = 'pending' 
            ORDER BY created_at DESC
        """)
        
        rows = c.fetchall()
        conn.close()
        
        escalations = []
        columns = ['id', 'employee_id', 'username', 'query', 'full_history', 'reason', 
                  'sensitivity_score', 'status', 'conversation_summary', 'created_at', 'resolved_at', 'resolution_notes']
        
        for row in rows:
            escalations.append(dict(zip(columns, row)))
            
        return escalations

    @staticmethod
    def resolve_escalation(escalation_id, resolution_notes):
        """Resolve a chat escalation."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            c.execute("""
                UPDATE chat_escalations
                SET status = 'resolved',
                    resolved_at = ?,
                    resolution_notes = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), resolution_notes, escalation_id))
            
            if c.rowcount == 0:
                return {'success': False, 'message': 'Escalation not found'}
                
            conn.commit()
            return {'success': True, 'message': 'Escalation resolved'}
            
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': f'Error resolving: {str(e)}'}
        finally:
            conn.close()

    @staticmethod
    def get_user_escalations(username, limit=5):
        """Get recent escalations for a specific user."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""
            SELECT reason, status, resolution_notes, created_at, resolved_at 
            FROM chat_escalations 
            WHERE username = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (username, limit))
        
        rows = c.fetchall()
        conn.close()
        
        history = []
        for r in rows:
            history.append({
                'reason': r[0],
                'status': r[1],
                'resolution_notes': r[2],
                'date': r[3],
                'resolved_at': r[4]
            })
        return history


    @staticmethod
    def get_analytics():
        """
        Calculate metrics for chat escalations and estimated savings.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            # AI Savings calculation
            # Rule: Each chat message saved by AI (not escalated) saves ~15 mins of HR time
            c.execute("SELECT COUNT(*) FROM logs")
            total_messages = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM chat_escalations")
            total_escalations = c.fetchone()[0]
            
            # Simple heuristic: messages that didn't lead to escalation
            # Or just total successful interactions
            # Let's say: (total_messages / 2) - escalations = successful sessions
            # assuming avg 2 messages per session
            sessions = total_messages / 2
            saved_sessions = max(0, sessions - total_escalations)
            
            # Each saved session = 15 mins (0.25 hrs)
            hr_hours_saved = saved_sessions * 0.25
            
            # Escalation resolution time
            c.execute("""
                SELECT 
                    AVG(julianday(resolved_at) - julianday(created_at)) 
                FROM chat_escalations 
                WHERE status = 'resolved' AND resolved_at IS NOT NULL
            """)
            avg_days = c.fetchone()[0] or 0
            
            return {
                "hr_hours_saved": round(hr_hours_saved, 1),
                "avg_escalation_time": round(avg_days, 1)
            }
        except Exception as e:
            print(f"Analytics error: {e}")
            return {"hr_hours_saved": 0, "avg_escalation_time": 0}
        finally:
            conn.close()
