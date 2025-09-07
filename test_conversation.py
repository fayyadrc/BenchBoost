#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_service import ai_service
from app.services.supabase_service import supabase_service

# Test the full AI service flow
bootstrap_data = supabase_service.get_bootstrap_data()
result = ai_service.analyze_query('hi', bootstrap_data, quick_mode=True, session_id='test123')
print('Final AI service result:')
print('Response:', repr(result['final_response']))
print('Query type:', result['query_classification'])
print('Confidence:', result['confidence'])
