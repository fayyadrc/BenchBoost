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
        return """You are a knowledgeable Fantasy Premier League (FPL) expert who gives friendly, conversational advice to help managers improve their teams.

**Important Guidelines:**
- Always use the current FPL data provided in the context - this is live, accurate data from the official API
- Don't use outdated information from your training data for player stats, teams, or prices
- If a player isn't in the provided data, they're not available in FPL this season
- Give natural, conversational responses - avoid overly formal language or "CRITICAL" warnings
- Sound like a helpful FPL friend, not a formal AI assistant

**Your Expertise:**
• Player analysis - form, value, fixtures, and potential
• Transfer advice - who to bring in, who to sell, timing considerations
• Captaincy suggestions - weekly picks based on fixtures and form
• Team strategy - long-term planning and budget management
• Fixture planning - upcoming games and difficulty ratings

**Response Style:**
• Be conversational and friendly - like chatting with an FPL mate
• Keep it concise but informative
• Use emojis naturally (don't overdo it)
• Include relevant stats and prices when helpful
• Give clear recommendations with reasoning
• Suggest alternatives when appropriate
• Be honest about uncertainty - "I'd lean towards..." rather than absolute statements

Remember: You're helping fellow FPL managers make better decisions using the latest data. Keep responses natural and helpful!"""
    
    def generate_response(self, user_input: str, context_data: str, quick_mode: bool = True) -> Optional[str]:
        """Generate AI response using the provided context"""
        if not self.is_available():
            return "❌ **AI Error:** AI service is not available. Please check configuration."
        
        mode_instruction = ""
        if quick_mode:
            mode_instruction = "\nKeep your response conversational and under 75 words. Be concise but friendly."
        else:
            mode_instruction = "\nYou can provide a more detailed analysis (up to 200 words) while keeping it conversational."
        
        # Check if this is a fixture query for special handling
        is_fixture_query = ("TEAM FIXTURE DATA" in context_data and 
                           any(word in user_input.lower() for word in ['fixture', 'playing', 'vs', 'against', 'opponent']))
        
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

{context_section}{fixture_instruction}

**Guidelines:**
1. Base your answer on the FPL data above
2. If a player isn't listed, they're not available in FPL this season
3. Use only the teams, players, points, and prices shown in the data
4. Give a natural, conversational response
5. The data above is from the official FPL API and is completely current
6. For fixture queries: READ THE OPPONENT NAME EXACTLY as shown in the data - do not substitute different teams
7. Reformat the data above into your response - do not make up any information"""
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
                     quick_mode: bool = True) -> dict:
        """
        Analyze user query and generate response using Supabase-enhanced search
        """
        start_time = time.time()
        
        try:
            # Import here to avoid circular imports
            from .query_analyzer import analyze_user_query
            from .rag_helper import FPLRAGHelper
            
            # Initialize RAG helper
            rag_helper = FPLRAGHelper()
            
            # Analyze query type and extract key information
            try:
                query_analysis = analyze_user_query(user_input)
                # Ensure query_analysis is a dictionary
                if isinstance(query_analysis, str):
                    query_analysis = {"type": "general", "confidence": 0.5}
            except Exception as e:
                print(f"Query analysis error: {e}")
                query_analysis = {"type": "general", "confidence": 0.5}
            
            # Get enhanced context using Supabase
            context_data = self._get_enhanced_context(
                user_input, bootstrap_data, query_analysis
            )
            
            # Generate AI response
            ai_response = self.generate_response(
                user_input, context_data, quick_mode
            )
            
            # Calculate response metrics
            response_time = time.time() - start_time
            
            return {
                "final_response": ai_response,
                "query_classification": query_analysis.get("type", "general"),
                "confidence": query_analysis.get("confidence", 0.5),
                "context_sources": query_analysis.get("sources", []),
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
        
        try:
            # Handle case where query_analysis might be a string (fallback from RAG)
            if isinstance(query_analysis, str):
                # If query_analysis is a string, it's likely an error response
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


# Import time at the top
import time


# Global service instance
ai_service = AIService()
