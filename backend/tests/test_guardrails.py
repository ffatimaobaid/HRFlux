"""
Comprehensive test cases for guardrails functionality.
Tests ContentFilter, InputValidator, and SecurityLogger.
"""

import pytest
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from guardrails import ContentFilter, InputValidator, SecurityLogger
from security_config import SecurityConfig

class TestContentFilter:
    """Test cases for ContentFilter class."""
    
    def test_sanitize_input_basic(self):
        """Test basic input sanitization."""
        # Test HTML sanitization
        input_text = "<script>alert('xss')</script>Hello"
        sanitized = ContentFilter.sanitize_input(input_text)
        assert "<script>" not in sanitized
        assert "Hello" in sanitized
        
        # Test SQL injection attempt
        sql_input = "'; DROP TABLE users; --"
        sanitized = ContentFilter.sanitize_input(sql_input)
        assert "DROP TABLE" not in sanitized
        
    def test_filter_content_allowed(self):
        """Test that normal HR questions are allowed."""
        normal_questions = [
            "What is the leave policy?",
            "How do I request time off?",
            "What are the working hours?",
            "Where can I find the employee handbook?"
        ]
        
        for question in normal_questions:
            result = ContentFilter.filter_content(question)
            assert result['allowed'] == True
            assert len(result['warnings']) == 0
            
    def test_filter_content_profanity_blocked(self):
        """Test that profanity is blocked."""
        profane_questions = [
            "What the fuck is this policy?",
            "This is bullshit",
            "Damn it"
        ]
        
        for question in profane_questions:
            result = ContentFilter.filter_content(question)
            assert result['allowed'] == False
            assert len(result['warnings']) > 0
            assert any('profanity' in warning.lower() for warning in result['warnings'])
            
    def test_filter_content_pii_blocked(self):
        """Test that PII is detected and blocked."""
        pii_questions = [
            "My email is john@example.com",
            "My phone is 555-123-4567",
            "My SSN is 123-45-6789"
        ]
        
        for question in pii_questions:
            result = ContentFilter.filter_content(question)
            assert result['allowed'] == False
            assert len(result['warnings']) > 0
            assert any('pii' in warning.lower() or 'personal' in warning.lower() 
                      for warning in result['warnings'])
                      
    def test_filter_content_sql_injection_blocked(self):
        """Test that SQL injection attempts are blocked."""
        sql_attempts = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "UNION SELECT * FROM passwords"
        ]
        
        for attempt in sql_attempts:
            result = ContentFilter.filter_content(attempt)
            assert result['allowed'] == False
            assert len(result['warnings']) > 0
            assert any('sql' in warning.lower() for warning in result['warnings'])

class TestInputValidator:
    """Test cases for InputValidator class."""
    
    def test_validate_email_valid(self):
        """Test valid email validation."""
        valid_emails = [
            "john@example.com",
            "user.name@company.co.uk",
            "test+tag@example.org"
        ]
        
        for email in valid_emails:
            result = InputValidator.validate_email(email)
            assert result['valid'] == True
            assert len(result['errors']) == 0
            
    def test_validate_email_invalid(self):
        """Test invalid email validation."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user..name@example.com"
        ]
        
        for email in invalid_emails:
            result = InputValidator.validate_email(email)
            assert result['valid'] == False
            assert len(result['errors']) > 0
            
    def test_validate_password_strong(self):
        """Test strong password validation."""
        strong_passwords = [
            "StrongP@ssw0rd!",
            "MySecure123#",
            "ComplexPass456$"
        ]
        
        for password in strong_passwords:
            result = InputValidator.validate_password(password)
            assert result['valid'] == True
            assert len(result['errors']) == 0
            
    def test_validate_password_weak(self):
        """Test weak password validation."""
        weak_passwords = [
            "123",  # Too short
            "password",  # No numbers, no special chars
            "12345678",  # No letters, no special chars
            "abcdefgh",  # No numbers, no special chars
            "Abc12345",  # No special chars
        ]
        
        for password in weak_passwords:
            result = InputValidator.validate_password(password)
            assert result['valid'] == False
            assert len(result['errors']) > 0
            
    def test_validate_leave_request_valid(self):
        """Test valid leave request validation."""
        valid_requests = [
            {
                'start_date': '2024-12-25',
                'end_date': '2024-12-26',
                'reason': 'Family vacation',
                'leave_type': 'annual'
            },
            {
                'start_date': '2024-11-01',
                'end_date': '2024-11-01',
                'reason': 'Medical appointment',
                'leave_type': 'sick'
            }
        ]
        
        for request in valid_requests:
            result = InputValidator.validate_leave_request(request)
            assert result['valid'] == True
            assert len(result['errors']) == 0
            
    def test_validate_leave_request_invalid(self):
        """Test invalid leave request validation."""
        invalid_requests = [
            {
                'start_date': '2024-12-25',
                'end_date': '2024-12-24',  # End before start
                'reason': '',
                'leave_type': 'annual'
            },
            {
                'start_date': 'invalid-date',
                'end_date': '2024-12-26',
                'reason': 'Test',
                'leave_type': 'invalid-type'
            }
        ]
        
        for request in invalid_requests:
            result = InputValidator.validate_leave_request(request)
            assert result['valid'] == False
            assert len(result['errors']) > 0

class TestSecurityLogger:
    """Test cases for SecurityLogger class."""
    
    def test_log_security_event(self):
        """Test security event logging."""
        # Test content blocking event
        event_data = {
            'original_question': 'Test question with profanity',
            'sanitized_question': 'Test question with ***',
            'filter_results': {'allowed': False, 'warnings': ['Profanity detected']}
        }
        
        # This should not raise an exception
        SecurityLogger.log_security_event('content_blocked', event_data, None, 'medium')
        
        # Test password policy violation
        password_data = {
            'validation_errors': ['Password too short'],
            'password_length': 5
        }
        
        SecurityLogger.log_security_event('password_policy_violation', password_data, 'test_user', 'low')
        
        # Test login attempt
        login_data = {
            'username': 'test@example.com',
            'ip_address': '127.0.0.1',
            'user_agent': 'Test Agent'
        }
        
        SecurityLogger.log_security_event('login_attempt', login_data, 'test_user', 'info')
        
        # Test failed login
        SecurityLogger.log_security_event('login_failed', login_data, 'test_user', 'high')
        
    def test_get_security_summary(self):
        """Test security summary generation."""
        summary = SecurityLogger.get_security_summary()
        
        # Should return a dictionary with expected keys
        assert isinstance(summary, dict)
        expected_keys = ['total_events', 'events_by_type', 'events_by_severity', 'recent_events']
        for key in expected_keys:
            assert key in summary

class TestSecurityConfig:
    """Test cases for SecurityConfig class."""
    
    def test_get_content_filter_config(self):
        """Test content filter configuration."""
        config = SecurityConfig.get_content_filter_config()
        
        assert isinstance(config, dict)
        assert 'profanity_filter' in config
        assert 'pii_detection' in config
        assert 'sql_injection_detection' in config
        
    def test_get_password_policy(self):
        """Test password policy configuration."""
        policy = SecurityConfig.get_password_policy()
        
        assert isinstance(policy, dict)
        assert 'min_length' in policy
        assert 'require_uppercase' in policy
        assert 'require_lowercase' in policy
        assert 'require_numbers' in policy
        assert 'require_special_chars' in policy
        
    def test_get_rate_limits(self):
        """Test rate limiting configuration."""
        limits = SecurityConfig.get_rate_limits()
        
        assert isinstance(limits, dict)
        assert 'login_attempts' in limits
        assert 'chat_requests' in limits

def run_guardrails_tests():
    """Run all guardrails tests."""
    print("🧪 Running Guardrails Test Suite...")
    print("=" * 50)
    
    # Test ContentFilter
    print("\n📝 Testing ContentFilter...")
    content_filter = TestContentFilter()
    
    try:
        content_filter.test_sanitize_input_basic()
        print("✅ Content sanitization test passed")
    except Exception as e:
        print(f"❌ Content sanitization test failed: {e}")
    
    try:
        content_filter.test_filter_content_allowed()
        print("✅ Normal content filtering test passed")
    except Exception as e:
        print(f"❌ Normal content filtering test failed: {e}")
    
    try:
        content_filter.test_filter_content_profanity_blocked()
        print("✅ Profanity filtering test passed")
    except Exception as e:
        print(f"❌ Profanity filtering test failed: {e}")
    
    try:
        content_filter.test_filter_content_pii_blocked()
        print("✅ PII filtering test passed")
    except Exception as e:
        print(f"❌ PII filtering test failed: {e}")
    
    try:
        content_filter.test_filter_content_sql_injection_blocked()
        print("✅ SQL injection filtering test passed")
    except Exception as e:
        print(f"❌ SQL injection filtering test failed: {e}")
    
    # Test InputValidator
    print("\n🔍 Testing InputValidator...")
    input_validator = TestInputValidator()
    
    try:
        input_validator.test_validate_email_valid()
        print("✅ Valid email validation test passed")
    except Exception as e:
        print(f"❌ Valid email validation test failed: {e}")
    
    try:
        input_validator.test_validate_email_invalid()
        print("✅ Invalid email validation test passed")
    except Exception as e:
        print(f"❌ Invalid email validation test failed: {e}")
    
    try:
        input_validator.test_validate_password_strong()
        print("✅ Strong password validation test passed")
    except Exception as e:
        print(f"❌ Strong password validation test failed: {e}")
    
    try:
        input_validator.test_validate_password_weak()
        print("✅ Weak password validation test passed")
    except Exception as e:
        print(f"❌ Weak password validation test failed: {e}")
    
    try:
        input_validator.test_validate_leave_request_valid()
        print("✅ Valid leave request test passed")
    except Exception as e:
        print(f"❌ Valid leave request test failed: {e}")
    
    try:
        input_validator.test_validate_leave_request_invalid()
        print("✅ Invalid leave request test passed")
    except Exception as e:
        print(f"❌ Invalid leave request test failed: {e}")
    
    # Test SecurityLogger
    print("\n📊 Testing SecurityLogger...")
    security_logger = TestSecurityLogger()
    
    try:
        security_logger.test_log_security_event()
        print("✅ Security logging test passed")
    except Exception as e:
        print(f"❌ Security logging test failed: {e}")
    
    try:
        security_logger.test_get_security_summary()
        print("✅ Security summary test passed")
    except Exception as e:
        print(f"❌ Security summary test failed: {e}")
    
    # Test SecurityConfig
    print("\n⚙️ Testing SecurityConfig...")
    security_config = TestSecurityConfig()
    
    try:
        security_config.test_get_content_filter_config()
        print("✅ Content filter config test passed")
    except Exception as e:
        print(f"❌ Content filter config test failed: {e}")
    
    try:
        security_config.test_get_password_policy()
        print("✅ Password policy test passed")
    except Exception as e:
        print(f"❌ Password policy test failed: {e}")
    
    try:
        security_config.test_get_rate_limits()
        print("✅ Rate limits test passed")
    except Exception as e:
        print(f"❌ Rate limits test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Guardrails Test Suite Complete!")
    print("Check the results above to see which tests passed or failed.")

if __name__ == "__main__":
    run_guardrails_tests()
