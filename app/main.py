"""
Main Blueprint for FPL Chatbot Routes
"""

import time
from flask import Blueprint, render_template, request, jsonify
from app.services import team_fixture_service, player_search_service, ai_service
from app.services.supabase_service import supabase_service

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
    """Main chat endpoint for processing user questions with Supabase optimization"""
    start_time = time.time()
    
    try:
        user_input = request.json.get("question", "") or request.json.get("message", "")
        quick_mode = request.json.get("quick_mode", True)
        manager_id = request.json.get("manager_id", None)
        manager_name = request.json.get("manager_name", None)
        user_session = request.json.get("session_id", "anonymous")

        if not user_input.strip():
            return jsonify({"answer": "Please ask me something about Fantasy Premier League!"})

        # Convert manager_id to int if provided
        if manager_id and str(manager_id).strip():
            try:
                manager_id = int(str(manager_id).strip())
                print(f"👤 Manager ID received: {manager_id}")
            except (ValueError, TypeError):
                manager_id = None
                print(f"⚠️ Invalid manager_id format: {manager_id}")
        else:
            manager_id = None
            print(f"ℹ️ No manager_id provided")
        
        # Get optimized bootstrap data from Supabase
        bootstrap_data = supabase_service.get_bootstrap_data()
        
        if not bootstrap_data:
            return jsonify({
                "answer": "I'm having trouble accessing FPL data right now. Please try again in a moment.",
                "error": True
            })
        
        # Analyze user query and get context data
        analysis_results = ai_service.analyze_query(
            user_input, 
            bootstrap_data, 
            manager_id=manager_id,
            manager_name=manager_name,
            quick_mode=quick_mode,
            session_id=user_session
        )
        
        # Enhanced response with Supabase data
        response_data = {
            "answer": analysis_results.get("final_response", "I couldn't process your question properly."),
            "query_type": analysis_results.get("query_classification", "general"),
            "confidence": analysis_results.get("confidence", 0.5),
            "response_time": round(time.time() - start_time, 3)
        }
        
        # Store conversation in Supabase for history
        conversation_metadata = {
            "confidence": response_data["confidence"],
            "sources": analysis_results.get("context_sources", []),
            "manager_id": manager_id,
            "manager_name": manager_name,
            "quick_mode": quick_mode
        }
        
        supabase_service.store_conversation_message(
            session_id=user_session,
            user_message=user_input,
            ai_response=response_data["answer"],
            query_type=response_data["query_type"],
            response_time=response_data["response_time"],
            metadata=conversation_metadata
        )
        
        # Log analytics to Supabase
        supabase_service.log_query_analytics(
            query=user_input,
            query_type=response_data["query_type"],
            response_time=response_data["response_time"],
            user_session=user_session
        )
        
        return jsonify(response_data)

    except Exception as e:
        response_time = time.time() - start_time
        
        # Log error to Supabase
        supabase_service.log_query_analytics(
            query=user_input if 'user_input' in locals() else "unknown",
            query_type="error",
            response_time=response_time,
            user_session=user_session if 'user_session' in locals() else "anonymous"
        )
        
        return jsonify({
            "answer": "I encountered an error processing your question. Please try again.",
            "error": True,
            "response_time": round(response_time, 3)
        })


@bp.route("/conversation/history", methods=["GET"])
def get_conversation_history():
    """Get conversation history for a session"""
    try:
        session_id = request.args.get("session_id")
        limit = int(request.args.get("limit", 10))
        
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        
        history = supabase_service.get_conversation_history(session_id, limit)
        
        return jsonify({
            "session_id": session_id,
            "history": history,
            "message_count": len(history)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/conversation/clear", methods=["POST"])
def clear_conversation():
    """Clear conversation history for a session"""
    try:
        session_id = request.json.get("session_id")
        
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        
        success = supabase_service.clear_conversation_history(session_id)
        
        return jsonify({
            "success": success,
            "message": f"Conversation history cleared for session: {session_id}" if success else "Failed to clear conversation history"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/conversation/stats", methods=["GET"])
def get_session_stats():
    """Get statistics for a conversation session"""
    try:
        session_id = request.args.get("session_id")
        
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        
        stats = supabase_service.get_session_stats(session_id)
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/conversations/recent", methods=["GET"])
def get_recent_conversations():
    """Get recent conversations across all sessions"""
    try:
        limit = int(request.args.get("limit", 20))
        
        conversations = supabase_service.get_recent_conversations(limit)
        
        return jsonify({
            "conversations": conversations,
            "count": len(conversations)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/conversation/delete/<session_id>", methods=["DELETE"])
def delete_conversation_session(session_id):
    """Delete a specific conversation session"""
    try:
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        
        success = supabase_service.delete_session(session_id)
        
        return jsonify({
            "success": success,
            "message": f"Session {session_id} deleted successfully" if success else "Failed to delete session"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/health", methods=["GET"])
def health_check():
    """System health check with Supabase metrics"""
    try:
        # Test Supabase connection
        metrics = supabase_service.get_performance_metrics(hours=24)
        
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "supabase_connected": supabase_service.supabase is not None,
            "performance_metrics": metrics
        }
        
        return jsonify(health_data)
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy", 
            "error": str(e),
            "timestamp": time.time()
        })


# Additional health check routes for different platforms
@bp.route("/kaithhealthcheck", methods=["GET"])
@bp.route("/kaithheathcheck", methods=["GET"])
@bp.route("/healthcheck", methods=["GET"])
@bp.route("/ping", methods=["GET"])
def platform_health_check():
    """Simple health check for deployment platforms"""
    return jsonify({
        "status": "healthy",
        "service": "FPL Chatbot",
        "timestamp": time.time()
    })


@bp.route("/analytics", methods=["GET"])
def analytics():
    """Get performance analytics from Supabase"""
    try:
        hours = request.args.get('hours', 24, type=int)
        metrics = supabase_service.get_performance_metrics(hours=hours)
        return jsonify(metrics)
        
    except Exception as e:
        return jsonify({"error": str(e)})


@bp.route("/refresh-data", methods=["POST"])
def refresh_data():
    """Force refresh of FPL data in Supabase"""
    try:
        bootstrap_data = supabase_service.get_bootstrap_data(force_refresh=True)
        
        if bootstrap_data:
            return jsonify({
                "status": "success",
                "message": "FPL data refreshed successfully",
                "player_count": len(bootstrap_data.get('elements', []))
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to refresh FPL data"
            })
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })
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
            
        # Check if it's an unavailable player message
        if context_data and "no longer playing in the Premier League" in context_data:
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
