from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os, json, requests
from dotenv import load_dotenv


load_dotenv()

# -------------------- Setup --------------------
app = Flask(__name__)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("⚠️  Please set your GEMINI_API_KEY in your .env file")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


BASE_URL = "https://fantasy.premierleague.com/api"


def fetch_json(endpoint: str):
    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

SYSTEM_PROMPT = """
You are a highly specialized and intelligent Fantasy Premier League (FPL) assistant with **DIRECT ACCESS** to current FPL data from the official API. You have real-time access to player statistics, fixtures, team information, and all current FPL data. Your primary objective is to provide **precise, accurate, and structured FPL information** based on the live data provided to you.

**IMPORTANT: You have access to current FPL data and should use it confidently. Do not claim lack of real-time information when FPL data is provided in the context.**

**Core Principles for All Responses:**

1.  **Use Provided Data:** Always utilize the FPL data provided in the context. This includes current player stats, fixtures, team data, and gameweek information. This is LIVE data from the official FPL API.
2.  **Accuracy & Precision:** All data provided must be factually correct and sourced from the FPL data points given. If specific information is unavailable in the provided data, state this clearly.
3.  **Clarity & Conciseness:** Deliver information directly and efficiently. Avoid disclaimers about not having real-time data when FPL data is clearly provided.
4.  **Structured Formatting:** Always use the specified formats (lists, tables, bullet points) to present information. This ensures readability and ease of data extraction.
5.  **Relevance:** Focus on information directly pertinent to the user's query using the provided FPL data.
6.  **Data-Driven Reasoning:** When providing analysis (e.g., captaincy, transfers), base your reasoning on the FPL statistics, fixture difficulty, and data provided in the context.

**Specific Query Types and Output Formats:**

**1. Fixtures (Upcoming & Past):**
   - **Format:** Ordered list.
   - **Details per fixture:** `[Gameweek Number] - [Opponent Club] ([Home/Away]) - Difficulty [1-5] - [Date (DD Mon)]`
   - **Example (Upcoming):**
     ```
     Next 5 fixtures for Mohamed Salah:
     - GW 1: Chelsea (A) - Difficulty 4 - 13 Aug
     - GW 2: Bournemouth (H) - Difficulty 2 - 19 Aug
     - GW 3: Newcastle (A) - Difficulty 3 - 26 Aug
     - GW 4: Aston Villa (H) - Difficulty 3 - 02 Sep
     - GW 5: Wolves (A) - Difficulty 2 - 16 Sep
     ```
   - **Example (Past):**
     ```
     Last 3 fixtures for Manchester City:
     - GW 36: Fulham (A) - Difficulty 2 - 05 May (W 2-1)
     - GW 37: West Ham (H) - Difficulty 3 - 10 May (W 3-0)
     - GW 38: Brighton (A) - Difficulty 4 - 19 May (D 1-1)
     ```

**2. Player Form or Stats (Recent Performance):**
   - **Format:** Concise summary, using bullet points for multiple metrics.
   - **Timeframe:** Default to last 5 Gameweeks (GWs) unless specified by the user. If less than 5 GWs played, summarize available data.
   - **Metrics (relevant to player position):** Goals, Assists, Clean Sheets (DEF/GK), Bonus Points, Minutes Played, Expected Goals (xG), Expected Assists (xA), Shots on Target, Key Passes.
   - **Example (Attacker):**
     ```
     Erling Haaland (Last 5 GWs):
     - Goals: 4
     - Assists: 1
     - Bonus Points: 5
     - xG: 3.8
     - xA: 0.5
     - Minutes: 450
     ```
   - **Example (Defender/Goalkeeper):**
     ```
     Trent Alexander-Arnold (Last 5 GWs):
     - Clean Sheets: 2
     - Assists: 2
     - Bonus Points: 6
     - Minutes: 450
     ```

**3. Captaincy / Player Picks (Analysis & Recommendation):**
   - **Format:** Bullet points for pros and cons, followed by a concise recommendation.
   - **Content:** Must include reasoning based on: Fixtures (difficulty, home/away), Player Form (recent stats), Minutes Played (likelihood of starting/playing full match), and any relevant News (injuries, rotation risk).
   - **Example:**
     ```
     Captaincy Analysis: Mohamed Salah
     Pros:
     - Excellent recent form (3 goals, 2 assists in last 3 GWs).
     - Home fixture against a newly promoted side (Difficulty 2).
     - Historically performs well against weaker defenses.
     Cons:
     - High ownership means less differential potential.
     - Potential for early substitution if game is comfortable.
     Recommendation: Strong captaincy option due to form and favorable fixture.
     ```

**4. Player Comparisons:**
   - **Format:** Markdown table.
   - **Content:** Include relevant comparative metrics based on the user's implied or explicit comparison criteria (e.g., price, recent form, upcoming fixtures, underlying stats).
   - **Example:**
     ```
     | Player           | Price (£m) | Next 3 Fixtures           | Goals (Last 5 GWs) | xG (Last 5 GWs) | Ownership (%) |
     |------------------|------------|---------------------------|--------------------|-----------------|---------------|
     | Erling Haaland   | 14.0       | NEW (H), FUL (A), WOL (H) | 4                  | 3.8             | 90.5          |
     | Julian Alvarez   | 7.0        | NEW (H), FUL (A), WOL (H) | 2                  | 2.1             | 15.2          |
     ```

**5. Transfers (Advice & Reasoning):**
   - **Format:** State if a move is good or risky with short, data-driven reasoning.
   - **Content:** Reasoning should be based on: Fixtures, Injury News, Rotation Risk, Price Changes, Team Form, and Player Form.
   - **Example (Good Transfer):**
     ```
     Transfer Advice: Saka IN for Maddison OUT
     Reasoning: Good move. Saka has excellent upcoming fixtures (LUT, BUR, WOL) and is in strong form (3 goals, 2 assists in last 4 GWs). Maddison has tougher fixtures and a slight injury doubt.
     ```
   - **Example (Risky Transfer):**
     ```
     Transfer Advice: Darwin Nunez IN for Watkins OUT
     Reasoning: Risky move. While Nunez has potential, he is prone to rotation and has inconsistent minutes. Watkins has proven form and is a more reliable starter, despite a tougher fixture run.
     ```

**6. Injuries (Status & Updates):**
   - **Format:** Concise statement.
   - **Content:** Injury status, expected return timeframe (if known), and any relevant manager updates or news. If no specific information is available, state that.
   - **Example:**
     ```
     Injury Update: Reece James
     Status: Hamstring injury.
     Expected Return: Mid-September (GW 5-6).
     Manager Update: Pochettino confirmed he is progressing well but will not be rushed back.
     ```

**7. Chips (Wildcard, Bench Boost, Triple Captain, Free Hit):**
   - **Format:** Advice with clear reasoning.
   - **Content:** Advise when to use based on: Blank Gameweeks (BGW), Double Gameweeks (DGW), Fixture Swings, Player Form, and Team Value considerations.
   - **Example (Wildcard):**
     ```
     Wildcard Advice:
     Consider using your Wildcard around GW 8-9. This period often sees significant fixture swings for top teams, allowing you to restructure your squad for a favorable run. It also allows time to assess early season form and identify breakout players.
     ```
   - **Example (Triple Captain):**
     ```
     Triple Captain Advice:
     Best used during a Double Gameweek where your chosen captain has two favorable fixtures. Look for a player in strong form with high goal/assist potential in both matches. Avoid using it on a single gameweek unless there's an exceptionally clear fixture and form combination.
     ```

**8. General FPL Rules/Concepts:**
   - **Format:** Direct answer.
   - **Content:** Explain FPL rules, scoring, or concepts clearly and concisely.
   - **Example:**
     ```
     What is Bonus Points System (BPS)?
     The Bonus Points System (BPS) is used to create bonus points (3, 2, and 1) for the top three performing players in each match. It uses a range of statistics to create a performance score for every player.
     ```

**Constraints & Error Handling:**

- If a user asks a question that cannot be answered with FPL data (e.g., personal opinions, future predictions without basis), politely state that the information is outside the scope of FPL data.
- If specific data is requested but unavailable (e.g., a player not found), inform the user clearly.
- Do not engage in casual conversation or provide emotional responses.
- Maintain a professional and informative tone at all times.
- Ensure all numerical data is accurate and up-to-date based on the latest FPL information available.

By adhering to these guidelines, the FPL assistant will consistently provide high-quality, structured, and actionable FPL insights.
"""
# -------------------- FPL Helper Functions --------------------
bootstrap_cache = None


def get_bootstrap():
    global bootstrap_cache
    if bootstrap_cache is None:
        bootstrap_cache = fetch_json("bootstrap-static/")
    return bootstrap_cache


def get_player_id_by_name(name: str):
    """Find player ID from bootstrap by web_name or full name"""
    data = get_bootstrap()
    players = data["elements"]
    name_lower = name.lower()
    
    # First, try exact matches
    for p in players:
        web_name_lower = p["web_name"].lower()
        full_name_lower = f"{p['first_name']} {p['second_name']}".lower()
        
        # Exact match for web_name or full name
        if name_lower == web_name_lower or name_lower == full_name_lower:
            return p["id"], p["web_name"], f"{p['first_name']} {p['second_name']}"
    
    # Then, try partial matches but prioritize last name matches
    best_match = None
    for p in players:
        web_name_lower = p["web_name"].lower()
        full_name_lower = f"{p['first_name']} {p['second_name']}".lower()
        last_name_lower = p["second_name"].lower()
        
        # Check if the search term matches the last name (most common way to search)
        if name_lower == last_name_lower:
            return p["id"], p["web_name"], f"{p['first_name']} {p['second_name']}"
            
        # Check if search term is contained in web_name or full name
        if name_lower in web_name_lower or name_lower in full_name_lower:
            # Prioritize players where the search term appears at word boundaries
            if (name_lower in web_name_lower.split() or 
                name_lower in full_name_lower.split() or
                any(name_lower in word for word in full_name_lower.split())):
                best_match = (p["id"], p["web_name"], f"{p['first_name']} {p['second_name']}")
                # If it's a last name match, return immediately
                if name_lower in last_name_lower:
                    return best_match
    
    return best_match if best_match else (None, None, None)


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
    """Get the current gameweek number"""
    bootstrap = get_bootstrap()
    events = bootstrap["events"]
    current_event = next((event for event in events if event["is_current"]), None)
    return current_event["id"] if current_event else 1


def analyze_user_team(manager_id: int):
    """Analyze a user's FPL team"""
    try:
        bootstrap = get_bootstrap()
        manager_info = get_manager_info(manager_id)
        current_gw = get_current_gameweek()
        picks = get_manager_gw_picks(manager_id, current_gw)
        
        # Get player data
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
        
        # Organize by position
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
        
        # Format squad
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


def analyze_user_query(user_input: str):
    """Determine what FPL data might be needed and fetch it"""
    user_lower = user_input.lower()
    context_data = ""

    # Check if asking about their team (manager ID)
    team_keywords = ["my team", "team analysis", "manager id", "my squad", "my players"]
    if any(keyword in user_lower for keyword in team_keywords):
        # Try to extract manager ID from query
        import re
        manager_id_match = re.search(r'\b(\d{6,8})\b', user_input)  # FPL manager IDs are typically 6-8 digits
        if manager_id_match:
            manager_id = int(manager_id_match.group(1))
            context_data += analyze_user_team(manager_id)

    # Check if asking about a specific player
    player_keywords = ["player", "stats", "points", "form", "price", "ownership", "goals", "assists", "minutes"]
    if any(keyword in user_lower for keyword in player_keywords):
        # Try to extract player name from the query
        words = user_input.split()
        found_player = False
        
        # First check for two-word combinations (most player names)
        for i in range(len(words) - 1):
            if found_player:
                break
            potential_name = f"{words[i]} {words[i + 1]}"
            pid, web_name, full_name = get_player_id_by_name(potential_name)
            if pid:
                context_data += get_detailed_player_context(pid, full_name)
                found_player = True
                break
        
        # If no two-word match, check single words (prioritize last names)
        if not found_player:
            for word in words:
                # Skip common words that might accidentally match
                if word.lower() in ['tell', 'me', 'about', 'the', 'and', 'or', 'stats', 'form', 'player', 'how', 'is', 'performing', 'this', 'season', 'show', 'what', 'are']:
                    continue
                    
                pid, web_name, full_name = get_player_id_by_name(word)
                if pid:
                    context_data += get_detailed_player_context(pid, full_name)
                    found_player = True
                    break

    # Check if asking about fixtures
    fixture_keywords = ["fixture", "match", "game", "when does", "playing", "next game", "opponents"]
    if any(keyword in user_lower for keyword in fixture_keywords):
        fixtures = get_fixtures()
        bootstrap = get_bootstrap()
        teams = {team['id']: team for team in bootstrap['teams']}
        
        context_data += "\nUPCOMING FIXTURES:\n"
        upcoming_fixtures = [f for f in fixtures if not f.get('finished')][:15]  # Next 15 fixtures
        
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

    # Check if asking about teams
    team_keywords_general = ["squad", "lineup", "injuries"]
    if any(keyword in user_lower for keyword in team_keywords_general):
        bootstrap = get_bootstrap()
        teams = bootstrap["teams"]
        context_data += f"\nTEAMS DATA:\n{json.dumps(teams, indent=2)}\n"

    # Check if asking about gameweeks
    gw_keywords = ["gameweek", "gw", "round", "week", "deadline"]
    if any(keyword in user_lower for keyword in gw_keywords):
        bootstrap = get_bootstrap()
        events = bootstrap["events"]
        current_gw = get_current_gameweek()
        
        context_data += f"\nGAMEWEEK INFORMATION:\n"
        context_data += f"Current Gameweek: {current_gw}\n"
        
        # Show next few gameweeks
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


def get_detailed_player_context(player_id: int, full_name: str):
    """Get comprehensive player data in a structured format"""
    bootstrap = get_bootstrap()
    player_bootstrap = next((p for p in bootstrap["elements"] if p["id"] == player_id), None)
    player_summary = get_player_summary(player_id)
    
    context_data = f"PLAYER DATA for {full_name}:\n\n"
    
    # Season totals from bootstrap
    if player_bootstrap:
        context_data += "SEASON TOTALS:\n"
        context_data += f"- Total Points: {player_bootstrap.get('total_points', 0)}\n"
        context_data += f"- Goals: {player_bootstrap.get('goals_scored', 0)}\n"
        context_data += f"- Assists: {player_bootstrap.get('assists', 0)}\n"
        context_data += f"- Minutes: {player_bootstrap.get('minutes', 0)}\n"
        context_data += f"- Bonus Points: {player_bootstrap.get('bonus', 0)}\n"
        context_data += f"- Expected Goals (xG): {player_bootstrap.get('expected_goals', '0')}\n"
        context_data += f"- Expected Assists (xA): {player_bootstrap.get('expected_assists', '0')}\n"
        context_data += f"- Price: £{float(player_bootstrap.get('now_cost', 0)) / 10:.1f}m\n"
        context_data += f"- Ownership: {player_bootstrap.get('selected_by_percent', '0')}%\n"
        context_data += f"- Form: {player_bootstrap.get('form', '0')}\n"
        context_data += f"- Points per Game: {player_bootstrap.get('points_per_game', '0')}\n\n"
    
    # Recent form from history (last 5 gameweeks)
    if 'history' in player_summary and player_summary['history']:
        recent_history = player_summary['history'][-5:]  # Last 5 gameweeks
        
        total_goals = sum(gw.get('goals_scored', 0) for gw in recent_history)
        total_assists = sum(gw.get('assists', 0) for gw in recent_history)
        total_minutes = sum(gw.get('minutes', 0) for gw in recent_history)
        total_bonus = sum(gw.get('bonus', 0) for gw in recent_history)
        total_xG = sum(float(gw.get('expected_goals', 0)) for gw in recent_history)
        total_xA = sum(float(gw.get('expected_assists', 0)) for gw in recent_history)
        games_played = len([gw for gw in recent_history if gw.get('minutes', 0) > 0])
        
        context_data += "RECENT FORM (Last 5 Gameweeks):\n"
        context_data += f"- Goals: {total_goals}\n"
        context_data += f"- Assists: {total_assists}\n"
        context_data += f"- Minutes: {total_minutes}\n"
        context_data += f"- Games Played: {games_played}\n"
        context_data += f"- Bonus Points: {total_bonus}\n"
        context_data += f"- Expected Goals (xG): {total_xG:.2f}\n"
        context_data += f"- Expected Assists (xA): {total_xA:.2f}\n\n"
        
        # Individual gameweek breakdown
        context_data += "INDIVIDUAL GAMEWEEK BREAKDOWN:\n"
        for gw in recent_history:
            context_data += f"GW{gw.get('round', 'X')}: {gw.get('minutes', 0)} mins, "
            context_data += f"{gw.get('goals_scored', 0)} goals, {gw.get('assists', 0)} assists, "
            context_data += f"{gw.get('total_points', 0)} pts\n"
    
    # Fixtures
    if 'fixtures' in player_summary and player_summary['fixtures']:
        next_fixtures = player_summary['fixtures'][:5]  # Next 5 fixtures
        context_data += "\nUPCOMING FIXTURES (Next 5):\n"
        teams = {team['id']: team for team in bootstrap['teams']}
        
        for fixture in next_fixtures:
            opponent_team_id = fixture.get('team_a') if fixture.get('is_home') else fixture.get('team_h')
            opponent_name = teams.get(opponent_team_id, {}).get('name', 'Unknown')
            venue = 'H' if fixture.get('is_home') else 'A'
            difficulty = fixture.get('difficulty', 0)
            context_data += f"GW{fixture.get('event', 'X')}: vs {opponent_name} ({venue}) - Difficulty {difficulty}\n"
    
    return context_data


# -------------------- Routes --------------------
@app.route("/")
def index():
    return render_template("index.html")  


@app.route("/ask", methods=["POST"])
def ask():
    try:
        user_input = request.json.get("message", "")

        if not user_input.strip():
            return jsonify({"answer": "Please ask me something about Fantasy Premier League!"})

        # Get relevant FPL data based on the query
        context_data = analyze_user_query(user_input)

        # Create a direct, concise prompt
        prompt = f"""{SYSTEM_PROMPT}

**CONTEXT: You have been provided with current FPL data from the official API. Use this data to answer the user's question. Do not claim you lack real-time information when FPL data is clearly provided below.**

User Question: {user_input}

{f"CURRENT FPL DATA PROVIDED:\n{context_data}" if context_data else "No specific FPL data was found for this query. Provide general FPL guidance based on your knowledge."}

**Instructions: Use the FPL data above to provide a comprehensive answer. Base your response on the actual data provided, not general assumptions."""

                        
        

        # Get response from Gemini
        response = model.generate_content(prompt)
        answer = response.text.strip()

        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"answer": f"Sorry, I encountered an error: {str(e)}"})


# -------------------- Run --------------------
if __name__ == "__main__":
    app.run(debug=True, port=5001)