#!/usr/bin/env python3
"""
Simple test for AI evaluation function
"""

import requests
import json
import os
from dotenv import load_dotenv
from groq import Groq

def judge_response_with_groq(query, response, expected_category):
    """Test the AI evaluation function directly"""
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
        print(f"Raw AI response: {result_text}")
        
        # Look for JSON content within the response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_content = result_text[json_start:json_end]
            print(f"Extracted JSON: {json_content}")
        else:
            json_content = result_text
            print("No JSON found, using full text")

        # Try to parse as JSON
        try:
            result = json.loads(json_content)
            return result
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            # If not valid JSON, extract what we can
            return {
                "verdict": "PARTIAL",
                "score": 5,
                "reasoning": "Could not parse AI response as JSON",
                "raw_response": result_text
            }

    except Exception as e:
        return {"error": str(e)}

def test_ai_evaluation():
    """Test the AI evaluation function"""
    print("🧪 Testing AI Evaluation Function")
    print("=" * 40)

    # Test case
    query = "How much does Harry Kane cost?"
    response = "Harry Kane costs 12.5 million in Fantasy Premier League."
    expected_category = "player"

    result = judge_response_with_groq(query, response, expected_category)

    print(f"Query: {query}")
    print(f"Response: {response}")
    print(f"Result: {result}")
    print("=" * 40)

if __name__ == "__main__":
    test_ai_evaluation()
