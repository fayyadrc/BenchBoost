#!/usr/bin/env python3
"""
Root-level app entry point for deployment compatibility
This file imports the Flask app from the backend directory
"""
import os
import sys

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Import the Flask app from backend
from app import app

if __name__ == "__main__":
    # Get port from environment variable for deployment
    port = int(os.environ.get('PORT', 5002))
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )
