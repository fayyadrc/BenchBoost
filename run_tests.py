#!/usr/bin/env python3
"""
Simple test runner for FPL Chatbot
"""

import subprocess
import sys
import time
import os

def check_server():
    """Check if the Flask server is running"""
    try:
        import requests
        response = requests.get("http://127.0.0.1:8080/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_server():
    """Start the Flask development server"""
    print("🚀 Starting FPL Chatbot server...")
    print("💡 Server will run in the background")
    print("🔗 URL: http://127.0.0.1:8080")
    print("⏹️  Press Ctrl+C to stop the server after testing\n")

    # Start server in background
    process = subprocess.Popen([
        sys.executable, "app.py"
    ], cwd="/Users/fayyadrc/Documents/Programming/FPLChatbot")

    # Wait for server to start
    print("⏳ Waiting for server to start...")
    for i in range(30):  # Wait up to 30 seconds
        if check_server():
            print("✅ Server is ready!")
            return process
        time.sleep(1)

    print("❌ Server failed to start within 30 seconds")
    process.terminate()
    return None

def run_tests():
    """Run the comprehensive test suite"""
    print("🧪 Running FPL Chatbot Test Suite...")
    print("=" * 50)

    result = subprocess.run([
        sys.executable, "fpl_chatbot_tester.py"
    ], cwd="/Users/fayyadrc/Documents/Programming/FPLChatbot")

    return result.returncode == 0

def main():
    """Main function"""
    print("🤖 FPL Chatbot Testing Runner")
    print("=" * 50)

    # Check if server is already running
    if check_server():
        print("✅ Server is already running")
        server_process = None
    else:
        server_process = start_server()
        if not server_process:
            print("❌ Cannot proceed without server")
            return False

    try:
        # Run the tests
        success = run_tests()

        if success:
            print("\n✅ All tests completed successfully!")
        else:
            print("\n❌ Some tests failed")

        return success

    finally:
        # Clean up server if we started it
        if server_process:
            print("\n🛑 Stopping server...")
            server_process.terminate()
            server_process.wait()
            print("✅ Server stopped")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
