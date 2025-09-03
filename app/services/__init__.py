"""
Services Package - Clean Production Version
"""

from .team_fixtures import team_fixture_service
from .player_search import player_search_service
from .ai_service import ai_service

# RAG system (always available with Supabase)
from .rag_helper import rag_helper

# Supabase Backend-as-a-Service
from .supabase_service import supabase_service

# Query processing
from .query_analyzer import analyze_user_query

# Knowledge base (used by RAG)
from . import fpl_knowledge

__all__ = [
    'team_fixture_service', 
    'player_search_service', 
    'ai_service', 
    'rag_helper',
    'supabase_service',
    'analyze_user_query',
    'fpl_knowledge'
]
