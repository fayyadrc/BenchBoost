"""
AI Service for handling Groq API interactions
"""

import os
from groq import Groq
from typing import Optional


class AIService:
    """Service for handling AI chat completions"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Groq client"""
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            self.client = Groq(api_key=api_key)
            print("✅ Using Groq (Llama 3.1)")
        else:
            print("⚠️  Please set GROQ_API_KEY in your .env file")
            print("🔗 Get your free API key at: https://console.groq.com/keys")
    
    def is_available(self) -> bool:
        """Check if AI service is available"""
        return self.client is not None
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the AI"""
        return """You are a professional Fantasy Premier League (FPL) data analyst who provides precise, data-driven insights to help managers improve their teams.

**Important Guidelines:**
- Always use the current FPL data provided in the context - this is live, accurate data from the official API
- Don't use outdated information from your training data for player stats, teams, or prices
- If a player isn't in the provided data, they're not available in FPL this season
- Provide direct, informative responses without informal greetings or casual language
- Present data in clear tables and structured formats when relevant

**Your Expertise:**
• Player analysis - form, value, fixtures, and potential
• Transfer advice - who to bring in, who to sell, timing considerations
• Captaincy suggestions - weekly picks based on fixtures and form
• Team strategy - long-term planning and budget management
• Fixture planning - upcoming games and difficulty ratings

**Response Style:**
• Be direct and professional - start with the key information
• Use tables, lists, and structured data presentation
• Include relevant stats and prices in organized formats
• Give clear recommendations with data-backed reasoning
• No informal greetings like "hey mate" or casual phrases
• Focus on presenting the requested information efficiently

Remember: You're providing professional FPL analysis using the latest data. Present information clearly and directly!"""
    
    def generate_response(self, user_input: str, context_data: str, quick_mode: bool = True) -> Optional[str]:
        """Generate AI response using the provided context"""
        if not self.is_available():
            return "❌ **AI Error:** AI service is not available. Please check configuration."
        
        mode_instruction = ""
        if quick_mode:
            mode_instruction = "\nProvide a direct, professional response. Start with key information, no greetings. Use tables/lists when showing multiple data points."
        else:
            mode_instruction = "\nProvide detailed analysis with structured data presentation. Use tables for player stats, fixtures, or comparisons. No informal language."
        
        # Check if this is a fixture query for special handling
        is_fixture_query = ("TEAM FIXTURE DATA" in context_data and 
                           any(word in user_input.lower() for word in ['fixture', 'playing', 'vs', 'against', 'opponent']))
        
        # Check if this is a price query for focused response
        is_price_query = "PRICE_QUERY:" in context_data
        
        # Build context data string safely
        if context_data and context_data.strip():
            context_section = "CURRENT FPL DATA PROVIDED:\n" + context_data
        else:
            context_section = "No specific FPL data was found for this query. Provide general FPL guidance based on your knowledge."
        
        # Special instructions for fixture queries
        fixture_instruction = ""
        if is_fixture_query:
            fixture_instruction = """

**FIXTURE QUERY SPECIAL INSTRUCTIONS:**
- This is a fixture/opponent query
- The data shows EXACT team matchups - read them VERY carefully
- When you see "Team A vs Team B", Team B is the opponent of Team A
- When you see "(H)" it means Home, "(A)" means Away
- Do NOT confuse team names - read the fixture data word-by-word
- DOUBLE-CHECK the opponent name before responding"""
        
        # Special instructions for price queries
        price_instruction = ""
        if is_price_query:
            price_instruction = """

**PRICE QUERY SPECIAL INSTRUCTIONS:**
- This is a simple price query - provide ONLY the player's price
- Format: "Player's Price: Player costs £Xm."
- Do NOT include any additional player statistics, form, points, or other data
- Keep the response extremely concise and focused"""

        try:
            completion = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",  
                messages=[
                    {
                        "role": "system", 
                        "content": f"{self.get_system_prompt()}{mode_instruction}"
                    },
                    {
                        "role": "user", 
                        "content": f"""**IMPORTANT: Use only the live FPL data provided below. This is current, accurate data from the official API.**

User Question: {user_input}

{context_section}{fixture_instruction}{price_instruction}

**Guidelines:**
1. Base your answer on the FPL data above
2. If a player isn't listed, they're not available in FPL this season
3. Use only the teams, players, points, and prices shown in the data
4. Start directly with the answer - NO greetings like "hey mate" or informal language
5. The data above is from the official FPL API and is completely current
6. For fixture queries: READ THE OPPONENT NAME EXACTLY as shown in the data - do not substitute different teams
7. Present data in tables/lists when showing multiple players, stats, or comparisons
8. Reformat the data above into your response - do not make up any information"""
                    }
                ],
                temperature=0.0,  # Changed to 0.0 for more deterministic responses
                max_tokens=800 if quick_mode else 1500,  
                top_p=0.1  # Reduced for more focused responses
            )
            
            return completion.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error calling Groq API: {str(e)}")
            return "❌ **AI Error:** Unable to generate response. The AI service might be temporarily unavailable. Please try again in a few moments."

    def analyze_query(self, user_input: str, bootstrap_data: dict, 
                     manager_id: int = None, manager_name: str = None, 
                     quick_mode: bool = True, session_id: str = None) -> dict:
        """
        Analyze user query and generate response using Supabase-enhanced search
        """
        start_time = time.time()
        
        # Get conversation context if session_id provided and resolve pronouns
        resolved_input = user_input
        if session_id and self._needs_context(user_input):
            conversation_context = self._get_conversation_context(session_id, user_input)
            if conversation_context:
                # Try to resolve pronouns in the input
                resolved_input = self._resolve_pronouns(user_input, conversation_context)
                print(f"🔄 Resolved pronouns: '{user_input}' → '{resolved_input}'")
        
        try:
            # Import here to avoid circular imports
            from .query_analyzer import analyze_user_query
            from .rag_helper import FPLRAGHelper
            
            # Initialize RAG helper
            rag_helper = FPLRAGHelper()
            
            # Analyze query type and extract key information
            try:
                # Use the resolved input (with pronouns replaced) for analysis
                query_analysis = analyze_user_query(resolved_input, manager_id)
                print(f"🔍 Query analyzer result type: {type(query_analysis)}")
                if isinstance(query_analysis, str):
                    print(f"🔍 Query analyzer returned string: '{query_analysis[:100]}...'")
                else:
                    print(f"🔍 Query analyzer returned dict: {query_analysis}")
            except Exception as e:
                print(f"Query analysis error: {e}")
                query_analysis = {"type": "general", "confidence": 0.5}

            # Extra guard: use the simple router to detect fixture queries and prefer the
            # fixture service result directly (ensures function output is used end-to-end).
            try:
                from .query_analyzer import _simple_query_router
                system_type, _conf = _simple_query_router(resolved_input)
                if system_type and str(system_type).upper() == 'FIXTURES':
                    from .team_fixtures import team_fixture_service as fixture_service
                    fixture_result = fixture_service.process_team_fixture_query(resolved_input)
                    if fixture_result:
                        # Return early with fixture result as authoritative
                        return {
                            "final_response": fixture_result,
                            "query_classification": "fixtures",
                            "confidence": 0.98,
                            "context_sources": [],
                            "response_time": time.time() - start_time
                        }
            except Exception as e:
                print(f"Fixture guard error: {e}")
                # Non-fatal - continue to normal flow
                pass
            
            # If the analyzer returned a direct string result (e.g. fixture data produced by functions),
            # prefer that string as the final response instead of sending it through the LLM again.
            if isinstance(query_analysis, str):
                # Treat fixture-like strings as the authoritative response
                if "TEAM FIXTURE DATA" in query_analysis.upper() or "NEXT" in query_analysis.upper() and "FIXTURE" in query_analysis.upper():
                    ai_response = query_analysis
                # Treat conversational responses as authoritative (greetings, etc.)
                elif (any(emoji in query_analysis for emoji in ['👋', '😊', '🙏', '🚀', '👍']) or
                      "I'm your FPL assistant" in query_analysis or
                      "Hello!" in query_analysis or
                      "doing great" in query_analysis or
                      "You're welcome" in query_analysis or
                      "Good luck" in query_analysis):
                    ai_response = query_analysis
                    # Return early with conversational classification
                    return {
                        "final_response": ai_response,
                        "query_classification": "conversational",
                        "confidence": 0.98,
                        "context_sources": [],
                        "response_time": time.time() - start_time
                    }
                else:
                    # Check if this is a focused price response - return it directly
                    if "'s Price:" in query_analysis and "costs £" in query_analysis:
                        ai_response = query_analysis
                        print(f"💰 Detected focused price response, returning directly: '{ai_response}'")
                        # Return early with price classification
                        return {
                            "final_response": ai_response,
                            "query_classification": "price",
                            "confidence": 0.98,
                            "context_sources": [],
                            "response_time": time.time() - start_time
                        }
                    # Check if this is a team analysis response - return it directly
                    elif "**Your Team Analysis" in query_analysis or "Total Points:" in query_analysis:
                        ai_response = query_analysis
                        print(f"� Detected team analysis response, returning directly: '{ai_response[:100]}...'")
                        # Return early with team analysis classification
                        return {
                            "final_response": ai_response,
                            "query_classification": "team_analysis",
                            "confidence": 0.98,
                            "context_sources": [],
                            "response_time": time.time() - start_time
                        }
                    else:
                        print(f"�📝 Query analysis is string but not recognized type: '{query_analysis[:100]}...'")
                        # Treat other strings as context and fall back to enhanced context handling
                        context_data = self._get_enhanced_context(resolved_input, bootstrap_data, query_analysis)
                        ai_response = self.generate_response(resolved_input, context_data, quick_mode)
            else:
                # Get enhanced context using Supabase
                context_data = self._get_enhanced_context(
                    resolved_input, bootstrap_data, query_analysis
                )

                # Generate AI response
                ai_response = self.generate_response(
                    resolved_input, context_data, quick_mode
                )
            
            # Calculate response metrics
            response_time = time.time() - start_time
            
            # Normalize query classification and confidence for results reporting
            if isinstance(query_analysis, dict):
                qc = query_analysis.get("type", "general")
                conf = query_analysis.get("confidence", 0.5)
                sources = query_analysis.get("sources", [])
            else:
                # If analyzer returned a string (e.g. fixture data), prefer a fixtures classification
                qc = "fixtures" if ("FIXTURE" in str(query_analysis).upper() or "TEAM FIXTURE DATA" in str(query_analysis).upper()) else "general"
                conf = 0.95 if qc == "fixtures" else 0.5
                sources = []

            return {
                "final_response": ai_response,
                "query_classification": qc,
                "confidence": conf,
                "context_sources": sources,
                "response_time": response_time
            }
            
        except Exception as e:
            print(f"Error in analyze_query: {e}")
            return {
                "final_response": "I encountered an error processing your question. Please try again.",
                "query_classification": "error",
                "confidence": 0.0,
                "context_sources": [],
                "response_time": time.time() - start_time
            }
    
    def _get_enhanced_context(self, user_input: str, bootstrap_data: dict, 
                            query_analysis: dict) -> str:
        """
        Get enhanced context using Supabase for faster, more accurate searches
        """
        context_parts = []
        
        # Check if this is a simple price query - provide minimal context
        user_lower = user_input.lower()
        is_price_query = any(phrase in user_lower for phrase in [
            'how much does', 'what is his price', 'what is her price', 
            'how much is', 'cost', 'price'
        ]) and any(pronoun in user_lower for pronoun in ['he', 'she', 'they', 'his', 'her', 'their'])
        
        if is_price_query:
            # For price queries, return minimal context to avoid verbose responses
            return "PRICE_QUERY: Provide only the player's price information in a concise format."
        
        try:
            # Handle case where query_analysis might be a string (fixture data or error response)
            if isinstance(query_analysis, str):
                # Check if it's fixture data (contains "TEAM FIXTURE DATA")
                if "TEAM FIXTURE DATA" in query_analysis:
                    # This is valid fixture data, return it directly
                    return query_analysis
                else:
                    # If query_analysis is a string without fixture data, it's likely an error response
                    # Fall back to RAG search
                    from .rag_helper import FPLRAGHelper
                    rag_helper = FPLRAGHelper()
                    return rag_helper.enhanced_rag_search(user_input, bootstrap_data, top_k=5)
            
            # For player queries, use Supabase search
            if query_analysis.get("mentions_players", False):
                player_names = query_analysis.get("player_names", [])
                
                for name in player_names:
                    players = supabase_service.search_players(name, limit=3)
                    if players:
                        for player in players:
                            player_info = (
                                f"**{player['first_name']} {player['second_name']}** "
                                f"({player['web_name']}) - {player['team_name']} {player['position_name']}\n"
                                f"Price: £{player['price']}m | Points: {player['total_points']} | "
                                f"Form: {player['form']} | Goals: {player['goals']} | "
                                f"Assists: {player['assists']}\n"
                            )
                            context_parts.append(player_info)
            
            # For team queries, use Supabase filtering
            elif query_analysis.get("mentions_team", False):
                team_name = query_analysis.get("team_name", "")
                position = query_analysis.get("position_filter")
                
                players = supabase_service.get_players_by_criteria(
                    team=team_name, position=position, limit=10
                )
                
                if players:
                    context_parts.append(f"**{team_name} Players:**\n")
                    for player in players:
                        player_info = (
                            f"• {player['web_name']} - £{player['price']}m "
                            f"({player['total_points']} pts, {player['form']} form)\n"
                        )
                        context_parts.append(player_info)
            
            # For statistical queries, use Supabase leaders
            elif query_analysis.get("asks_for_stats", False):
                stat_type = query_analysis.get("stat_type", "points")
                leaders = supabase_service.get_statistical_leaders(stat_type, limit=5)
                
                if leaders:
                    context_parts.append(f"**Top {stat_type.title()} Leaders:**\n")
                    for i, player in enumerate(leaders, 1):
                        stat_value = player.get(stat_type, player.get('total_points', 0))
                        player_info = (
                            f"{i}. {player['web_name']} ({player['team_name']}) - "
                            f"{stat_value} {stat_type}, £{player['price']}m\n"
                        )
                        context_parts.append(player_info)
            
            # If we have Supabase context, return it
            if context_parts:
                return "\n".join(context_parts)
            
            # Fallback to traditional RAG search for complex queries
            from .rag_helper import FPLRAGHelper
            rag_helper = FPLRAGHelper()
            context_data = rag_helper.enhanced_rag_search(
                user_input, bootstrap_data, top_k=8
            )
            return context_data
            
        except Exception as e:
            print(f"Error getting enhanced context: {e}")
            # Fallback to basic search using RAG
            from .rag_helper import FPLRAGHelper
            rag_helper = FPLRAGHelper()
            return rag_helper.enhanced_rag_search(user_input, bootstrap_data, top_k=5)

    def _get_conversation_context(self, session_id: str, current_query: str) -> str:
        """Get recent conversation context to understand references like 'he', 'this player'"""
        try:
            from .supabase_service import supabase_service
            
            # Get last 3 messages from conversation history
            history = supabase_service.get_conversation_history(session_id, limit=3)
            
            if not history:
                return ""
            
            # Extract key entities from recent conversation
            context_parts = []
            mentioned_players = set()
            mentioned_teams = set()
            
            for msg in reversed(history):  # Most recent first
                user_msg = msg.get('user_message', '')
                ai_msg = msg.get('ai_response', '')
                
                # Extract player names from user questions and AI responses
                import re
                
                # Improved patterns to extract player names
                player_patterns = [
                    r'\*\*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\*\*',  # **Player Name**
                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s+\()',  # Player Name (
                    r'about\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',   # about Player Name
                    r'tell\s+me\s+about\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # tell me about Player Name
                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:is|plays|costs|price)',  # Player Name is/plays/costs
                    r'(?:team\s+does\s+|which\s+team\s+does\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # which team does Player Name
                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s+play\s+for)',  # Player Name play for
                    r'([A-Z][a-z]+)(?:\s+is\s+not\s+listed|\s+plays\s+for)',  # Haaland is not listed/plays for
                    r'knowledge,\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # based on external knowledge, Haaland
                    r'([A-Z][a-z]+)(?:\s+(?:is|was|plays|costs|price))',  # Single name patterns
                ]
                
                # Search in both user message and AI response
                combined_text = f"{user_msg} {ai_msg}"
                
                # PRIORITY 1: Extract player names directly from user queries
                # Look for patterns like "which team does X play for", "tell me about X", etc.
                user_query_patterns = [
                    r'(?:which\s+team\s+does\s+|what\s+team\s+does\s+)([A-Za-z]+)(?:\s+play\s+for)',
                    r'(?:tell\s+me\s+about\s+|about\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
                    r'(?:how\s+much\s+(?:does\s+|is\s+))([A-Z][a-z]+)(?:\s+cost|\s+worth)',
                    r'(?:is\s+)([A-Z][a-z]+)(?:\s+(?:worth|good|available))',
                    r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:price|cost|team|position)',
                ]
                
                for pattern in user_query_patterns:
                    matches = re.findall(pattern, user_msg, re.IGNORECASE)
                    for match in matches:
                        clean_match = match.strip()
                        # Simple validation: should be a reasonable name length and start with capital
                        if 3 <= len(clean_match) <= 20 and clean_match[0].isupper():
                            mentioned_players.add(clean_match)
                            print(f"🔍 Debug: Found player in user query: '{clean_match}'")
                
                # PRIORITY 2: Simple word extraction from user message for famous single names
                user_words = user_msg.split()
                for word in user_words:
                    if (word and len(word) > 4 and word[0].isupper() and 
                        word.lower() not in ['which', 'team', 'does', 'play', 'for', 'much', 'cost', 'about', 'tell']):
                        mentioned_players.add(word)
                        print(f"🔍 Debug: Found single name: '{word}'")
                
                # PRIORITY 3: Look for player names in AI responses (more carefully)
                # Only look for names that are clearly marked or formatted as player names
                ai_response_patterns = [
                    r'\*\*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\*\*',  # **Player Name**
                    r'([A-Z][a-z]+)(?:\s+is\s+not\s+listed|\s+plays\s+for\s+[A-Z])',  # Haaland is not listed/plays for Team
                    r'knowledge,\s+([A-Z][a-z]+)(?:\s+plays)',  # knowledge, Haaland plays
                ]
                
                for pattern in ai_response_patterns:
                    matches = re.findall(pattern, ai_msg, re.IGNORECASE)
                    for match in matches:
                        clean_match = match.strip()
                        if 3 <= len(clean_match) <= 20 and clean_match[0].isupper():
                            mentioned_players.add(clean_match)
                            print(f"🔍 Debug: Found player in AI response: '{clean_match}'")
                
                # Extract team names
                team_patterns = [
                    r'plays\s+for\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+player',
                    r'team:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                ]
                
                for pattern in team_patterns:
                    matches = re.findall(pattern, combined_text, re.IGNORECASE)
                    for match in matches:
                        clean_match = match.strip()
                        if len(clean_match) > 2 and len(clean_match) < 25:
                            mentioned_teams.add(clean_match)
            
            # Build context for current query
            if self._needs_context(current_query):
                print(f"🔍 Debug: Found {len(mentioned_players)} players: {mentioned_players}")
                print(f"🔍 Debug: Found {len(mentioned_teams)} teams: {mentioned_teams}")
                
                if mentioned_players:
                    recent_player = list(mentioned_players)[-1]  # Most recent
                    context_parts.append(f"Recently discussed player: {recent_player}")
                    print(f"🔍 Debug: Using recent player: {recent_player}")
                
                if mentioned_teams:
                    recent_team = list(mentioned_teams)[-1]  # Most recent
                    context_parts.append(f"Recently discussed team: {recent_team}")
            
            return " | ".join(context_parts) if context_parts else ""
            
        except Exception as e:
            print(f"Error getting conversation context: {e}")
            return ""
    
    def _needs_context(self, query: str) -> bool:
        """Check if query contains pronouns or references that need context"""
        query_lower = query.lower()
        context_indicators = [
            'he', 'his', 'him', 'she', 'her', 'they', 'them', 'their',
            'this player', 'that player', 'the player', 'the same player',
            'how much does he', 'what team does he', 'is he', 'does he',
            'how much does she', 'what team does she', 'is she', 'does she',
            'how much do they', 'what team do they', 'are they', 'do they'
        ]
        
        return any(indicator in query_lower for indicator in context_indicators)
    
    def _resolve_pronouns(self, query: str, context: str) -> str:
        """Resolve pronouns in query using conversation context"""
        try:
            # Extract player name from context
            import re
            
            # Look for pattern "Recently discussed player: PlayerName"
            player_match = re.search(r'Recently discussed player:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', context)
            if not player_match:
                return query  # No player found in context
            
            player_name = player_match.group(1)
            resolved_query = query
            
            # Replace pronouns with player name
            pronoun_replacements = {
                r'\bhe\b': player_name,
                r'\bhis\b': f"{player_name}'s",
                r'\bhim\b': player_name,
                r'\bshe\b': player_name,
                r'\bher\b': f"{player_name}'s",
                r'\bthey\b': player_name,
                r'\bthem\b': player_name,
                r'\btheir\b': f"{player_name}'s",
                r'\bthis player\b': player_name,
                r'\bthat player\b': player_name,
                r'\bthe player\b': player_name
            }
            
            for pattern, replacement in pronoun_replacements.items():
                resolved_query = re.sub(pattern, replacement, resolved_query, flags=re.IGNORECASE)
            
            return resolved_query
            
        except Exception as e:
            print(f"Error resolving pronouns: {e}")
            return query  # Return original query if resolution fails


# Import time at the top
import time


# Global service instance
ai_service = AIService()
