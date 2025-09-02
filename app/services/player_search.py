"""
Player Search Service
Handles player name searches with fuzzy matching
"""

import unicodedata
from typing import List, Tuple, Optional
from app.models import fpl_client, Player


class PlayerSearchService:
    """Service for searching and matching player names"""
    
    def __init__(self):
        pass
    
    def normalize_name(self, text: str) -> str:
        """Normalize text by removing accents and converting to lowercase"""
        normalized = unicodedata.normalize('NFD', text)
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
        return ascii_text.lower()
    
    def fuzzy_match(self, s1: str, s2: str, threshold: float = 0.8) -> bool:
        """Simple fuzzy matching using character overlap"""
        if not s1 or not s2:
            return False
        
        s1, s2 = s1.lower(), s2.lower()
        
        # If strings are very similar in length, check character overlap
        if abs(len(s1) - len(s2)) <= 2:
            matches = sum(1 for a, b in zip(s1, s2) if a == b)
            similarity = matches / max(len(s1), len(s2))
            if similarity >= threshold:
                return True
        
        # Check if one string is contained in another with minor differences
        if len(s1) >= 3 and len(s2) >= 3:
            # Allow for 1-2 character differences
            for i in range(len(s1) - 2):
                substring = s1[i:i+3]
                if substring in s2:
                    return True
        
        return False
    
    def search_players(self, name: str, return_multiple: bool = False) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        """
        Search for players by name with fuzzy matching
        Returns: (player_id, web_name, full_name) or multiple matches if return_multiple=True
        """
        bootstrap = fpl_client.get_bootstrap()
        players = bootstrap["elements"]
        teams = {team['id']: team['name'] for team in bootstrap['teams']}
        
        # Filter out players who are no longer in the game (status 'u' = unavailable)
        active_players = [p for p in players if p.get('status', 'a') != 'u']
        
        name_normalized = self.normalize_name(name)
        
        exact_matches = []
        partial_matches = []
        fuzzy_matches = []
        
        for p in active_players:
            web_name_normalized = self.normalize_name(p["web_name"])
            full_name_normalized = self.normalize_name(f"{p['first_name']} {p['second_name']}")
            last_name_normalized = self.normalize_name(p["second_name"])
            first_name_normalized = self.normalize_name(p["first_name"])
            team_name = teams.get(p['team'], 'Unknown')
            
            player_info = (p["id"], p["web_name"], f"{p['first_name']} {p['second_name']}", team_name)
            
            # Exact match for web_name or full name (normalized)
            if name_normalized == web_name_normalized or name_normalized == full_name_normalized:
                exact_matches.append(player_info)
                continue
            
            # Check if the search term matches the last name (most common way to search)
            if name_normalized == last_name_normalized:
                partial_matches.append(player_info)
                continue
            
            # Check if the search term matches the first name
            if name_normalized == first_name_normalized:
                partial_matches.append(player_info)
                continue
            
            # For multi-word searches, check if all words are present in the full name
            search_words = name_normalized.split()
            full_name_words = full_name_normalized.split()
            
            if len(search_words) > 1:
                # Check if all search words are present in the full name words
                if all(any(search_word in full_word or full_word in search_word for full_word in full_name_words) for search_word in search_words):
                    partial_matches.append(player_info)
                    continue
                
                # Check if first name + last name match
                if (len(search_words) == 2 and 
                    search_words[0] == first_name_normalized and 
                    search_words[1] in last_name_normalized):
                    partial_matches.append(player_info)
                    continue
            
            # Check if search term is contained in web_name or full name
            if name_normalized in web_name_normalized or name_normalized in full_name_normalized:
                # Prioritize players where the search term appears at word boundaries
                if (name_normalized in web_name_normalized.split() or 
                    name_normalized in full_name_normalized.split() or
                    any(name_normalized in word for word in full_name_normalized.split())):
                    partial_matches.append(player_info)
                    continue
            
            # Fuzzy matching for misspellings
            if (self.fuzzy_match(name_normalized, web_name_normalized) or 
                self.fuzzy_match(name_normalized, last_name_normalized) or
                self.fuzzy_match(name_normalized, first_name_normalized)):
                fuzzy_matches.append(player_info)

        # Return results in order of priority
        if exact_matches:
            if return_multiple:
                return exact_matches
            else:
                match = exact_matches[0]
                return match[0], match[1], match[2]
        
        if partial_matches:
            if return_multiple:
                return partial_matches
            else:
                match = partial_matches[0]
                return match[0], match[1], match[2]
        
        # If only fuzzy matches found, return multiple for user to choose
        if fuzzy_matches:
            if return_multiple:
                return fuzzy_matches[:5]  # Limit to 5 suggestions
            else:
                # For single fuzzy match, suggest the user clarify
                return (None, None, f"Did you mean one of these players? {', '.join([f[2] for f in fuzzy_matches[:3]])}")
        
        if return_multiple:
            return []
        else:
            return (None, None, None)
    
    def create_player_disambiguation_message(self, matching_players: List[Tuple], search_term: str) -> str:
        """Create a message asking user to clarify which player they meant"""
        if len(matching_players) <= 1:
            return None
        
        message = f"I found multiple players matching '{search_term}':\n\n"
        
        for i, (player_id, web_name, full_name, team_name) in enumerate(matching_players, 1):
            # Get position info
            bootstrap = fpl_client.get_bootstrap()
            player_data = next((p for p in bootstrap["elements"] if p["id"] == player_id), None)
            if player_data:
                position_types = {pt['id']: pt['singular_name'] for pt in bootstrap['element_types']}
                position = position_types.get(player_data.get('element_type', 0), 'Unknown')
                price = float(player_data.get('now_cost', 0)) / 10
                message += f"{i}. **{full_name}** ({web_name}) - {team_name} {position} - £{price}m\n"
        
        message += f"\nPlease specify which {search_term} you're asking about by using their full name or team."
        return message


# Global service instance
player_search_service = PlayerSearchService()
