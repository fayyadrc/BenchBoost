"""
FPL Chatbot Flask Application Package
"""

from flask import Flask
from dotenv import load_dotenv
import os
import secrets

def create_app():
    """Application factory pattern"""
    # Load environment variables
    load_dotenv()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Production security configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
    app.config['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')
    
    # Security headers and production settings
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') != 'development'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes
    
    # Disable debug and testing in production
    if os.getenv('FLASK_ENV') != 'development':
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        app.config['ENV'] = 'production'
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    # Add security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        if os.getenv('FLASK_ENV') != 'development':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    return app
