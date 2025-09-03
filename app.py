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
        
        # Check if Gunicorn is available for production
        gunicorn_available = True
        try:
            import gunicorn
        except ImportError:
            gunicorn_available = False
        
        if gunicorn_available and os.environ.get('USE_GUNICORN', 'true').lower() == 'true':
            print("� Starting PRODUCTION server with Gunicorn")
            print(f"🌐 Application will be available on port {port}")
            # Use Gunicorn for production
            import subprocess
            import sys
            subprocess.run([
                sys.executable, '-m', 'gunicorn',
                '--config', 'gunicorn.conf.py',
                '--bind', f'0.0.0.0:{port}',
                'app:app'
            ])
        else:
            print("💡 Using Flask server (install gunicorn for better production performance)")
            # For platforms that call this directly, use development server with production settings
            app.run(
                host='0.0.0.0',
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
