import re
import requests
from collections import Counter
from typing import List, Dict, Optional
from fpl_knowledge import FPL_SEARCHABLE_RULES, FPL_RULES_KNOWLEDGE

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
        """Create rich searchable content for a player"""
        parts = [
            f"{player['web_name']} {player['first_name']} {player['second_name']}",
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
    
    def rag_fallback_search(self, query: str, bootstrap_data: Dict, top_k: int = 8) -> str:
        """
        Enhanced RAG fallback with knowledge base support
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
        
        # Regular player search
        results = []
        for doc in self.documents:
            if doc['type'] == 'player':  # Only search players for player queries
                similarity = self.calculate_similarity(query_tokens, doc['tokens'])
                if similarity > 0.005:  # Minimum threshold
                    doc_copy = doc.copy()
                    doc_copy['similarity_score'] = similarity
                    results.append(doc_copy)
        
        if not results:
            return ""
        
        # Sort by similarity
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        results = results[:top_k]
        
        # Format for LLM
        return self._format_player_results(query, results)
    
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
            strategy_indicators = ['differential', 'template', 'value', 'budget', 'should i use', 'options']
            
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
            'use my wildcard', 'should i use my wildcard'
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
        if 'wildcard' in query_lower and ('should' in query_lower or 'use' in query_lower):
            return self._wildcard_advice()
        
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
    
    def _wildcard_advice(self) -> str:
        """Provide wildcard usage advice"""
        return """
🃏 WILDCARD STRATEGY ADVICE

**When to Use Your Wildcard:**
• International breaks (time to plan)
• Major injury crisis in your team
• Fixture swing periods
• Early season (GW 3-6) team structure
• Before double gameweeks

**Things to Consider:**
• You get 2 wildcards per season
• First wildcard expires in January
• Don't panic-use after 1 bad week
• Plan for upcoming fixtures (3-4 GWs)
• Consider price rises/falls

**Current Timing:**
• Early season wildcards often effective
• Allows you to fix template issues
• Take advantage of early price rises
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
