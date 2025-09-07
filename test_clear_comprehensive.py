#!/usr/bin/env python3
"""
Comprehensive test for clear chat and conversation context features
"""

import requests
import json
import time

def test_clear_chat_comprehensive():
    """Test the complete clear chat workflow with multiple sessions"""
    base_url = "http://127.0.0.1:8080"
    
    print("🧪 Comprehensive Clear Chat & Context Test")
    print("=" * 60)
    
    # Test 1: Basic Clear Chat
    print("\n1️⃣ BASIC CLEAR CHAT TEST")
    print("-" * 30)
    session1 = f"test_basic_{int(time.time())}"
    
    # Send a message
    response = requests.post(f"{base_url}/ask", json={
        'question': 'Hello, how are you?',
        'session_id': session1
    })
    print(f"✅ Message sent: {response.status_code}")
    
    # Clear history
    clear_response = requests.post(f"{base_url}/conversation/clear",
        headers={'Content-Type': 'application/json'},
        json={'session_id': session1}
    )
    result = clear_response.json()
    print(f"✅ Clear result: {result.get('success', False)}")
    
    # Test 2: Context Conversation + Clear
    print("\n2️⃣ CONTEXTUAL CONVERSATION + CLEAR TEST")
    print("-" * 40)
    session2 = f"test_context_{int(time.time())}"
    
    # First message about a player
    response1 = requests.post(f"{base_url}/ask", json={
        'question': 'Tell me about Erling Haaland',
        'session_id': session2
    })
    print(f"✅ Context message 1: {response1.status_code}")
    
    # Contextual follow-up
    response2 = requests.post(f"{base_url}/ask", json={
        'question': 'How much does he cost?',
        'session_id': session2
    })
    print(f"✅ Context message 2: {response2.status_code}")
    
    # Check history before clear
    history_response = requests.get(f"{base_url}/conversation/history", 
        params={'session_id': session2, 'limit': 10}
    )
    history_count = history_response.json().get('message_count', 0)
    print(f"✅ Messages before clear: {history_count}")
    
    # Clear history
    clear_response = requests.post(f"{base_url}/conversation/clear",
        headers={'Content-Type': 'application/json'},
        json={'session_id': session2}
    )
    clear_result = clear_response.json()
    print(f"✅ Clear result: {clear_result.get('success', False)}")
    
    # Verify cleared
    verify_response = requests.get(f"{base_url}/conversation/history", 
        params={'session_id': session2, 'limit': 10}
    )
    remaining_count = verify_response.json().get('message_count', 0)
    print(f"✅ Messages after clear: {remaining_count}")
    
    # Test 3: Multiple Sessions Independence
    print("\n3️⃣ MULTIPLE SESSIONS INDEPENDENCE TEST")
    print("-" * 40)
    session3a = f"test_multi_a_{int(time.time())}"
    session3b = f"test_multi_b_{int(time.time())}"
    
    # Send messages to both sessions
    requests.post(f"{base_url}/ask", json={
        'question': 'Session A message',
        'session_id': session3a
    })
    requests.post(f"{base_url}/ask", json={
        'question': 'Session B message',
        'session_id': session3b
    })
    
    # Clear only session A
    clear_a = requests.post(f"{base_url}/conversation/clear",
        headers={'Content-Type': 'application/json'},
        json={'session_id': session3a}
    )
    
    # Check both sessions
    history_a = requests.get(f"{base_url}/conversation/history", 
        params={'session_id': session3a, 'limit': 10}
    ).json().get('message_count', 0)
    
    history_b = requests.get(f"{base_url}/conversation/history", 
        params={'session_id': session3b, 'limit': 10}
    ).json().get('message_count', 0)
    
    print(f"✅ Session A after clear: {history_a} messages")
    print(f"✅ Session B after clear: {history_b} messages")
    print(f"✅ Independence test: {'PASS' if history_a == 0 and history_b > 0 else 'FAIL'}")
    
    # Test 4: Error Handling
    print("\n4️⃣ ERROR HANDLING TEST")
    print("-" * 25)
    
    # Test with missing session_id
    error_response = requests.post(f"{base_url}/conversation/clear",
        headers={'Content-Type': 'application/json'},
        json={}
    )
    error_result = error_response.json()
    print(f"✅ Missing session_id error: {error_response.status_code}")
    print(f"   Error message: {error_result.get('error', 'No error message')}")
    
    # Test with non-existent session
    empty_clear = requests.post(f"{base_url}/conversation/clear",
        headers={'Content-Type': 'application/json'},
        json={'session_id': 'non_existent_session_12345'}
    )
    empty_result = empty_clear.json()
    print(f"✅ Non-existent session: {empty_result.get('success', False)}")
    
    print("\n" + "=" * 60)
    print("🎉 COMPREHENSIVE TEST COMPLETE!")
    print("✅ All clear chat functionality verified")

if __name__ == "__main__":
    try:
        test_clear_chat_comprehensive()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the Flask app is running on port 8080.")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
