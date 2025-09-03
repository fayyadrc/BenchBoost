"""
Supabase Integration Service for FPL Chatbot
Replaces custom caching and database services with Supabase BaaS
"""

import os
import json
import time
from typing import Dict, List, Optional, Any

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    print("⚠️  Supabase not available - falling back to FPL API only")
    SUPABASE_AVAILABLE = False
    Client = None

from config import Config


class SupabaseFPLService:
    """
    Replaces: cache_service.py + database_service.py + monitoring_service.py
    Uses Supabase for all data operations with built-in optimization
    """
    
    def __init__(self):
        self.url = Config.SUPABASE_URL
        self.key = Config.SUPABASE_ANON_KEY
        
        if not SUPABASE_AVAILABLE:
            print("⚠️  Supabase library not installed. Install with: pip install supabase")
            self.supabase = None
            return
            
        if not self.key:
            print("⚠️  SUPABASE_ANON_KEY not set. Please add it to your .env file")
            self.supabase = None
            return
            
        try:
            self.supabase: Client = create_client(self.url, self.key)
            print(f"✅ Connected to Supabase: {self.url}")
        except Exception as e:
            print(f"❌ Failed to connect to Supabase: {e}")
            self.supabase = None
    
    def _handle_supabase_error(self, error):
        """Handle common Supabase errors with helpful messages"""
        error_msg = str(error)
        if "nodename nor servname provided" in error_msg or "relation" in error_msg:
            print(f"❌ Supabase tables not found. Please run the database schema:")
            project_id = self.url.split('/')[-1].replace('.supabase.co', '')
            print(f"   1. Go to: https://supabase.com/dashboard/project/{project_id}/sql")
            print(f"   2. Run the SQL from supabase_schema.sql")
            print(f"   3. This will create the required tables: bootstrap_data, players, query_analytics")
        return error_msg
    
    def get_bootstrap_data(self, force_refresh: bool = False) -> Dict:
        """
        Get bootstrap data with automatic caching
        Supabase handles all caching automatically
        """
        if not self.supabase:
            return self._fallback_to_api()
            
        try:
            # Get cached data from Supabase
            response = self.supabase.table('bootstrap_data')\
                .select('*')\
                .eq('is_current', True)\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            if response.data and not force_refresh:
                data = json.loads(response.data[0]['data_json'])
                print("✅ Using cached bootstrap data from Supabase")
                return data
            
            # Fetch fresh data and cache it
            return self._fetch_and_store_bootstrap_data()
            
        except Exception as e:
            error_msg = self._handle_supabase_error(e)
            print(f"⚠️  Supabase error: {error_msg}")
            return self._fallback_to_api()
    
    def _fetch_and_store_bootstrap_data(self) -> Dict:
        """Fetch fresh data from FPL API and store in Supabase"""
        try:
            from app.models.fpl_api import FPLClient
            client = FPLClient()
            bootstrap_data = client.get_bootstrap()
            
            if not bootstrap_data:
                return {}
            
            # Extract current gameweek
            current_gw = 1
            for event in bootstrap_data.get('events', []):
                if event.get('is_current', False):
                    current_gw = event['id']
                    break
            
            # Store in Supabase
            self.store_bootstrap_data(bootstrap_data, current_gw)
            print(f"✅ Fresh bootstrap data cached for GW{current_gw}")
            
            return bootstrap_data
            
        except Exception as e:
            print(f"❌ Error fetching bootstrap data: {e}")
            return {}
    
    def _fallback_to_api(self) -> Dict:
        """Fallback to direct API call if Supabase unavailable"""
        try:
            from app.models.fpl_api import FPLClient
            client = FPLClient()
            return client.get_bootstrap()
        except Exception as e:
            print(f"❌ API fallback failed: {e}")
            return {}
    
    def store_bootstrap_data(self, bootstrap_data: Dict, gameweek: int):
        """Store bootstrap data with automatic indexing"""
        if not self.supabase:
            return
            
        try:
            # Mark previous data as not current
            self.supabase.table('bootstrap_data')\
                .update({'is_current': False})\
                .eq('gameweek', gameweek)\
                .execute()
            
            # Insert new data
            data_to_insert = {
                'gameweek': gameweek,
                'data_json': json.dumps(bootstrap_data),
                'is_current': True,
                'player_count': len(bootstrap_data.get('elements', [])),
                'team_count': len(bootstrap_data.get('teams', [])),
            }
            
            self.supabase.table('bootstrap_data').insert(data_to_insert).execute()
            
            # Store individual players for fast querying
            self._store_individual_players(bootstrap_data, gameweek)
            
        except Exception as e:
            print(f"❌ Error storing bootstrap data: {e}")
    
    def _store_individual_players(self, bootstrap_data: Dict, gameweek: int):
        """Store players individually for fast searches"""
        if not self.supabase:
            return
            
        try:
            players_data = []
            teams = {t['id']: t['name'] for t in bootstrap_data.get('teams', [])}
            positions = {p['id']: p['singular_name'] for p in bootstrap_data.get('element_types', [])}
            
            for player in bootstrap_data.get('elements', []):
                player_record = {
                    'player_id': player['id'],
                    'gameweek': gameweek,
                    'web_name': player['web_name'],
                    'first_name': player['first_name'],
                    'second_name': player['second_name'],
                    'team_name': teams.get(player['team'], ''),
                    'position_name': positions.get(player['element_type'], ''),
                    'price': player['now_cost'] / 10,
                    'total_points': player.get('total_points', 0),
                    'form': float(player.get('form', 0)),
                    'goals': player.get('goals_scored', 0),
                    'assists': player.get('assists', 0),
                    'clean_sheets': player.get('clean_sheets', 0),
                    'ownership': float(player.get('selected_by_percent', 0)),
                    'status': player.get('status', 'a'),
                    'searchable_text': self._create_searchable_text(player, teams, positions),
                }
                players_data.append(player_record)
            
            # Clear existing players for this gameweek
            self.supabase.table('players').delete().eq('gameweek', gameweek).execute()
            
            # Batch insert for performance
            batch_size = 100
            for i in range(0, len(players_data), batch_size):
                batch = players_data[i:i + batch_size]
                self.supabase.table('players').insert(batch).execute()
                
            print(f"✅ Stored {len(players_data)} players in Supabase")
            
        except Exception as e:
            print(f"❌ Error storing players: {e}")
    
    def _create_searchable_text(self, player: Dict, teams: Dict, positions: Dict) -> str:
        """Create searchable text for full-text search"""
        team_name = teams.get(player['team'], '')
        position_name = positions.get(player['element_type'], '')
        
        searchable = f"{player['web_name']} {player['first_name']} {player['second_name']} "
        searchable += f"{team_name} {position_name} "
        
        # Add performance descriptors
        points = player.get('total_points', 0)
        if points > 100:
            searchable += "excellent premium top "
        elif points > 50:
            searchable += "good solid "
        
        return searchable.lower()
    
    def search_players(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Fast player search using Supabase
        Replaces your entire RAG search system
        """
        if not self.supabase:
            return []
            
        try:
            # First try exact name matches
            response = self.supabase.table('players')\
                .select('*')\
                .or_(f"web_name.ilike.%{query}%,first_name.ilike.%{query}%,second_name.ilike.%{query}%")\
                .order('total_points', desc=True)\
                .limit(limit)\
                .execute()
            
            if response.data:
                return response.data
            
            # Fallback to searchable text
            response = self.supabase.table('players')\
                .select('*')\
                .ilike('searchable_text', f'%{query.lower()}%')\
                .order('total_points', desc=True)\
                .limit(limit)\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            print(f"❌ Error searching players: {e}")
            return []
    
    def get_players_by_criteria(self, team: str = None, position: str = None, 
                              price_min: float = None, price_max: float = None,
                              limit: int = 20) -> List[Dict]:
        """
        Fast filtered queries using Supabase indexes
        """
        if not self.supabase:
            return []
            
        try:
            query = self.supabase.table('players').select('*')
            
            if team:
                query = query.eq('team_name', team)
            if position:
                query = query.eq('position_name', position)
            if price_min:
                query = query.gte('price', price_min)
            if price_max:
                query = query.lte('price', price_max)
            
            response = query.order('total_points', desc=True).limit(limit).execute()
            return response.data or []
            
        except Exception as e:
            print(f"❌ Error filtering players: {e}")
            return []
    
    def get_statistical_leaders(self, stat: str, limit: int = 5) -> List[Dict]:
        """Get statistical leaders with automatic caching"""
        if not self.supabase:
            return []
            
        try:
            order_field = {
                'goals': 'goals',
                'assists': 'assists', 
                'points': 'total_points',
                'form': 'form'
            }.get(stat, 'total_points')
            
            response = self.supabase.table('players')\
                .select('*')\
                .order(order_field, desc=True)\
                .limit(limit)\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            print(f"❌ Error getting statistical leaders: {e}")
            return []
    
    def log_query_analytics(self, query: str, query_type: str, 
                          response_time: float, user_session: str = None):
        """Log query analytics for monitoring"""
        if not self.supabase:
            return
            
        try:
            analytics_data = {
                'query_text': query,
                'query_type': query_type,
                'response_time': response_time,
                'user_session': user_session or 'anonymous',
            }
            
            self.supabase.table('query_analytics').insert(analytics_data).execute()
            
        except Exception as e:
            print(f"❌ Error logging analytics: {e}")
    
    def get_performance_metrics(self, hours: int = 24) -> Dict:
        """Get performance metrics from Supabase"""
        if not self.supabase:
            return {'message': 'Supabase not available'}
            
        try:
            from datetime import datetime, timedelta
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Get query statistics
            response = self.supabase.table('query_analytics')\
                .select('query_type, response_time')\
                .gte('created_at', cutoff_time.isoformat())\
                .execute()
            
            if not response.data:
                return {'message': 'No data available'}
            
            # Calculate metrics
            total_queries = len(response.data)
            avg_response_time = sum(q['response_time'] for q in response.data) / total_queries
            
            query_types = {}
            for query in response.data:
                qtype = query['query_type']
                query_types[qtype] = query_types.get(qtype, 0) + 1
            
            return {
                'total_queries': total_queries,
                'average_response_time': round(avg_response_time, 3),
                'query_types': query_types,
                'time_period_hours': hours
            }
            
        except Exception as e:
            error_msg = self._handle_supabase_error(e)
            print(f"❌ Error getting metrics: {error_msg}")
            return {'error': error_msg}


# Global Supabase service instance
supabase_service = SupabaseFPLService()
