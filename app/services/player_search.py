

import unicodedata
from typing import List, Tuple, Optional
from app.models import fpl_client, Player


class PlayerSearchService:
    
    
    def __init__(self):
        pass
    
    def normalize_name(self, text: str) -> str:
      
        normalized = unicodedata.normalize('NFD', text)
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
        return ascii_text.lower()
    
    def fuzzy_match(self, s1: str, s2: str, threshold: float = 0.8) -> bool:
     
        if not s1 or not s2:
            return False
        
        s1, s2 = s1.lower(), s2.lower()
        
        
        if abs(len(s1) - len(s2)) <= 2:
            matches = sum(1 for a, b in zip(s1, s2) if a == b)
            similarity = matches / max(len(s1), len(s2))
            if similarity >= threshold:
                return True
        
        
        if len(s1) >= 3 and len(s2) >= 3:
            
            for i in range(len(s1) - 2):
                substring = s1[i:i+3]
                if substring in s2:
                    return True
        
        return False
    
    def search_players(self, name: str, return_multiple: bool = False, include_unavailable: bool = False) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        """
        Search for players by name with enhanced validation
        Returns: (player_id, web_name, full_name) or (None, None, None) if not found
        """
        bootstrap = fpl_client.get_bootstrap()
        players = bootstrap.get("elements", [])
        teams = {team['id']: team['name'] for team in bootstrap.get('teams', [])}
        
        # Validate that we have current season data
        if not players:
            print("⚠️  No player data available")
            return None, None, None
            
        # Check if this might be a non-Premier League player
        non_pl_names = ['messi', 'ronaldo', 'neymar', 'mbappe', 'haaland']  # Common non-PL players
        if any(non_pl_name in name.lower() for non_pl_name in non_pl_names):
            print(f"⚠️  Detected potential non-Premier League player: {name}")
            # Only allow if we can confirm they exist in current PL data
            found_in_pl = False
            for p in players:
                if (name.lower() in p.get('web_name', '').lower() or 
                    name.lower() in f"{p.get('first_name', '')} {p.get('second_name', '')}".lower()):
                    found_in_pl = True
                    break
            if not found_in_pl:
                print(f"❌ Player {name} not found in current Premier League data")
                return None, None, None
        
        
        if include_unavailable:
            active_players = players  # Include all players
        else:
            active_players = [p for p in players if p.get('status', 'a') != 'u']
        
        name_normalized = self.normalize_name(name)
        
        exact_matches = []
        partial_matches = []
        fuzzy_matches = []
        unavailable_matches = []  # Track unavailable players separately
        
        for p in players:  # Search all players first to find unavailable ones
            web_name_normalized = self.normalize_name(p["web_name"])
            full_name_normalized = self.normalize_name(f"{p['first_name']} {p['second_name']}")
            last_name_normalized = self.normalize_name(p["second_name"])
            first_name_normalized = self.normalize_name(p["first_name"])
            team_name = teams.get(p['team'], 'Unknown')
            
            player_info = (p["id"], p["web_name"], f"{p['first_name']} {p['second_name']}", team_name, p.get('status', 'a'))
            
            # Check if this is an unavailable player match
            is_unavailable = p.get('status', 'a') == 'u'
            
            # Check exact matches first (for both available and unavailable)
            if name_normalized == web_name_normalized or name_normalized == full_name_normalized:
                if is_unavailable:
                    unavailable_matches.append(player_info)
                elif p in active_players:
                    exact_matches.append(player_info)
                continue
            
            # For unavailable players, check partial matches before skipping
            if p not in active_players:
                # Check partial matches for unavailable players
                if name_normalized == last_name_normalized or name_normalized == first_name_normalized:
                    unavailable_matches.append(player_info)
                    continue
                
                search_words = name_normalized.split()
                full_name_words = full_name_normalized.split()
                
                # Partial word matching for surnames with multiple parts
                if len(search_words) > 1:
                    if all(any(search_word in full_word or full_word in search_word for full_word in full_name_words) for search_word in search_words):
                        unavailable_matches.append(player_info)
                        continue
                    
                    if (len(search_words) == 2 and 
                        search_words[0] == first_name_normalized and 
                        search_words[1] in last_name_normalized):
                        unavailable_matches.append(player_info)
                        continue
                
                # Skip to next player for unavailable ones
                continue
                
            # Active player matches (existing logic)
            if name_normalized == last_name_normalized:
                partial_matches.append(player_info)
                continue
            
            if name_normalized == first_name_normalized:
                partial_matches.append(player_info)
                continue
            
            search_words = name_normalized.split()
            full_name_words = full_name_normalized.split()
            
            # Partial word matching for surnames with multiple parts
            if len(search_words) > 1:
                if all(any(search_word in full_word or full_word in search_word for full_word in full_name_words) for search_word in search_words):
                    partial_matches.append(player_info)
                    continue
                
                if (len(search_words) == 2 and 
                    search_words[0] == first_name_normalized and 
                    search_words[1] in last_name_normalized):
                    partial_matches.append(player_info)
                    continue
            
            if name_normalized in web_name_normalized or name_normalized in full_name_normalized:
                if (name_normalized in web_name_normalized.split() or 
                    name_normalized in full_name_normalized.split() or
                    any(name_normalized in word for word in full_name_normalized.split())):
                    partial_matches.append(player_info)
                    continue
            
            if (self.fuzzy_match(name_normalized, web_name_normalized) or 
                self.fuzzy_match(name_normalized, last_name_normalized) or
                self.fuzzy_match(name_normalized, first_name_normalized)):
                fuzzy_matches.append(player_info)

        
        if exact_matches:
            if return_multiple:
                return exact_matches
            else:
                match = exact_matches[0]
                return match[0], match[1], match[2]
        
        # If no active players found but unavailable players match, inform user
        if unavailable_matches and not exact_matches and not partial_matches:
            match = unavailable_matches[0]
            player_id, web_name, full_name, team_name, status = match
            
            # Get more detailed status information
            bootstrap = fpl_client.get_bootstrap()
            player_data = next((p for p in bootstrap["elements"] if p["id"] == player_id), None)
            
            status_message = f"{full_name} is currently "
            if status == 'u':
                status_message += "unavailable for selection in FPL."
            elif status == 'i':
                status_message += "injured and unavailable for selection."
            elif status == 'd':
                status_message += "on loan and unavailable for selection."
            else:
                status_message += f"unavailable for selection (status: {status})."
            
            if player_data and player_data.get('news'):
                status_message += f" Latest news: {player_data.get('news')}"
            
            return (None, None, status_message)
        
        if partial_matches:
            if return_multiple:
                return partial_matches
            else:
                match = partial_matches[0]
                return match[0], match[1], match[2]
        
        if fuzzy_matches:
            # If we have fuzzy matches but they seem very unrelated, suggest player not in PL
            if len(fuzzy_matches) > 0:
                # Check if any fuzzy match is actually close enough to be relevant
                best_match = fuzzy_matches[0]
                search_words = name_normalized.split()
                match_words = best_match[2].lower().split()
                
                # If search has common football names and no good match, likely not in PL
                common_names = ['harry', 'kane', 'messi', 'ronaldo', 'neymar', 'mbappe', 'benzema']
                if any(word in common_names for word in search_words):
                    return (None, None, f"'{name}' is likely no longer playing in the Premier League and is not available in FPL.")
                
                # Otherwise show suggestions for potential misspellings
                if return_multiple:
                    return fuzzy_matches[:5]  
                else:
                    return (None, None, f"Did you mean one of these players? {', '.join([f[2] for f in fuzzy_matches[:3]])}")
            
        # If no matches found at all, suggest they're not in Premier League
        if return_multiple:
            return []
        else:
            return (None, None, f"Player '{name}' not found. They may no longer be playing in the Premier League or the name might be misspelled.")
    
    def create_player_disambiguation_message(self, matching_players: List[Tuple], search_term: str) -> str:
        """Create a message asking user to clarify which player they meant"""
        if len(matching_players) <= 1:
            return None
        
        message = f"I found multiple players matching '{search_term}':\n\n"
        
        for i, (player_id, web_name, full_name, team_name) in enumerate(matching_players, 1):
           
            bootstrap = fpl_client.get_bootstrap()
            player_data = next((p for p in bootstrap["elements"] if p["id"] == player_id), None)
            if player_data:
                position_types = {pt['id']: pt['singular_name'] for pt in bootstrap['element_types']}
                position = position_types.get(player_data.get('element_type', 0), 'Unknown')
                price = float(player_data.get('now_cost', 0)) / 10
                message += f"{i}. **{full_name}** ({web_name}) - {team_name} {position} - £{price}m\n"
        
        message += f"\nPlease specify which {search_term} you're asking about by using their full name or team."
        return message



player_search_service = PlayerSearchService()
