import pandas as pd
import requests
import time
import gspread
from datetime import datetime, timezone
from google.oauth2.service_account import Credentials
from config import (
    API_KEY, CREDS_PATH, ROUTING, MATCH_COUNT_PER_REQUEST,
    START_TIMESTAMP, CURRENT_TIMESTAMP,
    SUMMONERS, CHAMPION_LISTS, queue_types
)

# === GOOGLE SHEETS SETUP ===
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

try:
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=scope)
except FileNotFoundError:
    print(f"Error: {CREDS_PATH} not found. Please ensure the path in credentials/.env is correct.")
    exit(1)

client = gspread.authorize(creds)
sheet = client.open("LOL_Tracker")
worksheet = sheet.worksheet("Matches")

def get_summoner_puuid(full_id):
    """Gets PUUID for a summoner using their Riot ID."""
    summoner_name, tag_line = full_id.split('#')
    summoner_url = f"https://{ROUTING}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner_name}/{tag_line}"
    headers = {"X-Riot-Token": API_KEY}
    r = requests.get(summoner_url, headers=headers)
    if r.status_code == 200:
        return r.json().get("puuid")
    elif r.status_code == 429:
        print(f"Rate limit exceeded for {full_id}. Waiting 10 seconds...")
        time.sleep(10)
        return get_summoner_puuid(full_id)
    else:
        print(f"Error getting PUUID for {full_id}: {r.status_code} - {r.text}")
        return None

def get_match_ids(puuid):
    """Retrieves match IDs for a PUUID, filtering for those on or after START_TIMESTAMP."""
    match_list = []
    start = 0
    while True:
        url = (
            f"https://{ROUTING}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?"
            f"startTime={int(START_TIMESTAMP / 1000)}&endTime={int(CURRENT_TIMESTAMP / 1000)}&"
            f"count={MATCH_COUNT_PER_REQUEST}&start={start}"
        )
        headers = {"X-Riot-Token": API_KEY}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            matches = r.json()
            if not matches:
                print(f"No more matches for PUUID {puuid} at start={start}")
                break
            match_list.extend(matches)
            print(f"Added {len(matches)} match IDs for PUUID {puuid}. Total: {len(match_list)}")
            start += MATCH_COUNT_PER_REQUEST
        elif r.status_code == 429:
            print("Rate limit exceeded in match IDs request. Waiting 10 seconds...")
            time.sleep(10)
            continue
        else:
            print(f"Error getting match IDs for PUUID {puuid}: {r.status_code} - {r.text}")
            break
        time.sleep(1.2)  # Avoid rate limits
    return match_list

def get_match_data(match_id, summoner_name, tag_line):
    """Fetches match data and extracts relevant stats for a summoner."""
    url = f"https://{ROUTING}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": API_KEY}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        if r.status_code == 429:
            print(f"Rate limit exceeded for match {match_id}. Waiting 10 seconds...")
            time.sleep(10)
            return None, True
        print(f"Error getting match {match_id}: {r.status_code} - {r.text}")
        return None, False
    data = r.json()
    game_creation = int(data["info"]["gameCreation"])
    game_date = pd.to_datetime(game_creation, unit="ms").isoformat()
    if game_creation < START_TIMESTAMP or game_creation > CURRENT_TIMESTAMP:
        print(f"Match {match_id} is outside September 2025 (gameCreation: {game_creation}ms, date: {game_date}). Skipping.")
        return None, True
    queue_id = data["info"]["queueId"]
    game_type = queue_types.get(queue_id, "Unknown")
    if game_type == "Unknown":
        print(f"Unknown queueId {queue_id} for match {match_id}")
        return None, True
    for p in data["info"]["participants"]:
        if p["riotIdGameName"] == summoner_name and p["riotIdTagline"] == tag_line:
            return [
                match_id,
                summoner_name,
                tag_line,
                p["championName"],
                p["win"],
                p["kills"],
                p["deaths"],
                p["assists"],
                round(data["info"]["gameDuration"] / 60, 2),
                game_date,
                game_type
            ], True
    print(f"No participant data for {summoner_name}#{tag_line} in match {match_id}. Skipping.")
    return None, True

def update_match_data(worksheet):
    headers = ["match_id", "summonerName", "tagLine", "champion", "win", "kills", "deaths", "assists", "gameDuration_min", "gameCreation", "gameType"]
    try:
        existing_data = worksheet.get_all_values()
        if not existing_data or existing_data[0] != headers:
            worksheet.clear()
            worksheet.append_row(headers)
            existing_matches = set()
        else:
            existing_matches = set((row[0], row[1], row[2]) for row in existing_data[1:] if row and len(row) >= 3)
    except gspread.exceptions.WorksheetNotFound:
        print("Matches worksheet not found, creating new one")
        worksheet = sheet.add_worksheet(title="Matches", rows=100, cols=len(headers))
        worksheet.append_row(headers)
        existing_matches = set()

    for full_id in SUMMONERS:
        summoner_name, tag_line = full_id.split('#')
        puuid = get_summoner_puuid(full_id)
        if not puuid:
            print(f"Skipping {full_id}: No PUUID found.")
            continue
        match_ids = get_match_ids(puuid)
        print(f"Found {len(match_ids)} total match IDs for {full_id}")
        for mid in match_ids:
            if (mid, summoner_name, tag_line) in existing_matches:
                print(f"Match {mid} for {summoner_name}#{tag_line} already exists in sheet. Skipping.")
                continue
            match_data, should_continue = get_match_data(mid, summoner_name, tag_line)
            if match_data:
                print(f"Appending match data: {match_data}")
                worksheet.append_row(match_data)
                print(f"Successfully appended match {mid} for {summoner_name}#{tag_line}.")
            if not should_continue:
                break
            time.sleep(1.2)  # Avoid rate limits

def write_current_week():
    """Writes the current week's Monday start date to a new sheet named Current_Week."""
    try:
        current_date = pd.to_datetime(datetime.now(timezone.utc))
        current_monday = current_date - pd.Timedelta(days=(current_date.weekday() % 7))
        current_week_str = current_monday.strftime('%Y-%m-%d')
        
        try:
            current_week_sheet = sheet.worksheet("Current_Week")
            sheet.del_worksheet(current_week_sheet)
        except gspread.exceptions.WorksheetNotFound:
            pass
        current_week_sheet = sheet.add_worksheet(title="Current_Week", rows=2, cols=2)
        
        current_week_sheet.append_row(["Current Week Start", current_week_str])
        print(f"Written current week start ({current_week_str}) to 'Current_Week' sheet.")
        
    except Exception as e:
        print(f"Error writing current week to sheet: {e}")

def generate_champion_report():
    """Generates a report comparing games played to weekly requirements."""
    try:
        req_sheet = sheet.worksheet("Weekly_Requirements")
        requirements = pd.DataFrame(req_sheet.get_all_records())
    except gspread.exceptions.WorksheetNotFound:
        print("Creating Weekly_Requirements sheet.")
        req_sheet = sheet.add_worksheet(title="Weekly_Requirements", rows=100, cols=4)
        req_sheet.append_row(['Week_Start', 'SummonerName', 'Champion', 'Required_Games'])
        requirements = pd.DataFrame()

    matches = pd.DataFrame(worksheet.get_all_records())
    display_to_key = {
        "Aurelion Sol": "AurelionSol",
        "Cho'Gath": "Chogath",
        "Dr. Mundo": "DrMundo",
        "Jarvan IV": "JarvanIV",
        "Kai'Sa": "Kaisa",
        "Kha'Zix": "Khazix",
        "Kog'Maw": "KogMaw",
        "K'Sante": "KSante",
        "Lee Sin": "LeeSin",
        "Master Yi": "MasterYi",
        "Miss Fortune": "MissFortune",
        "MonkeyKing": "Wukong",
        "Nunu & Willump": "Nunu",
        "Rek'Sai": "RekSai",
        "Tahm Kench": "TahmKench",
        "Twisted Fate": "TwistedFate",
        "Vel'Koz": "Velkoz",
        "Xin Zhao": "XinZhao"
    }
    if not matches.empty:
        matches['champion'] = matches['champion'].map(display_to_key).fillna(matches['champion'])

    if matches.empty:
        print("No matches data. Skipping report.")
        games_played = pd.DataFrame(columns=['Week_Start', 'summonerName', 'champion', 'Games_Played'])
    else:
        matches['gameCreation'] = pd.to_datetime(matches['gameCreation'], errors='coerce')
        matches = matches.dropna(subset=['gameCreation'])
        sept_start = pd.to_datetime('2025-09-01')
        matches = matches[matches['gameCreation'] >= sept_start]
        
        matches['Week_Start'] = matches['gameCreation'].apply(
            lambda x: (x - pd.Timedelta(days=x.weekday())).normalize()
        )
        games_played = matches.groupby(['Week_Start', 'summonerName', 'champion']).size().reset_index(name='Games_Played')
        games_played['Week_Start'] = pd.to_datetime(games_played['Week_Start'])

    requirements['Week_Start'] = pd.to_datetime(requirements['Week_Start'], errors='coerce')
    requirements = requirements[requirements['Week_Start'] >= pd.to_datetime('2025-09-01')]
    requirements['Required_Games'] = requirements['Required_Games'].astype(int, errors='ignore')

    learning_rows = []
    for full_id in SUMMONERS:
        summoner_name = full_id.split('#')[0]
        config = CHAMPION_LISTS.get(full_id, {})
        core_champs = config.get("core_champions", [])
        learning_req = config.get("learning_games_required", 2)
        for week in requirements[requirements['SummonerName'] == summoner_name]['Week_Start'].unique():
            champ_rows = games_played[
                (games_played['Week_Start'] == week) &
                (games_played['summonerName'] == summoner_name) &
                (games_played['champion'].isin(core_champs))
            ]
            total_learning_games = champ_rows['Games_Played'].sum()
            learning_rows.append({
                'Week_Start': week,
                'summonerName': summoner_name,
                'champion': 'Learning',
                'Games_Played': total_learning_games,
                'Required_Games': learning_req,
                'Difference': total_learning_games - learning_req,
                'Met_Requirement': 'Yes' if total_learning_games >= learning_req else 'No'
            })

    total_rows = []
    for full_id in SUMMONERS:
        summoner_name = full_id.split('#')[0]
        config = CHAMPION_LISTS.get(full_id, {})
        total_req = config.get("total_games_required", 0)
        champs_to_count = config.get("total_champions", [])
        if total_req > 0 and champs_to_count:
            for week in requirements[requirements['SummonerName'] == summoner_name]['Week_Start'].unique():
                week_matches = matches[
                    (matches['Week_Start'] == week) &
                    (matches['summonerName'] == summoner_name) &
                    (matches['champion'].isin(champs_to_count))
                ]
                total_games = len(week_matches)
                total_rows.append({
                    'Week_Start': week,
                    'summonerName': summoner_name,
                    'champion': 'Total Games',
                    'Games_Played': total_games,
                    'Required_Games': total_req,
                    'Difference': total_games - total_req,
                    'Met_Requirement': 'Yes' if total_games >= total_req else 'No'
                })

    report = pd.concat([pd.DataFrame(learning_rows), pd.DataFrame(total_rows)], ignore_index=True)
    if not report.empty:
        report['Week_Start'] = pd.to_datetime(report['Week_Start'])
    else:
        report = pd.DataFrame(columns=['Week_Start', 'summonerName', 'champion', 'Games_Played', 'Required_Games', 'Difference', 'Met_Requirement'])

    report = pd.merge(
        requirements,
        report,
        how='left',
        left_on=['Week_Start', 'SummonerName', 'Champion'],
        right_on=['Week_Start', 'summonerName', 'champion'],
        suffixes=('', '_report')
    )
    for col in ['Games_Played', 'Required_Games']:
        if col not in report.columns:
            report[col] = 0
    report['summonerName'] = report['SummonerName']
    report['champion'] = report['Champion']
    report.drop(columns=['SummonerName', 'Champion'], inplace=True, errors='ignore')
    report['Games_Played'] = report['Games_Played'].fillna(0).astype(int)
    report['Required_Games'] = report['Required_Games'].fillna(0).astype(int)
    report['Difference'] = report['Games_Played'] - report['Required_Games']
    report['Met_Requirement'] = report.apply(lambda x: 'Yes' if x['Games_Played'] >= x['Required_Games'] else 'No', axis=1)

    report = report.sort_values(['Met_Requirement', 'summonerName', 'Week_Start', 'champion'])
    report['Week_Start'] = report['Week_Start'].dt.strftime('%Y-%m-%d')

    try:
        report_sheet = sheet.worksheet("Champion_Tracker")
        sheet.del_worksheet(report_sheet)
    except gspread.exceptions.WorksheetNotFound:
        pass
    report_sheet = sheet.add_worksheet(title="Champion_Tracker", rows=max(100, len(report)+1), cols=7)
    headers = ["Week_Start", "summonerName", "champion", "Games_Played", "Required_Games", "Difference", "Met_Requirement"]
    report_sheet.append_row(headers)
    report_sheet.append_rows(report[headers].values.tolist())
    print("Updated Champion tracking report generated in 'Champion_Tracker' sheet.")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    update_match_data(worksheet)
    generate_champion_report()
    write_current_week()