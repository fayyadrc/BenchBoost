#!/usr/bin/env python3
"""
Production entry point for deployment platforms.
This file maintains the standard app.py entry point that most platforms expect.
"""

import os
from app import create_app

# Create the Flask application using the factory pattern
app = create_app()

# Production configuration
app.config['ENV'] = 'production'
app.config['DEBUG'] = False
app.config['TESTING'] = False

if __name__ == "__main__":
    # Get port from environment variable or default to 8080
    port = int(os.environ.get('PORT', 8080))
    
    # Check if we're explicitly in development mode
    is_development = os.environ.get('FLASK_ENV') == 'development'
    
    if is_development:
        print("🔧 Running in DEVELOPMENT mode")
        app.run(
            host='0.0.0.0',
            port=port,
            debug=True
        )
    else:
        print("🚀 Running in PRODUCTION mode")
        print("💡 For local production testing, use: gunicorn -w 4 -b 0.0.0.0:8080 app:app")
        
        # For platforms that call this directly, use development server with production settings
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
