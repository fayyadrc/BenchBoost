"""
Main Blueprint for FPL Chatbot Routes
"""

from flask import Blueprint, render_template, request, jsonify
from app.services import team_fixture_service, player_search_service, ai_service

bp = Blueprint('main', __name__)


@bp.route("/")
def landing():
    """Landing page route"""
    return render_template("landing.html")


@bp.route("/home")
def home():
    """Home page route"""
    return render_template("home.html")


@bp.route("/chat")
def chat():
    """Chat interface route"""
    return render_template("chat.html")


@bp.route("/ask", methods=["POST"])
def ask():
    """Main chat endpoint for processing user questions"""
    try:
        user_input = request.json.get("question", "") or request.json.get("message", "")
        quick_mode = request.json.get("quick_mode", True)
        manager_id = request.json.get("manager_id", None)
        manager_name = request.json.get("manager_name", None)

        if not user_input.strip():
            return jsonify({"answer": "Please ask me something about Fantasy Premier League!"})

        # Convert manager_id to int if provided
        if manager_id and str(manager_id).strip():
            try:
                manager_id = int(str(manager_id).strip())
            except (ValueError, TypeError):
                manager_id = None
        else:
            manager_id = None
        
        # Analyze user query and get context data
        try:
            from app.services.query_analyzer import analyze_user_query
            context_data = analyze_user_query(user_input, manager_id)
        except Exception as e:
            print(f"Error analyzing user query: {str(e)}")
            return jsonify({"answer": "❌ **Error:** Unable to fetch current FPL data. The Fantasy Premier League API might be temporarily unavailable. Please try again in a few moments."})
        
        # Check for specific error conditions
        if "MANAGER_ID_REQUIRED" in context_data:
            return jsonify({"answer": "To analyze your team, please set your Manager ID in the settings panel (⚙️ Settings). You can find your Manager ID in the FPL website URL when viewing your team."})
        
        # Check if it's a disambiguation request (multiple players found)
        if context_data and "I found multiple players matching" in context_data:
            return jsonify({"answer": context_data})
        
        # Check if it's a player not found error
        if context_data and "Player(s) Not Found:" in context_data:
            return jsonify({"answer": context_data})

        # Generate AI response
        try:
            answer = ai_service.generate_response(user_input, context_data, quick_mode)
            if not answer:
                return jsonify({"answer": "❌ **AI Error:** Unable to generate response. Please try again."})
            
        except Exception as e:
            print(f"Error generating AI response: {str(e)}")
            return jsonify({"answer": "❌ **AI Error:** Unable to generate response. The AI service might be temporarily unavailable. Please try again in a few moments."})

        return jsonify({"answer": answer})

    except Exception as e:
        print(f"Unexpected error in /ask route: {str(e)}")  # For debugging
        return jsonify({"answer": f"❌ **System Error:** An unexpected error occurred. Please try refreshing the page or asking your question differently. Error: {str(e)[:100]}"})
