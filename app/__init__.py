"""
FPL Chatbot Flask Application Package
"""

from flask import Flask
from dotenv import load_dotenv
import os

def create_app():
    """Application factory pattern"""
    # Load environment variables
    load_dotenv()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    return app
