# src/config.py
"""
LoL Dashboard – Central configuration (FINAL – NO HARD-CODING EVER)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import pytz
from datetime import date, timedelta
from dotenv import load_dotenv

# ----------------------------------------------------------------------
# Load .env (one level up → credentials/.env)
# ----------------------------------------------------------------------
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials", ".env")
load_dotenv(_ENV_PATH)

# ----------------------------------------------------------------------
# Riot API
# ----------------------------------------------------------------------
API_KEY: str = os.getenv("RIOT_API_KEY")
if not API_KEY:
    raise ValueError("RIOT_API_KEY missing from .env")

ROUTING: str = "americas"

# ----------------------------------------------------------------------
# Insert start timestamp here (UTC-based)
# ----------------------------------------------------------------------
START_DATETIME_UTC = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
START_TIMESTAMP: int = int(START_DATETIME_UTC.timestamp() * 1000)

# Convert to Central for logging

central_version = START_DATETIME_UTC.astimezone(pytz.timezone("US/Central"))
print(f"[CONFIG] Dashboard starts from (Central): {central_version.strftime('%Y-%m-%d %I:%M %p %Z')}")
print(f"[CONFIG] START_TIMESTAMP (ms)          : {START_TIMESTAMP}")

# ----------------------------------------------------------------------
# Supabase
# ----------------------------------------------------------------------
SUPABASE_URL: str = os.getenv("SUPABASE_URL")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL or SUPABASE_KEY missing from .env")

# ----------------------------------------------------------------------
# Summoners
# ----------------------------------------------------------------------
SUMMONERS: List[Dict[str, str]] = [
    {"summonerName": "TreywayHella", "tagLine": "TWAY"},
    {"summonerName": "Ping is Skill", "tagLine": "NA1"},
    {"summonerName": "Simpleist", "tagLine": "Mewin"},
    #{"summonerName": "TEAGUZZLER19", "tagLine": "9810"},
    #{"summonerName": "DFG", "tagLine": "1v9"},
    #{"summonerName": "Tuzlo", "tagLine": "NA1"},
    #{"summonerName": "Kanto", "tagLine": "milk"},
]

# ----------------------------------------------------------------------
# Champion requirements per player
# ----------------------------------------------------------------------
CHAMPION_LISTS: Dict[str, Dict[str, Any]] = {
    "TreywayHella#TWAY": {
        "core_champions": ["LeeSin"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": ["LeeSin", "Volibear", "Kayn"],
    },
    "Ping is Skill#NA1": {
        "core_champions": ["Smolder", "Corki"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": [
            "Smolder",
            "Corki",
            "Viktor",
            "Aurora",
            "Veigar",
            "Galio",
            "Neeko",
            "Orianna",
            "Ahri",
        ],
    },
    "Simpleist#Mewin": {
        "core_champions": ["Gragas", "Gwen"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": [
            "KSante",
            "Ambessa",
            "Mordekaiser",
            "DrMundo",
            "Malphite",
        ],
    },
    "TEAGUZZLER19#9810": {
        "core_champions": ["Pantheon"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": [
            "Volibear",
            "Gangplank",
            "Ornn",
            "Malphite",
            "Chogath",
            "Mordekaiser",
        ],
    },
    "DFG#1v9": {
        "core_champions": ["Nidalee"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": [
            "Skarner",
            "Gwen",
            "Viego",
            "MonkeyKing",
            "XinZhao",
            "Sejuani",
        ],
    },
    "Tuzlo#NA1": {
        "core_champions": ["Yunara"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": [
            "Kaisa",
            "Sivir",
            "Xayah",
            "Jinx",
            "Smolder",
            "KogMaw",
            "Vayne",
        ],
    },
    "Kanto#milk": {
        "core_champions": ["Braum"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": ["Rakan", "Janna", "Bard", "Nautilus", "Neeko"],
    },
}

# ----------------------------------------------------------------------
# Queue type mapping
# ----------------------------------------------------------------------
queue_types: Dict[int, str] = {
    0: "Custom",
    400: "Normal Draft",
    420: "Ranked Solo",
    430: "Normal Blind",
    440: "Ranked Flex",
    450: "ARAM",
    700: "Clash",
    900: "URF",
    1020: "One for All",
    1700: "Arena",
    # add more if you want
}

# ----------------------------------------------------------------------
# Week helper – Monday of current week (UTC-based)
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# Week helper – Monday of the week we are ACTUALLY IN (Mon 00:00 → Sun 23:59)
# This is the correct one — Sunday belongs to the week that just ended
# ----------------------------------------------------------------------


def get_current_monday() -> date:
    """
    Returns the Monday of the current playing week.
    Sunday Nov 23 → 2025-11-17
    Monday Nov 24 → 2025-11-24
    """
    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())  # weekday(): 0=Mon → 6=Sun
    return monday
# ----------------------------------------------------------------------
# Final validation print
# ----------------------------------------------------------------------
print(f"[CONFIG] Current week start (Monday): {get_current_monday().isoformat()}")