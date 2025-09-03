"""
Enhanced RAG Knowledge Base for FPL Rules and Advanced Queries
"""

FPL_RULES_KNOWLEDGE = {
    "team_rules": {
        "max_players_per_team": 3,
        "squad_size": 15,
        "starting_xi": 11,
        "bench_size": 4,
        "free_transfers_per_week": 1,
        "transfer_cost": 4,  
        "starting_budget": 100.0, 
        "max_player_price": 15.0  # 
    },
    
    "scoring_system": {
        "goals": {
            "goalkeeper": 6,
            "defender": 6, 
            "midfielder": 5,
            "forward": 4
        },
        "assists": 3,
        "clean_sheet": {
            "goalkeeper": 4,
            "defender": 4,
            "midfielder": 1,
            "forward": 0
        },
        "cards": {
            "yellow": -1,
            "red": -3
        },
        "goals_conceded": {
            "goalkeeper": -1,  
            "defender": -1     
        },
        "saves": {
            "goalkeeper": 1    
        },
        "bonus_points": {
            "max_per_match": 3,
            "bps_threshold": "highest BPS scores"
        }
    },
    
    "captain_rules": {
        "captain_multiplier": 2,
        "vice_captain_backup": True,
        "triple_captain_chip": 3,
        "bench_boost_chip": "all 15 players score"
    },
    
    "transfer_rules": {
        "free_transfers": 1,
        "transfer_deadline": "1.5 hours before first match",
        "wildcard_transfers": "unlimited",
        "free_hit_transfers": "unlimited for one week",
        "point_deduction": 4,
        "maximum_transfers": "no limit with point hits",
        "transfer_banking": "up to 2 free transfers maximum",
        "price_changes": "daily based on net transfers"
    },
    
    "strategy_concepts": {
        "differential_players": {
            "definition": "low ownership players with high potential",
            "ownership_threshold": "under 15% ownership",
            "risk_reward": "high ceiling, low floor",
            "examples": "rotation risks, fixture swings, form players"
        },
        "template_players": {
            "definition": "high ownership essential players",
            "ownership_threshold": "over 40% ownership", 
            "characteristics": "consistent, premium, reliable"
        },
        "value_picks": {
            "definition": "budget players with good returns",
            "price_range": "under 6.0m typically",
            "characteristics": "good fixtures, regular starts, attacking threat"
        },
        "form_analysis": {
            "short_term": "last 3-4 gameweeks",
            "medium_term": "last 6-8 gameweeks", 
            "factors": "minutes, goals, assists, bonus, fixtures"
        }
    }
}

FPL_SEARCHABLE_RULES = f"""
FPL Rules and Regulations:

Team Building Rules:
- Maximum players from one team: {FPL_RULES_KNOWLEDGE['team_rules']['max_players_per_team']} players
- Total squad size: {FPL_RULES_KNOWLEDGE['team_rules']['squad_size']} players (11 starters + 4 bench)
- Starting budget: £{FPL_RULES_KNOWLEDGE['team_rules']['starting_budget']}m million pounds
- Free transfers per week: {FPL_RULES_KNOWLEDGE['team_rules']['free_transfers_per_week']} transfer
- Extra transfer cost: {FPL_RULES_KNOWLEDGE['team_rules']['transfer_cost']} points penalty deduction

Transfer Rules and Regulations:
- Free transfers: {FPL_RULES_KNOWLEDGE['transfer_rules']['free_transfers']} per gameweek
- Transfer deadline: {FPL_RULES_KNOWLEDGE['transfer_rules']['transfer_deadline']} before kickoff
- Banking transfers: {FPL_RULES_KNOWLEDGE['transfer_rules']['transfer_banking']} maximum
- Point deduction: {FPL_RULES_KNOWLEDGE['transfer_rules']['point_deduction']} points per extra transfer
- Wildcard transfers: {FPL_RULES_KNOWLEDGE['transfer_rules']['wildcard_transfers']} transfers no penalty
- Free hit chip: {FPL_RULES_KNOWLEDGE['transfer_rules']['free_hit_transfers']} for one gameweek only
- Price changes: {FPL_RULES_KNOWLEDGE['transfer_rules']['price_changes']} at 1:30am GMT

Scoring System Points:
- Goal by goalkeeper: {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['goalkeeper']} points
- Goal by defender: {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['defender']} points  
- Goal by midfielder: {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['midfielder']} points
- Goal by forward: {FPL_RULES_KNOWLEDGE['scoring_system']['goals']['forward']} points
- Assist any position: {FPL_RULES_KNOWLEDGE['scoring_system']['assists']} points
- Clean sheet goalkeeper: {FPL_RULES_KNOWLEDGE['scoring_system']['clean_sheet']['goalkeeper']} points
- Clean sheet defender: {FPL_RULES_KNOWLEDGE['scoring_system']['clean_sheet']['defender']} points
- Clean sheet midfielder: {FPL_RULES_KNOWLEDGE['scoring_system']['clean_sheet']['midfielder']} point
- Yellow card penalty: {FPL_RULES_KNOWLEDGE['scoring_system']['cards']['yellow']} point
- Red card penalty: {FPL_RULES_KNOWLEDGE['scoring_system']['cards']['red']} points
- Goalkeeper saves: {FPL_RULES_KNOWLEDGE['scoring_system']['saves']['goalkeeper']} point per 3 saves
- Goals conceded penalty: {FPL_RULES_KNOWLEDGE['scoring_system']['goals_conceded']['goalkeeper']} point per 2 goals (GK/DEF)

Captain and Chips:
- Captain points: double points multiplier {FPL_RULES_KNOWLEDGE['captain_rules']['captain_multiplier']}x
- Triple captain chip: {FPL_RULES_KNOWLEDGE['captain_rules']['triple_captain_chip']}x points for one gameweek
- Bench boost chip: all {FPL_RULES_KNOWLEDGE['team_rules']['squad_size']} players score points
- Free hit chip: unlimited transfers for one gameweek
- Wildcard chip: unlimited transfers reset team

Strategic Concepts:
- Differential players: {FPL_RULES_KNOWLEDGE['strategy_concepts']['differential_players']['definition']}
- Low ownership threshold: {FPL_RULES_KNOWLEDGE['strategy_concepts']['differential_players']['ownership_threshold']} differential
- Template players: {FPL_RULES_KNOWLEDGE['strategy_concepts']['template_players']['definition']}
- High ownership threshold: {FPL_RULES_KNOWLEDGE['strategy_concepts']['template_players']['ownership_threshold']} template
- Value picks: {FPL_RULES_KNOWLEDGE['strategy_concepts']['value_picks']['definition']}
- Budget range: {FPL_RULES_KNOWLEDGE['strategy_concepts']['value_picks']['price_range']} value
- Form analysis: {FPL_RULES_KNOWLEDGE['strategy_concepts']['form_analysis']['short_term']} short term form
"""
