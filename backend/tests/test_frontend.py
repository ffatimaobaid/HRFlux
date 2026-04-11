import unittest
from unittest.mock import patch, MagicMock
import streamlit as st
import chat_app
import admin_app

class TestFrontend(unittest.TestCase):

    @patch('chat_app.st')
    def test_login_signup_flow(self, mock_st):
        # Simulate not logged in state
        mock_st.session_state = {}
        mock_st.text_input.return_value = "user"
        mock_st.text_input.return_value = "pass"
        mock_st.button.return_value = True
        mock_st.session_state.logged_in = False

        # Call chat_app main code (would normally be in if __name__ == '__main__')
        with patch('chat_app.login_user', return_value=True):
            chat_app.init_db()
            chat_app.init_user_table()
            # We cannot run full Streamlit app in test, but can test login logic

    @patch('admin_app.st')
    def test_admin_model_selection_and_upload(self, mock_st):
        mock_st.selectbox.return_value = "models/gemini-1.5-flash"
        mock_st.button.return_value = True
        mock_st.file_uploader.return_value = None
        admin_app.init_db()
        # Test model selection save logic

if __name__ == "__main__":
    unittest.main()
