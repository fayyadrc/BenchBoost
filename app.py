from flask import Flask, request, jsonify, render_template
import os, json, requests
from dotenv import load_dotenv
import re
from groq import Groq

load_dotenv()

app = Flask(__name__)

# Setup Groq client
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

**RESPONSE RULES - CRITICAL:**
🎯 **KEEP IT SHORT:** Maximum 150 words for text responses
📊 **TABLES MANDATORY:** ALL stats, comparisons, and multi-column data MUST be in tables  
💡 **KEY POINTS ONLY:** Focus on 3-5 essential insights
🚀 **TABLE-FIRST APPROACH:** Use tables for any data with 2+ columns
❌ **NO FLUFF:** Skip lengthy explanations and disclaimers
📋 **STRUCTURED DATA:** Tables for stats, bullets for simple lists only

**Core Principles:**
1. **Use Provided Data:** Utilize the live FPL data confidently
2. **Tables for Stats:** ALL player stats, team data, comparisons in table format
3. **Be Visual:** Tables are easier to scan than bullet lists
4. **Format Consistently:** Tables for data, bullets only for simple points
5. **Show Key Stats:** Focus on decision-making metrics in table format

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

#FPL helper functions
bootstrap_cache = None

def get_bootstrap():
    global bootstrap_cache
    if bootstrap_cache is None:
        bootstrap_cache = fetch_json("bootstrap-static/")
    return bootstrap_cache

def get_player_id_by_name(name: str, return_multiple=False):
    import unicodedata
    
    def normalize_name(text):
        normalized = unicodedata.normalize('NFD', text)
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
        return ascii_text.lower()
    
    data = get_bootstrap()
    players = data["elements"]
    teams = {team['id']: team['name'] for team in data['teams']}
    name_normalized = normalize_name(name)
    
    exact_matches = []
    partial_matches = []
    
    for p in players:
        web_name_normalized = normalize_name(p["web_name"])
        full_name_normalized = normalize_name(f"{p['first_name']} {p['second_name']}")
        
        if name_normalized == web_name_normalized or name_normalized == full_name_normalized:
            team_name = teams.get(p['team'], 'Unknown')
            exact_matches.append((p["id"], p["web_name"], f"{p['first_name']} {p['second_name']}", team_name))
    
    if exact_matches:
        if return_multiple:
            return exact_matches
        else:
            match = exact_matches[0]
            return match[0], match[1], match[2]
    
    for p in players:
        web_name_normalized = normalize_name(p["web_name"])
        full_name_normalized = normalize_name(f"{p['first_name']} {p['second_name']}")
        last_name_normalized = normalize_name(p["second_name"])
        first_name_normalized = normalize_name(p["first_name"])
        team_name = teams.get(p['team'], 'Unknown')
        
        if name_normalized == last_name_normalized:
            partial_matches.append((p["id"], p["web_name"], f"{p['first_name']} {p['second_name']}", team_name))
            continue
        
        if name_normalized == first_name_normalized:
            partial_matches.append((p["id"], p["web_name"], f"{p['first_name']} {p['second_name']}", team_name))
            continue
        
        search_words = name_normalized.split()
        full_name_words = full_name_normalized.split()
        
        if len(search_words) > 1:
            if all(any(search_word in full_word or full_word in search_word for full_word in full_name_words) for search_word in search_words):
                partial_matches.append((p["id"], p["web_name"], f"{p['first_name']} {p['second_name']}", team_name))
                continue
            
            if (len(search_words) == 2 and 
                search_words[0] == first_name_normalized and 
                search_words[1] in last_name_normalized):
                partial_matches.append((p["id"], p["web_name"], f"{p['first_name']} {p['second_name']}", team_name))
                continue
            
        if name_normalized in web_name_normalized or name_normalized in full_name_normalized:
            if (name_normalized in web_name_normalized.split() or 
                name_normalized in full_name_normalized.split() or
                any(name_normalized in word for word in full_name_normalized.split())):
                partial_matches.append((p["id"], p["web_name"], f"{p['first_name']} {p['second_name']}", team_name))
    
    if partial_matches:
        if return_multiple:
            return partial_matches
        else:
            match = partial_matches[0]
            return match[0], match[1], match[2]
    
    if return_multiple:
        return []
    else:
        return (None, None, None)

def create_player_disambiguation_message(matching_players, search_term):
    if len(matching_players) <= 1:
        return None
    
    message = f"I found multiple players matching '{search_term}':\n\n"
    
    for i, (player_id, web_name, full_name, team_name) in enumerate(matching_players, 1):
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
    user_lower = user_input.lower()
    context_data = ""

    manager_keywords = [
        "my team", "team analysis", "my squad", "my players", "analyze my team",
        "tell me about my team", "my current team", "who should i transfer",
        "who should i captain", "my captain", "my vice captain", "my formation",
        "my starting xi", "my bench", "my gameweek", "my points", "my rank",
        "transfer out", "transfer in", "who to transfer", "should i transfer",
        "my transfers", "analyze", "who should i sell", "who should i buy"
    ]
    
    is_manager_query = any(keyword in user_lower for keyword in manager_keywords)
    
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

    comparison_keywords = ["compare", "vs", "versus", "or", "better", "who should i pick", "between"]
    is_comparison = any(keyword in user_lower for keyword in comparison_keywords)
    
    player_keywords = ["player", "stats", "points", "form", "price", "ownership", "goals", "assists", "minutes", "tell me about", "about", "how is", "performance"]
    has_player_keywords = any(keyword in user_lower for keyword in player_keywords)
    
    might_be_player_name = False
    words = user_input.strip().split()
    
    if (len(words) <= 2 and 
        len(user_input.strip()) > 2 and
        not any(word.lower() in ["what", "when", "where", "why", "how", "fixture", "match", "team", "my", "the", "a", "an", "is", "are", "was", "were", "that", "this", "not", "no"] for word in words)):
        
        potential_player = get_player_id_by_name(user_input.strip())
        if potential_player[0] is not None:
            might_be_player_name = True
    
    if has_player_keywords or is_comparison or might_be_player_name:
        words = user_input.split()
        found_players = []
        
        if is_comparison:
            comparison_pattern = r'\b(vs|versus|or|and|between|compare)\b'
            parts = re.split(comparison_pattern, user_input, flags=re.IGNORECASE)
            
            for part in parts:
                if part.lower() in ['vs', 'versus', 'or', 'and', 'between', 'compare']:
                    continue
                
                import string
                cleaned_part = part.translate(str.maketrans('', '', string.punctuation.replace('-', '').replace('\'', '')))
                part_words = cleaned_part.strip().split()
                found_in_part = False
                
                for i in range(len(part_words) - 1):
                    potential_name = f"{part_words[i]} {part_words[i + 1]}"
                    pid, web_name, full_name = get_player_id_by_name(potential_name)
                    if pid and not any(p[0] == pid for p in found_players):
                        found_players.append((pid, web_name, full_name))
                        found_in_part = True
                        break
                
                if not found_in_part:
                    for word in part_words:
                        if word.lower() in ['tell', 'me', 'about', 'the', 'and', 'or', 'stats', 'form', 'player', 'how', 'is', 'performing', 'this', 'season', 'show', 'what', 'are', 'compare', 'vs', 'versus', 'between', 'should', 'i', 'pick', 'who', 'bring', 'team', 'my']:
                            continue
                        
                        pid, web_name, full_name = get_player_id_by_name(word)
                        if pid and not any(p[0] == pid for p in found_players):
                            found_players.append((pid, web_name, full_name))
                            break
        elif might_be_player_name:
            matching_players = get_player_id_by_name(user_input.strip(), return_multiple=True)
            if len(matching_players) > 1:
                disambiguation_msg = create_player_disambiguation_message(matching_players, user_input.strip())
                return disambiguation_msg
            elif len(matching_players) == 1:
                match = matching_players[0]
                found_players.append((match[0], match[1], match[2]))
        else:
            two_word_matches = []
            for i in range(len(words) - 1):
                potential_name = f"{words[i]} {words[i + 1]}"
                if potential_name.lower() not in ['tell me', 'me about', 'about the', 'the player', 'how is', 'what is', 'who is']:
                    matching_players = get_player_id_by_name(potential_name, return_multiple=True)
                    if len(matching_players) > 1:
                        disambiguation_msg = create_player_disambiguation_message(matching_players, potential_name)
                        return disambiguation_msg
                    elif len(matching_players) == 1:
                        match = matching_players[0]
                        two_word_matches.append((match[0], match[1], match[2]))
            
            if two_word_matches:
                found_players.extend(two_word_matches)
            
            elif not found_players and any(keyword in user_lower for keyword in ["tell me about", "about", "stats", "form", "performance"]):
                for word in words:
                    if word.lower() not in ['tell', 'me', 'about', 'the', 'and', 'or', 'stats', 'form', 'player', 'how', 'is', 'performing', 'this', 'season', 'show', 'what', 'are']:
                        matching_players = get_player_id_by_name(word, return_multiple=True)
                        if len(matching_players) > 1:
                            disambiguation_msg = create_player_disambiguation_message(matching_players, word)
                            return disambiguation_msg
                        elif len(matching_players) == 1:
                            match = matching_players[0]
                            if not any(p[0] == match[0] for p in found_players):
                                found_players.append((match[0], match[1], match[2]))
                                break
        
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
        upcoming_fixtures = [f for f in fixtures if not f.get('finished')][:20]
        
        for fixture in upcoming_fixtures:
            home_team = teams.get(fixture['team_h'], {}).get('name', 'Unknown')
            away_team = teams.get(fixture['team_a'], {}).get('name', 'Unknown')
            kickoff = fixture.get('kickoff_time', 'TBD')
            if kickoff != 'TBD':
                try:
                    from datetime import datetime
                    kickoff_dt = datetime.fromisoformat(kickoff.replace('Z', '+00:00'))
                    kickoff = kickoff_dt.strftime('%d %b %H:%M')
                except:
                    pass
            context_data += f"GW{fixture.get('event', 'X')}: {home_team} vs {away_team} - {kickoff}\n"

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
        
        for event in events[current_gw-1:current_gw+2]:
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
    stats = {}
    
    stats['Total Points'] = player_data.get('total_points', 0)
    stats['Minutes'] = player_data.get('minutes', 0)
    stats['Price'] = f"£{float(player_data.get('now_cost', 0)) / 10:.1f}m"
    stats['Ownership'] = f"{player_data.get('selected_by_percent', '0')}%"
    stats['Form'] = player_data.get('form', '0')
    stats['Points per Game'] = player_data.get('points_per_game', '0')
    
    if position_id == 1:
        stats['Clean Sheets'] = player_data.get('clean_sheets', 0)
        stats['Goals Conceded'] = player_data.get('goals_conceded', 0)
        stats['Saves'] = player_data.get('saves', 0)
        stats['Penalties Saved'] = player_data.get('penalties_saved', 0)
        stats['Expected Goals Conceded (xGC)'] = player_data.get('expected_goals_conceded', '0')
        stats['Saves per 90'] = player_data.get('saves_per_90', '0')
        stats['Clean Sheets per 90'] = player_data.get('clean_sheets_per_90', '0')
        
    elif position_id == 2:
        stats['Clean Sheets'] = player_data.get('clean_sheets', 0)
        stats['Goals'] = player_data.get('goals_scored', 0)
        stats['Assists'] = player_data.get('assists', 0)
        stats['Goals Conceded'] = player_data.get('goals_conceded', 0)
        stats['Expected Goals (xG)'] = player_data.get('expected_goals', '0')
        stats['Expected Assists (xA)'] = player_data.get('expected_assists', '0')
        stats['Expected Goals Conceded (xGC)'] = player_data.get('expected_goals_conceded', '0')
        stats['Clean Sheets per 90'] = player_data.get('clean_sheets_per_90', '0')
        stats['Defensive Actions'] = player_data.get('clearances_blocks_interceptions', 0)
        
    elif position_id == 3:
        stats['Goals'] = player_data.get('goals_scored', 0)
        stats['Assists'] = player_data.get('assists', 0)
        stats['Clean Sheets'] = player_data.get('clean_sheets', 0)
        stats['Expected Goals (xG)'] = player_data.get('expected_goals', '0')
        stats['Expected Assists (xA)'] = player_data.get('expected_assists', '0')
        stats['Expected Goal Involvements (xGI)'] = player_data.get('expected_goal_involvements', '0')
        stats['Creativity'] = player_data.get('creativity', '0')
        stats['Threat'] = player_data.get('threat', '0')
        
    elif position_id == 4:
        stats['Goals'] = player_data.get('goals_scored', 0)
        stats['Assists'] = player_data.get('assists', 0)
        stats['Expected Goals (xG)'] = player_data.get('expected_goals', '0')
        stats['Expected Assists (xA)'] = player_data.get('expected_assists', '0')
        stats['Expected Goal Involvements (xGI)'] = player_data.get('expected_goal_involvements', '0')
        stats['Threat'] = player_data.get('threat', '0')
        stats['Expected Goals per 90'] = player_data.get('expected_goals_per_90', '0')
    
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
        position_id = player_bootstrap.get('element_type', 0)
        position_types = {pt['id']: pt['singular_name'] for pt in bootstrap['element_types']}
        position_name = position_types.get(position_id, 'Unknown')
        
        context_data += f"Position: {position_name}\n\n"
        
        relevant_stats = get_position_relevant_stats(player_bootstrap, position_id)
        
        context_data += "SEASON TOTALS:\n"
        for stat_name, stat_value in relevant_stats.items():
            context_data += f"- {stat_name}: {stat_value}\n"
        context_data += "\n"
    
    if 'history' in player_summary and player_summary['history']:
        recent_history = player_summary['history'][-5:]
        
        if player_bootstrap:
            position_id = player_bootstrap.get('element_type', 0)
            
            if position_id == 1:
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
                
                if position_id == 2:
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
    
    return context_data

# Routes
@app.route("/")
def index():
    return render_template("index.html")  

@app.route("/ask", methods=["POST"])
def ask():
    try:
        user_input = request.json.get("message", "")
        quick_mode = request.json.get("quick_mode", True)
        manager_id = request.json.get("manager_id", None)

        if not user_input.strip():
            return jsonify({"answer": "Please ask me something about Fantasy Premier League!"})

        if manager_id and str(manager_id).strip():
            try:
                manager_id = int(str(manager_id).strip())
            except (ValueError, TypeError):
                manager_id = None
        else:
            manager_id = None
        
        context_data = analyze_user_query(user_input, manager_id)
        
        if "MANAGER_ID_REQUIRED" in context_data:
            return jsonify({"answer": "To analyze your team, please set your Manager ID in the settings panel (⚙️ Settings). You can find your Manager ID in the FPL website URL when viewing your team."})

        mode_instruction = ""
        if quick_mode:
            mode_instruction = "\n🚀 **ULTRA-QUICK MODE:** Keep response under 75 words. Use bullet points and emojis. Be extremely concise.\n"
        else:
            mode_instruction = "\n📖 **DETAILED MODE:** You can provide more comprehensive analysis (up to 200 words).\n"
        
        prompt = f"""{SYSTEM_PROMPT}{mode_instruction}

**CONTEXT: You have been provided with current FPL data from the official API. Use this data to answer the user's question. Do not claim you lack real-time information when FPL data is clearly provided below.**

User Question: {user_input}

{f"CURRENT FPL DATA PROVIDED:\n{context_data}" if context_data else "No specific FPL data was found for this query. Provide general FPL guidance based on your knowledge."}

**Instructions: Use the FPL data above to provide a comprehensive answer. Base your response on the actual data provided, not general assumptions."""

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

{f"CURRENT FPL DATA PROVIDED:\n{context_data}" if context_data else "No specific FPL data was found for this query. Provide general FPL guidance based on your knowledge."}

**Instructions: Use the FPL data above to provide a comprehensive answer. Base your response on the actual data provided, not general assumptions."""
                }
            ],
            temperature=0.1,  
            max_tokens=800 if quick_mode else 1500,  
            top_p=0.9
        )
        
        answer = completion.choices[0].message.content.strip()

        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"answer": f"Sorry, I encountered an error: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True, port=5002)
