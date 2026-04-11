import unittest
from unittest.mock import patch, MagicMock
import agent
import db
import rag
import gemini_llm

class TestBackend(unittest.TestCase):

    def test_db_signup_and_login(self):
        username = "testuser"
        password = "testpass"
        # Ensure user does not exist
        db.delete_user_history(username)
        # Signup user
        result = db.signup_user(username, password)
        self.assertTrue(result)
        # Duplicate signup should fail
        result2 = db.signup_user(username, password)
        self.assertFalse(result2)
        # Login user
        login_result = db.login_user(username, password)
        self.assertTrue(login_result)
        # Wrong password
        login_result2 = db.login_user(username, "wrongpass")
        self.assertFalse(login_result2)

    @patch('gemini_llm.genai.GenerativeModel.generate_content')
    def test_gemini_llm_query_and_classify(self, mock_generate):
        mock_generate.return_value.text = "Test response"
        answer = gemini_llm.query_gemini(["context"], "question")
        self.assertEqual(answer, "Test response")

        mock_generate.return_value.text = '{"is_leave_request": true, "leave_type": "sick", "start_date": "2023-01-01", "end_date": "2023-01-02", "reason": "flu"}'
        result = gemini_llm.classify_and_extract_leave("I want leave")
        self.assertTrue(result["is_leave_request"])

    @patch('agent.get_recent_history')
    @patch('agent.classify_and_extract_leave')
    @patch('agent.retrieve_context')
    @patch('agent.query_gemini')
    @patch('agent.save_leave_request')
    @patch('agent.save_log')
    def test_run_agent_leave_request(self, mock_save_log, mock_save_leave, mock_query, mock_retrieve, mock_classify, mock_history):
        mock_history.return_value = []
        mock_classify.return_value = {"is_leave_request": True, "start_date": "2023-01-01", "end_date": "2023-01-02", "reason": "flu"}
        mock_query.return_value = "Leave approved"
        mock_save_leave.return_value = None
        mock_save_log.return_value = None
        answer, suggestions = agent.run_agent("user", "I want leave")
        self.assertIn("leave request", answer.lower())

    def test_rag_retrieve_context(self):
        # This test assumes keyword_search and search_context are functional
        context = rag.retrieve_context("test query")
        self.assertIsInstance(context, list)

if __name__ == "__main__":
    unittest.main()
