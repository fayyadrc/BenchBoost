#!/usr/bin/env python3
"""
Test script for clear chat functionality
"""

import requests
import json
import time

def test_clear_chat():
    """Test the clear chat functionality"""
    base_url = "http://127.0.0.1:8080"
    session_id = f"test_session_{int(time.time())}"
    
    print(f"🧪 Testing Clear Chat Feature")
    print(f"📱 Session ID: {session_id}")
    print("-" * 50)
    
    # Step 1: Send a test message to create conversation history
    print("1️⃣ Creating conversation history...")
    ask_response = requests.post(f"{base_url}/ask", 
        headers={'Content-Type': 'application/json'},
        json={
            'question': 'Hello there!',
            'session_id': session_id
        }
    )
    
    if ask_response.status_code == 200:
        print("✅ Test message sent successfully")
        print(f"   Response: {ask_response.json().get('answer', 'No response')[:100]}...")
    else:
        print(f"❌ Failed to send test message: {ask_response.status_code}")
        return
    
    # Step 2: Get conversation history to confirm it exists
    print("\n2️⃣ Checking conversation history...")
    history_response = requests.get(f"{base_url}/conversation/history", 
        params={'session_id': session_id, 'limit': 10}
    )
    
    if history_response.status_code == 200:
        history_data = history_response.json()
        message_count = history_data.get('message_count', 0)
        print(f"✅ Found {message_count} messages in history")
    else:
        print(f"❌ Failed to get history: {history_response.status_code}")
        return
    
    # Step 3: Clear the conversation history
    print("\n3️⃣ Clearing conversation history...")
    clear_response = requests.post(f"{base_url}/conversation/clear",
        headers={'Content-Type': 'application/json'},
        json={'session_id': session_id}
    )
    
    if clear_response.status_code == 200:
        clear_data = clear_response.json()
        print(f"✅ Clear response: {clear_data}")
        
        if clear_data.get('success'):
            print("✅ Chat history cleared successfully!")
        else:
            print(f"⚠️  Clear operation completed but success = {clear_data.get('success')}")
    else:
        print(f"❌ Failed to clear history: {clear_response.status_code}")
        print(f"   Response: {clear_response.text}")
        return
    
    # Step 4: Verify history is cleared
    print("\n4️⃣ Verifying history is cleared...")
    verify_response = requests.get(f"{base_url}/conversation/history", 
        params={'session_id': session_id, 'limit': 10}
    )
    
    if verify_response.status_code == 200:
        verify_data = verify_response.json()
        remaining_count = verify_data.get('message_count', 0)
        print(f"✅ Remaining messages: {remaining_count}")
        
        if remaining_count == 0:
            print("🎉 SUCCESS: Chat history completely cleared!")
        else:
            print(f"⚠️  WARNING: {remaining_count} messages still remain")
    else:
        print(f"❌ Failed to verify cleared history: {verify_response.status_code}")
    
    print("\n" + "=" * 50)
    print("✅ Clear Chat Test Complete!")

if __name__ == "__main__":
    try:
        test_clear_chat()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the Flask app is running on port 8080.")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
