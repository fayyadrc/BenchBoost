#!/usr/bin/env python3
"""
Debug test to see what's happening with context resolution
"""

import sys
sys.path.append('/Users/fayyadrc/Documents/Programming/FPLChatbot')

def debug_context_resolution():
    """Debug the context resolution process step by step"""
    print("🔍 DEBUGGING CONTEXT RESOLUTION")
    print("=" * 50)

    # Import the AI service
    from app.services.ai_service import ai_service

    # Mock conversation context as it would be returned by _get_conversation_context
    mock_context = "Recently discussed player: Haaland"

    # Test the pronoun resolution directly
    test_query = "how much does he cost"
    print(f"\n1️⃣ Testing pronoun resolution:")
    print(f"   Original query: '{test_query}'")
    print(f"   Context: '{mock_context}'")

    resolved = ai_service._resolve_pronouns(test_query, mock_context)
    print(f"   Resolved query: '{resolved}'")

    # Test if the query needs context
    needs_context = ai_service._needs_context(test_query)
    print(f"   Needs context: {needs_context}")

    print("\n2️⃣ Testing context extraction patterns:")
    print("-" * 40)

    # Test the patterns that should extract "Haaland" from the conversation
    import re

    # Test user query patterns
    user_query_patterns = [
        r'(?:which\s+team\s+does\s+|what\s+team\s+does\s+)([A-Za-z]+)(?:\s+play\s+for)',
        r'(?:tell\s+me\s+about\s+|about\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'(?:how\s+much\s+(?:does\s+|is\s+))([A-Z][a-z]+)(?:\s+cost|\s+worth)',
        r'(?:is\s+)([A-Z][a-z]+)(?:\s+(?:worth|good|available))',
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:price|cost|team|position)',
    ]

    test_user_msg = "which team does haaland play for"
    print(f"   Testing user message: '{test_user_msg}'")

    for i, pattern in enumerate(user_query_patterns, 1):
        matches = re.findall(pattern, test_user_msg, re.IGNORECASE)
        if matches:
            print(f"   Pattern {i} found: {matches}")

    # Test AI response patterns
    ai_response_patterns = [
        r'\*\*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\*\*',  # **Player Name**
        r'([A-Z][a-z]+)(?:\s+is\s+not\s+listed|\s+plays\s+for\s+[A-Z])',  # Haaland is not listed/plays for Team
        r'knowledge,\s+([A-Z][a-z]+)(?:\s+plays)',  # knowledge, Haaland plays
    ]

    test_ai_msg = "Haaland's Team: Haaland is not listed in the provided data. However, based on external knowledge, Haaland plays for Manchester City."
    print(f"\n   Testing AI message: '{test_ai_msg[:80]}...'")

    for i, pattern in enumerate(ai_response_patterns, 1):
        matches = re.findall(pattern, test_ai_msg, re.IGNORECASE)
        if matches:
            print(f"   Pattern {i} found: {matches}")

    print("\n3️⃣ CONCLUSION:")
    print("-" * 15)
    if resolved != test_query:
        print("✅ Pronoun resolution is working correctly")
    else:
        print("❌ Pronoun resolution is NOT working")

if __name__ == "__main__":
    debug_context_resolution()
