"""
Comprehensive Test Suite for Module 3: HR Agent Layer
HRFlux Project - FYP Team: Fatima Obaid, Hadia Mazhar, Shayane Zainab
"""

import unittest
import sqlite3
import os
import sys
import shutil
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db_schema_v2
import leave_bot_tools
import escalation_tools
import docu_tools
from workflow_engine import LeaveWorkflowEngine, ChatEscalationEngine

class TestModule3HRAgentLayer(unittest.TestCase):
    """Test cases for Module 3: HR Agent Layer"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.test_db = "test_module3.db"
        
        # Create fresh test database schema
        db_schema_v2.DB_PATH = cls.test_db
        db_schema_v2.create_enhanced_schema()
        
        # Setup paths logic for each module
        leave_bot_tools.DB_PATH = cls.test_db
        escalation_tools.DB_PATH = cls.test_db
        import notifications
        notifications.DB_PATH = cls.test_db
        import workflow_engine
        workflow_engine.DB_PATH = cls.test_db
        import db
        db.DB_PATH = cls.test_db
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)
    
    def setUp(self):
        """Set up basic employee for each test"""
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("DELETE FROM employees")
        c.execute("DELETE FROM leave_requests_v2")
        c.execute("DELETE FROM chat_escalations")
        c.execute("DELETE FROM notifications")
        conn.commit()
        conn.close()
        
        self.username = "emp_user"
        self.emp_id = "EMP999"
        
        db_schema_v2.add_employee(
            employee_id=self.emp_id,
            username=self.username,
            password="password123",
            full_name="Employee User",
            email="emp@company.com",
            department="Engineering",
            designation="Developer",
            joining_date="2024-01-01",
            salary=50000
        )
        
    def tearDown(self):
        pass

    # ========== 1. LeaveBot Tests ==========
    
    def test_leave_bot_check_balance(self):
        """Test LeaveBot: checking leave balance"""
        # Call the tool
        response = leave_bot_tools.tool_get_leave_balance.invoke({"username": self.username})
        
        # It should contain the default balances
        self.assertIn("10", response)
        self.assertIn("casual", response.lower())
        self.assertIn("sick", response.lower())
        
    def test_leave_bot_apply_leave(self):
        """Test LeaveBot: apply for leave"""
        # Apply valid leave
        response = leave_bot_tools.tool_submit_leave_request.invoke({
            "username": self.username,
            "leave_type": "casual",
            "start_date": "2025-01-01",
            "end_date": "2025-01-02",
            "reason": "Family gathering"
        })
        
        self.assertIn("successfully", response.lower())
        self.assertIn("id:", response.lower())
        
        # Verify in DB
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("SELECT status, total_days FROM leave_requests_v2 WHERE employee_id=?", (self.emp_id,))
        req = c.fetchone()
        conn.close()
        
        self.assertIsNotNone(req)
        self.assertEqual(req[0], "pending")
        self.assertGreater(req[1], 0)

    def test_leave_bot_insufficient_balance(self):
        """Test LeaveBot: apply for leave exceeding balance"""
        response = leave_bot_tools.tool_submit_leave_request.invoke({
            "username": self.username,
            "leave_type": "casual",
            "start_date": "2026-01-01",
            "end_date": "2026-01-20", # 20 days is greater than default casual balance of 10
            "reason": "Very long vacation"
        })
        self.assertIn("false", response.lower())
        self.assertIn("insufficient", response.lower())

    def test_leave_bot_invalid_user(self):
        """Test LeaveBot: check balance for non-existent user"""
        response = leave_bot_tools.tool_get_leave_balance.invoke({"username": "ghost_user"})
        self.assertIn("not found", response.lower())
        self.assertIn("error", response.lower())

    def test_leave_bot_get_history(self):
        """Test LeaveBot: check leave history parsing"""
        response = leave_bot_tools.tool_get_leave_history.invoke({"username": self.username})
        # Could be "No leave history" or actual history depending on order of tests, just ensure it doesn't crash
        self.assertIsInstance(response, str)
        self.assertTrue("history" in response.lower() or "no leave history" in response.lower())


    # ========== 2. PolicyBot Tests ==========
    
    @patch('rag.search_context')
    def test_policy_bot_retrieval(self, mock_search_context):
        """Test PolicyBot: RAG mechanism mocked behavior"""
        mock_search_context.return_value = ["According to company policy, remote work is allowed 2 days a week."]
        import rag
        
        # Emulating PolicyBot calling context retrieval
        answer_chunks = rag.retrieve_context("remote work policy")
        self.assertTrue(len(answer_chunks) > 0)
        self.assertIn("remote work", answer_chunks[0].lower())

    @patch('rag.search_context')
    @patch('rag.keyword_search')
    def test_policy_bot_no_policy_found(self, mock_kw, mock_sc):
        """Test PolicyBot: RAG returns completely empty context"""
        mock_kw.return_value = []
        mock_sc.return_value = []
        import rag
        chunks = rag.retrieve_context("gibberish that docs dont cover")
        self.assertEqual(len(chunks), 0)

    @patch('rag.search_context')
    @patch('rag.keyword_search')
    def test_policy_bot_multiple_contexts(self, mock_kw, mock_sc):
        """Test PolicyBot: RAG successfully combines dense and keyword results"""
        mock_sc.return_value = ["Context A"]
        mock_kw.return_value = ["Context A", "Context B"]
        import rag
        chunks = rag.retrieve_context("some HR query")
        self.assertEqual(len(chunks), 2)
        self.assertIn("Context A", chunks)
        self.assertIn("Context B", chunks)

    # ========== 3. DocuBot Tests ==========
    
    def test_docubot_draft_document(self):
        """Test DocuBot: drafting NOC document"""
        response = docu_tools.tool_draft_document_content.invoke({
            "document_type": "NOC for Visa",
            "username": self.username,
            "specific_requirements": ""
        })
        self.assertIn("draft_ready", response.lower())
        self.assertIn("noc", response.lower())
        
    @patch('docu_tools.convert_text_to_pdf')
    def test_docubot_generate_salary_cert(self, mock_convert):
        """Test DocuBot: generating Salary Certificate"""
        mock_convert.return_value = "documents/dummy.pdf"
        response = docu_tools.tool_generate_pdf_from_draft.invoke({
            "document_type": "Salary Certificate",
            "username": self.username,
            "approved_content": "This is a dummy salary cert."
        })
        
        self.assertIn("download_url", response.lower())
        self.assertIn(".pdf", response.lower())

    def test_docubot_draft_experience_letter(self):
        """Test DocuBot: drafting Experience Letter"""
        response = docu_tools.tool_draft_document_content.invoke({
            "document_type": "Experience Letter",
            "username": self.username,
            "specific_requirements": "Must mention proficiency in Python"
        })
        self.assertIn("draft_ready", response.lower())
        self.assertIn("python", response.lower())

    def test_docubot_invalid_document_type(self):
        """Test DocuBot: drafting invalid document type"""
        response = docu_tools.tool_draft_document_content.invoke({
            "document_type": "Medical Certificate",
            "username": self.username,
            "specific_requirements": ""
        })
        self.assertIn("error", response.lower())
        self.assertIn("not supported", response.lower())

    def test_docubot_fallback_employee_data(self):
        """Test DocuBot: drafting with invalid user falls back to demo data implicitly"""
        response = docu_tools.tool_draft_document_content.invoke({
            "document_type": "NOC for Visa",
            "username": "missing.person",
            "specific_requirements": ""
        })
        self.assertIn("draft_ready", response.lower())
        # The demo data title cases the username
        self.assertIn("Missing Person", response.title())

    # ========== 4. EscalationBot Tests ==========
    
    def test_escalation_bot_file_escalation(self):
        """Test EscalationBot: Filing a new escalation ticket"""
        with patch('escalation_tools.generate_escalation_summary', return_value="Summary of issue."):
            with patch('escalation_tools.get_recent_history', return_value=[]):
                response = escalation_tools.tool_file_escalation.invoke({
                    "username": self.username,
                    "incident_category": "GENERAL",
                    "incident_description": "I have an unexplained deduction in my paycheck.",
                    "parties_involved": "None",
                    "urgency_level": "Low"
                })
        
        self.assertIn("successfully", response.lower())
        self.assertIn("hr", response.lower())
        
        # Verify in DB
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("SELECT query, status FROM chat_escalations WHERE username=?", (self.username,))
        esc = c.fetchone()
        conn.close()
        
        self.assertIsNotNone(esc)
        self.assertEqual(esc[0], "I have an unexplained deduction in my paycheck.")
        self.assertEqual(esc[1], "pending")

    def test_escalation_bot_invalid_category(self):
        """Test EscalationBot: invalid category defaults to GENERAL"""
        with patch('escalation_tools.generate_escalation_summary', return_value="Summary"):
            with patch('escalation_tools.get_recent_history', return_value=[]):
                response = escalation_tools.tool_file_escalation.invoke({
                    "username": self.username,
                    "incident_category": "FOOD_COMPLAINT",
                    "incident_description": "Cafeteria food.",
                    "parties_involved": "None",
                    "urgency_level": "Low"
                })
        self.assertIn("successfully", response.lower())
        self.assertIn("hr helpdesk", response.lower())

    def test_escalation_bot_get_my_escalations(self):
        """Test EscalationBot: user can see their history"""
        # Ensure there is an escalation first
        with patch('escalation_tools.generate_escalation_summary', return_value="Summary"):
            with patch('escalation_tools.get_recent_history', return_value=[]):
                escalation_tools.tool_file_escalation.invoke({
                    "username": self.username,
                    "incident_category": "GENERAL",
                    "incident_description": "I need help.",
                    "parties_involved": "None",
                    "urgency_level": "Low"
                })
        
        response = escalation_tools.tool_get_my_escalations.invoke({"username": self.username})
        self.assertIn("total", response.lower())
        self.assertIn("pending hr review", response.lower())

    def test_escalation_bot_resolve_invalid(self):
        """Test EscalationBot: resolving non-existent ID fails gracefully"""
        result = ChatEscalationEngine.resolve_escalation(99999, "Will fail")
        self.assertFalse(result['success'])
        self.assertIn("not found", result['message'].lower())

    def test_escalation_bot_resolve_and_notify(self):
        """Test EscalationBot: Resolving an escalation sends notification"""
        # 1. Manually insert an escalation to avoid dependency failures
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("""
            INSERT INTO chat_escalations 
            (employee_id, username, query, full_history, reason, sensitivity_score, status, conversation_summary)
            VALUES (?, ?, 'Harassment complaint', '', 'Serious complaint', 1.0, 'pending', 'summary')
        """, (self.emp_id, self.username))
        esc_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # 2. Mock Notification Manager explicitly to ensure DB path binds properly
        with patch('workflow_engine.NotificationManager.create_notification') as mock_notif:
            # Resolve it
            result = ChatEscalationEngine.resolve_escalation(esc_id, "Investigated and resolved.")
            self.assertTrue(result['success'])
            
            # Ensure notification function was called on employee_id
            mock_notif.assert_called_once()
            args, kwargs = mock_notif.call_args
            self.assertEqual(kwargs.get('user_id'), self.emp_id)
            self.assertEqual(kwargs.get('n_type'), "success")

if __name__ == "__main__":
    unittest.main()
