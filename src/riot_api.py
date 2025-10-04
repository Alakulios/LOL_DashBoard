import requests
import time
import pandas as pd
from config import API_KEY, ROUTING, MATCH_COUNT_PER_REQUEST, START_TIMESTAMP, CURRENT_TIMESTAMP, queue_types

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

def get_match_ids(puuid, summoner_name, tag_line, last_fetched_match):
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
            # Stop if we encounter the last fetched match ID
            if last_fetched_match and last_fetched_match in matches:
                match_list.extend([m for m in matches[:matches.index(last_fetched_match)] if m != last_fetched_match])
                print(f"Stopped at last fetched match {last_fetched_match} for {summoner_name}#{tag_line}")
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