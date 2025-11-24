# src/riot_api.py
from typing import Dict, Any, List
import requests
import time
from datetime import datetime, timezone
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import API_KEY, ROUTING, queue_types

BASE_URL = f"https://{ROUTING}.api.riotgames.com"

# --- GLOBAL SESSION WITH RETRY ---
session = requests.Session()
retry = Retry(
    total=10,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
session.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=50, pool_maxsize=50))

# --- RATE LIMIT TRACKING ---
_last_call = 0.0
SHORT_RATE = 1.0 / 20
_call_history: List[float] = []

def _rate_limit():
    global _last_call, _call_history
    now = time.time()

    # Riot API Calls 20 per second
    elapsed = now - _last_call
    if elapsed < SHORT_RATE:
        time.sleep(SHORT_RATE - elapsed)
    _last_call = time.time()

    # Riot API Calls 100 per 2 minutes
    _call_history = [t for t in _call_history if now - t < 120]
    if len(_call_history) >= 100:
        wait = 120 - (now - _call_history[0])
        if wait > 0:
            print(f"[LIMIT] Sleeping {wait:.1f}s (100/2min)")
            time.sleep(wait)
    _call_history.append(time.time())

def _get(url: str, params=None):
    for attempt in range(20):  # 20 retries
        _rate_limit()
        try:
            # Fresh session per call to avoid SSL EOF
            with requests.Session() as sess:
                adapter = HTTPAdapter(
                    max_retries=Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
                )
                sess.mount("https://", adapter)
                resp = sess.get(
                    url,
                    params=params,
                    headers={"X-Riot-Token": API_KEY},
                    timeout=30
                )
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 120))
                print(f"[429] Waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.SSLError as e:
            print(f"[SSL ERROR] {e} — retry {attempt + 1}/20")
            time.sleep(5)
        except Exception as e:
            print(f"[ERROR] {e} — retry {attempt + 1}/20")
            time.sleep(10)
    raise Exception("Max retries exceeded")

def get_summoner_puuid(name: str, tag: str) -> str:
    return _get(f"{BASE_URL}/riot/account/v1/accounts/by-riot-id/{name}/{tag}")["puuid"]

def get_match_ids(puuid: str, start_time: int = 0) -> List[str]:
    params = {"startTime": start_time // 1000, "count": 100}  # MAX 100
    return _get(f"{BASE_URL}/lol/match/v5/matches/by-puuid/{puuid}/ids", params)

def get_match_data(match_id: str, puuid: str) -> Dict[str, Any]:
    data = _get(f"{BASE_URL}/lol/match/v5/matches/{match_id}")["info"]
    p = next(x for x in data["participants"] if x["puuid"] == puuid)
    name = p.get("riotIdGameName") or p.get("summonerName") or "UNKNOWN"
    
    # Calculate team total kills once
    team_kills = sum(part["kills"] for part in data["participants"])
    game_minutes = data["gameDuration"] / 60.0

    # Extract patch (e.g., "14.23")
    version = data.get("gameVersion", "0.0")
    patch = ".".join(version.split(".")[:2]) if "." in version else version

    return {
        "match_id": match_id,
        "summonername": name.lower(),
        "champion": p["championName"],
        "win": p["win"],
        "kills": p["kills"],
        "deaths": p["deaths"],
        "assists": p["assists"],
        "gameduration_min": int(data["gameDuration"] / 60),
        "gamecreation": datetime.fromtimestamp(data["gameCreation"]/1000, tz=timezone.utc).isoformat(),
        "gametype": queue_types.get(data.get("queueId", 0), "Unknown"),
        "role": p.get("role"),
        "lane": p.get("lane"),
        "teamPosition": p.get("teamPosition") or p.get("individualPosition"),
        
        "killsParticipation": round((p["kills"] + p["assists"]) / max(team_kills, 1), 3),
        "damagePerMinute": round(p["totalDamageDealtToChampions"] / game_minutes, 1),
        "visionScore": p.get("visionScore", 0),
        "visionScorePerMinute": round(p.get("visionScore", 0) / game_minutes, 2),
        
        "goldEarned": p["goldEarned"],
        "totalCs": p["totalMinionsKilled"] + p.get("neutralMinionsKilled", 0),
        "cspm": round((p["totalMinionsKilled"] + p.get("neutralMinionsKilled", 0)) / game_minutes, 1),
        
        "firstBloodKill": p.get("firstBloodKill", False),
        "firstBloodAssist": p.get("firstBloodAssist", False),
        
        "gameMode": data.get("gameMode"),
        "queueId": data.get("queueId"),
        "patch": patch,
    }