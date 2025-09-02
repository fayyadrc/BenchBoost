#!/usr/bin/env python3
"""
Leapcell deployment entry point for FPL Chatbot
"""
import os
import sys

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Import and run the Flask app
from backend.app import app

if __name__ == "__main__":
    # Get port from environment variable for deployment (Leapcell uses 8080)
    port = int(os.environ.get('PORT', 8080))
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )
