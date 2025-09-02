"""
Intelligent Query Router
Decides whether to use Functions (accurate) or RAG (semantic) based on query type
"""

import re
from typing import Tuple, Optional
from app.services.player_search import player_search_service


class QueryRouter:
    """
    Smart router that decides between Functions vs RAG based on query type
    Priority: Functions > RAG (accuracy over flexibility)
    """
    
    def __init__(self):
        # High-accuracy function patterns (use functions)
        self.function_patterns = {
            'specific_player': [
                r'\b(tell me about|about|stats for|how is|performance of)\s+([A-Z][a-z]+\s*[A-Z]*[a-z]*)\b',
                r'\b([A-Z][a-z]+\s*[A-Z]*[a-z]*)\s+(stats|points|price|form|goals|assists)\b',
                r'\b(is\s+)?([A-Z][a-z]+\s*[A-Z]*[a-z]*)\s+(good|worth|playing|injured)\b',
            ],
            'fixtures': [
                r'\b(when|who|which)\s+(is|are|does)\s+.*?(playing|facing|vs|against)',
                r'\b.*?(fixture|match|game|opponent).*?(gw|gameweek|\d+)',
                r'\b(liverpool|arsenal|chelsea|city|united|spurs|brighton|palace|wolves|villa|newcastle|west ham|everton|fulham|brentford|bournemouth|luton|burnley|sheffield|forest).*?(fixture|playing)',
            ],
            'team_analysis': [
                r'\b(my team|my squad|my players|analyze my team|team analysis)',
                r'\b(who should i|should i transfer|my captain|my formation)',
                r'\b(transfer (in|out)|who to (buy|sell))',
            ],
            'player_comparison': [
                r'\b(compare|vs|versus|or|better than)\b.*\b[A-Z][a-z]+',
                r'\b([A-Z][a-z]+)\s+(or|vs)\s+([A-Z][a-z]+)',
                r'\b(who should i pick|better option|which player)',
            ],
            'specific_data': [
                r'\b(price|cost|points|goals|assists|minutes|ownership|transfers)\s+(of|for)\b',
                r'\b(how much|what price|what cost)\b',
                r'\b(current price|total points|this season)\b',
            ]
        }
        
        # Semantic/strategy patterns (use RAG)
        self.rag_patterns = {
            'rules': [
                r'\b(how many points|points for|scoring system|rules)',
                r'\b(transfer rules|free transfers|wildcard|captain)',
                r'\b(clean sheet points|assist points|goal points)',
                r'\b(how does.*work|what are the rules)',
            ],
            'strategy': [
                r'\b(differential|template|essential|must have)',
                r'\b(strategy|tactics|advice|recommend|suggest)',
                r'\b(good form|in form|hot streak|value picks)',
                r'\b(budget|cheap|expensive|premium)',
                r'\b(when to wildcard|chip strategy|captain choice)',
            ],
            'general_advice': [
                r'\b(best|top|worst|avoid|good|bad)\s+(?!.*\b[A-Z][a-z]+\b)',
                r'\b(what to do|help me|advice|guidance)',
                r'\b(this week|next week|upcoming)',
            ]
        }
    
    def route_query(self, user_input: str) -> Tuple[str, float]:
        """
        Route query to appropriate system
        NEW APPROACH: RAG-Primary with Function Support + Special handling for fixtures
        
        Returns:
            Tuple[system_type, confidence]
            system_type: 'rag_primary', 'functions_only', 'fixtures', or 'hybrid'
            confidence: 0.0-1.0
        """
        query_lower = user_input.lower().strip()
        
        # PRIORITY 1: Team fixture queries (always use functions for accuracy)
        fixture_patterns = [
            r"fixture", r"fixtures", r"match", r"matches", r"game", r"games",
            r"next.*fixture", r"upcoming.*fixture", r"next.*match", r"upcoming.*match",
            r"\w+s?\s+next\s+\d+\s+fixtures", r"\w+s?\s+fixtures", r"\w+s?\s+next\s+fixtures",
            r"who.*facing", r"facing.*gw", r"who.*play", r"who.*against", r"opponents"
        ]
        
        if any(re.search(pattern, query_lower) for pattern in fixture_patterns):
            return 'fixtures', 0.95
        
        # PRIORITY 2: Only use functions for very specific data-only queries
        pure_data_patterns = [
            r'^\w+$',  # Single word (just player name)
            r'^price of \w+$',  # "price of salah"
            r'^stats for \w+$',  # "stats for kane"
        ]
        
        is_pure_data = any(re.match(pattern, query_lower) for pattern in pure_data_patterns)
        
        if is_pure_data:
            return 'functions_only', 0.9
        
        # PRIORITY 3: Everything else goes through RAG for intelligent processing
        # RAG will internally use functions when it needs specific data
        return 'rag_primary', 0.95
    
    def _is_likely_player_name(self, query: str) -> bool:
        """Check if query is likely just a player name"""
        query_clean = query.strip()
        words = query_clean.split()
        
        # Single word, likely a surname
        if len(words) == 1 and len(query_clean) > 2:
            return True
        
        # Two words, likely first name + surname
        if len(words) == 2 and all(word.isalpha() for word in words):
            return True
        
        # Check if it matches a player in the database
        try:
            result = player_search_service.search_players(query_clean)
            return result[0] is not None
        except:
            return False
    
    def _calculate_pattern_score(self, query: str, patterns: dict) -> float:
        """Calculate how well query matches patterns"""
        total_score = 0.0
        max_possible = 0.0
        
        for category, pattern_list in patterns.items():
            category_score = 0.0
            for pattern in pattern_list:
                if re.search(pattern, query, re.IGNORECASE):
                    category_score = max(category_score, 1.0)
            
            # Weight certain categories higher
            if category in ['specific_player', 'fixtures', 'specific_data']:
                category_score *= 1.5  # Higher weight for high-accuracy needs
            elif category in ['rules', 'strategy']:
                category_score *= 1.2  # Medium weight for RAG strengths
                
            total_score += category_score
            max_possible += 1.5 if category in ['specific_player', 'fixtures', 'specific_data'] else 1.2
        
        return min(total_score / max_possible if max_possible > 0 else 0.0, 1.0)
    
    def explain_routing_decision(self, user_input: str) -> str:
        """Explain why a particular routing decision was made"""
        system_type, confidence = self.route_query(user_input)
        
        explanation = f"Query: '{user_input}'\n"
        explanation += f"Routed to: {system_type.upper()}\n"
        explanation += f"Confidence: {confidence:.1%}\n\n"
        
        if system_type == 'functions':
            explanation += "✅ Functions chosen for:\n"
            explanation += "- High accuracy requirement\n"
            explanation += "- Specific data retrieval\n"
            explanation += "- Real-time information\n"
        else:
            explanation += "🧠 RAG chosen for:\n"
            explanation += "- Semantic understanding\n"
            explanation += "- Strategy/rules knowledge\n"
            explanation += "- Complex reasoning\n"
        
        return explanation


# Global router instance
query_router = QueryRouter()
