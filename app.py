import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import time

# File paths
GROUP_SCHEDULE_FILE = "group_schedule.csv"
SCORES_FILE = "scores.csv"

# Hardcoded admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "rhl2025"

# Team data
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

# Mapping for knockout references
knockout_map = {
    "QF1": "Quarterfinal 1", "QF2": "Quarterfinal 2", "QF3": "Quarterfinal 3", "QF4": "Quarterfinal 4",
    "SF1": "Semifinal 1", "SF2": "Semifinal 2"
}

def load_csv(file, columns):
    """Load CSV file or initialize one if it doesn't exist."""
    if os.path.exists(file):
        return pd.read_csv(file)
    else:
        df = pd.DataFrame(columns=columns)
        df.to_csv(file, index=False)
        return df

def replace_codes_with_names(teams_str):
    """Replace team codes with their full names."""
    for code, name in team_dict.items():
        teams_str = teams_str.replace(code, name)
    return teams_str

def check_login(username, password):
    """Validate admin credentials."""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def update_score(match, score):
    """Update or add a score for a given match."""
    scores = load_csv(SCORES_FILE, ["match", "score"])
    if match in scores["match"].values:
        scores.loc[scores["match"] == match, "score"] = score
    else:
        new_row = pd.DataFrame({"match": [match], "score": [score]})
        scores = pd.concat([scores, new_row], ignore_index=True)
    scores.to_csv(SCORES_FILE, index=False)

def calculate_group_standings(group_schedule, scores):
    """Calculate group standings from schedule and scores."""
    standings = {}
    groups = group_schedule["group"].unique()
    
    for group in groups:
        group_matches = group_schedule[group_schedule["group"] == group]
        teams_in_group = [t["code"] for t in teams if t["group"] == group]
        standings[group] = {team: {"points": 0, "wins": 0, "losses": 0, "gf": 0, "ga": 0} for team in teams_in_group}
        
        for _, row in group_matches.iterrows():
            score_val = scores[scores["match"] == row["match"]]["score"].values
            if len(score_val) > 0 and pd.notna(score_val[0]):
                t1, t2 = row["teams"].split(" vs ")
                try:
                    s1, s2 = map(int, score_val[0].split("-"))
                except Exception:
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
        standings[group] = sorted(
            standings[group].items(), 
            key=lambda x: (x[1]["points"], x[1]["gf"] - x[1]["ga"], x[1]["gf"]),
            reverse=True
        )
    return standings

def generate_knockout_schedule(standings, last_group_time):
    """Generate knockout stage schedule based on group standings."""
    knockout_matches = []
    match_id = 13
    start_time = datetime.strptime(last_group_time, "%H:%M:%S") + timedelta(minutes=3)

    # Quarterfinals
    qf_teams = [
        (f"{team_dict[standings['A'][0][0]]}", f"{team_dict[standings['C'][1][0]]}", "Quarterfinal 1"),
        (f"{team_dict[standings['B'][0][0]]}", f"{team_dict[standings['D'][1][0]]}", "Quarterfinal 2"),
        (f"{team_dict[standings['C'][0][0]]}", f"{team_dict[standings['A'][1][0]]}", "Quarterfinal 3"),
        (f"{team_dict[standings['D'][0][0]]}", f"{team_dict[standings['B'][1][0]]}", "Quarterfinal 4")
    ]
    for t1, t2, round_name in qf_teams:
        end_time = start_time + timedelta(minutes=12)
        knockout_matches.append({
            "match": match_id, "teams": f"{t1} vs {t2}", "group": round_name,
            "start_time": start_time.strftime("%H:%M:%S"), "end_time": end_time.strftime("%H:%M:%S")
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
            "match": match_id, "teams": f"{t1} vs {t2}", "group": round_name,
            "start_time": start_time.strftime("%H:%M:%S"), "end_time": end_time.strftime("%H:%M:%S")
        })
        match_id += 1
        start_time = end_time + timedelta(minutes=3)

    # Finals and third-place playoff
    final_teams = [
        ("Loser SF1", "Loser SF2", "Cup 3rd Place Playoff", 12),
        ("Winner SF1", "Winner SF2", "Cup Final", 17)
    ]
    for t1, t2, round_name, duration in final_teams:
        end_time = start_time + timedelta(minutes=duration)
        knockout_matches.append({
            "match": match_id, "teams": f"{t1} vs {t2}", "group": round_name,
            "start_time": start_time.strftime("%H:%M:%S"), "end_time": end_time.strftime("%H:%M:%S")
        })
        match_id += 1
        start_time = end_time + timedelta(minutes=3)

    return pd.DataFrame(knockout_matches)

def resolve_knockout_teams(full_schedule, scores):
    """Replace placeholders like 'Winner QF1' with actual team names based on scores."""
    for i, row in full_schedule.iterrows():
        if "Winner" in row["teams"] or "Loser" in row["teams"]:
            t1, t2 = row["teams"].split(" vs ")
            for team in [t1, t2]:
                if "Winner" in team:
                    match_ref = team.split("Winner ")[1].strip()
                    full_group_name = knockout_map.get(match_ref, "")
                    if full_group_name and not full_schedule[full_schedule["group"] == full_group_name].empty:
                        match_id = full_schedule[full_schedule["group"] == full_group_name]["match"].values[0]
                        score_val = scores[scores["match"] == match_id]["score"].values
                        if len(score_val) > 0 and pd.notna(score_val[0]):
                            prev_match_teams = full_schedule[full_schedule["match"] == match_id]["teams"].values[0]
                            t1_prev, t2_prev = prev_match_teams.split(" vs ")
                            try:
                                s1, s2 = map(int, score_val[0].split("-"))
                            except Exception:
                                continue
                            winner = t1_prev if s1 > s2 else t2_prev
                            full_schedule.loc[i, "teams"] = full_schedule.loc[i, "teams"].replace(team, winner)
                elif "Loser" in team:
                    match_ref = team.split("Loser ")[1].strip()
                    full_group_name = knockout_map.get(match_ref, "")
                    if full_group_name and not full_schedule[full_schedule["group"] == full_group_name].empty:
                        match_id = full_schedule[full_schedule["group"] == full_group_name]["match"].values[0]
                        score_val = scores[scores["match"] == match_id]["score"].values
                        if len(score_val) > 0 and pd.notna(score_val[0]):
                            prev_match_teams = full_schedule[full_schedule["match"] == match_id]["teams"].values[0]
                            t1_prev, t2_prev = prev_match_teams.split(" vs ")
                            try:
                                s1, s2 = map(int, score_val[0].split("-"))
                            except Exception:
                                continue
                            loser = t2_prev if s1 > s2 else t1_prev
                            full_schedule.loc[i, "teams"] = full_schedule.loc[i, "teams"].replace(team, loser)
    return full_schedule

def load_full_schedule():
    """Load schedule and scores then generate the full tournament schedule."""
    group_schedule = load_csv(GROUP_SCHEDULE_FILE, ["match", "teams", "group", "start_time", "end_time"])
    scores = load_csv(SCORES_FILE, ["match", "score"])
    standings = calculate_group_standings(group_schedule, scores)
    last_group_time = group_schedule["end_time"].iloc[-1] if not group_schedule.empty else "00:00:00"
    knockout_schedule = generate_knockout_schedule(standings, last_group_time)
    full_schedule = pd.concat([group_schedule, knockout_schedule], ignore_index=True)
    full_schedule = resolve_knockout_teams(full_schedule, scores)
    full_schedule["teams"] = full_schedule["teams"].apply(replace_codes_with_names)
    return full_schedule, scores

def display_tournament_data():
    """Display schedule, scores, and standings in elegant tabs."""
    full_schedule, scores = load_full_schedule()
    tabs = st.tabs(["📅 Schedule", "⚽ Scores", "🏆 Standings"])
    
    with tabs[0]:
        st.markdown('<h2 class="section-header">Tournament Schedule</h2>', unsafe_allow_html=True)
        st.dataframe(full_schedule.style.set_properties(**{
            'text-align': 'center', 'background-color': '#f9f9f9'
        }))
    
    with tabs[1]:
        st.markdown('<h2 class="section-header">Scores</h2>', unsafe_allow_html=True)
        st.dataframe(scores.style.set_properties(**{
            'text-align': 'center', 'background-color': '#f9f9f9'
        }))
    
    with tabs[2]:
        st.markdown('<h2 class="section-header">Group Standings</h2>', unsafe_allow_html=True)
        standings = calculate_group_standings(
            load_csv(GROUP_SCHEDULE_FILE, ["match", "teams", "group", "start_time", "end_time"]), 
            scores
        )
        for group, ranking in standings.items():
            st.write(f"**Group {group}**")
            df = pd.DataFrame([{"team": team_dict.get(t, t), **stats} for t, stats in ranking])
            st.dataframe(df.style.set_properties(**{
                'text-align': 'center', 'background-color': '#f9f9f9'
            }))

# Main application with sidebar navigation and custom styling
def main():
    st.set_page_config(
        page_title="RHL 2025 Tournament Scheduler",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for modern look
    st.markdown("""
        <style>
        /* Global Styles */
        body {
            font-family: 'Segoe UI', sans-serif;
        }
        .main-title {
            font-size: 48px;
            text-align: center;
            background: linear-gradient(90deg, #1e3c72, #2a5298);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-top: 20px;
        }
        .section-header {
            color: #2c3e50;
            text-align: center;
            margin-top: 20px;
        }
        /* Sidebar customization */
        [data-testid="stSidebar"] {
            background: #f4f6f9;
        }
        .sidebar .sidebar-content {
            color: #2c3e50;
        }
        .stButton>button {
            background: #e74c3c;
            color: white;
            border-radius: 8px;
            padding: 10px 20px;
            font-size: 16px;
        }
        .stButton>button:hover {
            background: #c0392b;
        }
        /* Admin panel styling */
        .admin-panel {
            background: #34495e;
            padding: 20px;
            border-radius: 10px;
            color: white;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state variables
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.is_admin = False

    # Sidebar Login if not authenticated
    if not st.session_state.logged_in:
        st.sidebar.header("Login")
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            if check_login(username, password):
                st.session_state.logged_in = True
                st.session_state.is_admin = True
                st.experimental_rerun()
            else:
                st.sidebar.error("Invalid credentials")
        if st.sidebar.button("Continue as Guest"):
            st.session_state.logged_in = True
            st.session_state.is_admin = False
            st.experimental_rerun()
        st.stop()

    # Sidebar Navigation Menu
    st.sidebar.title("Navigation")
    menu_options = ["Dashboard"]
    if st.session_state.is_admin:
        menu_options.append("Admin Panel")
    menu_options.append("Logout")
    choice = st.sidebar.radio("Menu", menu_options)
    
    # Handle Logout
    if choice == "Logout":
        st.session_state.logged_in = False
        st.session_state.is_admin = False
        st.experimental_rerun()

    # Main Title
    st.markdown('<h1 class="main-title">RHL 2025 Tournament Scheduler</h1>', unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # Display pages based on navigation
    if choice == "Dashboard":
        display_tournament_data()
    elif choice == "Admin Panel" and st.session_state.is_admin:
        st.markdown('<div class="admin-panel">', unsafe_allow_html=True)
        st.header("Admin Control Panel")
        full_schedule, scores = load_full_schedule()
        # Merge schedules to align scores with matches
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
            st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Optionally, add a refresh button to update data manually
    if st.button("Refresh Data"):
        st.experimental_rerun()

if __name__ == "__main__":
    main()
