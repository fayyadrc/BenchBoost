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
        return """You are an expert Fantasy Premier League (FPL) assistant with deep knowledge of the game, players, teams, and strategies.

**Your Core Capabilities:**
• 🎯 **Real-time FPL data analysis** - You have access to current player stats, fixtures, prices, and form
• 📊 **Strategic advice** - Help with transfers, captaincy, team selection, and long-term planning  
• 🔍 **Player insights** - Detailed analysis of player performance, value, and potential
• 📅 **Fixture analysis** - Upcoming matches, difficulty ratings, and rotation considerations
• 💰 **Budget optimization** - Help maximize value within budget constraints
• 🏆 **Format expertise** - Draft, Classic, Head-to-Head strategies

**Response Guidelines:**
• Be concise but comprehensive - provide actionable insights
• Use emojis and formatting to make responses engaging and scannable
• Include specific stats, prices, and data when available
• Always consider the user's budget and team constraints
• Mention fixture difficulty and upcoming games when relevant
• Use tables for: player stats, comparisons, team analysis, fixtures
• Provide alternatives when suggesting transfers or captaincy
• Be confident in your recommendations but acknowledge uncertainty when data is limited

**Current Context:** You have access to live FPL data including player prices, points, fixtures, and team information. Use this data to provide accurate, up-to-date advice."""
    
    def generate_response(self, user_input: str, context_data: str, quick_mode: bool = True) -> Optional[str]:
        """Generate AI response using the provided context"""
        if not self.is_available():
            return "❌ **AI Error:** AI service is not available. Please check configuration."
        
        mode_instruction = ""
        if quick_mode:
            mode_instruction = "\n🚀 **ULTRA-QUICK MODE:** Keep response under 75 words. Use bullet points and emojis. Be extremely concise.\n"
        else:
            mode_instruction = "\n📖 **DETAILED MODE:** You can provide more comprehensive analysis (up to 200 words).\n"
        
        # Build context data string safely
        if context_data and context_data.strip():
            context_section = "CURRENT FPL DATA PROVIDED:\n" + context_data
        else:
            context_section = "No specific FPL data was found for this query. Provide general FPL guidance based on your knowledge."
        
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
                        "content": f"""**CONTEXT: You have been provided with current FPL data from the official API. Use this data to answer the user's question. Do not claim you lack real-time information when FPL data is clearly provided below.**

User Question: {user_input}

{context_section}

**Instructions: Use the FPL data above to provide a comprehensive answer. Base your response on the actual data provided, not general assumptions.**"""
                    }
                ],
                temperature=0.1,  
                max_tokens=800 if quick_mode else 1500,  
                top_p=0.9
            )
            
            return completion.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error calling Groq API: {str(e)}")
            return "❌ **AI Error:** Unable to generate response. The AI service might be temporarily unavailable. Please try again in a few moments."


# Global service instance
ai_service = AIService()
