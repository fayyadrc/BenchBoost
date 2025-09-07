"""
Query Analyzer Service
Intelligent routing between Functions (accurate) and RAG (semantic) systems
"""

import re
from typing import Optional, Tuple
from app.services.team_fixtures import team_fixture_service
from app.services.player_search import player_search_service
from app.models import fpl_client


def _simple_query_router(user_input: str) -> Tuple[str, float]:
    """Simple query routing logic (replaces deleted query_router)"""
    # Safety check for None input
    if user_input is None:
        print("⚠️ Warning: user_input is None in router, defaulting to RAG")
        return "RAG_PRIMARY", 50.0
    
    user_lower = user_input.lower().strip()
    
    # Check for simple conversational queries (PRIORITY 1)
    conversational_patterns = [
        r'^(hi|hello|hey|greetings)(\s|$)',  # Greetings at start
        r'(how are you|how\'re you|how are ya)(\?)?',  # How are you anywhere in text
        r'^(good morning|good afternoon|good evening)(\s|$)',
        r'^(thanks|thank you|thx)(\s|$)',
        r'^(bye|goodbye|see ya|see you)(\s|$)',
        r'^(yes|no|ok|okay)(\s|$)',
        r'^(what\'s up|whats up|sup)(\?)?(\s|$)',
        r'^(hi\s+how\s+are\s+you|hello\s+how\s+are\s+you)',  # Combined greetings
        r'^(how\s+are\s+you\s+doing|how\s+is\s+it\s+going)',  # Alternative greetings
        r'^(nice\s+to\s+meet\s+you|good\s+to\s+see\s+you)'   # Polite greetings
    ]
    
    if any(re.search(pattern, user_lower) for pattern in conversational_patterns):
        return "CONVERSATIONAL", 98.0
    
    # Check for contextual queries that need conversation history (PRIORITY 2)
    contextual_patterns = [
        r'\b(he|his|him|she|her|they|them|their)\b',
        r'this player', r'that player', r'the player', r'the same player',
        r'how much does (he|she|they)', r'what team does (he|she|they)',
        r'is (he|she|they)', r'does (he|she|they)'
    ]
    
    if any(re.search(pattern, user_lower) for pattern in contextual_patterns):
        return "CONTEXTUAL", 96.0
    
    # Check for fixture-related queries (PRIORITY 3)
    fixture_keywords = ['fixture', 'fixtures', 'next game', 'next games', 'upcoming', 'match', 'matches', 'game', 'games', 'when do', 'when does', 'play', 'playing', 'vs', 'against', 'opponent', 'opponents']
    
    # Check for patterns like "next X games", "next X fixtures", etc.
    fixture_patterns = [
        r'next\s+\d+\s+(game|games|fixture|fixtures|match|matches)',
        r'upcoming\s+(game|games|fixture|fixtures|match|matches)',
        r'(game|games|fixture|fixtures|match|matches)\s+(this|next|upcoming)'
    ]
    
    if any(keyword in user_lower for keyword in fixture_keywords) or any(re.search(pattern, user_lower) for pattern in fixture_patterns):
        return "FIXTURES", 95.0
    
    # Check for pure data queries (PRIORITY 4)
    data_patterns = [
        r'\b(price|cost|value)\s+of\b',
        r'\bhow\s+much\s+(is|does|cost)\b',
        r'\bposition\s+of\b',
        r'\bteam\s+of\b',
        r'\bpoints\s+(scored|total)\b',
    ]
    
    if any(re.search(pattern, user_lower) for pattern in data_patterns):
        return "FUNCTIONS", 85.0
    
    # Default to RAG for semantic understanding
    return "RAG_PRIMARY", 95.0


def analyze_user_query(user_input: str, manager_id: Optional[int] = None) -> str:
    """
    Analyze user query with RAG-PRIMARY intelligent routing
    New Approach: RAG handles most queries intelligently, Functions only for pure data, Fixtures handled specially
    
    Args:
        user_input: The user's question/query
        manager_id: Optional manager ID for team analysis
        
    Returns:
        Context data string for AI processing
    """
    # Safety check for None input
    if user_input is None:
        print("⚠️ Warning: user_input is None, returning empty context")
        return ""
    
    user_lower = user_input.lower()
    
    # Step 1: Get routing decision (now RAG-primary)
    system_type, confidence = _simple_query_router(user_input)
    print(f"🧠 Smart Router: {system_type.upper()} (confidence: {confidence:.1f}%)")
    
    # Step 2: Handle conversational queries (greetings, etc.)
    if system_type.upper() == 'CONVERSATIONAL':
        return _handle_conversational_queries(user_input)
    
    # Step 3: Handle contextual queries (pronouns needing conversation history)
    elif system_type.upper() == 'CONTEXTUAL':
        # For contextual queries, we need to pass them through to RAG/AI with context
        # The AI service will handle adding conversation context
        return _handle_enhanced_rag_queries(user_input, manager_id)
    
    # Step 4: Handle fixture queries with high priority (always accurate)
    elif system_type.upper() == 'FIXTURES':
        return _handle_fixture_queries(user_input)
    
    # Step 5: Handle pure data queries with functions only
    elif system_type.upper() == 'FUNCTIONS':
        return _handle_function_queries(user_input, manager_id)
    
    # Step 6: Primary path - Enhanced RAG with intelligent function integration
    else:
        return _handle_enhanced_rag_queries(user_input, manager_id)


def _handle_conversational_queries(user_input: str) -> str:
    """Handle simple conversational queries like greetings"""
    print("💬 Using conversational handler for simple greeting...")
    
    user_lower = user_input.lower().strip()
    
    # How are you (check this first for combined greetings)
    if any(phrase in user_lower for phrase in ['how are you', "how're you", 'how are ya', 'how is it going', 'how are you doing']):
        return "� I'm doing great, thanks for asking! Ready to help you dominate your FPL mini-league. What FPL questions do you have?"
    
    # Simple greetings
    elif any(greeting in user_lower for greeting in ['hi', 'hello', 'hey', 'greetings']):
        return "� Hello! I'm your FPL assistant. I can help you with player analysis, fixtures, transfers, and FPL strategy. What would you like to know?"
    
    # Thank you
    elif any(thanks in user_lower for thanks in ['thanks', 'thank you', 'thx']):
        return "🙏 You're welcome! Feel free to ask me anything about Fantasy Premier League!"
    
    # Goodbye
    elif any(bye in user_lower for bye in ['bye', 'goodbye', 'see ya', 'see you']):
        return "👋 Goodbye! Good luck with your FPL team. Come back anytime for more advice!"
    
    # What's up
    elif any(phrase in user_lower for phrase in ["what's up", 'whats up', 'sup']):
        return "🚀 Just here helping FPL managers like you! What can I help you with today - player picks, transfers, or team strategy?"
    
    # Yes/No/OK
    elif user_lower in ['yes', 'no', 'ok', 'okay']:
        return "👍 Got it! Is there anything specific about Fantasy Premier League I can help you with?"
    
    # Fallback
    else:
        return "😊 Hello! I'm your FPL chatbot assistant. Feel free to ask me about players, fixtures, transfers, or any Fantasy Premier League strategy!"


def _handle_fixture_queries(user_input: str) -> str:
    """Handle fixture queries using the dedicated fixture service"""
    print("📅 Using fixture service for accurate fixture data...")
    
    fixture_result = team_fixture_service.process_team_fixture_query(user_input)
    if fixture_result:
        # For simple "who is X playing" queries, provide direct answer
        if _is_simple_opponent_query(user_input):
            return _format_direct_fixture_answer(fixture_result, user_input)
        return fixture_result
    else:
        # If fixture service doesn't handle it, try to extract number of fixtures requested
        import re
        numbers = re.findall(r'\d+', user_input)
        limit = int(numbers[0]) if numbers else 5
        
        # Try to get general fixture information
        try:
            bootstrap = fpl_client.get_bootstrap()
            fixtures = fpl_client.get_fixtures()
            teams = {team['id']: team['name'] for team in bootstrap['teams']}
            
            # Find team mentioned in query
            for team in bootstrap['teams']:
                team_name_lower = team['name'].lower()
                if team_name_lower in user_input.lower() or team_name_lower.replace(' ', '') in user_input.lower():
                    return _get_team_fixtures(team['id'], team['name'], limit, fixtures, teams)
            
            return "❌ Could not identify the team from your query. Please specify a team name (e.g., 'Arsenal fixtures')."
            
        except Exception as e:
            return f"❌ Error retrieving fixture data: {str(e)}"


def _is_simple_opponent_query(query: str) -> bool:
    """Check if this is a simple 'who is X playing' type query"""
    query_lower = query.lower()
    simple_patterns = [
        'who is',
        'who are',
        'who does',
        'who do',
        'playing gw',
        'opponent',
        'against'
    ]
    return any(pattern in query_lower for pattern in simple_patterns)


def _format_direct_fixture_answer(fixture_data: str, query: str) -> str:
    """Format a direct, clear answer for simple fixture queries bypassing AI"""
    # Extract team and opponent from the fixture data
    import re
    
    # Look for pattern like "Gameweek 4: Team A vs Team B (H)"
    match = re.search(r'Gameweek (\d+): (.+?) vs (.+?) \(([HA])\)', fixture_data)
    if match:
        gw, team1, team2, venue = match.groups()
        
        # Determine which team was asked about
        query_lower = query.lower()
        if any(name.lower() in query_lower for name in [team1.lower(), team1.replace(' ', '').lower()]):
            asking_team = team1
            opponent = team2
        else:
            asking_team = team2
            opponent = team1
            venue = 'A' if venue == 'H' else 'H'  # Flip venue
        
        venue_text = "at home" if venue == 'H' else "away"
        
        return f"🏟️ **GW{gw} Fixture:**\n\n**{asking_team}** vs **{opponent}** ({venue_text})\n\n✅ Direct from FPL API - 100% accurate"
    
    # Fallback to original data if parsing fails
    return fixture_data


def _get_team_fixtures(team_id: int, team_name: str, limit: int, fixtures: list, teams: dict) -> str:
    """Get team fixtures with proper formatting"""
    upcoming_fixtures = []
    
    for fixture in fixtures:
        if not fixture.get('finished') and (fixture['team_h'] == team_id or fixture['team_a'] == team_id):
            upcoming_fixtures.append(fixture)
    
    # Sort by gameweek
    upcoming_fixtures.sort(key=lambda x: x.get('event', 999))
    
    if not upcoming_fixtures:
        return f"❌ No upcoming fixtures found for {team_name}."
    
    result = f"📅 **{team_name}'s Next {min(limit, len(upcoming_fixtures))} Fixtures:**\n\n"
    
    for i, fixture in enumerate(upcoming_fixtures[:limit], 1):
        home_team = teams.get(fixture['team_h'], 'Unknown')
        away_team = teams.get(fixture['team_a'], 'Unknown')
        gw = fixture.get('event', 'X')
        
        if fixture['team_h'] == team_id:
            result += f"{i}. **GW{gw}**: {home_team} vs {away_team} (Home)\n"
        else:
            result += f"{i}. **GW{gw}**: {home_team} vs {away_team} (Away)\n"
    
    return result


def _handle_enhanced_rag_queries(user_input: str, manager_id: Optional[int] = None) -> str:
    """Handle queries using enhanced RAG system with intelligent function integration"""
    try:
        from app.services.rag_helper import rag_helper
        bootstrap = fpl_client.get_bootstrap()
        
        print("🧠 Using Enhanced RAG system for intelligent processing...")
        
        # Use the new enhanced RAG method
        rag_result = rag_helper.enhanced_rag_search(user_input, bootstrap)
        
        if rag_result and len(rag_result.strip()) > 20:
            return rag_result
        else:
            # RAG failed, fallback to functions
            print("📝 RAG insufficient, falling back to functions...")
            return _handle_function_queries(user_input, manager_id)
            
    except ImportError:
        print("⚠️ RAG system not available, using functions...")
        return _handle_function_queries(user_input, manager_id)
    except Exception as e:
        print(f"⚠️ RAG system error: {e}, falling back to functions...")
        return _handle_function_queries(user_input, manager_id)


def _handle_function_queries(user_input: str, manager_id: Optional[int] = None) -> str:
    """Handle queries using the function-based system (high accuracy)"""
    user_lower = user_input.lower()
    context_data = ""
    
def _handle_function_queries(user_input: str, manager_id: Optional[int] = None) -> str:
    """Handle queries using the function-based system (high accuracy)"""
    user_lower = user_input.lower()
    context_data = ""
    
    # PRIORITY 1: Team fixture queries (before player searches)
    team_fixture_result = team_fixture_service.process_team_fixture_query(user_input)
    if team_fixture_result:
        return team_fixture_result
    
    # PRIORITY 2: Manager team queries
    manager_keywords = [
        "my team", "team analysis", "my squad", "my players", "analyze my team",
        "tell me about my team", "my current team", "who should i transfer",
        "who should i captain", "my captain", "my vice captain", "my formation",
        "my starting xi", "my bench", "my gameweek", "my points", "my rank",
        "transfer out", "transfer in", "who to transfer", "should i transfer",
        "my transfers", "analyze", "who should i sell", "who should i buy"
    ]
    
    is_manager_query = any(keyword in user_lower for keyword in manager_keywords)
    personal_pronouns = ["i should", "i need", "i want", "should i", "can i", "do i"]
    has_personal_pronouns = any(pronoun in user_lower for pronoun in personal_pronouns)
    
    if (is_manager_query or has_personal_pronouns) and manager_id:
        try:
            context_data += analyze_user_team(manager_id)
            context_data += "\n" + "="*50 + "\n\n"
        except Exception as e:
            context_data += f"Error analyzing your team (Manager ID: {manager_id}): {str(e)}\n\n"
    elif is_manager_query and not manager_id:
        context_data += "MANAGER_ID_REQUIRED: To analyze your team, please set your Manager ID in the settings panel.\n\n"
    
    # PRIORITY 3: Player and comparison queries (high accuracy needed)
    comparison_keywords = ["compare", "vs", "versus", "or", "better", "who should i pick", "between"]
    is_comparison = any(keyword in user_lower for keyword in comparison_keywords)
    
    player_keywords = ["player", "stats", "points", "form", "price", "prices", "cost", "costs", "ownership", "goals", "assists", "minutes", "tell me about", "about", "how is", "performance", "much does", "how much"]
    has_player_keywords = any(keyword in user_lower for keyword in player_keywords)
    
    found_players = []
    
    # Check if the entire query might be just a player name
    might_be_player_name = False
    words = user_input.strip().split()
    
    if (len(words) <= 2 and 
        len(user_input.strip()) > 2 and
        not any(word.lower() in ["what", "when", "where", "why", "how", "fixture", "match", "team", "my", "the", "a", "an", "is", "are", "was", "were", "that", "this", "not", "no"] for word in words)):
        
        potential_player = player_search_service.search_players(user_input.strip())
        if potential_player[0] is not None:
            might_be_player_name = True
    
    if has_player_keywords or is_comparison or might_be_player_name:
        # Handle player searches based on query type
        if might_be_player_name:
            matching_players = player_search_service.search_players(user_input.strip(), return_multiple=True)
            if len(matching_players) > 1:
                return player_search_service.create_player_disambiguation_message(matching_players, user_input.strip())
            elif len(matching_players) == 1:
                match = matching_players[0]
                found_players.append((match[0], match[1], match[2]))
            else:
                return f"❌ **Player Not Found:** '{user_input.strip()}' is not in the current FPL database. This player may not be in the Premier League this season, or you might need to check the spelling. Try searching for a different player name."
        
        # For queries with player keywords, try to extract player names
        elif has_player_keywords:
            # Extract potential player names from the query
            words = user_input.strip().split()
            # Remove common question words and look for player names
            skip_words = {"tell", "me", "about", "how", "is", "what", "who", "when", "where", "why", "the", "a", "an"}
            potential_names = [word for word in words if word.lower() not in skip_words]
            
            if potential_names:
                # Try to search with the remaining words
                name_query = " ".join(potential_names)
                potential_player = player_search_service.search_players(name_query)
                if potential_player[0] is not None:
                    found_players.append((potential_player[0], potential_player[1], potential_player[2]))
        
        # Add player context data
        for i, (pid, web_name, full_name) in enumerate(found_players):
            if is_comparison and len(found_players) > 1:
                context_data += f"PLAYER {i+1} DATA:\n"
            context_data += get_detailed_player_context(pid, full_name, is_comparison)
            context_data += "\n" + "="*50 + "\n\n"
    
    # PRIORITY 4: General fixture information
    fixture_keywords = ["fixture", "match", "game", "when does", "playing", "next game", "opponents"]
    if any(keyword in user_lower for keyword in fixture_keywords):
        fixtures = fpl_client.get_fixtures()
        bootstrap = fpl_client.get_bootstrap()
        teams = {team['id']: team for team in bootstrap['teams']}
        
        context_data += "\nUPCOMING FIXTURES:\n"
        # Filter for upcoming fixtures only and sort by gameweek and kickoff time
        upcoming_fixtures = [f for f in fixtures if not f.get('finished') and f.get('event') is not None]
        upcoming_fixtures.sort(key=lambda x: (x.get('event', 999), x.get('kickoff_time', 'ZZZ')))
        
        # Limit to next 15 fixtures to avoid data overload
        for fixture in upcoming_fixtures[:15]:
            home_team = teams.get(fixture['team_h'], {}).get('name', 'Unknown')
            away_team = teams.get(fixture['team_a'], {}).get('name', 'Unknown')
            gw = fixture.get('event', 'X')
            kickoff = fixture.get('kickoff_time', 'TBD')
            
            # Format kickoff time properly
            if kickoff and kickoff != 'TBD':
                try:
                    from datetime import datetime
                    kickoff_dt = datetime.fromisoformat(kickoff.replace('Z', '+00:00'))
                    kickoff = kickoff_dt.strftime('%d %b %H:%M')
                except:
                    kickoff = 'TBD'
            
            # Validate team data before adding
            if home_team != 'Unknown' and away_team != 'Unknown' and gw != 'X':
                context_data += f"GW{gw}: {home_team} vs {away_team} - {kickoff}\n"
    
    # Handle general queries about good form, top players, recommendations
    form_keywords = ["good form", "top", "best", "in form", "recommend", "suggest", "who should", "which player"]
    if any(keyword in user_lower for keyword in form_keywords):
        try:
            context_data += get_top_players_context(user_input)
        except Exception as e:
            print(f"Error getting top players context: {e}")
            context_data += "Error retrieving current player form data.\n"
    
    # Add general gameweek information if no specific data found
    if not context_data.strip():
        try:
            bootstrap = fpl_client.get_bootstrap()
            events = bootstrap.get('events', [])
            current_event = next((e for e in events if e.get('is_current', False)), None)
            next_event = next((e for e in events if e.get('is_next', False)), None)
            
            context_data += "\nGAMEWEEK INFORMATION:\n"
            if current_event:
                context_data += f"Current Gameweek: {current_event.get('id', 'Unknown')}\n"
            
            for event in events[:5]:  # Show first 5 gameweeks
                deadline = event.get('deadline_time', 'TBD')
                context_data += f"GW{event.get('id', 'X')}: {event.get('name', 'Unknown')} - Deadline: {deadline[:11] + deadline[11:16] if len(deadline) > 16 else deadline}\n"
            
        except Exception as e:
            print(f"Error getting gameweek info: {e}")
    
    return context_data


def _handle_rag_queries(user_input: str, manager_id: Optional[int] = None) -> str:
    """Handle queries using the RAG system (semantic understanding)"""
    try:
        from app.services.rag_helper import rag_helper
        bootstrap = fpl_client.get_bootstrap()
        
        print("🧠 Using RAG system for semantic understanding...")
        rag_result = rag_helper.rag_fallback_search(user_input, bootstrap)
        
        if rag_result and len(rag_result.strip()) > 20:
            return rag_result
        else:
            # RAG failed, fallback to functions
            print("📝 RAG insufficient, falling back to functions...")
            return _handle_function_queries(user_input, manager_id)
            
    except ImportError:
        print("⚠️ RAG system not available, using functions...")
        return _handle_function_queries(user_input, manager_id)
    except Exception as e:
        print(f"⚠️ RAG system error: {e}, falling back to functions...")
        return _handle_function_queries(user_input, manager_id)


def analyze_user_team(manager_id: int) -> str:
    """Analyze user's FPL team"""
    try:
        # This would be implemented with actual team analysis logic
        # For now, return a placeholder
        return f"MANAGER TEAM ANALYSIS for ID {manager_id}:\n\nTeam analysis functionality would be implemented here.\n"
    except Exception as e:
        return f"Error analyzing team: {str(e)}\n"


def get_detailed_player_context(player_id: int, full_name: str, is_comparison: bool = False) -> str:
    """Get detailed context data for a specific player"""
    try:
        bootstrap = fpl_client.get_bootstrap()
        players = bootstrap['elements']
        teams = {team['id']: team['name'] for team in bootstrap['teams']}
        positions = {pos['id']: pos['singular_name'] for pos in bootstrap['element_types']}
        
        # Find the specific player
        player_data = next((p for p in players if p['id'] == player_id), None)
        if not player_data:
            return f"Player with ID {player_id} not found in current FPL data.\n"
        
        team_name = teams.get(player_data.get('team'), 'Unknown')
        position = positions.get(player_data.get('element_type'), 'Unknown')
        
        context = f"PLAYER DATA for {full_name}:\n\n"
        context += f"Team: {team_name}\n"
        context += f"Position: {position}\n"
        context += f"Price: £{float(player_data.get('now_cost', 0)) / 10}m\n"
        context += f"Total Points: {player_data.get('total_points', 0)}\n"
        context += f"Form: {player_data.get('form', 0)}\n"
        context += f"Status: {'Active' if player_data.get('status', 'a') == 'a' else 'Inactive/Injured'}\n"
        context += f"Ownership: {player_data.get('selected_by_percent', 0)}%\n"
        context += f"Transfers In: {player_data.get('transfers_in_event', 0)}\n"
        context += f"Transfers Out: {player_data.get('transfers_out_event', 0)}\n"
        
        return context
        
    except Exception as e:
        return f"Error getting detailed player context for {full_name}: {str(e)}\n"


def get_top_players_context(user_input: str) -> str:
    """Get context for queries about top players or players in good form"""
    try:
        bootstrap = fpl_client.get_bootstrap()
        players = bootstrap['elements']
        teams = {team['id']: team['name'] for team in bootstrap['teams']}
        positions = {pos['id']: pos['singular_name'] for pos in bootstrap['element_types']}
        
        # Filter for only active players (not injured, unavailable, etc.)
        active_players = [p for p in players if p.get('status', 'a') == 'a']
        
        # Check if query is specifically about top 6 clubs
        top_6_teams = ['Arsenal', 'Chelsea', 'Liverpool', 'Man City', 'Man Utd', 'Spurs']
        user_lower = user_input.lower()
        
        if any(phrase in user_lower for phrase in ['top 6', 'big 6', 'top six', 'big six']):
            # Filter for top 6 players only
            top_6_team_ids = [team_id for team_id, team_name in teams.items() if team_name in top_6_teams]
            active_players = [p for p in active_players if p.get('team') in top_6_team_ids]
        
        # Sort by total points to get players in good form
        top_performers = sorted(active_players, key=lambda x: x.get('total_points', 0), reverse=True)[:20]
        
        context_data = "CURRENT ACTIVE PLAYERS IN GOOD FORM:\n\n"
        
        for i, player in enumerate(top_performers, 1):
            team_name = teams.get(player.get('team'), 'Unknown')
            position = positions.get(player.get('element_type'), 'Unknown')
            points = player.get('total_points', 0)
            price = float(player.get('now_cost', 0)) / 10
            form = player.get('form', 0)
            
            # Only include players with significant points
            if points >= 5:
                context_data += f"{i}. {player['first_name']} {player['second_name']} ({player['web_name']})\n"
                context_data += f"   Team: {team_name} | Position: {position} | Points: {points} | Price: £{price}m | Form: {form}\n"
                context_data += f"   Status: Active and available for selection\n\n"
        
        # Add note about current data
        context_data += "NOTE: This data is from the current FPL season and only includes active, available players.\n"
        context_data += "Players who have transferred, retired, or are unavailable are automatically excluded.\n"
        
        return context_data
        
    except Exception as e:
        return f"Error getting top players context: {str(e)}\n"


def get_general_fpl_context(user_input: str) -> str:
    """Get general FPL context for queries"""
    try:
        return "General FPL context would be implemented here.\n"
    except Exception as e:
        return f"Error getting general FPL context: {str(e)}\n"
