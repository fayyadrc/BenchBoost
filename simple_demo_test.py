#!/usr/bin/env python3
"""
Simple demo test without importing the full tester class
"""

import requests
import json
import os
from dotenv import load_dotenv
from groq import Groq

def judge_response_with_groq(query, response, expected_category):
    """AI evaluation function"""
    # Load environment variables inside the function
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"error": "GROQ_API_KEY not found"}

    try:
        client = Groq(api_key=api_key)

        prompt = f"""
        Evaluate this chatbot response for Fantasy Premier League queries:

        User Query: {query}
        Chatbot Response: {response}
        Expected Category: {expected_category}

        Rate the response on a scale of 1-10 (10 being perfect) and provide a verdict:
        - PASS: Good response that answers the query appropriately
        - PARTIAL: Response has some relevant information but could be better
        - FAIL: Response doesn't adequately answer the query

        Return your evaluation as JSON with these fields:
        - verdict: PASS/PARTIAL/FAIL
        - score: number 1-10
        - reasoning: brief explanation
        """

        response_obj = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )

        result_text = response_obj.choices[0].message.content.strip()
        
        # Look for JSON content within the response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_content = result_text[json_start:json_end]
        else:
            json_content = result_text

        # Try to parse as JSON
        try:
            result = json.loads(json_content)
            return result
        except json.JSONDecodeError:
            return {
                "verdict": "PARTIAL",
                "score": 5,
                "reasoning": "Could not parse AI response as JSON",
                "raw_response": result_text
            }

    except Exception as e:
        return {"error": str(e)}

def ask_chatbot(query):
    """Send query to chatbot"""
    try:
        payload = {
            "question": query,
            "session_id": "demo_test",
            "quick_mode": True
        }

        response = requests.post(
            "http://127.0.0.1:8080/ask",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("answer", "No answer received")
        else:
            return f"Error: {response.status_code}"
            
    except Exception as e:
        return f"Connection error: {e}"

def run_demo_test():
    """Run demo test"""
    print("🎯 FPL Chatbot Testing Demo")
    print("=" * 40)

    # Test server connection
    try:
        health_response = requests.get("http://127.0.0.1:8080/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Server is running")
        else:
            print("❌ Server health check failed")
            return
    except:
        print("❌ Server not running. Please start with: python3 app.py")
        return

    # Demo queries
    demo_queries = [
        {"query": "What can you do?", "category": "conversational"},
        {"query": "How much does Harry Kane cost?", "category": "player"},
        {"query": "What are Arsenal's fixtures?", "category": "team"}
    ]

    print("\n🧪 Running demo tests...")
    print("-" * 40)

    for test_case in demo_queries:
        print(f"\nQuery: {test_case['query']}")
        
        # Get chatbot response
        chatbot_response = ask_chatbot(test_case['query'])
        print(f"Response: {chatbot_response[:100]}...")
        
        # Evaluate with AI
        evaluation = judge_response_with_groq(
            test_case['query'], 
            chatbot_response, 
            test_case['category']
        )
        
        print(f"Verdict: {evaluation.get('verdict', 'UNKNOWN')}")
        print(f"Score: {evaluation.get('score', 'N/A')}")
        print("-" * 40)

    print("✅ Demo complete!")

if __name__ == "__main__":
    run_demo_test()
