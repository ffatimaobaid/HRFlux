"""
Workflow Engine for HRFlux
Handles leave request approvals, balance validation, and escalations
"""

import sqlite3
from datetime import datetime, timedelta
from db_schema_v2 import get_employee, get_leave_balance, update_leave_balance

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
    def validate_leave_request(employee_id, leave_type, start_date, end_date):
        """
        Validate if employee has sufficient leave balance.
        
        Returns:
            dict: {'valid': bool, 'message': str, 'days_required': int, 'balance': int}
        """
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
                'message': f'Leave request valid. {current_balance - days_required} days remaining.',
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
            employee_id, leave_type, start_date, end_date
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
            if manager_id:
                message = f"Leave request submitted successfully (ID: {request_id}). Pending approval from manager."
            else:
                message = f"Leave request submitted successfully (ID: {request_id}). Pending HR approval."
            
            return {
                'success': True,
                'message': message,
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
                SELECT employee_id, leave_type, total_days, status
                FROM leave_requests_v2 WHERE id = ?
            """, (request_id,))
            
            request = c.fetchone()
            if not request:
                return {'success': False, 'message': 'Leave request not found'}
            
            employee_id, leave_type, total_days, status = request
            
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
    def reject_leave_request(request_id, approver_id, reason):
        """
        Reject a leave request.
        """
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            c.execute("""
                UPDATE leave_requests_v2
                SET status = 'rejected',
                    approver_id = ?,
                    approved_at = ?,
                    approval_comments = ?
                WHERE id = ? AND status = 'pending'
            """, (approver_id, datetime.now().isoformat(), reason, request_id))
            
            if c.rowcount == 0:
                return {'success': False, 'message': 'Request not found or already processed'}
            
            conn.commit()
            return {'success': True, 'message': 'Leave request rejected'}
            
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
