"""
Configuration settings for the FPL Chatbot application
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration class"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # FPL API Configuration
    FPL_BASE_URL = "https://fantasy.premierleague.com/api"
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://vdykinlwvrvbrubvagwb.supabase.co')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
    
    # Application settings
    DEBUG = False
    TESTING = False


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Security settings
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    
    # Performance settings
    WEB_CONCURRENCY = int(os.getenv('WEB_CONCURRENCY', 4))
    CACHE_TTL = int(os.getenv('CACHE_TTL', 1800))  # 30 minutes
    MAX_CONVERSATION_HISTORY = int(os.getenv('MAX_CONVERSATION_HISTORY', 10))
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', 100))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
