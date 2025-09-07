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
        try:
            bootstrap = fpl_client.get_bootstrap()
            teams = bootstrap.get('teams', [])
            
            if not teams:
                print("⚠️  No teams data available, using default team mappings")
                self._use_default_team_mappings()
                return
            
            # Clear existing mappings
            self.team_name_mappings = {}
            
            for team in teams:
                team_id = team.get('id')
                team_name = team.get('name', '')
                
                if not team_id or not team_name:
                    continue
                    
                # Add official name
                self.team_name_mappings[team_name.lower()] = (team_id, team_name)
            
            # Add common abbreviations and alternative names
            for team in teams:
                team_id = team.get('id')
                team_name = team.get('name', '')
                
                if not team_id or not team_name:
                    continue
                
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
                    
        except Exception as e:
            print(f"⚠️  Error building team mappings: {e}")
            print("Using default team mappings as fallback")
            self._use_default_team_mappings()
    
    def _use_default_team_mappings(self):
        """Use default team mappings when FPL API is unavailable"""
        default_teams = {
            "arsenal": (1, "Arsenal"),
            "aston villa": (2, "Aston Villa"),
            "brentford": (3, "Brentford"),
            "brighton": (4, "Brighton"),
            "chelsea": (5, "Chelsea"),
            "crystal palace": (6, "Crystal Palace"),
            "everton": (7, "Everton"),
            "fulham": (8, "Fulham"),
            "liverpool": (9, "Liverpool"),
            "man city": (10, "Man City"),
            "manchester city": (10, "Man City"),
            "city": (10, "Man City"),
            "man utd": (11, "Man Utd"),
            "manchester united": (11, "Man Utd"),
            "united": (11, "Man Utd"),
            "newcastle": (12, "Newcastle"),
            "spurs": (13, "Spurs"),
            "tottenham": (13, "Spurs"),
            "west ham": (14, "West Ham"),
            "wolves": (15, "Wolves"),
            "leicester": (16, "Leicester"),
            "leeds": (17, "Leeds"),
            "burnley": (18, "Burnley"),
            "watford": (19, "Watford"),
            "norwich": (20, "Norwich")
        }
        self.team_name_mappings = default_teams
    
    def is_team_fixture_query(self, query: str) -> bool:
        """Check if query is asking about team fixtures"""
        query_lower = query.lower()
        
        # Enhanced patterns for fixture queries
        team_fixture_patterns = [
            r"who.*facing",
            r"facing.*gw",
            r"who.*play",
            r"who.*against",
            r"opponents",
            r"fixture",
            r"fixtures",
            r"match",
            r"matches", 
            r"game",
            r"games",
            r"next.*fixtures",
            r"upcoming.*fixtures",
            r"next.*matches",
            r"upcoming.*matches",
            r"\w+s?\s+next\s+\d+\s+fixtures",  # "arsenals next 5 fixtures"
            r"\w+s?\s+fixtures",  # "arsenal fixtures"
            r"\w+s?\s+next\s+fixtures",  # "arsenal next fixtures"
        ]
        
        return any(re.search(pattern, query_lower) for pattern in team_fixture_patterns)
    
    def extract_team_from_query(self, query: str) -> Optional[Tuple[int, str]]:
        """Extract team ID and name from query"""
        query_lower = query.lower()
        
        # Remove possessive forms (arsenal's -> arsenal)
        query_clean = re.sub(r"(\w+)'s", r"\1", query_lower)
        
        # Find mentioned team using mappings
        for team_key, (team_id, team_name) in self.team_name_mappings.items():
            if team_key in query_clean:
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
                    home_team = teams.get(fixture_data['team_h'], 'Unknown')
                    away_team = teams.get(fixture_data['team_a'], 'Unknown')
                    
                    if fixture_data['team_h'] == team_id:
                        # Team is playing at home
                        opponent = away_team
                        venue = 'H'
                        is_home = True
                    else:
                        # Team is playing away
                        opponent = home_team
                        venue = 'A'
                        is_home = False
                    
                    result = f"**TEAM FIXTURE DATA for {team_name}:**\n\n"
                    result += f"**Gameweek {gameweek}:** {team_name} vs {opponent} ({venue})\n"
                    result += f"**Venue:** {'Home' if is_home else 'Away'}\n\n"
                    return result
        
        # No fixture found
        result = f"**TEAM FIXTURE DATA for {team_name}:**\n\n"
        result += f"❌ No fixture found for {team_name} in Gameweek {gameweek}\n\n"
        return result
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
                upcoming_fixtures.append(fixture_data)  # Store raw fixture data
        
        # Sort by gameweek
        upcoming_fixtures.sort(key=lambda x: x.get('event', 999))
        
        result = f"**TEAM FIXTURE DATA for {team_name}:**\n\n"
        result += "**Upcoming Fixtures:**\n"
        
        for fixture_data in upcoming_fixtures[:limit]:
            home_team = teams.get(fixture_data['team_h'], 'Unknown')
            away_team = teams.get(fixture_data['team_a'], 'Unknown')
            gw = fixture_data.get('event', 'X')
            
            if fixture_data['team_h'] == team_id:
                # Team is playing at home
                opponent = away_team
                venue = 'H'
            else:
                # Team is playing away
                opponent = home_team  
                venue = 'A'
                
            result += f"- **GW{gw}**: {team_name} vs {opponent} ({venue})\n"
        
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
