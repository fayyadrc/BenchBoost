import re
import requests
from collections import Counter
from typing import List, Dict, Optional
from .fpl_knowledge import FPL_SEARCHABLE_RULES, FPL_RULES_KNOWLEDGE

class FPLRAGHelper:
    def __init__(self):
        self.documents = []
        self.knowledge_doc = None
        self.is_indexed = False
    
    def simple_tokenize(self, text: str) -> List[str]:
        """Basic tokenization for similarity matching"""
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return [word for word in text.split() if len(word) > 2]
    
    def calculate_similarity(self, query_tokens: List[str], doc_tokens: List[str]) -> float:
        """Calculate TF-IDF-like similarity"""
        if not query_tokens or not doc_tokens:
            return 0.0
        
        query_counter = Counter(query_tokens)
        doc_counter = Counter(doc_tokens)
        
        intersection = set(query_tokens) & set(doc_tokens)
        if not intersection:
            return 0.0
        
        score = 0.0
        for word in intersection:
            tf_query = query_counter[word] / len(query_tokens)
            tf_doc = doc_counter[word] / len(doc_tokens)
            score += tf_query * tf_doc
        
        return score
    
    def index_players(self, bootstrap_data: Dict):
        """Create searchable index from FPL data"""
        if self.is_indexed:
            return
        
        players = bootstrap_data['elements']
        teams = {team['id']: team['name'] for team in bootstrap_data['teams']}
        positions = {pos['id']: pos['singular_name'] for pos in bootstrap_data['element_types']}
        
        self.documents = []
        
        # Add FPL rules knowledge as a searchable document
        self.knowledge_doc = {
            'text': FPL_SEARCHABLE_RULES,
            'tokens': self.simple_tokenize(FPL_SEARCHABLE_RULES),
            'type': 'knowledge',
            'data': FPL_RULES_KNOWLEDGE
        }
        
        # Index all players
        for player in players:
            team_name = teams.get(player['team'], 'Unknown')
            position_name = positions.get(player['element_type'], 'Unknown')
            price = float(player['now_cost']) / 10
            
            # Create rich searchable text
            doc_text = self._create_searchable_text(player, team_name, position_name, price)
            
            self.documents.append({
                'text': doc_text,
                'tokens': self.simple_tokenize(doc_text),
                'player_data': player,
                'team_name': team_name,
                'position_name': position_name,
                'price': price,
                'type': 'player'
            })
        
        # Add team-level aggregations
        self._add_team_aggregations(bootstrap_data)
        
        self.is_indexed = True
    
    def _add_team_aggregations(self, bootstrap_data: Dict):
        """Add team-level statistics as searchable documents"""
        teams = bootstrap_data['teams']
        players = bootstrap_data['elements']
        
        # Calculate team stats
        team_stats = {}
        for team in teams:
            team_id = team['id']
            team_name = team['name']
            team_players = [p for p in players if p['team'] == team_id]
            
            total_goals = sum(p.get('goals_scored', 0) for p in team_players)
            total_assists = sum(p.get('assists', 0) for p in team_players)
            total_clean_sheets = sum(p.get('clean_sheets', 0) for p in team_players if p['element_type'] in [1, 2])
            goals_conceded = sum(p.get('goals_conceded', 0) for p in team_players if p['element_type'] == 1)
            
            team_doc_text = f"""
            Team {team_name} statistics performance:
            Goals scored this season: {total_goals} goals attack attacking
            Assists provided: {total_assists} assists creative
            Clean sheets defensive: {total_clean_sheets} defense
            Goals conceded: {goals_conceded} defensive record
            Team strength squad depth
            """
            
            self.documents.append({
                'text': team_doc_text,
                'tokens': self.simple_tokenize(team_doc_text),
                'type': 'team',
                'team_name': team_name,
                'team_data': {
                    'goals': total_goals,
                    'assists': total_assists,
                    'clean_sheets': total_clean_sheets,
                    'goals_conceded': goals_conceded
                }
            })
    
    def _create_searchable_text(self, player: Dict, team_name: str, position_name: str, price: float) -> str:
        """Create rich searchable content for a player with enhanced name variations"""
        # Start with comprehensive name variations
        names_part = f"{player['web_name']} {player['first_name']} {player['second_name']}"
        
        # Add name variations for better matching
        name_variations = []
        
        # Add common nickname patterns
        first_name = player['first_name'].lower()
        last_name = player['second_name'].lower()
        web_name = player['web_name'].lower()
        
        # Common name patterns
        name_variations.extend([
            f"{first_name} {last_name}",
            last_name,
            web_name,
            first_name
        ])
        
        # Handle special character cases (accents, etc.)
        import unicodedata
        normalized_names = []
        for name in [player['web_name'], player['first_name'], player['second_name']]:
            normalized = unicodedata.normalize('NFD', name)
            ascii_name = normalized.encode('ascii', 'ignore').decode('ascii')
            if ascii_name != name:
                normalized_names.append(ascii_name.lower())
        
        name_variations.extend(normalized_names)
        
        parts = [
            names_part,
            " ".join(name_variations),
            f"{position_name} {team_name}",
            f"price {price} cost"
        ]

        # Add descriptive keywords based on performance
        points = player['total_points']
        form = float(player.get('form', 0))

        # Performance descriptors
        if points > 100:
            parts.append("excellent top class premium high scoring star player")
        elif points > 50:
            parts.append("good solid reliable consistent performer")
        elif points > 20:
            parts.append("decent average moderate option")
        else:
            parts.append("poor low scoring disappointing underperformer")

        # Form descriptors  
        if form > 5:
            parts.append("excellent form hot streak in form")
        elif form > 3:
            parts.append("good form decent recent performance")
        elif form < 2:
            parts.append("poor form cold streak out of form")

        # Value descriptors
        if price > 10:
            parts.append("expensive premium high priced costly")
        elif price < 5:
            parts.append("cheap budget affordable value bargain")

        # Position-specific keywords
        if player['element_type'] == 1:  # GK
            cs = player.get('clean_sheets', 0)
            saves = player.get('saves', 0)
            parts.append(f"goalkeeper keeper clean sheets {cs} saves {saves}")
            if cs > 10:
                parts.append("reliable shot stopper defensive")
                
        elif player['element_type'] == 2:  # Defender
            cs = player.get('clean_sheets', 0)
            goals = player.get('goals_scored', 0)
            parts.append(f"defender defence clean sheets {cs} goals {goals}")
            if goals > 2:
                parts.append("attacking defender goal threat set pieces")
                
        elif player['element_type'] == 3:  # Midfielder
            goals = player.get('goals_scored', 0)
            assists = player.get('assists', 0)
            parts.append(f"midfielder midfield goals {goals} assists {assists}")
            if goals > 8:
                parts.append("attacking midfielder goal scorer box to box")
            if assists > 5:
                parts.append("creative playmaker through balls crosses")
                
        elif player['element_type'] == 4:  # Forward
            goals = player.get('goals_scored', 0)
            parts.append(f"forward striker goals {goals}")
            if goals > 15:
                parts.append("prolific clinical finisher goal machine")
            elif goals > 8:
                parts.append("decent scorer reliable target man")

        return " ".join(parts)
    
    def enhanced_rag_search(self, query: str, bootstrap_data: Dict, top_k: int = 8) -> str:
        """
        Enhanced RAG that intelligently combines semantic search with function calls
        This is the new primary method that provides intelligent, contextual responses
        """
        # Index data if not already done
        if not self.is_indexed:
            self.index_players(bootstrap_data)

        query_tokens = self.simple_tokenize(query)
        query_lower = query.lower()

        # Step 1: Check for filtered statistical queries first (more specific)
        if self._is_filtered_statistical_query(query_lower):
            return self._handle_filtered_statistical_query(query, bootstrap_data)

        # Step 2: Check for statistical leader queries (general)
        if self._is_statistical_leader_query(query_lower):
            return self._handle_statistical_leader_query(query, bootstrap_data)

        # Step 3: Determine if we need specific player data
        player_data_needed = self._extract_player_mentions(query, bootstrap_data)
        
        # Step 4: Handle different query types intelligently
        if self._is_rules_query(query_lower):
            return self._handle_rules_query(query, query_tokens)
        
        elif self._is_strategy_query(query_lower):
            strategy_response = self._handle_strategy_query(query, query_tokens, bootstrap_data)
            # Enhance with specific player data if mentioned
            if player_data_needed:
                strategy_response += "\n\n" + self._get_contextual_player_data(player_data_needed, bootstrap_data)
            return strategy_response
        
        elif player_data_needed:
            # Player-focused query - provide intelligent analysis but avoid contamination
            return self._handle_clean_player_query(query, player_data_needed, bootstrap_data)
        
        else:
            # General query - semantic search with context
            return self._handle_general_semantic_query(query, query_tokens, bootstrap_data, top_k)
    
    def _is_statistical_leader_query(self, query_lower: str) -> bool:
        """Check if this is asking for statistical leaders"""
        leader_patterns = [
            "most assists", "highest assists", "top assists",
            "most goals", "highest goals", "top goals", 
            "highest xg", "most xg", "top xg",
            "most points", "highest points", "top points",
            "best value", "highest points per million",
            "most ownership", "highest ownership"
        ]
        return any(pattern in query_lower for pattern in leader_patterns)
    
    def _is_filtered_statistical_query(self, query_lower: str) -> bool:
        """Check if this is asking for filtered statistics (e.g., forwards under £7m)"""
        filter_patterns = [
            "under £", "under $", "below £", "below $",
            "over £", "over $", "above £", "above $",
            "forward", "defender", "midfielder", "goalkeeper"
        ]
        stat_patterns = ["highest", "most", "top", "best"]
        
        has_filter = any(pattern in query_lower for pattern in filter_patterns)
        has_stat = any(pattern in query_lower for pattern in stat_patterns)
        
        return has_filter and has_stat
    
    def _handle_statistical_leader_query(self, query: str, bootstrap_data: Dict) -> str:
        """Handle queries asking for statistical leaders"""
        query_lower = query.lower()
        players = bootstrap_data['elements']
        
        # Determine what stat we're looking for
        if "assists" in query_lower:
            stat_key = "assists"
            stat_name = "Assists"
            sorted_players = sorted(players, key=lambda x: x.get('assists', 0), reverse=True)[:5]
        elif "goals" in query_lower and "xg" not in query_lower:
            stat_key = "goals_scored"
            stat_name = "Goals"
            sorted_players = sorted(players, key=lambda x: x.get('goals_scored', 0), reverse=True)[:5]
        elif "xg" in query_lower:
            stat_key = "expected_goals"
            stat_name = "Expected Goals (xG)"
            sorted_players = sorted(players, key=lambda x: x.get('expected_goals', 0), reverse=True)[:5]
        elif "points" in query_lower:
            stat_key = "total_points"
            stat_name = "Points"
            sorted_players = sorted(players, key=lambda x: x.get('total_points', 0), reverse=True)[:5]
        elif "ownership" in query_lower:
            stat_key = "selected_by_percent"
            stat_name = "Ownership"
            sorted_players = sorted(players, key=lambda x: x.get('selected_by_percent', 0), reverse=True)[:5]
        else:
            return "❌ Could not determine which statistic you're asking about."
        
        # Build response
        teams = {team['id']: team['name'] for team in bootstrap_data['teams']}
        positions = {pos['id']: pos['singular_name'] for pos in bootstrap_data['element_types']}
        
        response = f"📊 **Top 5 Players by {stat_name}:**\n\n"
        
        for i, player in enumerate(sorted_players, 1):
            team_name = teams.get(player['team'], 'Unknown')
            position = positions.get(player['element_type'], 'Unknown')
            price = player['now_cost'] / 10
            stat_value = player.get(stat_key, 0)
            
            # Handle different stat value types
            try:
                if stat_key == "selected_by_percent":
                    stat_display = f"{float(stat_value)}%"
                elif stat_key == "expected_goals":
                    stat_display = f"{float(stat_value):.1f}"
                else:
                    stat_display = str(int(float(stat_value)))
            except (ValueError, TypeError):
                stat_display = str(stat_value)
            
            response += f"**{i}. {player['first_name']} {player['second_name']}** ({team_name} {position})\n"
            response += f"💰 £{price}m | 📊 {stat_display} {stat_name.lower()} | 📈 {player.get('form', 0)} form\n\n"
        
        return response
    
    def _handle_filtered_statistical_query(self, query: str, bootstrap_data: Dict) -> str:
        """Handle filtered statistical queries like 'forwards under £7m with highest xG'"""
        query_lower = query.lower()
        players = bootstrap_data['elements']
        
        # Apply position filter
        if "forward" in query_lower:
            players = [p for p in players if p['element_type'] == 4]
            position_name = "Forwards"
        elif "midfielder" in query_lower:
            players = [p for p in players if p['element_type'] == 3]
            position_name = "Midfielders"
        elif "defender" in query_lower:
            players = [p for p in players if p['element_type'] == 2]
            position_name = "Defenders"
        elif "goalkeeper" in query_lower:
            players = [p for p in players if p['element_type'] == 1]
            position_name = "Goalkeepers"
        else:
            position_name = "Players"
        
        # Apply price filter
        import re
        price_match = re.search(r'(under|below|over|above)\s*£?(\d+(?:\.\d+)?)', query_lower)
        if price_match:
            operator = price_match.group(1)
            price_limit = float(price_match.group(2))
            
            if operator in ['under', 'below']:
                players = [p for p in players if (p['now_cost'] / 10) < price_limit]
                price_filter = f"under £{price_limit}m"
            else:
                players = [p for p in players if (p['now_cost'] / 10) > price_limit]
                price_filter = f"over £{price_limit}m"
        else:
            price_filter = ""
        
        if not players:
            return f"❌ No {position_name.lower()} found {price_filter}"
        
        # Determine stat to sort by
        if "xg" in query_lower:
            stat_key = "expected_goals"
            stat_name = "xG"
            sorted_players = sorted(players, key=lambda x: x.get('expected_goals', 0), reverse=True)[:5]
        elif "goals" in query_lower:
            stat_key = "goals_scored"
            stat_name = "Goals"
            sorted_players = sorted(players, key=lambda x: x.get('goals_scored', 0), reverse=True)[:5]
        elif "assists" in query_lower:
            stat_key = "assists"
            stat_name = "Assists"
            sorted_players = sorted(players, key=lambda x: x.get('assists', 0), reverse=True)[:5]
        elif "points" in query_lower:
            stat_key = "total_points"
            stat_name = "Points"
            sorted_players = sorted(players, key=lambda x: x.get('total_points', 0), reverse=True)[:5]
        else:
            stat_key = "total_points"
            stat_name = "Points"
            sorted_players = sorted(players, key=lambda x: x.get('total_points', 0), reverse=True)[:5]
        
        # Build response
        teams = {team['id']: team['name'] for team in bootstrap_data['teams']}
        
        filter_text = f"{position_name} {price_filter}".strip()
        response = f"📊 **Top {filter_text} by {stat_name}:**\n\n"
        
        for i, player in enumerate(sorted_players, 1):
            team_name = teams.get(player['team'], 'Unknown')
            price = player['now_cost'] / 10
            stat_value = player.get(stat_key, 0)
            
            # Handle different stat value types
            try:
                if stat_key == "expected_goals":
                    stat_display = f"{float(stat_value):.1f}"
                else:
                    stat_display = str(int(float(stat_value)))
            except (ValueError, TypeError):
                stat_display = str(stat_value)
            
            response += f"**{i}. {player['first_name']} {player['second_name']}** ({team_name})\n"
            response += f"💰 £{price}m | 📊 {stat_display} {stat_name.lower()} | 📈 {player.get('form', 0)} form\n\n"
        
        return response
    
    def _handle_clean_player_query(self, query: str, players: list, bootstrap_data: Dict) -> str:
        """Handle player queries without contamination from irrelevant players"""
        if not players:
            return self.rag_fallback_search(query, bootstrap_data)
        
        query_lower = query.lower()
        
        # For ownership queries, prioritize showing just the main player
        if "ownership" in query_lower:
            if len(players) >= 1:
                player_info = players[0]  # Take the first (best) match
                player_data = next((p for p in bootstrap_data['elements'] if p['id'] == player_info['id']), None)
                
                if player_data:
                    ownership = player_data.get('selected_by_percent', 0)
                    return f"👥 **{player_info['full_name']} Ownership:** {ownership}% owned"
        
        # For team analysis queries
        is_team_query = any(word in query_lower for word in ['triple', 'three', 'multiple', 'team', 'forest', 'players'])
        
        if is_team_query and len(players) > 3:
            return self._handle_team_analysis_query(query, players, bootstrap_data)
        
        # For individual player analysis
        return self._handle_intelligent_player_query(query, players, bootstrap_data)
    
    def _extract_player_mentions(self, query: str, bootstrap_data: Dict) -> list:
        """Extract player names mentioned in the query"""
        from app.services.player_search import player_search_service
        
        players_found = []
        query_lower = query.lower()
        found_player_ids = set()  # Track unique players
        best_matches = {}  # Track best match for each player
        
        # Handle team-based queries (e.g., "forest players", "arsenal players")
        team_queries = self._extract_team_based_queries(query_lower, bootstrap_data)
        if team_queries:
            return team_queries
        
        words = query.split()
        
        # Try different combinations of words as potential player names
        # Prioritize longer matches (more specific)
        for length in range(2, 0, -1):  # Try 2-word combinations first, then 1-word
            for i in range(len(words) - length + 1):
                potential_name = " ".join(words[i:i + length])
                if len(potential_name) > 2:
                    try:
                        result = player_search_service.search_players(potential_name)
                        if result[0] is not None:
                            player_id = result[0]
                            # Keep longer, more specific matches
                            if player_id not in best_matches or len(potential_name) > len(best_matches[player_id]['query_mention']):
                                best_matches[player_id] = {
                                    'id': result[0],
                                    'web_name': result[1], 
                                    'full_name': result[2],
                                    'query_mention': potential_name
                                }
                    except:
                        continue
        
        # Convert best matches to list
        players_found = list(best_matches.values())
        return players_found
    
    def _extract_team_based_queries(self, query_lower: str, bootstrap_data: Dict) -> list:
        """Handle team-based queries like 'forest players', 'triple arsenal players'"""
        teams = {team['id']: team['name'] for team in bootstrap_data['teams']}
        
        # Comprehensive team name mappings including nicknames and abbreviations
        team_mappings = {}
        for team_id, team_name in teams.items():
            team_mappings[team_name.lower()] = team_id
            
            # Add comprehensive nicknames and abbreviations
            if team_name == "Arsenal":
                team_mappings["arsenal"] = team_id
                team_mappings["gunners"] = team_id
                team_mappings["gooners"] = team_id
                team_mappings["afc"] = team_id
            elif team_name == "Liverpool":
                team_mappings["liverpool"] = team_id
                team_mappings["pool"] = team_id
                team_mappings["reds"] = team_id
                team_mappings["lfc"] = team_id
                team_mappings["scousers"] = team_id
            elif team_name == "Man City":
                team_mappings["city"] = team_id
                team_mappings["manchester city"] = team_id
                team_mappings["mcfc"] = team_id
                team_mappings["citizens"] = team_id
                team_mappings["sky blues"] = team_id
            elif team_name == "Man Utd":
                team_mappings["united"] = team_id
                team_mappings["manchester united"] = team_id
                team_mappings["mufc"] = team_id
                team_mappings["red devils"] = team_id
                team_mappings["devils"] = team_id
            elif team_name == "Chelsea":
                team_mappings["chelsea"] = team_id
                team_mappings["blues"] = team_id
                team_mappings["cfc"] = team_id
                team_mappings["pensioners"] = team_id
            elif team_name == "Spurs":
                team_mappings["tottenham"] = team_id
                team_mappings["spurs"] = team_id
                team_mappings["thfc"] = team_id
                team_mappings["lilywhites"] = team_id
                team_mappings["coys"] = team_id
            elif team_name == "Newcastle":
                team_mappings["newcastle"] = team_id
                team_mappings["toon"] = team_id
                team_mappings["magpies"] = team_id
                team_mappings["nufc"] = team_id
                team_mappings["geordies"] = team_id
            elif team_name == "West Ham":
                team_mappings["west ham"] = team_id
                team_mappings["hammers"] = team_id
                team_mappings["irons"] = team_id
                team_mappings["whufc"] = team_id
            elif team_name == "Brighton":
                team_mappings["brighton"] = team_id
                team_mappings["seagulls"] = team_id
                team_mappings["albion"] = team_id
                team_mappings["bhafc"] = team_id
            elif team_name == "Aston Villa":
                team_mappings["aston villa"] = team_id
                team_mappings["villa"] = team_id
                team_mappings["villans"] = team_id
                team_mappings["avfc"] = team_id
            elif team_name == "Wolves":
                team_mappings["wolves"] = team_id
                team_mappings["wolverhampton"] = team_id
                team_mappings["wanderers"] = team_id
                team_mappings["wwfc"] = team_id
            elif team_name == "Crystal Palace":
                team_mappings["crystal palace"] = team_id
                team_mappings["palace"] = team_id
                team_mappings["eagles"] = team_id
                team_mappings["cpfc"] = team_id
            elif team_name == "Fulham":
                team_mappings["fulham"] = team_id
                team_mappings["cottagers"] = team_id
                team_mappings["ffc"] = team_id
            elif team_name == "Brentford":
                team_mappings["brentford"] = team_id
                team_mappings["bees"] = team_id
                team_mappings["bfc"] = team_id
            elif team_name == "Leicester":
                team_mappings["leicester"] = team_id
                team_mappings["foxes"] = team_id
                team_mappings["lcfc"] = team_id
            elif team_name == "Everton":
                team_mappings["everton"] = team_id
                team_mappings["toffees"] = team_id
                team_mappings["efc"] = team_id
                # Note: Removed "blues" mapping as Chelsea is more commonly called "the Blues"
            elif team_name == "Nott'm Forest":
                team_mappings["forest"] = team_id
                team_mappings["nottingham forest"] = team_id
                team_mappings["nottingham"] = team_id
                team_mappings["notts forest"] = team_id
                team_mappings["nffc"] = team_id
                team_mappings["reds"] = team_id  # Note: Liverpool also uses this
            elif team_name == "Bournemouth":
                team_mappings["bournemouth"] = team_id
                team_mappings["cherries"] = team_id
                team_mappings["afcb"] = team_id
            elif team_name == "Southampton":
                team_mappings["southampton"] = team_id
                team_mappings["saints"] = team_id
                team_mappings["sfc"] = team_id
            elif team_name == "Ipswich":
                team_mappings["ipswich"] = team_id
                team_mappings["tractor boys"] = team_id
                team_mappings["itfc"] = team_id
        
        # Check for team mentions in query
        mentioned_team_id = None
        mentioned_team_name = None
        
        # Handle ambiguous nicknames with context priority
        ambiguous_nicknames = {
            "blues": ["Chelsea", "Everton"],  # Chelsea more commonly called blues
            "reds": ["Liverpool", "Nott'm Forest"],  # Liverpool more commonly called reds
            "united": ["Man Utd"],  # Only one United in PL
            "city": ["Man City"]  # Only one City in PL
        }
        
        # First try exact matches (most specific)
        for team_key, team_id in team_mappings.items():
            if team_key in query_lower and len(team_key) > 3:  # Prefer longer matches
                mentioned_team_id = team_id
                mentioned_team_name = teams[team_id]
                print(f"🏟️ Found team reference: '{team_key}' -> {mentioned_team_name} (ID: {team_id})")
                break
        
        # If no specific match, handle ambiguous cases with priority
        if not mentioned_team_id:
            for nickname, possible_teams in ambiguous_nicknames.items():
                if nickname in query_lower:
                    # Use the first (most common) team for ambiguous nicknames
                    preferred_team = possible_teams[0]
                    for team_id, team_name in teams.items():
                        if team_name == preferred_team:
                            mentioned_team_id = team_id
                            mentioned_team_name = team_name
                            print(f"🏟️ Found ambiguous team reference: '{nickname}' -> {mentioned_team_name} (ID: {team_id}) [preferred]")
                            break
                    break
        
        # Final fallback to any match
        if not mentioned_team_id:
            for team_key, team_id in team_mappings.items():
                if team_key in query_lower:
                    mentioned_team_id = team_id
                    mentioned_team_name = teams[team_id]
                    print(f"🏟️ Found team reference: '{team_key}' -> {mentioned_team_name} (ID: {team_id})")
                    break
        
        if mentioned_team_id:
            # Get players from that team only
            team_players = [p for p in bootstrap_data['elements'] if p['team'] == mentioned_team_id]
            print(f"🔍 Found {len(team_players)} players from {mentioned_team_name}")
            
            # Convert to our player format
            players_found = []
            for player in team_players:
                players_found.append({
                    'id': player['id'],
                    'web_name': player['web_name'],
                    'full_name': f"{player['first_name']} {player['second_name']}",
                    'query_mention': mentioned_team_name,
                    'team_id': mentioned_team_id
                })
            
            return players_found
        
        return []
    
    def _handle_intelligent_player_query(self, query: str, players: list, bootstrap_data: Dict) -> str:
        """Handle player queries with intelligent analysis and context"""
        if not players:
            return self.rag_fallback_search(query, bootstrap_data)
        
        # Check if this is a team analysis query
        query_lower = query.lower()
        is_team_query = any(word in query_lower for word in ['triple', 'three', 'multiple', 'team', 'forest', 'players'])
        
        if is_team_query and len(players) > 3:
            return self._handle_team_analysis_query(query, players, bootstrap_data)
        
        response = "🎯 **Player Analysis:**\n\n"
        
        for player_info in players[:3]:  # Limit to 3 players to avoid overwhelming
            player_data = next((p for p in bootstrap_data['elements'] if p['id'] == player_info['id']), None)
            if not player_data:
                continue
                
            # Get team and position info
            teams = {team['id']: team['name'] for team in bootstrap_data['teams']}
            positions = {pos['id']: pos['singular_name'] for pos in bootstrap_data['element_types']}
            
            team_name = teams.get(player_data['team'], 'Unknown')
            position = positions.get(player_data['element_type'], 'Unknown')
            price = float(player_data['now_cost']) / 10
            points = player_data['total_points']
            form = float(player_data.get('form', 0))
            ownership = player_data.get('selected_by_percent', 0)
            
            # Intelligent analysis based on query context
            analysis = self._generate_player_analysis(query, player_data, team_name, position, price, points, form, ownership)
            
            response += f"**{player_info['full_name']}** ({team_name} {position})\n"
            response += f"💰 £{price}m | 📊 {points} pts | 📈 {form} form | 👥 {ownership}% owned\n"
            response += f"{analysis}\n\n"
        
        return response
    
    def _handle_team_analysis_query(self, query: str, players: list, bootstrap_data: Dict) -> str:
        """Handle queries about multiple players from the same team"""
        query_lower = query.lower()
        
        if not players:
            return "❌ No team players found for analysis"
        
        # Verify all players are from the same team
        team_ids = set()
        for player_info in players:
            player_data = next((p for p in bootstrap_data['elements'] if p['id'] == player_info['id']), None)
            if player_data:
                team_ids.add(player_data['team'])
        
        if len(team_ids) > 1:
            print(f"⚠️ Warning: Players from multiple teams found: {team_ids}")
        
        # Get team info from first player
        first_player = next((p for p in bootstrap_data['elements'] if p['id'] == players[0]['id']), None)
        if not first_player:
            return "❌ Player data not found"
        
        teams = {team['id']: team['name'] for team in bootstrap_data['teams']}
        team_name = teams.get(first_player['team'], 'Unknown')
        team_id = first_player['team']
        
        print(f"🏟️ Analyzing team: {team_name} (ID: {team_id})")
        print(f"📊 Found {len(players)} players from this team")
        
        response = f"🏟️ **{team_name} Players Analysis:**\n\n"
        
        # Filter players to only include those from the correct team
        team_players = []
        for player_info in players:
            player_data = next((p for p in bootstrap_data['elements'] if p['id'] == player_info['id']), None)
            if player_data and player_data['team'] == team_id:
                team_players.append(player_info)
        
        # Focus on top players by points
        sorted_players = sorted(team_players, key=lambda x: self._get_player_points(x['id'], bootstrap_data), reverse=True)
        
        total_cost = 0
        total_points = 0
        
        for i, player_info in enumerate(sorted_players[:5]):  # Top 5 players
            player_data = next((p for p in bootstrap_data['elements'] if p['id'] == player_info['id']), None)
            if not player_data:
                continue
            
            positions = {pos['id']: pos['singular_name'] for pos in bootstrap_data['element_types']}
            position = positions.get(player_data['element_type'], 'Unknown')
            price = float(player_data['now_cost']) / 10
            points = player_data['total_points']
            form = float(player_data.get('form', 0))
            
            total_cost += price
            total_points += points
            
            # Star ratings based on performance
            stars = "⭐" * min(5, max(1, int(points / 20)))
            
            response += f"**{i+1}. {player_info['full_name']}** ({position}) {stars}\n"
            response += f"💰 £{price}m | 📊 {points} pts | 📈 {form} form\n\n"
        
        # Team strategy advice
        if 'triple' in query_lower or 'three' in query_lower:
            response += "💡 **Triple Up Strategy:**\n"
            avg_points = total_points / min(3, len(sorted_players)) if sorted_players else 0
            if avg_points > 40:
                response += "✅ Strong team for tripling - good point returns across players\n"
            elif avg_points > 20:
                response += "📊 Moderate team for tripling - decent returns but consider alternatives\n"
            else:
                response += "⚠️ Consider carefully - mixed performance from team players\n"
            
            response += f"💰 Total cost for top 3: £{total_cost:.1f}m\n"
            response += f"📊 Average points: {avg_points:.1f} per player\n"
        
        return response
    
    def _get_player_points(self, player_id: int, bootstrap_data: Dict) -> int:
        """Helper to get player points"""
        player = next((p for p in bootstrap_data['elements'] if p['id'] == player_id), None)
        return player['total_points'] if player else 0
    
    def _generate_player_analysis(self, query: str, player_data: Dict, team_name: str, position: str, price: float, points: int, form: float, ownership: float) -> str:
        """Generate intelligent analysis based on query context and player stats"""
        query_lower = query.lower()
        analysis_parts = []
        
        # Context-aware analysis
        if 'worth' in query_lower or 'buy' in query_lower or 'transfer' in query_lower:
            if form > 4 and points > 30:
                analysis_parts.append("✅ Strong transfer target - excellent form and points return")
            elif price < 6 and points > 20:
                analysis_parts.append("💰 Great value pick - solid points at budget price")
            elif form < 2:
                analysis_parts.append("⚠️ Consider avoiding - poor recent form")
            else:
                analysis_parts.append("📊 Decent option - monitor fixtures and form")
        
        if 'differential' in query_lower or 'template' in query_lower:
            if ownership < 10:
                analysis_parts.append(f"🎯 Excellent differential - only {ownership}% ownership")
            elif ownership > 30:
                analysis_parts.append(f"📈 Template player - {ownership}% ownership, consider carefully")
        
        if 'captain' in query_lower:
            goals = player_data.get('goals_scored', 0)
            if goals > 5 and form > 4:
                analysis_parts.append("🏆 Strong captaincy option - consistent scorer in good form")
            elif position == 'Forward' and goals < 3:
                analysis_parts.append("⚠️ Risky captain choice - low goal output for a forward")
        
        # Default analysis if no specific context
        if not analysis_parts:
            if form > 4:
                analysis_parts.append("📈 In excellent form - trending upward")
            elif form < 2:
                analysis_parts.append("📉 Poor form - avoid for now")
            
            if points > 50:
                analysis_parts.append("⭐ Premium option with strong season stats")
            elif points > 20:
                analysis_parts.append("✅ Solid contributor this season")
        
        return " | ".join(analysis_parts) if analysis_parts else "📊 Monitor performance and fixtures"
    
    def _handle_general_semantic_query(self, query: str, query_tokens: List[str], bootstrap_data: Dict, top_k: int) -> str:
        """Handle general queries with semantic understanding"""
        # Use existing semantic search but enhance the response
        results = []
        for doc in self.documents:
            if doc['type'] == 'player':
                similarity = self.calculate_similarity(query_tokens, doc['tokens'])
                if similarity > 0.01:  # Lower threshold for general queries
                    doc_copy = doc.copy()
                    doc_copy['similarity_score'] = similarity
                    results.append(doc_copy)

        if not results:
            return "🤔 I couldn't find specific information for that query. Try asking about specific players, fixtures, or FPL strategy."

        # Sort and limit results
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        results = results[:top_k]

        # Format with intelligence
        response = f"🧠 **Based on your query '{query}':**\n\n"
        response += self._format_intelligent_results(results, query)
        
        return response
    
    def _format_intelligent_results(self, results: List[Dict], query: str) -> str:
        """Format results with intelligent context"""
        formatted = ""
        query_lower = query.lower()
        
        # Group by relevance and add context
        high_relevance = [r for r in results if r['similarity_score'] > 0.1]
        medium_relevance = [r for r in results if 0.05 <= r['similarity_score'] <= 0.1]
        
        if high_relevance:
            formatted += "**Top Matches:**\n"
            for i, result in enumerate(high_relevance[:3], 1):
                player_data = result['player_data']
                team_name = result['team_name']
                position = result['position_name']
                price = result['price']
                
                formatted += f"{i}. **{player_data['web_name']}** ({team_name} {position})\n"
                formatted += f"   £{price}m | {player_data['total_points']} pts | {player_data.get('form', 0)} form\n"
                
                # Add contextual insight
                if 'cheap' in query_lower and price < 6:
                    formatted += "   💰 Great budget option\n"
                elif 'premium' in query_lower and price > 10:
                    formatted += "   ⭐ Premium player\n"
                elif 'form' in query_lower:
                    form = float(player_data.get('form', 0))
                    if form > 4:
                        formatted += "   📈 Excellent recent form\n"
                    elif form < 2:
                        formatted += "   📉 Struggling recently\n"
                
                formatted += "\n"
        
        return formatted
    
    def _get_contextual_player_data(self, players: list, bootstrap_data: Dict) -> str:
        """Get contextual player data for strategy responses"""
        if not players:
            return ""
        
        context = "**Relevant Players:**\n"
        for player_info in players[:2]:  # Limit to avoid overwhelming
            player_data = next((p for p in bootstrap_data['elements'] if p['id'] == player_info['id']), None)
            if player_data:
                teams = {team['id']: team['name'] for team in bootstrap_data['teams']}
                team_name = teams.get(player_data['team'], 'Unknown')
                price = float(player_data['now_cost']) / 10
                points = player_data['total_points']
                
                context += f"• **{player_info['full_name']}** ({team_name}) - £{price}m, {points} pts\n"
        
        return context
        """
        Enhanced RAG fallback with knowledge base support and improved player matching
        """
        # Index data if not already done
        if not self.is_indexed:
            self.index_players(bootstrap_data)

        query_tokens = self.simple_tokenize(query)
        query_lower = query.lower()

        # Check if this is a rules/knowledge query first
        if self._is_rules_query(query_lower):
            return self._handle_rules_query(query, query_tokens)

        # Check if this is a strategy query
        if self._is_strategy_query(query_lower):
            return self._handle_strategy_query(query, query_tokens, bootstrap_data)

        # Check if this is a team statistics query
        if self._is_team_stats_query(query_lower):
            return self._handle_team_stats_query(query, query_tokens, bootstrap_data)

        # Enhanced player search with exact name matching priority
        results = []
        exact_name_matches = []
        
        # First pass: Look for exact name matches
        for doc in self.documents:
            if doc['type'] == 'player':
                player_data = doc['player_data']
                web_name = player_data['web_name'].lower()
                full_name = f"{player_data['first_name']} {player_data['second_name']}".lower()
                
                # Check for exact matches first (higher priority)
                if (query_lower == web_name or 
                    query_lower == player_data['second_name'].lower() or
                    query_lower in web_name or
                    any(word in [web_name, player_data['second_name'].lower()] for word in query_lower.split())):
                    doc_copy = doc.copy()
                    doc_copy['similarity_score'] = 1.0  # Highest priority
                    exact_name_matches.append(doc_copy)
                    continue
                
                # Regular similarity matching
                similarity = self.calculate_similarity(query_tokens, doc['tokens'])
                if similarity > 0.005:  # Minimum threshold
                    doc_copy = doc.copy()
                    doc_copy['similarity_score'] = similarity
                    results.append(doc_copy)

        # Combine results: exact matches first, then similarity matches
        all_results = exact_name_matches + results
        
        if not all_results:
            return ""

        # Sort by similarity (exact matches will be at top)
        all_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        all_results = all_results[:top_k]

        # Format for LLM
        return self._format_player_results(query, all_results)
    
    def _is_rules_query(self, query_lower: str) -> bool:
        """Check if query is about FPL rules"""
        # Strong rules indicators (high priority)
        strong_rules_keywords = [
            'how many points', 'points for', 'points penalty', 'points do you get',
            'how many transfers', 'maximum squad', 'squad size', 'team limit',
            'starting budget', 'how much money', 'free transfers',
            'yellow card penalty', 'red card penalty', 'clean sheet points',
            'assist points', 'goal points', 'save points', 'transfer rules',
            'transfer deadline', 'how transfers work', 'wildcard rules',
            'free hit rules', 'triple captain rules', 'bench boost rules',
            'what are the rules', 'how do transfers', 'rules for transfers'
        ]
        
        # Medium rules indicators
        medium_rules_keywords = [
            'scoring system', 'penalty', 'captain', 'triple captain', 
            'bench boost', 'wildcard', 'free hit', 'transfers per week',
            'budget', 'money', 'cost of transfer', 'transfer cost'
        ]
        
        # Check strong indicators first (high confidence)
        if any(keyword in query_lower for keyword in strong_rules_keywords):
            return True
            
        # Check medium indicators (but not if it looks like a player query OR strategy query)
        if any(keyword in query_lower for keyword in medium_rules_keywords):
            # Don't treat as rules if it contains specific player indicators
            player_indicators = ['who', 'which player', 'best', 'top', 'under']
            # Don't treat as rules if it contains strategy indicators
            strategy_indicators = ['differential', 'template', 'value', 'budget', 'should i use', 'options',
                                 'timing', 'advice', 'strategy', 'help', 'decision', 'when should',
                                 'guide', 'should i', 'use my', 'play my', 'activate']
            
            if (not any(indicator in query_lower for indicator in player_indicators) and
                not any(indicator in query_lower for indicator in strategy_indicators)):
                return True
        
        return False
    
    def _is_strategy_query(self, query_lower: str) -> bool:
        """Check if query is about FPL strategy concepts"""
        strategy_keywords = [
            'differential', 'differentials', 'template', 'punts', 'punt picks',
            'value picks', 'budget options', 'budget option', 'cheap gems', 'under the radar',
            'low ownership', 'essential players', 'must have', 'nailed on',
            'rotation risk', 'form players', 'in form', 'good form',
            'captain choice', 'captaincy', 'who to captain', 'triple captain',
            'transfer strategy', 'when to wildcard', 'chip strategy',
            'who should i captain', 'captain recommendations', 'transfer targets',
            'should i use', 'wildcard this week', 'should i wildcard',
            'use my wildcard', 'should i use my wildcard', 'wildcard now',
            'play my wildcard', 'activate wildcard', 'wildcard timing',
            'best time to wildcard', 'when should i wildcard',
            'wildcard advice', 'wildcard strategy', 'wildcard decision',
            'wildcard help', 'timing wildcard', 'when wildcard'
        ]
        return any(keyword in query_lower for keyword in strategy_keywords)

    def _is_team_stats_query(self, query_lower: str) -> bool:
        """Check if query is about team statistics"""
        team_keywords = [
            'which team', 'what team', 'team has scored', 'team performance',
            'defensive record', 'most goals', 'best defense', 'clean sheets'
        ]
        return any(keyword in query_lower for keyword in team_keywords)
    
    def _handle_rules_query(self, query: str, query_tokens: List[str]) -> str:
        """Handle FPL rules and knowledge queries"""
        query_lower = query.lower()
        
        # Provide specific answers for common scoring questions
        if 'assist' in query_lower and 'points' in query_lower:
            return f"""
📊 FPL SCORING: ASSISTS

**Answer: {FPL_RULES_KNOWLEDGE['scoring_system']['assists']} points**

Assists in FPL:
• Any player who provides an assist gets {FPL_RULES_KNOWLEDGE['scoring_system']['assists']} points
• This applies to all positions (defenders, midfielders, forwards)
• Goalkeepers can theoretically get assists too (rare but possible)

Additional Scoring Info:
• Goals: GK/DEF = {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['defender']} pts, MID = {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['midfielder']} pts, FWD = {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['forward']} pts
• Clean Sheet: GK/DEF = {FPL_RULES_KNOWLEDGE['scoring_system']['clean_sheet']['defender']} pts, MID = {FPL_RULES_KNOWLEDGE['scoring_system']['clean_sheet']['midfielder']} pt
"""

        elif 'transfer' in query_lower and ('rules' in query_lower or 'how' in query_lower or 'work' in query_lower):
            return f"""
🔄 FPL TRANSFER RULES & SYSTEM

**Key Transfer Rules:**

**Free Transfers:**
• You get {FPL_RULES_KNOWLEDGE['transfer_rules']['free_transfers']} free transfer per gameweek
• Unused transfers can be banked: {FPL_RULES_KNOWLEDGE['transfer_rules']['transfer_banking']}
• Transfer deadline: {FPL_RULES_KNOWLEDGE['transfer_rules']['transfer_deadline']}

**Point Deductions:**
• Extra transfers cost {FPL_RULES_KNOWLEDGE['transfer_rules']['point_deduction']} points each
• No limit on transfers, but each costs {FPL_RULES_KNOWLEDGE['transfer_rules']['point_deduction']} points

**Special Chips:**
• Wildcard: {FPL_RULES_KNOWLEDGE['transfer_rules']['wildcard_transfers']} transfers, no point penalty
• Free Hit: {FPL_RULES_KNOWLEDGE['transfer_rules']['free_hit_transfers']}, team reverts next week

**Price Changes:**
• Players' prices change {FPL_RULES_KNOWLEDGE['transfer_rules']['price_changes']}
• Based on net transfers in/out
• Price changes at 1:30am GMT daily
"""

        elif 'goal' in query_lower and 'midfielder' in query_lower:
            return f"""
📊 FPL SCORING: MIDFIELDER GOALS

**Answer: {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['midfielder']} points**

Goal Points by Position:
• Goalkeeper: {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['goalkeeper']} points
• Defender: {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['defender']} points  
• Midfielder: {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['midfielder']} points
• Forward: {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['forward']} points

Why fewer points for forwards? Because goals are expected from them!
"""

        elif 'clean sheet' in query_lower and 'defender' in query_lower:
            return f"""
� FPL SCORING: DEFENDER CLEAN SHEETS

**Answer: {FPL_RULES_KNOWLEDGE['scoring_system']['clean_sheet']['defender']} points**

Clean Sheet Points:
• Goalkeeper: {FPL_RULES_KNOWLEDGE['scoring_system']['clean_sheet']['goalkeeper']} points
• Defender: {FPL_RULES_KNOWLEDGE['scoring_system']['clean_sheet']['defender']} points
• Midfielder: {FPL_RULES_KNOWLEDGE['scoring_system']['clean_sheet']['midfielder']} point
• Forward: {FPL_RULES_KNOWLEDGE['scoring_system']['clean_sheet']['forward']} points

Clean sheets are achieved when a team doesn't concede any goals in a match.
"""

        elif 'yellow card' in query_lower:
            return f"""
📊 FPL SCORING: YELLOW CARD PENALTY

**Answer: {FPL_RULES_KNOWLEDGE['scoring_system']['cards']['yellow']} point**

Card Penalties:
• Yellow Card: {FPL_RULES_KNOWLEDGE['scoring_system']['cards']['yellow']} point
• Red Card: {FPL_RULES_KNOWLEDGE['scoring_system']['cards']['red']} points

Note: These are point deductions, so they reduce your player's total score.
"""

        elif 'saves' in query_lower and ('goalkeeper' in query_lower or 'keeper' in query_lower):
            return f"""
📊 FPL SCORING: GOALKEEPER SAVES

**Answer: {FPL_RULES_KNOWLEDGE['scoring_system']['saves']['goalkeeper']} point per {3} saves**

Goalkeeper Scoring:
• Saves: {FPL_RULES_KNOWLEDGE['scoring_system']['saves']['goalkeeper']} point for every 3 saves made
• Clean Sheet: {FPL_RULES_KNOWLEDGE['scoring_system']['clean_sheet']['goalkeeper']} points
• Goal: {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['goalkeeper']} points (rare!)
• Goals Conceded: {FPL_RULES_KNOWLEDGE['scoring_system']['goals_conceded']['goalkeeper']} point per 2 goals conceded

So a goalkeeper needs to make 3, 6, 9, etc. saves to earn 1, 2, 3, etc. points.
"""

        # Fallback to general rules information
        similarity = self.calculate_similarity(query_tokens, self.knowledge_doc['tokens'])
        
        if similarity > 0.01:  # Rules threshold
            return f"""
🧠 FPL RULES & KNOWLEDGE:
Query: '{query}'

🏆 SCORING SYSTEM:
- Goal by midfielder: {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['midfielder']} points
- Goal by defender: {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['defender']} points
- Assist: {FPL_RULES_KNOWLEDGE['scoring_system']['assists']} points
- Clean sheet (DEF): {FPL_RULES_KNOWLEDGE['scoring_system']['clean_sheet']['defender']} points
- Yellow card: {FPL_RULES_KNOWLEDGE['scoring_system']['cards']['yellow']} point
- Goalkeeper saves: {FPL_RULES_KNOWLEDGE['scoring_system']['saves']['goalkeeper']} point per 3 saves

💡 TEAM RULES:
- Maximum players from one team: {FPL_RULES_KNOWLEDGE['team_rules']['max_players_per_team']}
- Squad size: {FPL_RULES_KNOWLEDGE['team_rules']['squad_size']} players
- Starting budget: £{FPL_RULES_KNOWLEDGE['team_rules']['starting_budget']}m
- Free transfers per week: {FPL_RULES_KNOWLEDGE['team_rules']['free_transfers_per_week']}
- Extra transfer cost: {FPL_RULES_KNOWLEDGE['team_rules']['transfer_cost']} points
"""
        
        return ""
    
    def _handle_strategy_query(self, query: str, query_tokens: List[str], bootstrap_data: Dict) -> str:
        """Handle FPL strategy and tactical queries"""
        query_lower = query.lower()
        
        # Handle differential player queries
        if 'differential' in query_lower or 'low ownership' in query_lower:
            return self._find_differential_players(bootstrap_data)
        
        # Handle template/essential player queries  
        if 'template' in query_lower or 'essential' in query_lower or 'must have' in query_lower:
            return self._find_template_players(bootstrap_data)
        
        # Handle value/budget option queries
        if 'value' in query_lower or 'budget' in query_lower or 'cheap' in query_lower:
            return self._find_value_players(bootstrap_data)
        
        # Handle form player queries
        if 'form' in query_lower or 'in form' in query_lower:
            return self._find_form_players(bootstrap_data)
        
        # Handle captaincy queries
        if 'captain' in query_lower and ('who' in query_lower or 'choice' in query_lower or 'recommend' in query_lower):
            return self._suggest_captains(bootstrap_data)
        
        # Handle transfer target queries
        if 'transfer' in query_lower and ('target' in query_lower or 'best' in query_lower):
            return self._find_transfer_targets(bootstrap_data)
        
        # Handle wildcard decision queries
        if 'wildcard' in query_lower and ('should' in query_lower or 'use' in query_lower or 
                                         'timing' in query_lower or 'advice' in query_lower or
                                         'decision' in query_lower or 'help' in query_lower or
                                         'when' in query_lower or 'strategy' in query_lower):
            return self._wildcard_advice(bootstrap_data)
        
        # Handle general budget queries
        if 'budget' in query_lower and ('option' in query_lower or 'pick' in query_lower):
            return self._find_value_players(bootstrap_data)
        
        # Default strategy response with general concepts
        return f"""
🎯 FPL STRATEGY CONCEPTS

**Differential Players:**
{FPL_RULES_KNOWLEDGE['strategy_concepts']['differential_players']['definition']}
• Ownership: {FPL_RULES_KNOWLEDGE['strategy_concepts']['differential_players']['ownership_threshold']}
• Risk/Reward: {FPL_RULES_KNOWLEDGE['strategy_concepts']['differential_players']['risk_reward']}

**Template Players:**  
{FPL_RULES_KNOWLEDGE['strategy_concepts']['template_players']['definition']}
• Ownership: {FPL_RULES_KNOWLEDGE['strategy_concepts']['template_players']['ownership_threshold']}

**Value Picks:**
{FPL_RULES_KNOWLEDGE['strategy_concepts']['value_picks']['definition']}
• Price Range: {FPL_RULES_KNOWLEDGE['strategy_concepts']['value_picks']['price_range']}

**Form Analysis:**
• Short-term: {FPL_RULES_KNOWLEDGE['strategy_concepts']['form_analysis']['short_term']}
• Factors: {FPL_RULES_KNOWLEDGE['strategy_concepts']['form_analysis']['factors']}
"""
    
    def _find_differential_players(self, bootstrap_data: Dict) -> str:
        """Find low ownership differential players"""
        players = bootstrap_data['elements']
        teams_map = {t['id']: t['name'] for t in bootstrap_data['teams']}
        positions_map = {p['id']: p['singular_name'] for p in bootstrap_data['element_types']}
        
        # Find players with ownership < 15% and decent points
        differentials = []
        for player in players:
            ownership = float(player.get('selected_by_percent', 0))
            points = player['total_points']
            price = float(player['now_cost']) / 10
            
            if ownership < 15.0 and points > 15:  # Low ownership but scoring
                differentials.append({
                    'name': player['web_name'],
                    'team': teams_map.get(player['team'], 'Unknown'),
                    'position': positions_map.get(player['element_type'], 'Unknown'),
                    'ownership': ownership,
                    'points': points,
                    'price': price,
                    'form': float(player.get('form', 0))
                })
        
        # Sort by points/ownership ratio
        differentials.sort(key=lambda x: x['points'] / max(x['ownership'], 1), reverse=True)
        
        result = "🎯 DIFFERENTIAL PLAYERS (Low Ownership, High Potential)\n\n"
        for i, player in enumerate(differentials[:5], 1):
            result += f"{i}. **{player['name']}** ({player['position']}, {player['team']})\n"
            result += f"   Price: £{player['price']}m | Ownership: {player['ownership']:.1f}%\n"
            result += f"   Points: {player['points']} | Form: {player['form']}\n\n"
        
        return result
    
    def _find_template_players(self, bootstrap_data: Dict) -> str:
        """Find high ownership template players"""
        players = bootstrap_data['elements']
        teams_map = {t['id']: t['name'] for t in bootstrap_data['teams']}
        positions_map = {p['id']: p['singular_name'] for p in bootstrap_data['element_types']}
        
        # Find players with ownership > 40%
        templates = []
        for player in players:
            ownership = float(player.get('selected_by_percent', 0))
            if ownership > 40.0:
                templates.append({
                    'name': player['web_name'],
                    'team': teams_map.get(player['team'], 'Unknown'),
                    'position': positions_map.get(player['element_type'], 'Unknown'),
                    'ownership': ownership,
                    'points': player['total_points'],
                    'price': float(player['now_cost']) / 10
                })
        
        # Sort by ownership
        templates.sort(key=lambda x: x['ownership'], reverse=True)
        
        result = "👑 TEMPLATE PLAYERS (High Ownership Essential Picks)\n\n"
        for i, player in enumerate(templates[:6], 1):
            result += f"{i}. **{player['name']}** ({player['position']}, {player['team']})\n"
            result += f"   Ownership: {player['ownership']:.1f}% | Price: £{player['price']}m\n"
            result += f"   Points: {player['points']}\n\n"
        
        return result
    
    def _find_value_players(self, bootstrap_data: Dict) -> str:
        """Find budget players with good returns"""
        players = bootstrap_data['elements']
        teams_map = {t['id']: t['name'] for t in bootstrap_data['teams']}
        positions_map = {p['id']: p['singular_name'] for p in bootstrap_data['element_types']}
        
        # Find players under £6m with good points per million
        value_picks = []
        for player in players:
            price = float(player['now_cost']) / 10
            points = player['total_points']
            
            if price <= 6.0 and points > 10:  # Cheap but productive
                value_picks.append({
                    'name': player['web_name'],
                    'team': teams_map.get(player['team'], 'Unknown'),
                    'position': positions_map.get(player['element_type'], 'Unknown'),
                    'price': price,
                    'points': points,
                    'ppm': points / price,  # Points per million
                    'form': float(player.get('form', 0))
                })
        
        # Sort by points per million
        value_picks.sort(key=lambda x: x['ppm'], reverse=True)
        
        result = "💰 VALUE PLAYERS (Budget Options with Returns)\n\n"
        for i, player in enumerate(value_picks[:6], 1):
            result += f"{i}. **{player['name']}** ({player['position']}, {player['team']})\n"
            result += f"   Price: £{player['price']}m | Points: {player['points']}\n"
            result += f"   Value: {player['ppm']:.1f} pts/£m | Form: {player['form']}\n\n"
        
        return result
    
    def _find_form_players(self, bootstrap_data: Dict) -> str:
        """Find players in good recent form"""
        players = bootstrap_data['elements']
        teams_map = {t['id']: t['name'] for t in bootstrap_data['teams']}
        positions_map = {p['id']: p['singular_name'] for p in bootstrap_data['element_types']}
        
        # Find players with form > 6.0
        form_players = []
        for player in players:
            form = float(player.get('form', 0))
            if form > 6.0:
                form_players.append({
                    'name': player['web_name'],
                    'team': teams_map.get(player['team'], 'Unknown'),
                    'position': positions_map.get(player['element_type'], 'Unknown'),
                    'form': form,
                    'points': player['total_points'],
                    'price': float(player['now_cost']) / 10,
                    'ownership': float(player.get('selected_by_percent', 0))
                })
        
        # Sort by form
        form_players.sort(key=lambda x: x['form'], reverse=True)
        
        result = "🔥 PLAYERS IN FORM (Recent Strong Performance)\n\n"
        for i, player in enumerate(form_players[:6], 1):
            result += f"{i}. **{player['name']}** ({player['position']}, {player['team']})\n"
            result += f"   Form: {player['form']} | Price: £{player['price']}m\n"
            result += f"   Points: {player['points']} | Ownership: {player['ownership']:.1f}%\n\n"
        
        return result
    
    def _suggest_captains(self, bootstrap_data: Dict) -> str:
        """Suggest captain options based on form and fixtures"""
        players = bootstrap_data['elements']
        teams_map = {t['id']: t['name'] for t in bootstrap_data['teams']}
        positions_map = {p['id']: p['singular_name'] for p in bootstrap_data['element_types']}
        
        # Get current gameweek
        current_gw = None
        for event in bootstrap_data['events']:
            if event['is_current']:
                current_gw = event['id']
                break
        if not current_gw:
            current_gw = max([e['id'] for e in bootstrap_data['events'] if e['finished']]) + 1
        
        # Get fixtures for current gameweek
        try:
            fixtures_response = requests.get(f'https://fantasy.premierleague.com/api/fixtures/?event={current_gw}')
            fixtures = fixtures_response.json() if fixtures_response.status_code == 200 else []
        except:
            fixtures = []
        
        # Create team difficulty mapping
        team_difficulty = {}
        for fixture in fixtures:
            home_team = fixture['team_h']
            away_team = fixture['team_a']
            home_difficulty = fixture.get('team_h_difficulty', 3)
            away_difficulty = fixture.get('team_a_difficulty', 3)
            
            team_difficulty[home_team] = {
                'opponent': teams_map.get(away_team, 'Unknown'),
                'venue': 'H',
                'difficulty': home_difficulty
            }
            team_difficulty[away_team] = {
                'opponent': teams_map.get(home_team, 'Unknown'), 
                'venue': 'A',
                'difficulty': away_difficulty
            }
        
        # Find premium players with good form for captaincy
        captain_options = []
        for player in players:
            price = float(player['now_cost']) / 10
            form = float(player.get('form', 0))
            points = player['total_points']
            
            # Premium players (over £9m) with decent form
            if price > 9.0 and form > 4.0:
                team_id = player['team']
                fixture_info = team_difficulty.get(team_id, {
                    'opponent': 'Unknown',
                    'venue': 'H',
                    'difficulty': 3
                })
                
                # Calculate captaincy score (form + fixture ease)
                fixture_ease = 6 - fixture_info['difficulty']  # Invert difficulty (5=easy, 1=hard)
                captaincy_score = form + (fixture_ease * 0.5)  # Weight fixtures lower than form
                
                captain_options.append({
                    'name': player['web_name'],
                    'team': teams_map.get(player['team'], 'Unknown'),
                    'position': positions_map.get(player['element_type'], 'Unknown'),
                    'form': form,
                    'points': points,
                    'price': price,
                    'ownership': float(player.get('selected_by_percent', 0)),
                    'fixture_info': fixture_info,
                    'captaincy_score': captaincy_score
                })
        
        # Sort by captaincy score (form + fixture ease)
        captain_options.sort(key=lambda x: x['captaincy_score'], reverse=True)
        
        result = "⚡ CAPTAIN RECOMMENDATIONS (Form + Fixtures)\n\n"
        
        # Add fixture difficulty legend
        result += "📊 Fixture Difficulty: 1=Very Hard 🔴, 2=Hard 🟠, 3=Medium 🟡, 4=Easy 🟢, 5=Very Easy 💚\n\n"
        
        for i, player in enumerate(captain_options[:5], 1):
            fixture = player['fixture_info']
            difficulty_emoji = {1: '🔴', 2: '🟠', 3: '🟡', 4: '🟢', 5: '💚'}.get(fixture['difficulty'], '🟡')
            
            result += f"{i}. **{player['name']}** ({player['position']}, {player['team']})\n"
            result += f"   Form: {player['form']} | Price: £{player['price']}m\n"
            result += f"   Fixture: vs {fixture['opponent']} ({fixture['venue']}) - {fixture['difficulty']}/5 {difficulty_emoji}\n"
            result += f"   Ownership: {player['ownership']:.1f}% | Points: {player['points']}\n"
            result += f"   Captain Score: {player['captaincy_score']:.1f}\n\n"
        
        # Add captaincy advice
        if captain_options:
            top_pick = captain_options[0]
            result += f"🎯 **TOP PICK**: {top_pick['name']} - Best combination of form ({top_pick['form']}) "
            result += f"and fixture difficulty ({top_pick['fixture_info']['difficulty']}/5)\n\n"
            
            result += "💡 **Captaincy Tips**:\n"
            result += "• Fixture difficulty often trumps form\n"
            result += "• Easy fixtures (4-5/5) are ideal for captaincy\n"
            result += "• Consider penalty takers for extra upside\n"
        
        return result
    
    def _find_transfer_targets(self, bootstrap_data: Dict) -> str:
        """Suggest good transfer targets based on form and value"""
        players = bootstrap_data['elements']
        teams_map = {t['id']: t['name'] for t in bootstrap_data['teams']}
        positions_map = {p['id']: p['singular_name'] for p in bootstrap_data['element_types']}
        
        # Find players with good form and reasonable ownership
        targets = []
        for player in players:
            form = float(player.get('form', 0))
            price = float(player['now_cost']) / 10
            points = player['total_points']
            ownership = float(player.get('selected_by_percent', 0))
            
            # Good transfer targets: decent form, not over-owned, reasonable price
            if form > 5.0 and ownership < 50.0 and price < 12.0 and points > 15:
                targets.append({
                    'name': player['web_name'],
                    'team': teams_map.get(player['team'], 'Unknown'),
                    'position': positions_map.get(player['element_type'], 'Unknown'),
                    'form': form,
                    'price': price,
                    'points': points,
                    'ownership': ownership
                })
        
        # Sort by form
        targets.sort(key=lambda x: x['form'], reverse=True)
        
        result = "🎯 TRANSFER TARGETS (Form + Value)\n\n"
        for i, player in enumerate(targets[:6], 1):
            result += f"{i}. **{player['name']}** ({player['position']}, {player['team']})\n"
            result += f"   Form: {player['form']} | Price: £{player['price']}m\n"
            result += f"   Ownership: {player['ownership']:.1f}% | Points: {player['points']}\n\n"
        
        return result
    
    def _wildcard_advice(self, bootstrap_data: Dict = None) -> str:
        """Provide wildcard usage advice with current FPL data"""
        current_gameweek = None
        next_deadline = None
        
        # Get current gameweek from FPL data if available
        if bootstrap_data:
            events = bootstrap_data.get('events', [])
            for event in events:
                if event.get('is_current', False):
                    current_gameweek = event['id']
                    break
                elif event.get('is_next', False):
                    current_gameweek = event['id']
                    next_deadline = event.get('deadline_time', 'Unknown')
                    break
            
            # If no current/next found, find the latest finished gameweek
            if not current_gameweek:
                finished_events = [e for e in events if e.get('finished', False)]
                if finished_events:
                    latest_finished = max(finished_events, key=lambda x: x['id'])
                    current_gameweek = latest_finished['id'] + 1  # Next gameweek
                    
                    # Find next event details
                    next_event = next((e for e in events if e['id'] == current_gameweek), None)
                    if next_event:
                        next_deadline = next_event.get('deadline_time', 'Unknown')
        
        # Current situation analysis
        current_info = ""
        if current_gameweek:
            current_info = f"**Current Status:** Gameweek {current_gameweek}"
            if next_deadline:
                # Format deadline nicely
                try:
                    from datetime import datetime
                    if 'T' in next_deadline:
                        dt = datetime.fromisoformat(next_deadline.replace('Z', '+00:00'))
                        deadline_str = dt.strftime('%Y-%m-%d %H:%M')
                        current_info += f" | Next Deadline: {deadline_str}"
                except:
                    current_info += f" | Next Deadline: {next_deadline}"
            current_info += "\n\n"
        
        # Season timing advice
        timing_advice = ""
        if current_gameweek:
            if current_gameweek <= 6:
                timing_advice = """
**Early Season Timing (GW 1-6):**
✅ **Good time for first wildcard** - Template is still forming
• Fix early transfer mistakes
• Jump on price rises from popular picks
• Establish solid team structure
• Take advantage of early season data
"""
            elif 7 <= current_gameweek <= 15:
                timing_advice = """
**Mid-Season Timing (GW 7-15):**
⚠️ **Consider carefully** - Save for fixture swings or injury crisis
• Wait for international breaks
• Look for upcoming fixture turns
• Consider injury situations
• Plan for Christmas period
"""
            elif current_gameweek >= 16:
                timing_advice = """
**Late Season Timing (GW 16+):**
💡 **Strategic timing** - Plan for DGWs and BGWs
• Double gameweeks coming up
• First wildcard expires in January
• Blank gameweeks to navigate
• Use data from half season
"""
        
        return f"""
🃏 **WILDCARD STRATEGY ADVICE**

{current_info}{timing_advice}

**Key Considerations:**
• You get 2 wildcards per season (1st expires Jan 31st)
• Don't panic-use after 1 bad gameweek
• Plan for 3-4 gameweeks ahead, not just next
• Consider price changes and popular transfers
• International breaks = more time to plan

**Good Times to Wildcard:**
• Early season (GW 3-6) for team structure
• Before fixture difficulty swings
• During injury crisis (3+ players affected)
• Before double gameweeks
• After international breaks

**Avoid Wildcarding:**
• Immediately after one bad week
• Without clear plan for next 4+ gameweeks
• Just before price deadline with no research
• When your team has good fixtures coming
"""

    def _handle_team_stats_query(self, query: str, query_tokens: List[str], bootstrap_data: Dict) -> str:
        """Handle team statistics queries"""
        team_results = []
        
        for doc in self.documents:
            if doc['type'] == 'team':
                similarity = self.calculate_similarity(query_tokens, doc['tokens'])
                if similarity > 0.005:
                    doc_copy = doc.copy()
                    doc_copy['similarity_score'] = similarity
                    team_results.append(doc_copy)
        
        if not team_results:
            return ""
        
        team_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        context_parts = [
            f"🏆 TEAM STATISTICS SEARCH:",
            f"Query: '{query}'\n"
        ]
        
        for i, result in enumerate(team_results[:5], 1):
            team_data = result['team_data']
            context_parts.append(f"{i}. **{result['team_name']}**")
            context_parts.append(f"   Goals Scored: {team_data['goals']}")
            context_parts.append(f"   Assists: {team_data['assists']}")
            context_parts.append(f"   Clean Sheets: {team_data['clean_sheets']}")
            context_parts.append(f"   Goals Conceded: {team_data['goals_conceded']}")
            context_parts.append(f"   Relevance: {result['similarity_score']:.3f}\n")
        
        return "\n".join(context_parts)
    
    def _format_player_results(self, query: str, results: List[Dict]) -> str:
        """Format player search results for LLM"""
        context_parts = [
            f"🧠 RAG SEARCH RESULTS (Semantic Match):",
            f"Query: '{query}' matched {len(results)} relevant players\n"
        ]
        
        for i, result in enumerate(results, 1):
            player = result['player_data']
            score = result['similarity_score']
            
            context_parts.append(
                f"{i}. **{player['web_name']}** ({result['position_name']}, {result['team_name']})"
            )
            context_parts.append(
                f"   Price: £{result['price']:.1f}m | Points: {player['total_points']} | "
                f"Form: {player.get('form', 0)} | Ownership: {player.get('selected_by_percent', 0)}%"
            )
            
            # Position-specific stats
            if player['element_type'] == 1:  # GK
                context_parts.append(
                    f"   Clean Sheets: {player.get('clean_sheets', 0)} | "
                    f"Saves: {player.get('saves', 0)} | Goals Conceded: {player.get('goals_conceded', 0)}"
                )
            else:  # Outfield
                context_parts.append(
                    f"   Goals: {player.get('goals_scored', 0)} | "
                    f"Assists: {player.get('assists', 0)} | Minutes: {player.get('minutes', 0)}"
                )
            
            context_parts.append(f"   Relevance Score: {score:.3f}\n")
        
        return "\n".join(context_parts)


# Global RAG helper instance
rag_helper = FPLRAGHelper()
