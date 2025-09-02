"""
Team Fixture Service
Handles team fixture queries and data processing
"""

import re
from typing import Dict, List, Optional, Tuple
from app.models import fpl_client, TeamFixture


class TeamFixtureService:
    """Service for handling team fixture queries"""
    
    def __init__(self):
        self.team_name_mappings = {}
        self._build_team_mappings()
    
    def _build_team_mappings(self):
        """Build team name mappings for common abbreviations"""
        bootstrap = fpl_client.get_bootstrap()
        teams = {team['id']: team['name'] for team in bootstrap['teams']}
        
        # Clear existing mappings
        self.team_name_mappings = {}
        
        for team_id, team_name in teams.items():
            # Add official name
            self.team_name_mappings[team_name.lower()] = (team_id, team_name)
            
            # Add common abbreviations and alternative names
            if team_name == "Man Utd":
                self.team_name_mappings["united"] = (team_id, team_name)
                self.team_name_mappings["manchester united"] = (team_id, team_name)
                self.team_name_mappings["man united"] = (team_id, team_name)
            elif team_name == "Man City":
                self.team_name_mappings["city"] = (team_id, team_name)
                self.team_name_mappings["manchester city"] = (team_id, team_name)
                self.team_name_mappings["man city"] = (team_id, team_name)
            elif team_name == "Spurs":
                self.team_name_mappings["tottenham"] = (team_id, team_name)
                self.team_name_mappings["tottenham hotspur"] = (team_id, team_name)
            elif team_name == "Nott'm Forest":
                self.team_name_mappings["nottingham forest"] = (team_id, team_name)
                self.team_name_mappings["forest"] = (team_id, team_name)
                self.team_name_mappings["nottingham"] = (team_id, team_name)
            elif team_name == "West Ham":
                self.team_name_mappings["west ham united"] = (team_id, team_name)
                self.team_name_mappings["hammers"] = (team_id, team_name)
    
    def is_team_fixture_query(self, query: str) -> bool:
        """Check if query is asking about team fixtures"""
        query_lower = query.lower()
        team_fixture_keywords = [
            "who.*facing", "facing.*gw", "who.*play", "who.*against", 
            "opponents", "fixture", "match", "game"
        ]
        return any(re.search(keyword, query_lower) for keyword in team_fixture_keywords)
    
    def extract_team_from_query(self, query: str) -> Optional[Tuple[int, str]]:
        """Extract team ID and name from query"""
        query_lower = query.lower()
        
        # Find mentioned team using mappings
        for team_key, (team_id, team_name) in self.team_name_mappings.items():
            if team_key in query_lower:
                return team_id, team_name
        
        return None
    
    def extract_gameweek_from_query(self, query: str) -> Optional[int]:
        """Extract gameweek number from query"""
        query_lower = query.lower()
        gw_match = re.search(r'gw(\d+)|gameweek\s*(\d+)', query_lower)
        if gw_match:
            return int(gw_match.group(1) or gw_match.group(2))
        return None
    
    def get_team_fixture_for_gameweek(self, team_id: int, team_name: str, gameweek: int) -> str:
        """Get team fixture for specific gameweek"""
        fixtures = fpl_client.get_fixtures()
        bootstrap = fpl_client.get_bootstrap()
        teams = {team['id']: team['name'] for team in bootstrap['teams']}
        
        # Find fixture for the team in the specified gameweek
        for fixture_data in fixtures:
            if fixture_data.get('event') == gameweek:
                if fixture_data['team_h'] == team_id or fixture_data['team_a'] == team_id:
                    fixture = TeamFixture(fixture_data, teams)
                    opponent = fixture.get_opponent_for_team(team_id)
                    is_home = fixture.is_home_for_team(team_id)
                    venue = 'H' if is_home else 'A'
                    
                    result = f"TEAM FIXTURE DATA for {team_name}:\n\n"
                    result += f"Gameweek {gameweek}: {team_name} vs {opponent} ({venue})\n"
                    result += f"Venue: {'Home' if is_home else 'Away'}\n\n"
                    return result
        
        # No fixture found
        result = f"TEAM FIXTURE DATA for {team_name}:\n\n"
        result += f"No fixture found for {team_name} in Gameweek {gameweek}\n\n"
        return result
    
    def get_upcoming_team_fixtures(self, team_id: int, team_name: str, limit: int = 5) -> str:
        """Get upcoming fixtures for a team"""
        fixtures = fpl_client.get_fixtures()
        bootstrap = fpl_client.get_bootstrap()
        teams = {team['id']: team['name'] for team in bootstrap['teams']}
        
        # Find upcoming fixtures for the team
        upcoming_fixtures = []
        for fixture_data in fixtures:
            if not fixture_data.get('finished') and (
                fixture_data['team_h'] == team_id or fixture_data['team_a'] == team_id
            ):
                upcoming_fixtures.append(TeamFixture(fixture_data, teams))
        
        # Sort by gameweek
        upcoming_fixtures.sort(key=lambda x: x.gameweek)
        
        result = f"TEAM FIXTURE DATA for {team_name}:\n\n"
        result += "Upcoming Fixtures:\n"
        
        for fixture in upcoming_fixtures[:limit]:
            opponent = fixture.get_opponent_for_team(team_id)
            is_home = fixture.is_home_for_team(team_id)
            venue = 'H' if is_home else 'A'
            result += f"GW{fixture.gameweek}: {team_name} vs {opponent} ({venue})\n"
        
        result += "\n"
        return result
    
    def process_team_fixture_query(self, query: str) -> Optional[str]:
        """Process a team fixture query and return formatted result"""
        if not self.is_team_fixture_query(query):
            return None
        
        # Extract team
        team_info = self.extract_team_from_query(query)
        if not team_info:
            return None
        
        team_id, team_name = team_info
        
        # Extract gameweek
        target_gw = self.extract_gameweek_from_query(query)
        
        if target_gw:
            return self.get_team_fixture_for_gameweek(team_id, team_name, target_gw)
        else:
            return self.get_upcoming_team_fixtures(team_id, team_name)


# Global service instance
team_fixture_service = TeamFixtureService()
