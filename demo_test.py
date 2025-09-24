#!/usr/bin/env python3
"""
Quick demo of FPL Chatbot testing framework
"""

import sys
import os
sys.path.append('/Users/fayyadrc/Documents/Programming/FPLChatbot')

from fpl_chatbot_tester import FPLChatbotTester

def demo_test():
    """Run a quick demo test"""
    print("🎯 FPL Chatbot Testing Demo")
    print("=" * 40)

    tester = FPLChatbotTester()

    # Check server status
    if not tester.is_server_running():
        print("❌ Server not running. Please start with: python3 app.py")
        return

    print("✅ Server is running")

    # Run a few sample tests
    demo_queries = [
        {"query": "What can you do?", "category": "conversational"},
        {"query": "How much does Harry Kane cost?", "category": "player"},
        {"query": "What are Arsenal's fixtures?", "category": "team"}
    ]

    print("\n🧪 Running demo tests...")
    print("-" * 40)

    for test_case in demo_queries:
        result = tester.run_single_test(test_case)
        print(f"Verdict: {result['overall_verdict']} | Score: {result['score']}")
        print("-" * 40)

    print("✅ Demo complete!")
    print("💡 Run 'python3 run_tests.py' for full test suite")

if __name__ == "__main__":
    demo_test()
