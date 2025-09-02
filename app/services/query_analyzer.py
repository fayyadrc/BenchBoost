"""
Query Analyzer Service
Main service for analyzing user queries and building context data
"""

import re
from typing import Optional
from app.services.team_fixtures import team_fixture_service
from app.services.player_search import player_search_service
from app.models import fpl_client


def analyze_user_query(user_input: str, manager_id: Optional[int] = None) -> str:
    """
    Analyze user query and build context data for AI response
    
    Args:
        user_input: The user's question/query
        manager_id: Optional manager ID for team analysis
        
    Returns:
        Context data string for AI processing
    """
    user_lower = user_input.lower()
    context_data = ""
    
    # PRIORITY CHECK: Team fixture queries (before player searches)
    team_fixture_result = team_fixture_service.process_team_fixture_query(user_input)
    if team_fixture_result:
        return team_fixture_result
    
    # PRIORITY CHECK: Manager team queries
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
    
    # PRIORITY CHECK: FPL Rules queries
    try:
        from app.services.rag_helper import rag_helper
        if rag_helper._is_rules_query(user_lower):
            print("🧠 Detected FPL rules query, using RAG knowledge base...")
            bootstrap = fpl_client.get_bootstrap()
            rag_context = rag_helper._handle_rules_query(user_input, rag_helper.simple_tokenize(user_input))
            if rag_context:
                context_data += rag_context
                return context_data
    except ImportError:
        pass  # RAG not available
    except Exception as e:
        print(f"⚠️ RAG rules check failed: {e}")
    
    # Player and comparison queries
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
    
    # General fixture information
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
    
    # Add general gameweek information
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
    
    # Handle general queries about good form, top players, recommendations
    form_keywords = ["good form", "top", "best", "in form", "recommend", "suggest", "who should", "which player"]
    if any(keyword in user_lower for keyword in form_keywords):
        try:
            context_data += get_top_players_context(user_input)
        except Exception as e:
            print(f"Error getting top players context: {e}")
            context_data += "Error retrieving current player form data.\n"
    
    return context_data


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
