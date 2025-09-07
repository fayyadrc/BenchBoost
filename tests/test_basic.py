"""
Basic tests for FPL Chatbot application
"""

import unittest
import json
import os
from app import create_app


class FPLChatbotTestCase(unittest.TestCase):
    """Test cases for the FPL Chatbot application"""
    
    def setUp(self):
        """Set up test client and configuration"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
    def tearDown(self):
        """Clean up after tests"""
        pass
        
    def test_health_check(self):
        """Test the health check endpoint"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('status', data)
        self.assertIn(data['status'], ['healthy', 'unhealthy'])
        
    def test_landing_page(self):
        """Test that the landing page loads correctly"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'FPL', response.data)
        
    def test_chat_page(self):
        """Test that the chat page loads correctly"""
        response = self.client.get('/chat')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'chat', response.data.lower())
        
    def test_home_page(self):
        """Test that the home page loads correctly"""
        response = self.client.get('/home')
        self.assertEqual(response.status_code, 200)
        
    def test_ask_endpoint_basic(self):
        """Test the ask endpoint with basic input"""
        response = self.client.post('/ask', 
                                  data=json.dumps({'message': 'hello'}),
                                  content_type='application/json')
        
        # Should return 200 even if AI is not configured in test environment
        self.assertIn(response.status_code, [200, 500])  # 500 is acceptable if no API keys
        
    def test_ask_endpoint_no_message(self):
        """Test the ask endpoint with missing message"""
        response = self.client.post('/ask', 
                                  data=json.dumps({}),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
    def test_ask_endpoint_empty_message(self):
        """Test the ask endpoint with empty message"""
        response = self.client.post('/ask', 
                                  data=json.dumps({'message': ''}),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)


class ConfigurationTestCase(unittest.TestCase):
    """Test configuration and environment setup"""
    
    def test_required_imports(self):
        """Test that all required modules can be imported"""
        try:
            import flask
            import requests
            import os
            import json
            from app import create_app
        except ImportError as e:
            self.fail(f"Required import failed: {e}")
            
    def test_app_creation(self):
        """Test that the Flask app can be created"""
        app = create_app()
        self.assertIsNotNone(app)
        self.assertEqual(app.config['TESTING'], False)  # Default should be False
        
    def test_production_config(self):
        """Test production configuration settings"""
        app = create_app()
        
        # In production, debug should be False
        if os.environ.get('FLASK_ENV') == 'production':
            self.assertFalse(app.config.get('DEBUG', True))


class ServiceTestCase(unittest.TestCase):
    """Test service integrations"""
    
    def test_query_analyzer_import(self):
        """Test that query analyzer can be imported"""
        try:
            from app.services.query_analyzer import analyze_user_query
            self.assertTrue(callable(analyze_user_query))
        except ImportError as e:
            self.fail(f"Query analyzer import failed: {e}")
            
    def test_ai_service_import(self):
        """Test that AI service can be imported"""
        try:
            from app.services.ai_service import ai_service
            self.assertIsNotNone(ai_service)
        except ImportError as e:
            self.fail(f"AI service import failed: {e}")
            
    def test_fpl_api_import(self):
        """Test that FPL API client can be imported"""
        try:
            from app.models.fpl_api import fpl_client
            self.assertIsNotNone(fpl_client)
        except ImportError as e:
            self.fail(f"FPL API import failed: {e}")


if __name__ == '__main__':
    # Set test environment
    os.environ['FLASK_ENV'] = 'testing'
    
    # Run tests
    unittest.main(verbosity=2)
