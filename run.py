#!/usr/bin/env python3
"""
FPL Chatbot Application Entry Point
"""

import os
from app import create_app

# Create the application
app = create_app()

if __name__ == "__main__":
    # Get port from environment variable or default to 8080
    port = int(os.environ.get('PORT', 8080))
    
    # Determine if we're in debug mode
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )
