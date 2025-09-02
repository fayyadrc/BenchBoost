"""
Services Package
"""

from .team_fixtures import team_fixture_service
from .player_search import player_search_service
from .ai_service import ai_service

# Try to import RAG components
try:
    from .rag_helper import rag_helper
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    rag_helper = None

__all__ = ['team_fixture_service', 'player_search_service', 'ai_service', 'rag_helper', 'RAG_AVAILABLE']
