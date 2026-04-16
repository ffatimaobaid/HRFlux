"""
Enhanced authentication manager with rate limiting and session security.
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from security_config import SecurityConfig
from guardrails import InputValidator, SecurityLogger

class AuthManager:
    """Enhanced authentication with rate limiting and session management."""
    
    def __init__(self):
        self.login_attempts = {}
        self.sessions = {}
        # Ensure session file is always in the same directory as this script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.session_file = os.path.join(base_dir, "sessions.json")
        self.load_sessions()
    
    def load_sessions(self):
        """Load existing sessions from file."""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    self.sessions = json.load(f)
        except Exception:
            self.sessions = {}
    
    def save_sessions(self):
        """Save sessions to file."""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(self.sessions, f)
        except Exception as e:
            print(f"Error saving sessions: {e}")
    
    def is_rate_limited(self, user_id: str) -> tuple[bool, Optional[int]]:
        """Check if user is rate limited."""
        if not SecurityConfig.ENABLE_RATE_LIMITING:
            return False, None
        
        attempts = self.login_attempts.get(user_id, {'count': 0, 'last_attempt': None})
        
        if attempts['count'] >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
            # Check if timeout period has passed
            if attempts['last_attempt']:
                time_since_last = time.time() - attempts['last_attempt']
                if time_since_last < SecurityConfig.LOGIN_TIMEOUT:
                    return True, SecurityConfig.LOGIN_TIMEOUT - int(time_since_last)
        
        return False, None
    
    def record_login_attempt(self, user_id: str, success: bool = False):
        """Record login attempt for rate limiting."""
        if user_id not in self.login_attempts:
            self.login_attempts[user_id] = {'count': 0, 'last_attempt': None}
        
        self.login_attempts[user_id]['count'] += 1
        self.login_attempts[user_id]['last_attempt'] = time.time()
        
        if success:
            # Reset count on successful login
            self.login_attempts[user_id]['count'] = 0
        
        # Log security event
        SecurityLogger.log_security_event(
            'login_attempt',
            {
                'user_id': user_id,
                'success': success,
                'attempt_count': self.login_attempts[user_id]['count'],
                'rate_limited': self.is_rate_limited(user_id)[0]
            },
            user_id,
            'high' if not success else 'low'
        )
    
    def create_session(self, user_id: str, user_data: Dict[str, Any]) -> str:
        """Create secure session token."""
        session_token = SecurityConfig.generate_session_token()
        
        session_data = {
            'user_id': user_id,
            'user_data': user_data,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'ip_address': '127.0.0.1',  # Would be real IP in production
            'user_agent': 'HRFlux-System'
        }
        
        self.sessions[session_token] = session_data
        self.save_sessions()
        
        SecurityLogger.log_security_event(
            'session_created',
            {
                'user_id': user_id,
                'session_token': session_token[:8] + '...',  # Partially mask token
                'ip_address': session_data['ip_address']
            },
            user_id,
            'low'
        )
        
        return session_token
    
    def validate_session(self, session_token: str) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Validate session token and check for expiration."""
        if not session_token:
            return False, None
        
        if session_token not in self.sessions:
            return False, None
        
        session_data = self.sessions[session_token]
        
        # Check token format
        if not SecurityConfig.validate_session_token(session_token):
            return False, None
        
        # Check session timeout
        created_at = datetime.fromisoformat(session_data['created_at'])
        last_activity = datetime.fromisoformat(session_data['last_activity'])
        now = datetime.now()
        
        if (now - last_activity).seconds > SecurityConfig.SESSION_TIMEOUT:
            return False, None
        
        # Update last activity
        session_data['last_activity'] = now.isoformat()
        self.save_sessions()
        
        return True, session_data
    
    def destroy_session(self, session_token: str) -> bool:
        """Destroy session token."""
        if session_token in self.sessions:
            session_data = self.sessions[session_token]
            del self.sessions[session_token]
            self.save_sessions()
            
            SecurityLogger.log_security_event(
                'session_destroyed',
                {
                    'user_id': session_data.get('user_id'),
                    'session_duration': datetime.now() - datetime.fromisoformat(session_data['created_at'])
                },
                session_data.get('user_id'),
                'low'
            )
            
            return True
        
        return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        now = datetime.now()
        expired_tokens = []
        
        for token, session_data in self.sessions.items():
            created_at = datetime.fromisoformat(session_data['created_at'])
            last_activity = datetime.fromisoformat(session_data['last_activity'])
            
            if (now - last_activity).seconds > SecurityConfig.SESSION_TIMEOUT:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            self.destroy_session(token)
    
    def get_active_sessions(self) -> Dict[str, Any]:
        """Get all active sessions."""
        self.cleanup_expired_sessions()
        return self.sessions
    
    def enforce_password_policy(self, password: str) -> Dict[str, Any]:
        """Enforce password security policy."""
        validation = InputValidator.validate_password(password)
        
        if not validation['valid']:
            SecurityLogger.log_security_event(
                'password_policy_violation',
                {
                    'validation_errors': validation['errors'],
                    'password_length': len(password)
                },
                None,  # user_id not available in this context
                'medium'
            )
        
        return validation

# Global auth manager instance
auth_manager = AuthManager()
