import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import time
from collections import defaultdict

# --------------------
# FILE PATHS & CREDENTIALS
# --------------------
GROUP_SCHEDULE_FILE = "group_schedule.csv"
SCORES_FILE = "scores.csv"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "rhl2025"

# --------------------
# TEAM DATA
# --------------------
teams = [
    {"name": "Royal Lions", "group": "A", "code": "A1"},
    {"name": "Royal Tuskers", "group": "A", "code": "A2"},
    {"name": "Royal Panthers", "group": "A", "code": "A3"},
    {"name": "Royal Sharks", "group": "B", "code": "B1"},
    {"name": "Royal Tigers", "group": "B", "code": "B2"},
    {"name": "Royal Leopards", "group": "B", "code": "B3"},
    {"name": "Royal Cheetahs", "group": "C", "code": "C1"},
    {"name": "Royal Bulls", "group": "C", "code": "C2"},
    {"name": "Royal Zebras", "group": "C", "code": "C3"},
    {"name": "Royal Eagles", "group": "D", "code": "D1"},
    {"name": "Royal Rhinos", "group": "D", "code": "D2"},
    {"name": "Royal Wolves", "group": "D", "code": "D3"}
]
team_dict = {t["code"]: t["name"] for t in teams}

# Mapping for resolving knockout placeholders (if needed)
knockout_map = {
    "QF1": "Quarterfinal 1", "QF2": "Quarterfinal 2",
    "QF3": "Quarterfinal 3", "QF4": "Quarterfinal 4",
    "SF1": "Semifinal 1",  "SF2": "Semifinal 2"
}

# --------------------
# HELPER FUNCTIONS
# --------------------
def load_csv(file, columns):
    if os.path.exists(file):
        return pd.read_csv(file)
    else:
        df = pd.DataFrame(columns=columns)
        df.to_csv(file, index=False)
        return df

def replace_codes_with_names(teams_str):
    for code, name in team_dict.items():
        teams_str = teams_str.replace(code, name)
    return teams_str

def check_login(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def update_score(match, score):
    scores = load_csv(SCORES_FILE, ["match", "score"])
    if match in scores["match"].values:
        scores.loc[scores["match"] == match, "score"] = score
    else:
        new_row = pd.DataFrame({"match": [match], "score": [score]})
        scores = pd.concat([scores, new_row], ignore_index=True)
    scores.to_csv(SCORES_FILE, index=False)

def calculate_group_standings(group_schedule, scores):
    standings = {}
    groups = group_schedule["group"].unique()
    for group in groups:
        group_matches = group_schedule[group_schedule["group"] == group]
        teams_in_group = [t["code"] for t in teams if t["group"] == group]
        standings[group] = {team: {"points": 0, "wins": 0, "losses": 0, "gf": 0, "ga": 0}
                             for team in teams_in_group}
        for _, row in group_matches.iterrows():
            score_val = scores[scores["match"] == row["match"]]["score"].values
            if len(score_val) > 0 and pd.notna(score_val[0]):
                t1, t2 = row["teams"].split(" vs ")
                try:
                    s1, s2 = map(int, score_val[0].split("-"))
                except ValueError:
                    continue
                standings[group][t1]["gf"] += s1
                standings[group][t1]["ga"] += s2
                standings[group][t2]["gf"] += s2
                standings[group][t2]["ga"] += s1
                if s1 > s2:
                    standings[group][t1]["points"] += 3
                    standings[group][t1]["wins"] += 1
                    standings[group][t2]["losses"] += 1
                elif s2 > s1:
                    standings[group][t2]["points"] += 3
                    standings[group][t2]["wins"] += 1
                    standings[group][t1]["losses"] += 1
                else:
                    standings[group][t1]["points"] += 1
                    standings[group][t2]["points"] += 1
    for group in standings:
        standings[group] = sorted(standings[group].items(),
                                  key=lambda x: (x[1]["points"], x[1]["gf"] - x[1]["ga"], x[1]["gf"]),
                                  reverse=True)
    return standings

def generate_knockout_schedule(standings, last_group_time):
    """Generate the Cup knockout bracket using top‐2 teams from each group."""
    knockout_matches = []
    match_id = 13
    start_time = datetime.strptime(last_group_time, "%H:%M:%S") + timedelta(minutes=3)
    # Quarterfinals: Pairings based on the standings
    qf_teams = [
        (f"{team_dict[standings['A'][0][0]]}", f"{team_dict[standings['C'][1][0]]}", "Quarterfinal 1"),
        (f"{team_dict[standings['B'][0][0]]}", f"{team_dict[standings['D'][1][0]]}", "Quarterfinal 2"),
        (f"{team_dict[standings['C'][0][0]]}", f"{team_dict[standings['A'][1][0]]}", "Quarterfinal 3"),
        (f"{team_dict[standings['D'][0][0]]}", f"{team_dict[standings['B'][1][0]]}", "Quarterfinal 4")
    ]
    for t1, t2, round_name in qf_teams:
        end_time = start_time + timedelta(minutes=12)
        knockout_matches.append({
            "match": match_id,
            "teams": f"{t1} vs {t2}",
            "group": round_name,
            "start_time": start_time.strftime("%H:%M:%S"),
            "end_time": end_time.strftime("%H:%M:%S")
        })
        match_id += 1
        start_time = end_time + timedelta(minutes=3)
    # Semifinals
    semi_teams = [
        ("Winner QF1", "Winner QF2", "Semifinal 1"),
        ("Winner QF3", "Winner QF4", "Semifinal 2")
    ]
    for t1, t2, round_name in semi_teams:
        end_time = start_time + timedelta(minutes=12)
        knockout_matches.append({
            "match": match_id,
            "teams": f"{t1} vs {t2}",
            "group": round_name,
            "start_time": start_time.strftime("%H:%M:%S"),
            "end_time": end_time.strftime("%H:%M:%S")
        })
        match_id += 1
        start_time = end_time + timedelta(minutes=3)
    # Finals & Third-Place playoff
    final_teams = [
        ("Loser SF1", "Loser SF2", "Cup 3rd Place Playoff", 12),
        ("Winner SF1", "Winner SF2", "Cup Final", 17)
    ]
    for t1, t2, round_name, duration in final_teams:
        end_time = start_time + timedelta(minutes=duration)
        knockout_matches.append({
            "match": match_id,
            "teams": f"{t1} vs {t2}",
            "group": round_name,
            "start_time": start_time.strftime("%H:%M:%S"),
            "end_time": end_time.strftime("%H:%M:%S")
        })
        match_id += 1
        start_time = end_time + timedelta(minutes=3)
    return pd.DataFrame(knockout_matches)

def generate_bowl_schedule(standings, last_group_time):
    """Generate the Bowl bracket using the 3rd-place teams from each group."""
    knockout_matches = []
    match_id = 25  # IDs for Bowl bracket start after Cup
    start_time = datetime.strptime(last_group_time, "%H:%M:%S") + timedelta(minutes=5)
    # Assume 3rd place teams from groups A-D form the Bowl (4 teams total)
    bowl_teams = [
        team_dict[standings["A"][2][0]],
        team_dict[standings["B"][2][0]],
        team_dict[standings["C"][2][0]],
        team_dict[standings["D"][2][0]],
    ]
    # Bowl Semifinals
    sf_pairs = [
        (bowl_teams[0], bowl_teams[1], "Bowl Semifinal 1"),
        (bowl_teams[2], bowl_teams[3], "Bowl Semifinal 2"),
    ]
    for t1, t2, round_name in sf_pairs:
        end_time = start_time + timedelta(minutes=12)
        knockout_matches.append({
            "match": match_id,
            "teams": f"{t1} vs {t2}",
            "group": round_name,
            "start_time": start_time.strftime("%H:%M:%S"),
            "end_time": end_time.strftime("%H:%M:%S")
        })
        match_id += 1
        start_time = end_time + timedelta(minutes=3)
    # Bowl Finals & Third-Place playoff
    final_teams = [
        ("Loser Bowl Semifinal 1", "Loser Bowl Semifinal 2", "Bowl 3rd Place", 12),
        ("Winner Bowl Semifinal 1", "Winner Bowl Semifinal 2", "Bowl Final", 17),
    ]
    for t1, t2, round_name, duration in final_teams:
        end_time = start_time + timedelta(minutes=duration)
        knockout_matches.append({
            "match": match_id,
            "teams": f"{t1} vs {t2}",
            "group": round_name,
            "start_time": start_time.strftime("%H:%M:%S"),
            "end_time": end_time.strftime("%H:%M:%S")
        })
        match_id += 1
        start_time = end_time + timedelta(minutes=3)
    return pd.DataFrame(knockout_matches)

def resolve_knockout_teams(full_schedule, scores):
    """Replace placeholders (e.g., 'Winner QF1') with the actual team names based on match scores."""
    for i, row in full_schedule.iterrows():
        if "Winner" in row["teams"] or "Loser" in row["teams"]:
            t1, t2 = row["teams"].split(" vs ")
            for team in [t1, t2]:
                if "Winner" in team or "Loser" in team:
                    try:
                        if "Winner" in team:
                            bracket_ref = team.split("Winner ")[1].strip()
                        else:
                            bracket_ref = team.split("Loser ")[1].strip()
                    except IndexError:
                        continue
                    mask = full_schedule["group"].str.contains(bracket_ref, case=False, na=False)
                    if not full_schedule[mask].empty:
                        match_id = full_schedule[mask]["match"].values[0]
                        score_val = scores[scores["match"] == match_id]["score"].values
                        if len(score_val) > 0 and pd.notna(score_val[0]):
                            prev_match_teams = full_schedule[full_schedule["match"] == match_id]["teams"].values[0]
                            prev_t1, prev_t2 = prev_match_teams.split(" vs ")
                            try:
                                s1, s2 = map(int, score_val[0].split("-"))
                            except ValueError:
                                continue
                            if "Winner" in team:
                                winner = prev_t1 if s1 > s2 else prev_t2
                                full_schedule.loc[i, "teams"] = full_schedule.loc[i, "teams"].replace(team, winner)
                            else:
                                loser = prev_t2 if s1 > s2 else prev_t1
                                full_schedule.loc[i, "teams"] = full_schedule.loc[i, "teams"].replace(team, loser)
    return full_schedule

def load_full_schedule():
    """
    Load group stage schedule and scores.
    If every group match has a score (i.e. group stage complete),
    generate the Cup and Bowl knockout brackets based on final standings.
    Otherwise, only the group stage matches are returned.
    """
    group_schedule = load_csv(GROUP_SCHEDULE_FILE, ["match", "teams", "group", "start_time", "end_time"])
    scores = load_csv(SCORES_FILE, ["match", "score"])
    
    # Check if all group stage matches have been completed
    group_stage_complete = True
    for _, row in group_schedule.iterrows():
        score_val = scores[scores["match"] == row["match"]]["score"].values
        if len(score_val) == 0 or pd.isna(score_val[0]):
            group_stage_complete = False
            break
    
    if group_stage_complete:
        standings = calculate_group_standings(group_schedule, scores)
        last_group_time = group_schedule["end_time"].iloc[-1]
        cup_schedule = generate_knockout_schedule(standings, last_group_time)
        bowl_schedule = generate_bowl_schedule(standings, last_group_time)
        knockout_schedule = pd.concat([cup_schedule, bowl_schedule], ignore_index=True)
        full_schedule = pd.concat([group_schedule, knockout_schedule], ignore_index=True)
    else:
        full_schedule = group_schedule.copy()
    
    full_schedule = resolve_knockout_teams(full_schedule, scores)
    full_schedule["teams"] = full_schedule["teams"].apply(replace_codes_with_names)
    return full_schedule, scores, group_stage_complete

# --------------------
# BRACKET UI FUNCTIONS
# --------------------
def create_bracket_html(matches, bracket_title):
    rounds = defaultdict(list)
    for m in matches:
        rounds[m["round"]].append(m)
    round_keys = sorted(rounds.keys())
    bracket_html = f"""
    <div class='bracket-container'>
      <h2>{bracket_title}</h2>
      <div class='bracket'>
    """
    for rkey in round_keys:
        bracket_html += f"<div class='round'><h3>{rkey}</h3>"
        for match_data in rounds[rkey]:
            bracket_html += f"""
            <div class='match'>
              <div class='match-teams'>{match_data["match_str"]}</div>
              <div class='match-score'>{match_data["score_str"]}</div>
            </div>
            """
        bracket_html += "</div>"
    bracket_html += """
      </div>
    </div>
    """
    return bracket_html

def build_bracket_data(schedule_df, scores_df, bracket_filter):
    bracket_matches = schedule_df[schedule_df["group"].str.contains(bracket_filter, case=False, na=False)]
    bracket_data = []
    for _, row in bracket_matches.iterrows():
        match_id = row["match"]
        match_str = row["teams"]
        round_name = row["group"]
        score_val = scores_df[scores_df["match"] == match_id]["score"].values
        score_str = score_val[0] if (len(score_val) > 0 and pd.notna(score_val[0])) else "TBD"
        bracket_data.append({
            "round": round_name,
            "match_str": match_str,
            "score_str": score_str
        })
    return bracket_data

def display_brackets(schedule_df, scores_df):
    # Build Cup bracket data from Quarterfinals, Semifinals, Finals and 3rd Place playoff
    cup_bracket_data = build_bracket_data(schedule_df, scores_df, "Quarterfinal")
    cup_bracket_data += build_bracket_data(schedule_df, scores_df, "Semifinal")
    cup_bracket_data += build_bracket_data(schedule_df, scores_df, "Cup Final")
    cup_bracket_data += build_bracket_data(schedule_df, scores_df, "3rd Place")
    
    # Build Bowl bracket data from Bowl Semifinals, Finals and 3rd Place playoff
    bowl_bracket_data = build_bracket_data(schedule_df, scores_df, "Bowl Semifinal")
    bowl_bracket_data += build_bracket_data(schedule_df, scores_df, "Bowl Final")
    bowl_bracket_data += build_bracket_data(schedule_df, scores_df, "Bowl 3rd Place")
    
    cup_html = create_bracket_html(cup_bracket_data, "Cup Knockout Bracket")
    bowl_html = create_bracket_html(bowl_bracket_data, "Bowl Knockout Bracket")
    
    st.markdown(cup_html, unsafe_allow_html=True)
    st.markdown(bowl_html, unsafe_allow_html=True)

# --------------------
# DISPLAY TOURNAMENT DATA
# --------------------
def display_tournament_data():
    full_schedule, scores, group_stage_complete = load_full_schedule()
    tabs = st.tabs(["📅 Schedule", "⚽ Scores", "🏆 Standings", "🏅 Knockout Brackets"])
    
    with tabs[0]:
        st.markdown('<h2 class="section-header">Tournament Schedule</h2>', unsafe_allow_html=True)
        st.dataframe(full_schedule.style.set_properties(**{'text-align': 'center', 'background-color': '#f9f9f9'}))
    
    with tabs[1]:
        st.markdown('<h2 class="section-header">Scores</h2>', unsafe_allow_html=True)
        st.dataframe(scores.style.set_properties(**{'text-align': 'center', 'background-color': '#f9f9f9'}))
    
    with tabs[2]:
        st.markdown('<h2 class="section-header">Group Standings</h2>', unsafe_allow_html=True)
        group_schedule = load_csv(GROUP_SCHEDULE_FILE, ["match", "teams", "group", "start_time", "end_time"])
        standings = calculate_group_standings(group_schedule, scores)
        for group, ranking in standings.items():
            st.write(f"**Group {group}**")
            df = pd.DataFrame([{"team": team_dict.get(t, t), **stats} for t, stats in ranking])
            st.dataframe(df.style.set_properties(**{'text-align': 'center', 'background-color': '#f9f9f9'}))
    
    with tabs[3]:
        st.markdown('<h2 class="section-header">Knockout Brackets</h2>', unsafe_allow_html=True)
        if group_stage_complete:
            display_brackets(full_schedule, scores)
        else:
            st.info("Knockout brackets will be displayed once the group stage is complete.")

# --------------------
# MAIN APP
# --------------------
def main():
    st.set_page_config(page_title="RHL 2025 Tournament Scheduler", layout="wide", initial_sidebar_state="expanded")
    st.markdown("""
    <style>
    body { font-family: 'Segoe UI', sans-serif; }
    .main-title { font-size: 48px; text-align: center;
      background: linear-gradient(90deg, #1e3c72, #2a5298);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      margin-top: 20px; }
    .section-header { color: #2c3e50; text-align: center; margin-top: 20px; }
    [data-testid="stSidebar"] { background: #f4f6f9; }
    .sidebar .sidebar-content { color: #2c3e50; }
    .stButton>button { background: #e74c3c; color: white;
      border-radius: 8px; padding: 10px 20px; font-size: 16px; }
    .stButton>button:hover { background: #c0392b; }
    .admin-panel { background: #34495e; padding: 20px;
      border-radius: 10px; color: white; margin-bottom: 20px; }
    .bracket-container { margin: 40px auto; max-width: 1000px;
      background: #ecf0f1; padding: 20px; border-radius: 10px; }
    .bracket-container h2 { text-align: center; margin-bottom: 20px; }
    .bracket { display: flex; flex-wrap: wrap; justify-content: space-around; }
    .round { display: flex; flex-direction: column; align-items: center;
      margin: 0 10px; min-width: 200px; }
    .round h3 { text-align: center; margin-bottom: 10px;
      background: #3498db; color: white; padding: 5px 10px; border-radius: 5px; }
    .match { background: white; border: 2px solid #3498db;
      border-radius: 5px; margin: 10px 0; padding: 10px; width: 180px;
      text-align: center; }
    .match-teams { font-weight: 600; margin-bottom: 5px; }
    .match-score { color: #e74c3c; }
    </style>
    """, unsafe_allow_html=True)
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.is_admin = False

    if not st.session_state.logged_in:
        st.sidebar.header("Login")
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            if check_login(username, password):
                st.session_state.logged_in = True
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.sidebar.error("Invalid credentials")
        if st.sidebar.button("Continue as Guest"):
            st.session_state.logged_in = True
            st.session_state.is_admin = False
            st.rerun()
        st.stop()

    st.sidebar.title("Navigation")
    menu_options = ["Dashboard"]
    if st.session_state.is_admin:
        menu_options.append("Admin Panel")
    menu_options.append("Logout")
    choice = st.sidebar.radio("Menu", menu_options)
    
    if choice == "Logout":
        st.session_state.logged_in = False
        st.session_state.is_admin = False
        st.rerun()

    st.markdown('<h1 class="main-title">RHL 2025 Tournament Scheduler</h1>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    
    if choice == "Dashboard":
        display_tournament_data()
    elif choice == "Admin Panel" and st.session_state.is_admin:
        st.markdown('<div class="admin-panel">', unsafe_allow_html=True)
        st.header("Admin Control Panel")
        full_schedule, scores, group_stage_complete = load_full_schedule()
        merged = full_schedule.merge(scores, on="match", how="left")
        pending_matches = merged[merged["score"].isna()]["match"].tolist()
        all_matches = full_schedule["match"].tolist()
        mode = st.radio("Mode", ["Add New Score", "Edit Old Score"], horizontal=True)
        if mode == "Add New Score":
            match = st.selectbox("Select Pending Match", pending_matches, key="match_select_pending")
        else:
            match = st.selectbox("Select Match to Edit", all_matches, key="match_select_all")
        match_teams = full_schedule[full_schedule["match"] == match]["teams"].values[0]
        st.write(f"Selected: **{match_teams}**")
        score_row = scores[scores["match"] == match]["score"].values
        current_score = score_row[0] if (len(score_row) > 0 and pd.notna(score_row[0])) else ""
        score = st.text_input("Enter Score (e.g., 2-1)", value=current_score, key="score_input_field")
        if st.button("Update Score"):
            update_score(match, score)
            st.success(f"Score updated for Match {match}!")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Refresh Data"):
        st.rerun()

if __name__ == "__main__":
    main()
