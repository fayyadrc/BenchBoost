"""
FPL API Models and Data Access Layer
"""

import requests
import os
from typing import Dict, List, Any, Optional


class FPLClient:
    """Client for interacting with the Fantasy Premier League API"""
    
    BASE_URL = "https://fantasy.premierleague.com/api"
    
    def __init__(self):
        self._bootstrap_cache = None
        self._fixtures_cache = None
    
    def fetch_json(self, endpoint: str) -> Dict[str, Any]:
        """Fetch JSON data from FPL API endpoint"""
        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_bootstrap(self) -> Dict[str, Any]:
        """Get bootstrap-static data (players, teams, gameweeks)"""
        if self._bootstrap_cache is None:
            self._bootstrap_cache = self.fetch_json("bootstrap-static/")
        return self._bootstrap_cache
    
    def get_fixtures(self) -> List[Dict[str, Any]]:
        """Get fixtures data"""
        if self._fixtures_cache is None:
            self._fixtures_cache = self.fetch_json("fixtures/")
        return self._fixtures_cache
    
    def get_player_summary(self, player_id: int) -> Dict[str, Any]:
        """Get detailed player summary including fixtures and history"""
        return self.fetch_json(f"element-summary/{player_id}/")
    
    def get_manager_team(self, manager_id: int, gameweek: Optional[int] = None) -> Dict[str, Any]:
        """Get manager's team for a specific gameweek"""
        if gameweek:
            return self.fetch_json(f"entry/{manager_id}/event/{gameweek}/picks/")
        else:
            return self.fetch_json(f"entry/{manager_id}/")
    
    def get_manager_history(self, manager_id: int) -> Dict[str, Any]:
        """Get manager's season history"""
        return self.fetch_json(f"entry/{manager_id}/history/")
    
    def clear_cache(self):
        """Clear cached data"""
        self._bootstrap_cache = None
        self._fixtures_cache = None


# Global client instance
fpl_client = FPLClient()


class TeamFixture:
    """Represents a team fixture"""
    
    def __init__(self, fixture_data: Dict[str, Any], teams: Dict[int, Dict[str, Any]]):
        self.fixture_data = fixture_data
        self.teams = teams
    
    @property
    def gameweek(self) -> int:
        return self.fixture_data.get('event', 0)
    
    @property
    def home_team_id(self) -> int:
        return self.fixture_data['team_h']
    
    @property
    def away_team_id(self) -> int:
        return self.fixture_data['team_a']
    
    @property
    def home_team_name(self) -> str:
        return self.teams.get(self.home_team_id, {}).get('name', 'Unknown')
    
    @property
    def away_team_name(self) -> str:
        return self.teams.get(self.away_team_id, {}).get('name', 'Unknown')
    
    @property
    def is_finished(self) -> bool:
        return self.fixture_data.get('finished', False)
    
    @property
    def kickoff_time(self) -> str:
        return self.fixture_data.get('kickoff_time', 'TBD')
    
    def get_opponent_for_team(self, team_id: int) -> Optional[str]:
        """Get the opponent team name for a given team ID"""
        if team_id == self.home_team_id:
            return self.away_team_name
        elif team_id == self.away_team_id:
            return self.home_team_name
        return None
    
    def is_home_for_team(self, team_id: int) -> Optional[bool]:
        """Check if a team is playing at home"""
        if team_id == self.home_team_id:
            return True
        elif team_id == self.away_team_id:
            return False
        return None


class Player:
    """Represents an FPL player"""
    
    def __init__(self, player_data: Dict[str, Any], teams: Dict[int, Dict[str, Any]], positions: Dict[int, Dict[str, Any]]):
        self.player_data = player_data
        self.teams = teams
        self.positions = positions
    
    @property
    def id(self) -> int:
        return self.player_data['id']
    
    @property
    def web_name(self) -> str:
        return self.player_data.get('web_name', '')
    
    @property
    def full_name(self) -> str:
        first_name = self.player_data.get('first_name', '')
        second_name = self.player_data.get('second_name', '')
        return f"{first_name} {second_name}".strip()
    
    @property
    def team_name(self) -> str:
        team_id = self.player_data.get('team', 0)
        return self.teams.get(team_id, {}).get('name', 'Unknown')
    
    @property
    def position_name(self) -> str:
        position_id = self.player_data.get('element_type', 0)
        return self.positions.get(position_id, {}).get('singular_name', 'Unknown')
    
    @property
    def price(self) -> float:
        return float(self.player_data.get('now_cost', 0)) / 10
    
    @property
    def total_points(self) -> int:
        return self.player_data.get('total_points', 0)
    
    @property
    def is_available(self) -> bool:
        """Check if player is available for selection"""
        return self.player_data.get('status', 'a') != 'u'
