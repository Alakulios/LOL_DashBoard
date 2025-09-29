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

# Initialize Last_Fetched_Match sheet
try:
    last_fetched_sheet = sheet.worksheet("Last_Fetched_Match")
except gspread.exceptions.WorksheetNotFound:
    last_fetched_sheet = sheet.add_worksheet(title="Last_Fetched_Match", rows=100, cols=3)
    last_fetched_sheet.append_row(["SummonerName", "TagLine", "LastMatchID"])

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

def get_last_fetched_match(summoner_name, tag_line):
    """Retrieve the last fetched match ID for a summoner."""
    try:
        last_fetched_data = last_fetched_sheet.get_all_values()
        for row in last_fetched_data[1:]:  # Skip header
            if len(row) >= 3 and row[0] == summoner_name and row[1] == tag_line:
                return row[2]
    except Exception as e:
        print(f"Error reading last fetched match for {summoner_name}#{tag_line}: {e}")
    return None

def update_last_fetched_match(summoner_name, tag_line, match_id):
    """Update the last fetched match ID for a summoner."""
    try:
        last_fetched_data = last_fetched_sheet.get_all_values()
        for i, row in enumerate(last_fetched_data[1:], start=2):  # Skip header
            if len(row) >= 3 and row[0] == summoner_name and row[1] == tag_line:
                last_fetched_sheet.update_cell(i, 3, match_id)
                return
        # If summoner not found, append new row
        last_fetched_sheet.append_row([summoner_name, tag_line, match_id])
    except Exception as e:
        print(f"Error updating last fetched match for {summoner_name}#{tag_line}: {e}")

def get_match_ids(puuid, summoner_name, tag_line):
    """Retrieves match IDs for a PUUID, filtering for those on or after START_TIMESTAMP."""
    match_list = []
    start = 0
    last_match_id = get_last_fetched_match(summoner_name, tag_line)
    
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
            # Stop if we encounter the last fetched match ID
            if last_match_id and last_match_id in matches:
                match_list.extend([m for m in matches[:matches.index(last_match_id)] if m != last_match_id])
                print(f"Stopped at last fetched match {last_match_id} for {summoner_name}#{tag_line}")
                break
            match_list.extend(matches)
            print(f"Added {len(matches)} match IDs for PUUID {puuid}. Total: {len(match_list)}")
            start += MATCH_COUNT_PER_REQUEST
        elif r.status_code == 429:
            print("Rate limit exceeded in match IDs zapew: Waiting 10 seconds...")
            time.sleep(10)
            continue
        else:
            print(f"Error getting match IDs for PUUID {puuid}: {r.status_code} - {r.text}")
            break
        time.sleep(1.2)  # Avoid rate limits
    
    # Update last fetched match ID if new matches were found
    if match_list:
        update_last_fetched_match(summoner_name, tag_line, match_list[0])
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
    game_date = pd.to_datetime(game_creation, unit="ms", utc=True).isoformat()
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
        match_ids = get_match_ids(puuid, summoner_name, tag_line)
        print(f"Found {len(match_ids)} total match IDs for {full_id}")
        for mid in match_ids:
            if (mid, summoner_name, tag_line) in existing_matches:
                print(f"Match {mid} for {summoner_name}#{tag_line} already exists in sheet. Skipping.")
                continue
            match_data, should_continue = get_match_data(mid, summoner_name, tag_line)
            if match_data:
                print(f"Appending match data: {match_data}")
                worksheet.append_row(match_data)
                existing_matches.add((mid, summoner_name, tag_line))
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
    max_retries = 3
    retry_delay = 5  # Seconds to wait between retries

    try:
        req_sheet = sheet.worksheet("Weekly_Requirements")
        requirements_data = req_sheet.get_all_values()
        headers = ['Week_Start', 'SummonerName', 'Champion', 'Required_Games']
        
        # Verify or set headers
        if not requirements_data or requirements_data[0] != headers:
            print("Initializing Weekly_Requirements sheet with correct headers.")
            req_sheet.clear()
            req_sheet.append_row(headers)
            requirements = pd.DataFrame(columns=headers)
        else:
            requirements = pd.DataFrame(req_sheet.get_all_records())
            if not requirements.empty:
                print(f"Weekly_Requirements columns: {requirements.columns.tolist()}")
    
    except gspread.exceptions.WorksheetNotFound:
        print("Creating Weekly_Requirements sheet.")
        req_sheet = sheet.add_worksheet(title="Weekly_Requirements", rows=100, cols=4)
        headers = ['Week_Start', 'SummonerName', 'Champion', 'Required_Games']
        req_sheet.append_row(headers)
        requirements = pd.DataFrame(columns=headers)

    # Verify that Week_Start column exists
    if 'Week_Start' not in requirements.columns:
        print("Warning: 'Week_Start' column not found in Weekly_Requirements sheet. Initializing empty requirements.")
        requirements = pd.DataFrame(columns=headers)

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
        # Convert gameCreation to UTC timezone-aware datetime
        matches['gameCreation'] = pd.to_datetime(matches['gameCreation'], errors='coerce', utc=True)
        matches = matches.dropna(subset=['gameCreation'])
        sept_start = pd.to_datetime('2025-09-01', utc=True)
        matches = matches[matches['gameCreation'] >= sept_start]
        
        # Calculate Week_Start as UTC timezone-aware
        matches['Week_Start'] = matches['gameCreation'].apply(
            lambda x: (x - pd.Timedelta(days=x.weekday())).normalize()
        )
        games_played = matches.groupby(['Week_Start', 'summonerName', 'champion']).size().reset_index(name='Games_Played')
        games_played['Week_Start'] = pd.to_datetime(games_played['Week_Start'], utc=True)

        # Fill missing weeks in requirements
        min_week = matches['Week_Start'].min()
        current_date = pd.to_datetime(datetime.now(timezone.utc), utc=True)
        current_monday = (current_date - pd.Timedelta(days=current_date.weekday())).normalize()
        weeks = pd.date_range(min_week, current_monday, freq='W-MON', tz='UTC')
        new_rows = []
        for week in weeks:
            for full_id in SUMMONERS:
                summoner_name = full_id.split('#')[0]
                config = CHAMPION_LISTS.get(full_id, {})
                learning_req = config.get("learning_games_required", 2)
                if not ((requirements['Week_Start'] == week) &
                        (requirements['SummonerName'] == summoner_name) &
                        (requirements['Champion'] == 'Learning')).any():
                    new_rows.append([week.strftime('%Y-%m-%d'), summoner_name, 'Learning', learning_req])
                total_req = config.get("total_games_required", 0)
                if total_req > 0:
                    if not ((requirements['Week_Start'] == week) &
                            (requirements['SummonerName'] == summoner_name) &
                            (requirements['Champion'] == 'Total Games')).any():
                        new_rows.append([week.strftime('%Y-%m-%d'), summoner_name, 'Total Games', total_req])

        if new_rows:
            print(f"Appending {len(new_rows)} new requirement rows to Weekly_Requirements.")
            # Append rows in smaller batches to avoid API overload
            batch_size = 20
            for i in range(0, len(new_rows), batch_size):
                batch = new_rows[i:i + batch_size]
                for attempt in range(max_retries):
                    try:
                        req_sheet.append_rows(batch)
                        print(f"Successfully appended batch {i//batch_size + 1} of {len(new_rows)//batch_size + 1}")
                        time.sleep(1)  # Brief delay to avoid rate limits
                        break
                    except gspread.exceptions.APIError as e:
                        if attempt < max_retries - 1:
                            print(f"APIError on batch {i//batch_size + 1}: {e}. Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                        else:
                            print(f"Failed to append batch {i//batch_size + 1} after {max_retries} attempts: {e}")
                            raise
            # Reload requirements after appending
            requirements_data = req_sheet.get_all_values()
            if requirements_data and requirements_data[0] == headers:
                requirements = pd.DataFrame(req_sheet.get_all_records())
            else:
                requirements = pd.DataFrame(new_rows, columns=headers)
            print(f"Reloaded Weekly_Requirements columns: {requirements.columns.tolist()}")

    # Convert Week_Start to datetime, if it exists
    if not requirements.empty and 'Week_Start' in requirements.columns:
        requirements['Week_Start'] = pd.to_datetime(requirements['Week_Start'], errors='coerce', utc=True)
        requirements = requirements[requirements['Week_Start'] >= pd.to_datetime('2025-09-01', utc=True)]
        requirements['Required_Games'] = requirements['Required_Games'].astype(int, errors='ignore')
    else:
        print("No valid requirements data after reload. Proceeding with empty requirements.")
        requirements = pd.DataFrame(columns=['Week_Start', 'SummonerName', 'Champion', 'Required_Games'])

    learning_rows = []
    for full_id in SUMMONERS:
        summoner_name = full_id.split('#')[0]
        config = CHAMPION_LISTS.get(full_id, {})
        core_champs = config.get("core_champions", [])
        learning_req = config.get("learning_games_required", 2)
        for week in requirements[requirements['SummonerName'] == summoner_name]['Week_Start'].unique():
            if pd.isna(week):
                continue  # Skip NaT values
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
                if pd.isna(week):
                    continue  # Skip NaT values
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
        report['Week_Start'] = pd.to_datetime(report['Week_Start'], utc=True)
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