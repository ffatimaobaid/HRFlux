import sqlite3
import json
import logging
from datetime import datetime
from fastapi import Request

DB_PATH = "queries.db"
logger = logging.getLogger(__name__)

class SecurityManager:
    @staticmethod
    def log_action(user_id, action, target_id=None, status="success", metadata=None, request: Request = None):
        """Record a sensitive action in the security audit logs."""
        ip_address = None
        if request:
            ip_address = request.client.host
            
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                INSERT INTO security_audit_logs 
                (user_id, action, target_id, ip_address, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, action, target_id, ip_address, status, json.dumps(metadata) if metadata else None))
            conn.commit()
            conn.close()
            logger.info(f"SECURITY AUDIT: User {user_id} performed {action} on {target_id} - Status: {status}")
        except Exception as e:
            logger.error(f"Failed to log security action: {e}")

    @staticmethod
    def mask_pii(data):
        """
        Recursively mask sensitive PII fields in a dictionary or list.
        Fields masked: email, salary, phone, password, bank_account
        """
        if isinstance(data, list):
            return [SecurityManager.mask_pii(item) for item in data]
        
        if not isinstance(data, dict):
            return data
            
        masked_data = data.copy()
        
        sensitive_fields = {
            'email': lambda v: v[:2] + '****' + v[v.find('@'):] if '@' in v else '****',
            'salary': lambda v: '****',
            'password': lambda v: '********',
            'phone': lambda v: '******' + str(v)[-4:],
            'bank_account': lambda v: '****' + str(v)[-4:]
        }
        
        for field, masker in sensitive_fields.items():
            if field in masked_data and masked_data[field] is not None:
                try:
                    masked_data[field] = masker(str(masked_data[field]))
                except:
                    masked_data[field] = '****'
                    
        # Recursively mask nested objects
        for key, value in masked_data.items():
            if isinstance(value, (dict, list)):
                masked_data[key] = SecurityManager.mask_pii(value)
                
        return masked_data

security_manager = SecurityManager()
