"""
Enhanced guardrails implementation with comprehensive security configuration.
"""

import re
import hashlib
from typing import List, Optional, Dict, Any
from security_config import SecurityConfig

class ContentFilter:
    """Enhanced content filtering using security configuration."""
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input to prevent XSS and injection attacks."""
        if not text:
            return ""
        
        # Use security config sanitization
        text = SecurityConfig.sanitize_html_input(text)
        text = SecurityConfig.sanitize_sql_input(text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    @staticmethod
    def detect_pii(text: str) -> Dict[str, Any]:
        """Detect PII using security configuration patterns."""
        return SecurityConfig.detect_pii(text)
    
    @staticmethod
    def check_profanity(text: str) -> Dict[str, Any]:
        """Check for profanity using security configuration."""
        return SecurityConfig.check_profanity(text)
    
    @staticmethod
    def filter_content(text: str) -> Dict[str, Any]:
        """Comprehensive content filtering using security configuration."""
        result = {
            'allowed': True,
            'blocked': False,
            'warnings': [],
            'sanitized_text': ContentFilter.sanitize_input(text)
        }
        
        # Apply content filtering if enabled
        if SecurityConfig.ENABLE_CONTENT_FILTERING:
            # Check for profanity
            profanity_check = ContentFilter.check_profanity(text)
            if profanity_check['has_profanity']:
                result['allowed'] = False
                result['blocked'] = True
                result['warnings'].append(f"Profanity detected: {profanity_check['detected_words']}")
            
            # Check for PII
            pii_check = ContentFilter.detect_pii(text)
            if pii_check:
                result['allowed'] = False
                result['blocked'] = True
                result['warnings'].append(f"PII patterns detected: {list(pii_check.keys())}")
                result['sanitized_text'] = pii_check.get('masked_text', result['sanitized_text'])
            
            # Check for SQL injection attempts
            for pattern in SecurityConfig.SQL_INJECTION_PATTERNS:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    result['allowed'] = False
                    result['blocked'] = True
                    result['warnings'].append("Potential SQL injection attempt detected")
                    break
        
        return result

class InputValidator:
    """Enhanced input validation using security configuration."""
    
    @staticmethod
    def validate_email(email: str) -> Dict[str, Any]:
        """Validate email format and domain with enhanced security."""
        if not email:
            return {'valid': False, 'errors': ['Email is required']}
        
        # Use security config patterns
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return {'valid': False, 'errors': ['Invalid email format']}
        
        # Enhanced domain checking
        suspicious_domains = ['tempmail.com', '10minutemail.com', 'guerrillamail.com']
        domain = email.split('@')[-1] if '@' in email else ''
        
        if domain in suspicious_domains:
            return {'valid': False, 'errors': ['Suspicious email domain']}
        
        return {'valid': True, 'errors': []}
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Validate password against security requirements."""
        errors = []
        
        # Length validation
        if len(password) < SecurityConfig.MIN_PASSWORD_LENGTH:
            errors.append(f'Password must be at least {SecurityConfig.MIN_PASSWORD_LENGTH} characters')
        
        # Character requirements
        if SecurityConfig.REQUIRE_SPECIAL_CHARS:
            special_chars = re.search(r'[!@#$%^&*()]', password)
            if not special_chars:
                errors.append('Password must contain at least one special character')
        
        if SecurityConfig.REQUIRE_UPPERCASE:
            if not re.search(r'[A-Z]', password):
                errors.append('Password must contain at least one uppercase letter')
        
        if SecurityConfig.REQUIRE_NUMBERS:
            if not re.search(r'\d', password):
                errors.append('Password must contain at least one number')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def validate_leave_request(leave_request: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced leave request validation with content filtering."""
        errors = []
        
        # Extract values from dictionary
        start_date = leave_request.get('start_date', '')
        end_date = leave_request.get('end_date', '')
        reason = leave_request.get('reason', '')
        leave_type = leave_request.get('leave_type', 'annual')
        
        # Validate date format
        try:
            from datetime import datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            if start_dt >= end_dt:
                errors.append('End date must be after start date')
            
            if start_dt.year != end_dt.year:
                errors.append('Leave requests should be within the same calendar year')
                
        except ValueError:
            errors.append('Invalid date format. Use YYYY-MM-DD')
        
        # Validate reason length and content
        if len(reason.strip()) < 5:
            errors.append('Reason must be at least 5 characters')
        
        # Apply content filtering to reason
        content_filter = ContentFilter.filter_content(reason)
        if not content_filter['allowed']:
            errors.append('Inappropriate content detected in leave reason')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'sanitized_reason': content_filter.get('sanitized_text', reason)
        }

class SecurityLogger:
    """Enhanced security logging using security configuration."""
    
    @staticmethod
    def log_security_event(event_type: str, details: Dict[str, Any], user_id: Optional[str] = None, severity: str = "medium"):
        """Log security events with enhanced security configuration."""
        return SecurityConfig.log_security_event(event_type, details, user_id, severity)
    
    @staticmethod
    def get_security_summary() -> Dict[str, Any]:
        """Get a summary of security events."""
        try:
            # This would typically read from a log file or database
            # For now, return a mock summary
            return {
                'total_events': 0,
                'events_by_type': {},
                'events_by_severity': {},
                'recent_events': []
            }
        except Exception:
            return {
                'total_events': 0,
                'events_by_type': {},
                'events_by_severity': {},
                'recent_events': []
            }
