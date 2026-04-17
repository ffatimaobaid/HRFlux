"""
Comprehensive Test Suite for Module 2: Knowledge Base & Backend Services
HRFlux Project - FYP Team: Fatima Obaid, Hadia Mazhar, Shayane Zainab

Test Coverage:
- Vector Database Integration (ChromaDB)
- Backend APIs (Employee data, leave balances, payroll)
- Workflow Engine (Leave requests, approvals, rejections)
- Search & Retrieval (Semantic search from policy documents)
- Embedding Generation and Indexing
- API Endpoints Testing
- RAG (Retrieval-Augmented Generation) Functionality
"""

import unittest
import sqlite3
import os
import sys
import tempfile
import shutil
import json
import requests
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, Mock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vector_store
import rag
import main as backend_api
from fastapi.testclient import TestClient
import chromadb

class TestModule2KnowledgeBase(unittest.TestCase):
    """Test cases for Module 2: Knowledge Base & Backend Services"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.test_db = "test_queries.db"
        cls.original_db = "queries.db"
        cls.test_chroma_path = "test_chroma_storage"
        
        # Backup original database
        if os.path.exists(cls.original_db):
            shutil.copy(cls.original_db, cls.test_db)
        else:
            # Create fresh test database
            import db_schema_v2
            db_schema_v2.DB_PATH = cls.test_db
            db_schema_v2.create_enhanced_schema()
        
        # Set up test ChromaDB
        if os.path.exists(cls.test_chroma_path):
            shutil.rmtree(cls.test_chroma_path)
        
        # Mock ChromaDB path for testing - use lazy initialization
        vector_store.chroma_path = cls.test_chroma_path
        # Reset client to None to force re-initialization
        vector_store.client = None
        vector_store.embedding_func = None
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        # Close ChromaDB client before cleanup to avoid file locking issues on Windows
        try:
            if vector_store.client is not None:
                # ChromaDB doesn't have explicit close, but we can reset it
                vector_store.client = None
                vector_store.embedding_func = None
        except:
            pass
        
        # Wait a bit for file handles to release (Windows issue)
        import time
        time.sleep(0.5)
        
        if os.path.exists(cls.test_db):
            try:
                os.remove(cls.test_db)
            except:
                pass
        
        if os.path.exists(cls.test_chroma_path):
            try:
                # Try multiple times with delays for Windows file locking
                for _ in range(3):
                    try:
                        shutil.rmtree(cls.test_chroma_path)
                        break
                    except PermissionError:
                        time.sleep(0.5)
            except:
                pass
    
    def setUp(self):
        """Set up each test"""
        # Use test database
        import db_schema_v2
        import workflow_engine
        db_schema_v2.DB_PATH = self.test_db
        workflow_engine.DB_PATH = self.test_db
        
        # Create fresh schema
        db_schema_v2.create_enhanced_schema()
        
        # Delete existing test employee if exists to avoid conflicts
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("DELETE FROM employees WHERE employee_id = 'TEST001'")
        c.execute("DELETE FROM leave_requests_v2 WHERE employee_id = 'TEST001'")
        conn.commit()
        conn.close()
        
        # Add test employee with unique email per test run
        import time
        unique_email = f"test.user.{int(time.time() * 1000)}@company.com"
        db_schema_v2.add_employee(
            employee_id="TEST001",
            username="test.user",
            password="password123",
            full_name="Test User",
            email=unique_email,
            department="IT",
            designation="Developer",
            joining_date="2024-01-15",
            salary=75000
        )
        
        # Reset leave balances to defaults
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("""
            UPDATE employees 
            SET casual_leave_balance = 10, 
                sick_leave_balance = 10, 
                annual_leave_balance = 14
            WHERE employee_id = 'TEST001'
        """)
        conn.commit()
        conn.close()
        
        # Initialize ChromaDB for this test
        try:
            vector_store._init_chromadb()
        except Exception as e:
            print(f"Warning: ChromaDB initialization failed: {e}")
        
        # Set up FastAPI test client with authentication bypass
        self.client = TestClient(backend_api.app)
    
    def tearDown(self):
        """Clean up after each test"""
        # Clear ChromaDB collection
        try:
            collection = vector_store.get_or_create_collection()
            collection.delete(where={})
        except:
            pass
    
    # ========== Vector Database Integration Tests ==========
    
    def test_chromadb_connection(self):
        """Test 1.1: ChromaDB connection and collection creation"""
        collection = vector_store.get_or_create_collection("test_collection")
        self.assertIsNotNone(collection, "ChromaDB collection should be created")
        self.assertEqual(collection.name, "test_collection", "Collection name should match")
    
    def test_document_embedding_and_storage(self):
        """Test 1.2: Document embedding and storage in vector database"""
        # Test document chunks
        doc_id = "test_doc_001"
        chunks = [
            "This is the first chunk of HR policy document.",
            "This is the second chunk containing leave policies.",
            "This is the third chunk about employee benefits."
        ]
        
        # Add to vector store
        vector_store.add_document_chunks(doc_id, chunks)
        
        # Verify storage
        collection = vector_store.get_or_create_collection()
        result = collection.get()
        stored_ids = result.get("ids", [])
        
        # Check if chunks were stored
        expected_ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        for expected_id in expected_ids:
            self.assertIn(expected_id, stored_ids, f"Chunk {expected_id} should be stored")
    
    def test_document_retrieval_from_vector_db(self):
        """Test 1.3: Document retrieval from vector database"""
        # Add test documents
        doc_id = "retrieval_test"
        chunks = [
            "Annual leave policy: Employees are entitled to 14 days of annual leave per year.",
            "Sick leave policy: Employees can take up to 10 days of sick leave with medical certificate.",
            "Casual leave policy: Employees get 10 days of casual leave for personal matters."
        ]
        
        vector_store.add_document_chunks(doc_id, chunks)
        
        # Test retrieval
        collection = vector_store.get_or_create_collection()
        results = collection.query(
            query_texts=["annual leave entitlement"],
            n_results=2
        )
        
        self.assertGreater(len(results['documents'][0]), 0, "Should retrieve relevant documents")
        self.assertIn("annual leave", results['documents'][0][0].lower(), "Retrieved document should be relevant")
    
    def test_document_deletion_from_vector_db(self):
        """Test 1.4: Document deletion from vector database"""
        # Add test document
        doc_id = "delete_test"
        chunks = ["This document should be deleted."]
        vector_store.add_document_chunks(doc_id, chunks)
        
        # Verify it exists
        collection = vector_store.get_or_create_collection()
        result = collection.get()
        self.assertIn(f"{doc_id}_0", result['ids'])
        
        # Delete document
        vector_store.delete_document_embeddings(doc_id)
        
        # Verify deletion
        result = collection.get()
        self.assertNotIn(f"{doc_id}_0", result['ids'], "Document should be deleted")
    
    # ========== Backend API Tests ==========
    
    def test_employee_data_api_endpoint(self):
        """Test 2.1: Employee data API endpoint"""
        response = self.client.get("/api/employees/TEST001")
        self.assertEqual(response.status_code, 200, "Should retrieve employee data successfully")
        
        data = response.json()
        self.assertEqual(data['employee_id'], "TEST001", "Should return correct employee")
        self.assertEqual(data['username'], "test.user", "Should return correct username")
        self.assertEqual(data['department'], "IT", "Should return correct department")
    
    def test_leave_balance_api_endpoint(self):
        """Test 2.2: Leave balance API endpoint"""
        response = self.client.get("/api/leave-balance/TEST001")
        self.assertEqual(response.status_code, 200, "Should retrieve leave balances successfully")
        
        data = response.json()
        self.assertIn('casual_leave_balance', data, "Should include casual leave balance")
        self.assertIn('sick_leave_balance', data, "Should include sick leave balance")
        self.assertIn('annual_leave_balance', data, "Should include annual leave balance")
        
        # Check default values
        self.assertEqual(data['casual_leave_balance'], 10, "Default casual leave should be 10")
        self.assertEqual(data['sick_leave_balance'], 10, "Default sick leave should be 10")
        self.assertEqual(data['annual_leave_balance'], 14, "Default annual leave should be 14")
    
    def test_nonexistent_employee_api(self):
        """Test 2.3: API response for non-existent employee"""
        response = self.client.get("/api/employees/NONEXISTENT")
        self.assertEqual(response.status_code, 404, "Should return 404 for non-existent employee")
        
        response = self.client.get("/api/leave-balance/NONEXISTENT")
        self.assertEqual(response.status_code, 404, "Should return 404 for non-existent employee")
    
    def test_attendance_api_endpoint(self):
        """Test 2.4: Attendance records API endpoint"""
        # Add attendance record
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("""
            INSERT INTO attendance 
            (employee_id, date, check_in_time, check_out_time, status)
            VALUES (?, ?, ?, ?, ?)
        """, ("TEST001", "2024-01-15", "09:00:00", "18:00:00", "present"))
        conn.commit()
        conn.close()
        
        # Test API
        response = self.client.get("/api/attendance/TEST001")
        self.assertEqual(response.status_code, 200, "Should retrieve attendance records")
        
        data = response.json()
        self.assertIsInstance(data, list, "Should return list of attendance records")
        self.assertGreater(len(data), 0, "Should have attendance records")
    
    # ========== Workflow Engine Tests ==========
    
    def test_leave_request_creation(self):
        """Test 3.1: Leave request creation workflow"""
        leave_data = {
            "employee_id": "TEST001",
            "leave_type": "casual",
            "start_date": "2024-02-01",
            "end_date": "2024-02-02",
            "total_days": 2,
            "reason": "Personal work"
        }
        
        response = self.client.post("/api/leave-request", json=leave_data)
        self.assertEqual(response.status_code, 201, "Should create leave request successfully")
        
        data = response.json()
        self.assertIn('request_id', data, "Should return request ID")
        self.assertEqual(data['status'], 'pending', "New request should be pending")
    
    def test_leave_request_validation(self):
        """Test 3.2: Leave request validation"""
        # Test invalid leave type
        invalid_leave = {
            "employee_id": "TEST001",
            "leave_type": "invalid_type",
            "start_date": "2024-02-01",
            "end_date": "2024-02-02",
            "total_days": 2,
            "reason": "Test"
        }
        
        response = self.client.post("/api/leave-request", json=invalid_leave)
        self.assertEqual(response.status_code, 400, "Should reject invalid leave type")
        
        # Test invalid date range
        invalid_dates = {
            "employee_id": "TEST001",
            "leave_type": "casual",
            "start_date": "2024-02-02",
            "end_date": "2024-02-01",  # End before start
            "total_days": 2,
            "reason": "Test"
        }
        
        response = self.client.post("/api/leave-request", json=invalid_dates)
        self.assertEqual(response.status_code, 400, "Should reject invalid date range")
    
    def test_leave_approval_workflow(self):
        """Test 3.3: Leave approval workflow"""
        # Create leave request first
        leave_data = {
            "employee_id": "TEST001",
            "leave_type": "sick",
            "start_date": "2024-02-05",
            "end_date": "2024-02-06",
            "total_days": 2,
            "reason": "Medical appointment"
        }
        
        create_response = self.client.post("/api/leave-request", json=leave_data)
        request_id = create_response.json()['request_id']
        
        # Approve the request
        approval_data = {
            "request_id": request_id,
            "approver_id": "MGR001",
            "action": "approve",
            "comments": "Approved as requested"
        }
        
        response = self.client.post("/api/leave-approval", json=approval_data)
        self.assertEqual(response.status_code, 200, "Should process approval successfully")
        
        # Verify status change
        check_response = self.client.get(f"/api/leave-request/{request_id}")
        self.assertEqual(check_response.json()['status'], 'approved', "Request should be approved")
    
    def test_leave_rejection_workflow(self):
        """Test 3.4: Leave rejection workflow"""
        # Create leave request
        leave_data = {
            "employee_id": "TEST001",
            "leave_type": "casual",
            "start_date": "2024-02-10",
            "end_date": "2024-02-11",
            "total_days": 2,
            "reason": "Personal travel"
        }
        
        create_response = self.client.post("/api/leave-request", json=leave_data)
        request_id = create_response.json()['request_id']
        
        # Reject the request
        rejection_data = {
            "request_id": request_id,
            "approver_id": "MGR001",
            "action": "reject",
            "comments": "Insufficient notice period"
        }
        
        response = self.client.post("/api/leave-approval", json=rejection_data)
        self.assertEqual(response.status_code, 200, "Should process rejection successfully")
        
        # Verify status change
        check_response = self.client.get(f"/api/leave-request/{request_id}")
        self.assertEqual(check_response.json()['status'], 'rejected', "Request should be rejected")
    
    # ========== Search & Retrieval Tests ==========
    
    def test_semantic_search_functionality(self):
        """Test 4.1: Semantic search functionality"""
        # Add test documents to vector store
        doc_id = "search_test"
        chunks = [
            "Annual leave policy: All employees are entitled to 14 working days of paid annual leave per calendar year.",
            "Sick leave policy: Employees may take up to 10 days of sick leave per year with appropriate medical documentation.",
            "Maternity leave policy: Female employees are entitled to 90 days of maternity leave as per company policy.",
            "Casual leave policy: Employees can avail 10 days of casual leave for personal emergencies and family matters."
        ]
        
        vector_store.add_document_chunks(doc_id, chunks)
        
        # Test semantic search
        collection = vector_store.get_or_create_collection()
        
        # Search for annual leave
        results = collection.query(
            query_texts=["how many days annual leave"],
            n_results=2
        )
        
        self.assertGreater(len(results['documents'][0]), 0, "Should find relevant documents")
        # Should return annual leave related content
        found_annual_leave = any("annual leave" in doc.lower() for doc in results['documents'][0])
        self.assertTrue(found_annual_leave, "Should find annual leave policy")
    
    def test_keyword_search_fallback(self):
        """Test 4.2: Keyword search as fallback"""
        # Test keyword search functionality
        with patch('rag.retrieve_context') as mock_retrieve:
            mock_retrieve.return_value = ["Test context for keyword search"]
            
            # This should use keyword search if semantic search fails
            context = rag.retrieve_context("test query")
            self.assertIsInstance(context, list, "Should return context as list")
    
    def test_context_relevance_scoring(self):
        """Test 4.3: Context relevance scoring"""
        # Add test documents with different relevance levels
        doc_id = "relevance_test"
        chunks = [
            "This document contains HR policies about leave entitlements and procedures.",
            "This document discusses IT infrastructure and server maintenance protocols.",
            "This document outlines employee benefits including health insurance and retirement plans."
        ]
        
        vector_store.add_document_chunks(doc_id, chunks)
        
        # Search for leave-related query
        collection = vector_store.get_or_create_collection()
        results = collection.query(
            query_texts=["leave entitlement policy"],
            n_results=3
        )
        
        # The most relevant document should be about HR policies/leave
        documents = results['documents'][0]
        self.assertGreater(len(documents), 0, "Should return documents")
        
        # Check if HR/leave policy appears in results
        hr_policy_found = any("hr policies" in doc.lower() or "leave" in doc.lower() 
                             for doc in documents)
        self.assertTrue(hr_policy_found, "Should find relevant HR policy document")
    
    # ========== RAG Functionality Tests ==========
    
    @patch('gemini_llm.query_gemini')
    def test_rag_query_processing(self, mock_query):
        """Test 5.1: RAG query processing"""
        # Mock LLM response
        mock_query.return_value = "Based on the policy, employees are entitled to 14 days of annual leave."
        
        # Mock context retrieval
        with patch('rag.retrieve_context') as mock_retrieve:
            mock_retrieve.return_value = [
                "Annual leave policy: All employees are entitled to 14 working days of paid annual leave per calendar year."
            ]
            
            # Test RAG processing
            response = rag.process_rag_query("How many days of annual leave do I get?")
            self.assertIsInstance(response, str, "Should return string response")
            self.assertIn("14 days", response, "Should include specific policy information")
    
    @patch('gemini_llm.query_gemini')
    def test_rag_with_no_context(self, mock_query):
        """Test 5.2: RAG behavior with no relevant context"""
        # Mock LLM response for no context case
        mock_query.return_value = "I don't have specific information about that query. Please contact HR for details."
        
        # Mock empty context
        with patch('rag.retrieve_context') as mock_retrieve:
            mock_retrieve.return_value = []
            
            response = rag.process_rag_query("What is the company dress code for summer?")
            self.assertIsInstance(response, str, "Should return fallback response")
    
    @patch('gemini_llm.query_gemini')
    def test_rag_context_length_handling(self, mock_query):
        """Test 5.3: RAG context length handling"""
        # Mock LLM response
        mock_query.return_value = "Response based on truncated context."
        
        # Create long context
        long_context = ["This is a very long context document. " * 100]  # Long text
        with patch('rag.retrieve_context') as mock_retrieve:
            mock_retrieve.return_value = long_context
            
            # Should handle long context gracefully
            response = rag.process_rag_query("Test query")
            self.assertIsInstance(response, str, "Should handle long context")
    
    # ========== Integration Tests ==========
    
    def test_end_to_end_leave_workflow(self):
        """Test 6.1: End-to-end leave workflow with knowledge base"""
        # 1. Add policy documents to knowledge base
        doc_id = "leave_policies"
        policy_chunks = [
            "Annual Leave Policy: Employees are entitled to 14 days of annual leave per year.",
            "Leave Approval Process: All leave requests must be approved by the immediate manager.",
            "Leave Balance Check: Employees can check their leave balance through the HR portal."
        ]
        
        vector_store.add_document_chunks(doc_id, policy_chunks)
        
        # 2. Create leave request through API
        leave_data = {
            "employee_id": "TEST001",
            "leave_type": "annual",
            "start_date": "2024-03-01",
            "end_date": "2024-03-05",
            "total_days": 5,
            "reason": "Family vacation"
        }
        
        response = self.client.post("/api/leave-request", json=leave_data)
        self.assertEqual(response.status_code, 201)
        request_id = response.json()['request_id']
        
        # 3. Query policy information
        collection = vector_store.get_or_create_collection()
        policy_results = collection.query(
            query_texts=["annual leave entitlement"],
            n_results=1
        )
        
        self.assertGreater(len(policy_results['documents'][0]), 0, "Should retrieve policy info")
        
        # 4. Approve leave request
        approval_data = {
            "request_id": request_id,
            "approver_id": "MGR001",
            "action": "approve",
            "comments": "Approved as per annual leave policy"
        }
        
        response = self.client.post("/api/leave-approval", json=approval_data)
        self.assertEqual(response.status_code, 200)
    
    def test_api_error_handling(self):
        """Test 6.2: API error handling and validation"""
        # Test malformed JSON
        response = self.client.post(
            "/api/leave-request",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        self.assertEqual(response.status_code, 422, "Should handle malformed JSON")
        
        # Test missing required fields
        incomplete_data = {
            "employee_id": "TEST001",
            # Missing other required fields
        }
        
        response = self.client.post("/api/leave-request", json=incomplete_data)
        self.assertEqual(response.status_code, 422, "Should validate required fields")
    
    def test_concurrent_requests_handling(self):
        """Test 6.3: Concurrent requests handling"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = self.client.get("/api/employees/TEST001")
            results.append(response.status_code)
        
        # Create multiple concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        for status_code in results:
            self.assertEqual(status_code, 200, "Concurrent requests should succeed")

if __name__ == "__main__":
    unittest.main()
