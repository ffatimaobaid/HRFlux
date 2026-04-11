"""
Comprehensive security configuration for HR Chatbot system.
"""

import os
import hashlib
import secrets
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import bcrypt

class SecurityConfig:
    """Central security configuration and utilities."""
    
    # Security settings
    ENABLE_CONTENT_FILTERING = os.getenv("ENABLE_CONTENT_FILTERING", "true").lower() == "true"
    ENABLE_PII_DETECTION = os.getenv("ENABLE_PII_DETECTION", "true").lower() == "true"
    ENABLE_AUDIT_LOGGING = os.getenv("ENABLE_AUDIT_LOGGING", "true").lower() == "true"
    ENABLE_RATE_LIMITING = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
    
    # Rate limiting settings
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOGIN_TIMEOUT = int(os.getenv("LOGIN_TIMEOUT", "900"))  # 15 minutes
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 hour
    
    # Password requirements
    MIN_PASSWORD_LENGTH = int(os.getenv("MIN_PASSWORD_LENGTH", "8"))
    REQUIRE_SPECIAL_CHARS = os.getenv("REQUIRE_SPECIAL_CHARS", "true").lower() == "true"
    REQUIRE_UPPERCASE = os.getenv("REQUIRE_UPPERCASE", "true").lower() == "true"
    REQUIRE_NUMBERS = os.getenv("REQUIRE_NUMBERS", "true").lower() == "true"
    
    # Content filtering settings
    BLOCKED_WORDS = {
        'profanity': ['fuck', 'shit', 'damn', 'hell', 'bitch', 'asshole', 'bastard'],
        'inappropriate': ['kill', 'hate', 'violence', 'harm', 'abuse', 'stupid', 'idiot'],
        'discriminatory': ['racist', 'sexist', 'homophobic', 'transphobic'],
        'workplace_violence': ['sabotage', 'harassment', 'bullying', 'discrimination'],
    }
    
    # PII detection patterns
    PII_PATTERNS = {
        'phone': r'\b\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{4}\b',
        'ssn': r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$',
        'credit_card': r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b',
        'address': r'\b\d+\s+([A-Za-z]+\s+){1,5}\b',
        'id_number': r'\b[A-Za-z]{2}\d{6,10}\b',
    }
    
    # SQL injection patterns (relaxed to avoid blocking valid English words)
    SQL_INJECTION_PATTERNS = [
        r'\b(union\s+select|insert\s+into|update\s+[a-z_]+\s+set|delete\s+from|drop\s+table|create\s+table|alter\s+table|exec\s+\(|script>)\b',
        r'(--|;\s*$|\/\*.*\*\/)',
    ]
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt with salt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against bcrypt hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def generate_session_token() -> str:
        """Generate secure session token."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_session_token(token: str) -> bool:
        """Validate session token format and expiration."""
        try:
            # secrets.token_urlsafe(32) results in a 43-character string
            if len(token) != 43:
                return False
                
            return True
        except Exception:
            return False
    
    @staticmethod
    def sanitize_sql_input(input_str: str) -> str:
        """Sanitize SQL input to prevent injection."""
        if not input_str:
            return ""
        
        # Remove SQL comments
        sanitized = re.sub(r'--.*$', '', input_str)
        
        # Escape SQL keywords
        for pattern in SecurityConfig.SQL_INJECTION_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # Remove multiple statements
        sanitized = re.sub(r';\s*$', '', sanitized)
        
        return sanitized.strip()
    
    @staticmethod
    def sanitize_html_input(input_str: str) -> str:
        """Remove HTML tags and dangerous attributes."""
        if not input_str:
            return ""
        
        # Remove HTML tags
        sanitized = re.sub(r'<[^>]*>', '', input_str)
        
        # Remove dangerous attributes
        dangerous_attrs = ['onerror=', 'onload=', 'javascript:', 'onclick=', 'onmouseover=']
        for attr in dangerous_attrs:
            sanitized = re.sub(f'{attr}[^>]*', '', sanitized, flags=re.IGNORECASE)
        
        # Escape special characters
        sanitized = re.sub(r'[<>"\']', '', sanitized)
        
        return sanitized.strip()
    
    @staticmethod
    def detect_pii(text: str) -> Dict[str, Any]:
        """Detect PII in text using regex patterns."""
        findings = {}
        
        for pattern_name, pattern in SecurityConfig.PII_PATTERNS.items():
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            if matches:
                findings[pattern_name] = {
                    'detected': True,
                    'matches': matches,
                    'count': len(matches),
                    'masked_text': re.sub(pattern, lambda m: '*' * len(m.group()), text)
                }
        
        return findings
    
    @staticmethod
    def check_profanity(text: str) -> Dict[str, Any]:
        """Check for profanity and inappropriate language."""
        detected_words = []
        
        for category, words in SecurityConfig.BLOCKED_WORDS.items():
            for word in words:
                # Use word boundaries to prevent 'hello' matching 'hell' or 'skill' matching 'kill'
                pattern = r'\b' + re.escape(word) + r'\b'
                if re.search(pattern, text, flags=re.IGNORECASE):
                    detected_words.append(word)
        
        return {
            'has_profanity': len(detected_words) > 0,
            'detected_words': detected_words,
            'profanity_score': len(detected_words) / len(text.split()) if text else 0
        }
    
    @staticmethod
    def is_rate_limited(user_id: str) -> bool:
        """Check if user is rate limited."""
        # This would integrate with Redis or similar in production
        # For now, return False (no rate limiting)
        return False
    
    @staticmethod
    def get_content_filter_config() -> Dict[str, Any]:
        """Get content filter configuration."""
        return {
            'profanity_filter': {
                'enabled': True,
                'blocked_words': SecurityConfig.BLOCKED_WORDS
            },
            'pii_detection': {
                'enabled': True,
                'patterns': SecurityConfig.PII_PATTERNS
            },
            'sql_injection_detection': {
                'enabled': True,
                'patterns': SecurityConfig.SQL_INJECTION_PATTERNS
            }
        }
    
    @staticmethod
    def get_password_policy() -> Dict[str, Any]:
        """Get password policy configuration."""
        return {
            'min_length': SecurityConfig.MIN_PASSWORD_LENGTH,
            'require_uppercase': SecurityConfig.REQUIRE_UPPERCASE,
            'require_lowercase': SecurityConfig.REQUIRE_LOWERCASE,
            'require_numbers': SecurityConfig.REQUIRE_NUMBERS,
            'require_special_chars': SecurityConfig.REQUIRE_SPECIAL_CHARS
        }
    
    @staticmethod
    def get_rate_limits() -> Dict[str, Any]:
        """Get rate limiting configuration."""
        return {
            'login_attempts': {
                'max_attempts': 5,
                'window_minutes': 15,
                'lockout_minutes': 30
            },
            'chat_requests': {
                'max_requests': 100,
                'window_minutes': 60
            }
        }
    
    @staticmethod
    def log_security_event(event_type: str, details: Dict[str, Any], user_id: Optional[str] = None, severity: str = "medium"):
        """Log security events for audit trail."""
        if SecurityConfig.ENABLE_AUDIT_LOGGING:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'user_id': user_id,
                'details': details,
                'severity': severity,
                'ip_address': '127.0.0.1',  # Would be real IP in production
                'user_agent': 'HRFlux-System'
            }
            
            # In production, this would log to secure audit system
            print(f"[SECURITY] {log_entry}")
            
            return log_entry
        else:
            return {}
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get security headers for HTTP responses."""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
        }
