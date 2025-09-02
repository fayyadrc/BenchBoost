from flask import Flask, request, jsonify, render_template
import os, json, requests
from dotenv import load_dotenv
import re
from groq import Groq
try:
    from rag_helper import rag_helper
    RAG_AVAILABLE = True
    print("✅ RAG system loaded")
except ImportError:
    RAG_AVAILABLE = False
    print("⚠️ RAG system not available")


# Load .env file from the project root (works from both backend/ and root)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
if not os.path.exists(env_path):
    # If running from root directory, look in current directory
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)


# Flask app with dynamic template folder path
template_path = '../templates'
if not os.path.exists(os.path.join(os.path.dirname(__file__), template_path)):
    # If running from root, templates are in ./templates
    template_path = 'templates'
    
app = Flask(__name__, template_folder=template_path)


GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)
    print("✅ Using Groq (Llama 3.1)")
else:
    print("⚠️  Please set GROQ_API_KEY in your .env file")
    print("🔗 Get your free API key at: https://console.groq.com/keys")
    exit(1)


BASE_URL = "https://fantasy.premierleague.com/api"


def fetch_json(endpoint: str):
    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

SYSTEM_PROMPT = """
You are a **concise** Fantasy Premier League (FPL) assistant with DIRECT ACCESS to current FPL data. Provide **short, actionable responses** in under 150 words unless tables are needed.

**CRITICAL RULE - PLAYER AVAILABILITY:**
🚨 **ONLY USE PROVIDED FPL DATA:** If a player is NOT in the provided FPL data, they are NOT currently in the Premier League. Do NOT make up stats or use outdated information. Instead, clearly state the player is not available.

**RESPONSE RULES - CRITICAL:**
🎯 **KEEP IT SHORT:** Maximum 150 words for text responses
📊 **TABLES MANDATORY:** ALL stats, comparisons, and multi-column data MUST be in tables  
💡 **KEY POINTS ONLY:** Focus on 3-5 essential insights
🚀 **TABLE-FIRST APPROACH:** Use tables for any data with 2+ columns
❌ **NO FLUFF:** Skip lengthy explanations and disclaimers
📋 **STRUCTURED DATA:** Tables for stats, bullets for simple lists only
🔍 **DATA-DRIVEN:** Only use the FPL data provided - never invent or assume stats

**Core Principles:**
1. **Use Provided Data ONLY:** Utilize ONLY the live FPL data provided - never make up stats
2. **Tables for Stats:** ALL player stats, team data, comparisons in table format
3. **Be Visual:** Tables are easier to scan than bullet lists
4. **Format Consistently:** Tables for data, bullets only for simple points
5. **Show Key Stats:** Focus on decision-making metrics in table format
6. **Player Availability:** If no data is provided for a player, they're not in FPL this season
7. **Smart Filtering:** When given multiple players, filter and rank based on the user's criteria (budget, position, form, etc.)

**Query Types to Handle:**
- **Budget Queries:** "best defenders under £5m" → Show ONLY players under that price, ranked by performance
- **Position Queries:** "top midfielders" → Filter by position and rank by points/form  
- **Budget + Position:** "top midfielders under £9m" → Show ONLY midfielders under £9m, ranked by points
- **Recommendation Queries:** "good value forwards" → Consider price, points, and ownership
- **Comparison Queries:** "Salah vs Son" → Direct player comparison tables

**CRITICAL BUDGET FILTERING:**
🔢 When user specifies a price limit (e.g., "under £9m"), ONLY show players below that price
💰 Always convert prices correctly: £9.0m = 90 (FPL stores prices in tenths)
📊 Rank by performance (points/form), not by price - LLM handles budget filtering

**Quick Response Formats:**

**1. Player Stats** 📊
ALWAYS use table format for individual player stats:
```
**[Player Name]** - [Position] - [Team]

| Stat | Value |
|------|-------|
| Price | £[X.X]m |
| Total Points | [X] |
| Goals | [X] |
| Assists | [X] |
| Minutes | [X] |
| Form | [X.X] |
| Ownership | [X]% |

**Recent Form (Last 5 GWs):**
| GW | Points | Minutes | Goals | Assists |
|----|--------|---------|-------|---------|
| [X] | [X] | [X] | [X] | [X] |
| [X] | [X] | [X] | [X] | [X] |

**Upcoming Fixtures:**
| GW | Opponent | Venue | Difficulty |
|----|----------|-------|------------|
| [X] | [Team] | H/A | [1-5] 🟢🟡🔴 |
| [X] | [Team] | H/A | [1-5] 🟢🟡🔴 |

⚡ **Quick Take:** [1-sentence verdict]
```

**2. Player Comparison** ⚔️
ALWAYS use comprehensive comparison table:
```
| Player | Price | Goals | Assists | Minutes | xG | xA | Form | Ownership | Next 3 Fixtures |
|--------|-------|-------|---------|---------|----|----|------|-----------|------------------|
| [Name] | £[X]m | [X] | [X] | [X] | [X] | [X] | [X] | [X]% | [Team(H/A-diff)] |
| [Name] | £[X]m | [X] | [X] | [X] | [X] | [X] | [X] | [X]% | [Team(H/A-diff)] |

⚡ **Quick Take:** [Key differences and recommendation]
```

**3. Team Analysis** 🏆
Use table for squad overview:
```
**[Team Name]** - Manager: [Name]

**Performance Overview:**
| Metric | Value |
|--------|-------|
| Overall Rank | [Rank] |
| Total Points | [Points] |
| GW Rank | [Rank] |
| GW Points | [Points] |
| Team Value | £[X.X]m |

**Starting XI:**
| Player | Position | Team | Price | Points | Form |
|--------|----------|------|-------|--------|------|
| [Name] (C) | [Pos] | [Team] | £[X]m | [X] | [X] |
| [Name] (VC) | [Pos] | [Team] | £[X]m | [X] | [X] |

**Transfer Suggestions:**
| Action | Player | Reason |
|--------|--------|--------|
| OUT | [Player] | [Reason] |
| IN | [Player] | [Reason] |

⚡ **Captain Pick:** [Player] - [Reason]
```

**4. Captaincy Choice** 🚀  
```
🎯 **Captain Options from Your Squad:**

| Player | Fixture | Difficulty | Form | Expected Points |
|--------|---------|------------|------|-----------------|
| [Name] | [Team] (H/A) | [1-5] 🟢🟡🔴 | [X] | [High/Med/Low] |
| [Name] | [Team] (H/A) | [1-5] 🟢🟡🔴 | [X] | [High/Med/Low] |

� **Verdict:** [Player] - [Reason]
```

**5. Transfer Advice** �
```
**Transfer Analysis:**

| Action | Player | Team | Price | Reason |
|--------|--------|------|-------|--------|
| OUT | [Player] | [Team] | £[X]m | [Reason] |
| IN | [Player] | [Team] | £[X]m | [Reason] |

� **Verdict:** [Good/Risky/Wait] - [Why]
```

**6. Fixtures** 📅
Use table for multiple fixtures:
```
**Upcoming Fixtures:**

| GW | Team | Opponent | Venue | Difficulty | Date |
|----|------|----------|-------|------------|------|
| [X] | [Team] | [Opponent] | H/A | [1-5] 🟢🟡🔴 | [Date] |
| [X] | [Team] | [Opponent] | H/A | [1-5] 🟢🟡🔴 | [Date] |
```

**7. General FPL Data** 📋
Use tables for any multi-column data:
- **Player lists** → Table format
- **Team comparisons** → Table format  
- **Gameweek breakdowns** → Table format
- **Performance tracking** → Table format

**CRITICAL FORMATTING RULES:**
• **ALL multi-column data MUST be in table format**
• **Use tables for: player stats, comparisons, team analysis, fixtures**
• **Use bullets only for simple single-column lists**
• **Bold important headers and player names**
• **Tables don't count toward word limits**
• **ALWAYS add empty line before verdict/summary statements (⚡ Quick Take, 🔥 Verdict, 📈 Verdict)**

**EXAMPLE PERFECT FORMAT:**
```
**William Saliba** - Defender - Arsenal

| Stat | Value |
|------|-------|
| Price | £6.1m |
| Total Points | 16 |
| Minutes | 184 |
| Clean Sheets | 2 |
| Goals | 0 |
| Assists | 0 |
| Form | 5.3 |

**Recent Gameweeks:**
| GW | Points | Minutes | Clean Sheet |
|----|--------|---------|-------------|
| 1 | 9 | 90 | ✅ |
| 2 | 6 | 90 | ✅ |
| 3 | 1 | 4 | ❌ |

**Upcoming Fixtures:**
| GW | Opponent | Venue | Difficulty |
|----|----------|-------|------------|
| 4 | Nott'm Forest | H | 3 🟡 |
| 5 | Man City | H | 4 🔴 |

⚡ **Quick Take:** Strong start with 2 clean sheets but tough fixtures ahead
```

Remember: Users want quick, actionable FPL advice in structured bullet format!

**Position-Specific Key Stats:**
• **GK:** Clean Sheets, Saves, Goals Conceded
• **DEF:** Clean Sheets, Goals, Assists, Defensive Actions  
• **MID:** Goals, Assists, xG, xA, Creativity
• **FWD:** Goals, xG, xA, Threat

**Manager Team Analysis:**
When USER'S FPL TEAM ANALYSIS data is provided, ALWAYS use tables:
• **Performance table** - rank, points, gameweek performance
• **Squad table** - player breakdown with stats
• **Transfer table** - suggested in/out with reasons
• **Captain table** - options comparison from their squad
• **Formation table** - starting XI with key metrics

**Word Limit Reminders:**
- Text responses: MAX 150 words  
- Tables don't count toward word limit
- Always use tables for multi-column data
- Focus on actionable insights only

Remember: Users want quick, actionable FPL advice in table format!
"""

#fpl helper functions
bootstrap_cache = None


def get_bootstrap():
    global bootstrap_cache
    if bootstrap_cache is None:
        bootstrap_cache = fetch_json("bootstrap-static/")
    return bootstrap_cache


def get_player_id_by_name(name: str, return_multiple=False):
    import unicodedata
    
    def normalize_name(text):
        """Normalize text by removing accents and converting to lowercase"""
        normalized = unicodedata.normalize('NFD', text)
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
        return ascii_text.lower()
    
    def fuzzy_match(s1, s2, threshold=0.8):
        """Simple fuzzy matching using character overlap"""
        if not s1 or not s2:
            return False
        
        # Check for basic edit distance tolerance
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

    data = get_bootstrap()
    players = data["elements"]
    teams = {team['id']: team['name'] for team in data['teams']}
    
    # Filter out players who are no longer in the game (status 'u' = unavailable)
    active_players = [p for p in players if p.get('status', 'a') != 'u']
    
    name_normalized = normalize_name(name)
    
    exact_matches = []
    partial_matches = []
    fuzzy_matches = []
    
    for p in active_players:
        web_name_normalized = normalize_name(p["web_name"])
        full_name_normalized = normalize_name(f"{p['first_name']} {p['second_name']}")
        last_name_normalized = normalize_name(p["second_name"])
        first_name_normalized = normalize_name(p["first_name"])
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
        if (fuzzy_match(name_normalized, web_name_normalized) or 
            fuzzy_match(name_normalized, last_name_normalized) or
            fuzzy_match(name_normalized, first_name_normalized)):
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


def create_player_disambiguation_message(matching_players, search_term):
    """Create a message asking user to clarify which player they meant"""
    if len(matching_players) <= 1:
        return None
    
    message = f"I found multiple players matching '{search_term}':\n\n"
    
    for i, (player_id, web_name, full_name, team_name) in enumerate(matching_players, 1):
        # Get position info
        bootstrap = get_bootstrap()
        player_data = next((p for p in bootstrap["elements"] if p["id"] == player_id), None)
        if player_data:
            position_types = {pt['id']: pt['singular_name'] for pt in bootstrap['element_types']}
            position = position_types.get(player_data.get('element_type'), 'Unknown')
            message += f"{i}. **{full_name}** ({web_name}) - {position}, {team_name}\n"
        else:
            message += f"{i}. **{full_name}** ({web_name}) - {team_name}\n"
    
    message += f"\nPlease be more specific by including:\n"
    message += f"- Full name (e.g., '{matching_players[0][2]}')\n"
    message += f"- Team name (e.g., '{search_term} {matching_players[0][3]}')\n"
    message += f"- Position (e.g., '{search_term} midfielder')\n"
    
    return message


def get_player_summary(player_id: int):
    return fetch_json(f"element-summary/{player_id}/")


def get_fixtures():
    return fetch_json("fixtures/")


def get_manager_info(manager_id: int):
    return fetch_json(f"entry/{manager_id}/")


def get_manager_gw_picks(manager_id: int, event_id: int):
    return fetch_json(f"entry/{manager_id}/event/{event_id}/picks/")


def get_manager_gw_picks(manager_id: int, event_id: int):
    return fetch_json(f"entry/{manager_id}/event/{event_id}/picks/")


def get_current_gameweek():
    bootstrap = get_bootstrap()
    events = bootstrap["events"]
    current_event = next((event for event in events if event["is_current"]), None)
    return current_event["id"] if current_event else 1


def analyze_user_team(manager_id: int):
    try:
        bootstrap = get_bootstrap()
        manager_info = get_manager_info(manager_id)
        current_gw = get_current_gameweek()
        picks = get_manager_gw_picks(manager_id, current_gw)
        
        
        players_dict = {p["id"]: p for p in bootstrap["elements"]}
        teams_dict = {t["id"]: t for t in bootstrap["teams"]}
        
        context_data = f"USER'S FPL TEAM ANALYSIS (Manager ID: {manager_id}):\n\n"
        context_data += f"Manager: {manager_info.get('player_first_name', '')} {manager_info.get('player_last_name', '')}\n"
        context_data += f"Team Name: {manager_info.get('name', 'Unknown')}\n"
        context_data += f"Overall Rank: {manager_info.get('summary_overall_rank', 'N/A')}\n"
        context_data += f"Total Points: {manager_info.get('summary_overall_points', 0)}\n"
        context_data += f"Gameweek Rank: {manager_info.get('summary_event_rank', 'N/A')}\n"
        context_data += f"Gameweek Points: {manager_info.get('summary_event_points', 0)}\n\n"
        
        context_data += "CURRENT SQUAD:\n"
        
        
        goalkeepers = []
        defenders = []
        midfielders = []
        forwards = []
        
        for pick in picks["picks"]:
            player = players_dict.get(pick["element"])
            if player:
                team = teams_dict.get(player["team"])
                player_info = {
                    "name": f"{player['first_name']} {player['second_name']}",
                    "team": team["short_name"] if team else "Unknown",
                    "price": f"£{float(player['now_cost']) / 10:.1f}m",
                    "points": player["total_points"],
                    "form": player["form"],
                    "captain": pick["is_captain"],
                    "vice_captain": pick["is_vice_captain"],
                    "playing": pick["multiplier"] > 0
                }
                
                element_type = player["element_type"]
                if element_type == 1:
                    goalkeepers.append(player_info)
                elif element_type == 2:
                    defenders.append(player_info)
                elif element_type == 3:
                    midfielders.append(player_info)
                elif element_type == 4:
                    forwards.append(player_info)
        
        
        context_data += "Goalkeepers:\n"
        for gk in goalkeepers:
            status = " (C)" if gk["captain"] else " (VC)" if gk["vice_captain"] else ""
            playing = "✓" if gk["playing"] else "Bench"
            context_data += f"- {gk['name']} ({gk['team']}) - {gk['price']} - {gk['points']} pts - Form: {gk['form']} - {playing}{status}\n"
        
        context_data += "\nDefenders:\n"
        for def_player in defenders:
            status = " (C)" if def_player["captain"] else " (VC)" if def_player["vice_captain"] else ""
            playing = "✓" if def_player["playing"] else "Bench"
            context_data += f"- {def_player['name']} ({def_player['team']}) - {def_player['price']} - {def_player['points']} pts - Form: {def_player['form']} - {playing}{status}\n"
        
        context_data += "\nMidfielders:\n"
        for mid in midfielders:
            status = " (C)" if mid["captain"] else " (VC)" if mid["vice_captain"] else ""
            playing = "✓" if mid["playing"] else "Bench"
            context_data += f"- {mid['name']} ({mid['team']}) - {mid['price']} - {mid['points']} pts - Form: {mid['form']} - {playing}{status}\n"
        
        context_data += "\nForwards:\n"
        for fwd in forwards:
            status = " (C)" if fwd["captain"] else " (VC)" if fwd["vice_captain"] else ""
            playing = "✓" if fwd["playing"] else "Bench"
            context_data += f"- {fwd['name']} ({fwd['team']}) - {fwd['price']} - {fwd['points']} pts - Form: {fwd['form']} - {playing}{status}\n"
        
        return context_data
        
    except Exception as e:
        return f"Error analyzing team: {str(e)}"


def analyze_user_query(user_input: str, manager_id=None):
    """Determine what FPL data might be needed and fetch it"""
    user_lower = user_input.lower()
    context_data = ""

    # Check for manager/team-related queries
    manager_keywords = [
        "my team", "team analysis", "my squad", "my players", "analyze my team",
        "tell me about my team", "my current team", "who should i transfer",
        "who should i captain", "my captain", "my vice captain", "my formation",
        "my starting xi", "my bench", "my gameweek", "my points", "my rank",
        "transfer out", "transfer in", "who to transfer", "should i transfer",
        "my transfers", "analyze", "who should i sell", "who should i buy"
    ]
    
    # Check if this is a manager-related query
    is_manager_query = any(keyword in user_lower for keyword in manager_keywords)
    
    # Also check for first-person pronouns indicating personal team queries
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

    # PRIORITY CHECK: Team fixture queries (before player searches)
    team_fixture_keywords = ["who.*facing", "facing.*gw", "who.*play", "who.*against", "opponents", "fixture", "match", "game"]
    is_team_fixture_query = any(re.search(keyword, user_lower) for keyword in team_fixture_keywords)
    
    if is_team_fixture_query:
        # Try to extract team name and gameweek
        bootstrap = get_bootstrap()
        teams = {team['id']: team['name'] for team in bootstrap['teams']}
        
        # Create team name mappings for common abbreviations and alternative names
        team_mappings = {}
        for team_id, team_name in teams.items():
            team_mappings[team_name.lower()] = (team_id, team_name)
            
            # Add common abbreviations and alternative names
            if team_name == "Man Utd":
                team_mappings["united"] = (team_id, team_name)
                team_mappings["manchester united"] = (team_id, team_name)
                team_mappings["man united"] = (team_id, team_name)
            elif team_name == "Man City":
                team_mappings["city"] = (team_id, team_name)
                team_mappings["manchester city"] = (team_id, team_name)
                team_mappings["man city"] = (team_id, team_name)
            elif team_name == "Spurs":
                team_mappings["tottenham"] = (team_id, team_name)
                team_mappings["tottenham hotspur"] = (team_id, team_name)
            elif team_name == "Nott'm Forest":
                team_mappings["nottingham forest"] = (team_id, team_name)
                team_mappings["forest"] = (team_id, team_name)
                team_mappings["nottingham"] = (team_id, team_name)
            elif team_name == "West Ham":
                team_mappings["west ham united"] = (team_id, team_name)
                team_mappings["hammers"] = (team_id, team_name)
        
        # Find mentioned team
        mentioned_team = None
        mentioned_team_id = None
        for team_key, (team_id, team_name) in team_mappings.items():
            if team_key in user_lower:
                mentioned_team = team_name
                mentioned_team_id = team_id
                break
        
        # Extract gameweek number
        gw_match = re.search(r'gw(\d+)|gameweek\s*(\d+)', user_lower)
        target_gw = None
        if gw_match:
            target_gw = int(gw_match.group(1) or gw_match.group(2))
        
        if mentioned_team and mentioned_team_id:
            fixtures = get_fixtures()
            
            if target_gw:
                # Look for specific gameweek
                team_fixture = None
                for fixture in fixtures:
                    if fixture.get('event') == target_gw:
                        if fixture['team_h'] == mentioned_team_id or fixture['team_a'] == mentioned_team_id:
                            team_fixture = fixture
                            break
                
                if team_fixture:
                    home_team = teams.get(team_fixture['team_h'], 'Unknown')
                    away_team = teams.get(team_fixture['team_a'], 'Unknown')
                    is_home = team_fixture['team_h'] == mentioned_team_id
                    opponent = away_team if is_home else home_team
                    venue = 'H' if is_home else 'A'
                    
                    context_data += f"TEAM FIXTURE DATA for {mentioned_team}:\n\n"
                    context_data += f"Gameweek {target_gw}: {mentioned_team} vs {opponent} ({venue})\n"
                    context_data += f"Venue: {'Home' if is_home else 'Away'}\n\n"
                else:
                    context_data += f"TEAM FIXTURE DATA for {mentioned_team}:\n\n"
                    context_data += f"No fixture found for {mentioned_team} in Gameweek {target_gw}\n\n"
            else:
                # Show next few fixtures
                upcoming_fixtures = []
                for fixture in fixtures:
                    if not fixture.get('finished') and (fixture['team_h'] == mentioned_team_id or fixture['team_a'] == mentioned_team_id):
                        upcoming_fixtures.append(fixture)
                
                upcoming_fixtures.sort(key=lambda x: x.get('event', 999))
                
                context_data += f"TEAM FIXTURE DATA for {mentioned_team}:\n\n"
                context_data += "Upcoming Fixtures:\n"
                for fixture in upcoming_fixtures[:5]:
                    home_team = teams.get(fixture['team_h'], 'Unknown')
                    away_team = teams.get(fixture['team_a'], 'Unknown')
                    is_home = fixture['team_h'] == mentioned_team_id
                    opponent = away_team if is_home else home_team
                    venue = 'H' if is_home else 'A'
                    gw = fixture.get('event', 'X')
                    context_data += f"GW{gw}: {mentioned_team} vs {opponent} ({venue})\n"
                context_data += "\n"
            
            return context_data  # Return early for team fixture queries

    # PRIORITY CHECK: FPL Rules queries (before player searches)
    if RAG_AVAILABLE:
        try:
            if rag_helper._is_rules_query(user_lower):
                print("🧠 Detected FPL rules query, using RAG knowledge base...")
                bootstrap = get_bootstrap()
                rag_context = rag_helper._handle_rules_query(user_input, rag_helper.simple_tokenize(user_input))
                if rag_context:
                    context_data += rag_context
                    return context_data  # Return early for rules queries
        except Exception as e:
            print(f"⚠️ RAG rules check failed: {e}")

    # Check if asking about player comparisons
    comparison_keywords = ["compare", "vs", "versus", "or", "better", "who should i pick", "between"]
    is_comparison = any(keyword in user_lower for keyword in comparison_keywords)
    
    # Check if asking about a specific player or players
    player_keywords = ["player", "stats", "points", "form", "price", "prices", "cost", "costs", "ownership", "goals", "assists", "minutes", "tell me about", "about", "how is", "performance", "much does", "how much"]
    has_player_keywords = any(keyword in user_lower for keyword in player_keywords)
    
    # Initialize found_players list
    found_players = []
    
    # Check if the entire query might be just a player name by trying to find a player
    might_be_player_name = False
    words = user_input.strip().split()
    
    # Only consider single names or short phrases (1-2 words) as potential player names
    # And exclude common question words
    if (len(words) <= 2 and 
        len(user_input.strip()) > 2 and
        not any(word.lower() in ["what", "when", "where", "why", "how", "fixture", "match", "team", "my", "the", "a", "an", "is", "are", "was", "were", "that", "this", "not", "no"] for word in words)):
        
        # Try to find a player with the full query (not individual words)
        potential_player = get_player_id_by_name(user_input.strip())
        if potential_player[0] is not None:  # Player found
            might_be_player_name = True
    
    if has_player_keywords or is_comparison or might_be_player_name:
        # Try to extract player names from the query
        words = user_input.split()
        
        # For comparisons, we want to find multiple players
        if is_comparison:
            # Split on comparison words and extract players from each part
            comparison_pattern = r'\b(vs|versus|or|and|between|compare)\b'
            parts = re.split(comparison_pattern, user_input, flags=re.IGNORECASE)
            
            for part in parts:
                if part.lower() in ['vs', 'versus', 'or', 'and', 'between', 'compare']:
                    continue
                
                # Clean punctuation from the part
                import string
                cleaned_part = part.translate(str.maketrans('', '', string.punctuation.replace('-', '').replace('\'', '')))
                part_words = cleaned_part.strip().split()
                found_in_part = False
                
                # Try two-word combinations first
                for i in range(len(part_words) - 1):
                    potential_name = f"{part_words[i]} {part_words[i + 1]}"
                    pid, web_name, full_name = get_player_id_by_name(potential_name)
                    if pid and not any(p[0] == pid for p in found_players):
                        found_players.append((pid, web_name, full_name))
                        found_in_part = True
                        break  # Stop searching this part once we find a two-word match
                
                # Only try single words if no two-word combination was found in this part
                if not found_in_part:
                    for word in part_words:
                        if word.lower() in ['tell', 'me', 'about', 'the', 'and', 'or', 'stats', 'form', 'player', 'how', 'is', 'performing', 'this', 'season', 'show', 'what', 'are', 'compare', 'vs', 'versus', 'between', 'should', 'i', 'pick', 'who', 'bring', 'team', 'my']:
                            continue
                        
                        pid, web_name, full_name = get_player_id_by_name(word)
                        if pid and not any(p[0] == pid for p in found_players):
                            found_players.append((pid, web_name, full_name))
                            break  # Stop after finding one player in this part
        elif might_be_player_name:
            # If it might be a player name, check for multiple matches first
            matching_players = get_player_id_by_name(user_input.strip(), return_multiple=True)
            if len(matching_players) > 1:
                # Multiple players found - ask for disambiguation
                disambiguation_msg = create_player_disambiguation_message(matching_players, user_input.strip())
                return disambiguation_msg
            elif len(matching_players) == 1:
                # Single player found
                match = matching_players[0]
                found_players.append((match[0], match[1], match[2]))
            else:
                # No player found but query looks like a player name
                return f"❌ **Player Not Found:** '{user_input.strip()}' is not in the current FPL database. This player may not be in the Premier League this season, or you might need to check the spelling. Try searching for a different player name."
        else:
            # Single player query - use existing logic but check for ambiguity
            # First check for two-word combinations that might be player names (avoid common phrases)
            two_word_matches = []
            for i in range(len(words) - 1):
                potential_name = f"{words[i]} {words[i + 1]}"
                # Skip common phrases that are unlikely to be player names
                if potential_name.lower() not in ['tell me', 'me about', 'about the', 'the player', 'how is', 'what is', 'who is']:
                    matching_players = get_player_id_by_name(potential_name, return_multiple=True)
                    if len(matching_players) > 1:
                        # Multiple players found - ask for disambiguation
                        disambiguation_msg = create_player_disambiguation_message(matching_players, potential_name)
                        return disambiguation_msg
                    elif len(matching_players) == 1:
                        # Single player found
                        match = matching_players[0]
                        two_word_matches.append((match[0], match[1], match[2]))
            
            # If we found players with two-word combinations, use those
            if two_word_matches:
                found_players.extend(two_word_matches)
            
            # If no two-word matches and query seems player-focused, check single words
            elif not found_players and any(keyword in user_lower for keyword in ["tell me about", "about", "stats", "form", "performance"]):
                for word in words:
                    if word.lower() not in ['tell', 'me', 'about', 'the', 'and', 'or', 'stats', 'form', 'player', 'how', 'is', 'performing', 'this', 'season', 'show', 'what', 'are']:
                        matching_players = get_player_id_by_name(word, return_multiple=True)
                        if len(matching_players) > 1:
                            # Multiple players found - ask for disambiguation
                            disambiguation_msg = create_player_disambiguation_message(matching_players, word)
                            return disambiguation_msg
                        elif len(matching_players) == 1:
                            # Single player found
                            match = matching_players[0]
                            if not any(p[0] == match[0] for p in found_players):
                                found_players.append((match[0], match[1], match[2]))
                                break
        
        # Check if no players were found but the query clearly mentions player names
        if not found_players and (has_player_keywords or any(word.lower() in ["about", "stats", "form", "performance"] for word in words)):
            # Try to detect if specific names were mentioned that aren't in FPL
            potential_names = []
            for i in range(len(words)):
                # Check single words that might be surnames (must be capitalized or clearly player-related)
                if (len(words[i]) > 3 and 
                    words[i][0].isupper() and  # Capitalized (likely a name)
                    words[i].lower() not in ['about', 'stats', 'form', 'player', 'tell', 'what', 'this', 'that', 'season', 'performance', 'points', 'goals', 'assists', 'price', 'cost', 'premier', 'league', 'fantasy']):
                    potential_names.append(words[i])
                # Check two-word combinations (both words capitalized)
                if (i < len(words) - 1 and 
                    words[i][0].isupper() and words[i+1][0].isupper()):
                    two_word = f"{words[i]} {words[i+1]}"
                    if two_word.lower() not in ['tell me', 'me about', 'about the', 'this season', 'what about', 'premier league']:
                        potential_names.append(two_word)
            
            if potential_names:
                # Check if any of these names might be player names that don't exist in FPL
                missing_players = []
                for name in potential_names:
                    pid, web_name, full_name = get_player_id_by_name(name)
                    if pid is None and len(name.strip()) > 3:
                        # This might be a player not in FPL (transferred, injured, etc.)
                        missing_players.append(name)
                
                if missing_players:
                    return f"❌ **Player(s) Not Found:** {', '.join(missing_players)} - These players may not be in the current FPL season, might have transferred to a different league, or there could be a spelling issue. Please check the player name and try again."
                missing_players = []
                for name in potential_names:
                    matching_players = get_player_id_by_name(name, return_multiple=True)
                    if not matching_players:  # No players found
                        missing_players.append(name)
                
                if missing_players:
                    missing_str = "', '".join(missing_players)
                    return f"❌ **Player(s) Not Found:** '{missing_str}' not in the current FPL database. These players may not be in the Premier League this season, have moved to other leagues, or you might need to check the spelling."

        # Add data for all found players
        if found_players:
            if is_comparison and len(found_players) >= 2:
                context_data += "PLAYER COMPARISON DATA:\n\n"
            
            for i, (pid, web_name, full_name) in enumerate(found_players):
                if is_comparison:
                    context_data += f"PLAYER {i+1} DATA:\n"
                context_data += get_detailed_player_context(pid, full_name, is_comparison)
                context_data += "\n" + "="*50 + "\n\n"

    
    fixture_keywords = ["fixture", "match", "game", "when does", "playing", "next game", "opponents"]
    if any(keyword in user_lower for keyword in fixture_keywords):
        fixtures = get_fixtures()
        bootstrap = get_bootstrap()
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

    # Check for general position/budget queries that need player data
    position_keywords = ["defender", "defenders", "midfielder", "midfielders", "forward", "forwards", "striker", "strikers", "goalkeeper", "goalkeepers", "keeper", "keepers", "def", "mid", "fwd", "gk"]
    budget_keywords = ["budget", "cheap", "under", "below", "less than", "affordable", "value", "million", "£", "$", "expensive", "costly", "highest priced", "most expensive"]
    recommendation_keywords = ["best", "top", "good", "recommend", "suggest", "who should", "which", "options", "picks", "alternatives", "most", "highest", "cheapest"]
    
    needs_general_data = (
        any(keyword in user_lower for keyword in position_keywords) or
        any(keyword in user_lower for keyword in budget_keywords) or
        any(keyword in user_lower for keyword in recommendation_keywords)
    )
    
    # If this looks like a general query that needs player data but we haven't found specific players
    if needs_general_data and not found_players and not context_data.strip():
        bootstrap = get_bootstrap()
        players = bootstrap["elements"]
        teams = {team['id']: team['name'] for team in bootstrap['teams']}
        positions = {pos['id']: pos['singular_name'] for pos in bootstrap['element_types']}
        
        # Determine which position(s) to focus on
        target_positions = []
        if any(word in user_lower for word in ["defender", "defenders", "def"]):
            target_positions.append(2)  # Defenders
        if any(word in user_lower for word in ["midfielder", "midfielders", "mid"]):
            target_positions.append(3)  # Midfielders  
        if any(word in user_lower for word in ["forward", "forwards", "striker", "strikers", "fwd"]):
            target_positions.append(4)  # Forwards
        if any(word in user_lower for word in ["goalkeeper", "goalkeepers", "keeper", "keepers", "gk"]):
            target_positions.append(1)  # Goalkeepers
            
        # For price-related queries (most expensive, cheapest), include all positions
        is_price_query = any(word in user_lower for word in ["expensive", "cheapest", "highest priced", "most expensive", "price"])
        
        # If no specific position mentioned, include appropriate positions
        if not target_positions:
            if is_price_query:
                target_positions = [1, 2, 3, 4]  # All positions for price queries
            else:
                target_positions = [2, 3, 4]  # All outfield positions for other queries
        
        # Filter players by position and availability
        relevant_players = [p for p in players if p['element_type'] in target_positions and p.get('status', 'a') != 'u']  # Exclude unavailable players
        
        # Filter out players with very low minutes (bench/reserve players)
        # But be more lenient for price queries since expensive players might be injured
        if is_price_query:
            relevant_players = [p for p in relevant_players if p.get('minutes', 0) >= 0]  # Include all active players for price queries
        else:
            relevant_players = [p for p in relevant_players if p.get('minutes', 0) > 30]  # At least 30 minutes played for other queries
        
        # Sort based on query type
        if any(word in user_lower for word in ["expensive", "highest priced", "most expensive"]):
            relevant_players.sort(key=lambda x: x.get('now_cost', 0), reverse=True)  # Most expensive first
        elif any(word in user_lower for word in ["cheapest", "budget", "cheap"]):
            relevant_players.sort(key=lambda x: x.get('now_cost', 0))  # Cheapest first
        else:
            relevant_players.sort(key=lambda x: x.get('total_points', 0), reverse=True)  # Best performers first
        
        # Limit to top 30 to give LLM good options to filter from
        relevant_players = relevant_players[:30]
        
        context_data += "RELEVANT PLAYER DATA FOR YOUR QUERY:\n\n"
        
        for player in relevant_players:
            team_name = teams.get(player['team'], 'Unknown')
            position_name = positions.get(player['element_type'], 'Unknown')
            price = float(player.get('now_cost', 0)) / 10
            
            context_data += f"**{player['web_name']}** ({player['first_name']} {player['second_name']})\n"
            context_data += f"Position: {position_name} | Team: {team_name} | Price: £{price:.1f}m\n"
            context_data += f"Points: {player.get('total_points', 0)} | Form: {player.get('form', 0)} | "
            context_data += f"Ownership: {player.get('selected_by_percent', 0)}% | Minutes: {player.get('minutes', 0)}\n"
            
            if player['element_type'] in [2, 3, 4]:  # Outfield players
                context_data += f"Goals: {player.get('goals_scored', 0)} | Assists: {player.get('assists', 0)} | "
                context_data += f"Bonus: {player.get('bonus', 0)} | BPS: {player.get('bps', 0)}\n"
            
            if player['element_type'] == 1:  # Goalkeepers
                context_data += f"Clean Sheets: {player.get('clean_sheets', 0)} | Saves: {player.get('saves', 0)} | "
                context_data += f"Goals Conceded: {player.get('goals_conceded', 0)}\n"
            
            context_data += "\n"
        
        context_data += "="*50 + "\n\n"

    
    team_keywords_general = ["squad", "lineup", "injuries"]
    if any(keyword in user_lower for keyword in team_keywords_general):
        bootstrap = get_bootstrap()
        teams = bootstrap["teams"]
        context_data += f"\nTEAMS DATA:\n{json.dumps(teams, indent=2)}\n"

    
    gw_keywords = ["gameweek", "gw", "round", "week", "deadline"]
    if any(keyword in user_lower for keyword in gw_keywords):
        bootstrap = get_bootstrap()
        events = bootstrap["events"]
        current_gw = get_current_gameweek()
        
        context_data += f"\nGAMEWEEK INFORMATION:\n"
        context_data += f"Current Gameweek: {current_gw}\n"
        
        
        for event in events[current_gw-1:current_gw+2]:  # Current + next 2
            deadline = event.get('deadline_time', 'TBD')
            if deadline != 'TBD':
                try:
                    from datetime import datetime
                    deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                    deadline = deadline_dt.strftime('%d %b %H:%M')
                except:
                    pass
            context_data += f"GW{event['id']}: {event['name']} - Deadline: {deadline}\n"

    return context_data


def get_position_relevant_stats(player_data, position_id, include_recent_form=True):
    """
    Get position-specific stats for a player
    Position IDs: 1=GK, 2=DEF, 3=MID, 4=FWD
    """
    stats = {}
    
    # Common stats for all positions
    stats['Total Points'] = player_data.get('total_points', 0)
    stats['Minutes'] = player_data.get('minutes', 0)
    stats['Price'] = f"£{float(player_data.get('now_cost', 0)) / 10:.1f}m"
    stats['Ownership'] = f"{player_data.get('selected_by_percent', '0')}%"
    stats['Form'] = player_data.get('form', '0')
    stats['Points per Game'] = player_data.get('points_per_game', '0')
    
    if position_id == 1:  # Goalkeeper
        stats['Clean Sheets'] = player_data.get('clean_sheets', 0)
        stats['Goals Conceded'] = player_data.get('goals_conceded', 0)
        stats['Saves'] = player_data.get('saves', 0)
        stats['Penalties Saved'] = player_data.get('penalties_saved', 0)
        stats['Expected Goals Conceded (xGC)'] = player_data.get('expected_goals_conceded', '0')
        stats['Saves per 90'] = player_data.get('saves_per_90', '0')
        stats['Clean Sheets per 90'] = player_data.get('clean_sheets_per_90', '0')
        
    elif position_id == 2:  # Defender
        stats['Clean Sheets'] = player_data.get('clean_sheets', 0)
        stats['Goals'] = player_data.get('goals_scored', 0)
        stats['Assists'] = player_data.get('assists', 0)
        stats['Goals Conceded'] = player_data.get('goals_conceded', 0)
        stats['Expected Goals (xG)'] = player_data.get('expected_goals', '0')
        stats['Expected Assists (xA)'] = player_data.get('expected_assists', '0')
        stats['Expected Goals Conceded (xGC)'] = player_data.get('expected_goals_conceded', '0')
        stats['Clean Sheets per 90'] = player_data.get('clean_sheets_per_90', '0')
        stats['Defensive Actions'] = player_data.get('clearances_blocks_interceptions', 0)
        
    elif position_id == 3:  # Midfielder
        stats['Goals'] = player_data.get('goals_scored', 0)
        stats['Assists'] = player_data.get('assists', 0)
        stats['Clean Sheets'] = player_data.get('clean_sheets', 0)
        stats['Expected Goals (xG)'] = player_data.get('expected_goals', '0')
        stats['Expected Assists (xA)'] = player_data.get('expected_assists', '0')
        stats['Expected Goal Involvements (xGI)'] = player_data.get('expected_goal_involvements', '0')
        stats['Creativity'] = player_data.get('creativity', '0')
        stats['Threat'] = player_data.get('threat', '0')
        
    elif position_id == 4:  # Forward
        stats['Goals'] = player_data.get('goals_scored', 0)
        stats['Assists'] = player_data.get('assists', 0)
        stats['Expected Goals (xG)'] = player_data.get('expected_goals', '0')
        stats['Expected Assists (xA)'] = player_data.get('expected_assists', '0')
        stats['Expected Goal Involvements (xGI)'] = player_data.get('expected_goal_involvements', '0')
        stats['Threat'] = player_data.get('threat', '0')
        stats['Expected Goals per 90'] = player_data.get('expected_goals_per_90', '0')
    
    # Additional stats for all positions
    stats['Bonus Points'] = player_data.get('bonus', 0)
    stats['ICT Index'] = player_data.get('ict_index', '0')
    stats['Yellow Cards'] = player_data.get('yellow_cards', 0)
    stats['Red Cards'] = player_data.get('red_cards', 0)
    
    return stats


def get_detailed_player_context(player_id: int, full_name: str, is_comparison=False):
    bootstrap = get_bootstrap()
    player_bootstrap = next((p for p in bootstrap["elements"] if p["id"] == player_id), None)
    player_summary = get_player_summary(player_id)
    
    context_data = f"PLAYER DATA for {full_name}:\n\n"
    
    if player_bootstrap:
        # Get player position and position name
        position_id = player_bootstrap.get('element_type', 0)
        position_types = {pt['id']: pt['singular_name'] for pt in bootstrap['element_types']}
        position_name = position_types.get(position_id, 'Unknown')
        
        context_data += f"Position: {position_name}\n\n"
        
        # Get position-relevant stats
        relevant_stats = get_position_relevant_stats(player_bootstrap, position_id)
        
        context_data += "SEASON TOTALS:\n"
        for stat_name, stat_value in relevant_stats.items():
            context_data += f"- {stat_name}: {stat_value}\n"
        context_data += "\n"
    
    
    if 'history' in player_summary and player_summary['history']:
        recent_history = player_summary['history'][-5:]  # Last 5 gameweeks
        
        if player_bootstrap:
            position_id = player_bootstrap.get('element_type', 0)
            
            # Calculate recent form stats based on position
            if position_id == 1:  # Goalkeeper
                total_clean_sheets = sum(gw.get('clean_sheets', 0) for gw in recent_history)
                total_saves = sum(gw.get('saves', 0) for gw in recent_history)
                total_goals_conceded = sum(gw.get('goals_conceded', 0) for gw in recent_history)
                
                context_data += "RECENT FORM (Last 5 Gameweeks):\n"
                context_data += f"- Clean Sheets: {total_clean_sheets}\n"
                context_data += f"- Saves: {total_saves}\n"
                context_data += f"- Goals Conceded: {total_goals_conceded}\n"
                
            elif position_id in [2, 3, 4]:  
                total_goals = sum(gw.get('goals_scored', 0) for gw in recent_history)
                total_assists = sum(gw.get('assists', 0) for gw in recent_history)
                
                context_data += "RECENT FORM (Last 5 Gameweeks):\n"
                context_data += f"- Goals: {total_goals}\n"
                context_data += f"- Assists: {total_assists}\n"
                
                if position_id == 2:  # Defender
                    total_clean_sheets = sum(gw.get('clean_sheets', 0) for gw in recent_history)
                    context_data += f"- Clean Sheets: {total_clean_sheets}\n"
        
        
        total_minutes = sum(gw.get('minutes', 0) for gw in recent_history)
        total_bonus = sum(gw.get('bonus', 0) for gw in recent_history)
        games_played = len([gw for gw in recent_history if gw.get('minutes', 0) > 0])
        
        context_data += f"- Minutes: {total_minutes}\n"
        context_data += f"- Games Played: {games_played}\n"
        context_data += f"- Bonus Points: {total_bonus}\n\n"
        
        
        context_data += "INDIVIDUAL GAMEWEEK BREAKDOWN:\n"
        for gw in recent_history:
            context_data += f"GW{gw.get('round', 'X')}: {gw.get('minutes', 0)} mins, "
            context_data += f"{gw.get('goals_scored', 0)} goals, {gw.get('assists', 0)} assists, "
            context_data += f"{gw.get('total_points', 0)} pts\n"
    
    
    if 'fixtures' in player_summary and player_summary['fixtures']:
        next_fixtures = player_summary['fixtures'][:5]  
        context_data += "\nUPCOMING FIXTURES (Next 5):\n"
        teams = {team['id']: team for team in bootstrap['teams']}
        
        fixture_summary = []
        for fixture in next_fixtures:
            opponent_team_id = fixture.get('team_a') if fixture.get('is_home') else fixture.get('team_h')
            opponent_name = teams.get(opponent_team_id, {}).get('name', 'Unknown')
            venue = 'H' if fixture.get('is_home') else 'A'
            difficulty = fixture.get('difficulty', 0)
            fixture_text = f"{opponent_name[:3].upper()} ({venue}-{difficulty})"
            fixture_summary.append(fixture_text)
            context_data += f"GW{fixture.get('event', 'X')}: vs {opponent_name} ({venue}) - Difficulty {difficulty}\n"
        
        
        if is_comparison:
            context_data += f"\nTABLE_FRIENDLY_FIXTURES: {', '.join(fixture_summary[:3])}\n"
    
    
    if is_comparison and player_bootstrap:
        context_data += "\nTABLE_FRIENDLY_SUMMARY:\n"
        context_data += f"TABLE_PRICE: {float(player_bootstrap.get('now_cost', 0)) / 10:.1f}\n"
        context_data += f"TABLE_GOALS: {player_bootstrap.get('goals_scored', 0)}\n"
        context_data += f"TABLE_ASSISTS: {player_bootstrap.get('assists', 0)}\n"
        context_data += f"TABLE_MINUTES: {player_bootstrap.get('minutes', 0)}\n"
        context_data += f"TABLE_XG: {player_bootstrap.get('expected_goals', '0')}\n"
        context_data += f"TABLE_XA: {player_bootstrap.get('expected_assists', '0')}\n"
        context_data += f"TABLE_FORM: {player_bootstrap.get('form', '0')}\n"
        context_data += f"TABLE_OWNERSHIP: {player_bootstrap.get('selected_by_percent', '0')}\n"
    
    # RAG FALLBACK: If no context found, try semantic search
    if not context_data.strip() and user_input.strip() and RAG_AVAILABLE:
        print("🧠 Attempting RAG fallback for query...")
        try:
            bootstrap = get_bootstrap()
            rag_context = rag_helper.rag_fallback_search(user_input, bootstrap)
            if rag_context:
                context_data = rag_context
                print(f"✅ RAG found relevant matches")
            else:
                print("❌ RAG found no relevant matches")
        except Exception as e:
            print(f"⚠️ RAG fallback failed: {e}")
    
    return context_data


# -------------------- Routes --------------------
@app.route("/")
def index():
    return render_template("landing.html")  

@app.route("/home")
def home():
    return render_template("home.html")

@app.route("/chat")
def chat():
    return render_template("chat.html")


@app.route("/ask", methods=["POST"])
def ask():
    try:
        user_input = request.json.get("question", "") or request.json.get("message", "")
        quick_mode = request.json.get("quick_mode", True)
        manager_id = request.json.get("manager_id", None)
        manager_name = request.json.get("manager_name", None)

        if not user_input.strip():
            return jsonify({"answer": "Please ask me something about Fantasy Premier League!"})

        # Convert manager_id to int if provided
        if manager_id and str(manager_id).strip():
            try:
                manager_id = int(str(manager_id).strip())
            except (ValueError, TypeError):
                manager_id = None
        else:
            manager_id = None
        
        # Analyze user query and get context data
        try:
            context_data = analyze_user_query(user_input, manager_id)
        except Exception as e:
            print(f"Error analyzing user query: {str(e)}")
            return jsonify({"answer": "❌ **Error:** Unable to fetch current FPL data. The Fantasy Premier League API might be temporarily unavailable. Please try again in a few moments."})
        
        # Check for specific error conditions
        if "MANAGER_ID_REQUIRED" in context_data:
            return jsonify({"answer": "To analyze your team, please set your Manager ID in the settings panel (⚙️ Settings). You can find your Manager ID in the FPL website URL when viewing your team."})
        
        # Check if it's a disambiguation request (multiple players found)
        if context_data and "I found multiple players matching" in context_data:
            return jsonify({"answer": context_data})
        
        # Check if it's a player not found error
        if context_data and "Player(s) Not Found:" in context_data:
            return jsonify({"answer": context_data})

        mode_instruction = ""
        if quick_mode:
            mode_instruction = "\n🚀 **ULTRA-QUICK MODE:** Keep response under 75 words. Use bullet points and emojis. Be extremely concise.\n"
        else:
            mode_instruction = "\n📖 **DETAILED MODE:** You can provide more comprehensive analysis (up to 200 words).\n"
        
        # Build context data string safely
        if context_data and context_data.strip():
            context_section = "CURRENT FPL DATA PROVIDED:\n" + context_data
        else:
            context_section = "No specific FPL data was found for this query. Provide general FPL guidance based on your knowledge."
        
        prompt = f"""{SYSTEM_PROMPT}{mode_instruction}

**CONTEXT: You have been provided with current FPL data from the official API. Use this data to answer the user's question. Do not claim you lack real-time information when FPL data is clearly provided below.**

User Question: {user_input}

{context_section}

**Instructions: Use the FPL data above to provide a comprehensive answer. Base your response on the actual data provided, not general assumptions.**"""

        # Get response from Groq
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",  
                messages=[
                    {
                        "role": "system", 
                        "content": f"{SYSTEM_PROMPT}{mode_instruction}"
                    },
                    {
                        "role": "user", 
                        "content": f"""**CONTEXT: You have been provided with current FPL data from the official API. Use this data to answer the user's question. Do not claim you lack real-time information when FPL data is clearly provided below.**

User Question: {user_input}

{context_section}

**Instructions: Use the FPL data above to provide a comprehensive answer. Base your response on the actual data provided, not general assumptions.**"""
                    }
                ],
                temperature=0.1,  
                max_tokens=800 if quick_mode else 1500,  
                top_p=0.9
            )
            
            answer = completion.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error calling Groq API: {str(e)}")
            return jsonify({"answer": "❌ **AI Error:** Unable to generate response. The AI service might be temporarily unavailable. Please try again in a few moments."})

        return jsonify({"answer": answer})

    except Exception as e:
        print(f"Unexpected error in /ask route: {str(e)}")  # For debugging
        return jsonify({"answer": f"❌ **System Error:** An unexpected error occurred. Please try refreshing the page or asking your question differently. Error: {str(e)[:100]}"})



if __name__ == "__main__":
    
    port = int(os.environ.get('PORT', 8080))
    
    
    debug_mode = False 
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode
    )