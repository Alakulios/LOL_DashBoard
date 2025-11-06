from datetime import datetime, timezone
from dotenv import load_dotenv
import os

# Load environment variables from .env file in src folder
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials", ".env"))

# Sensitive variables loaded from .env
API_KEY = os.getenv("RIOT_API_KEY")
CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH")
ROUTING = "americas"
MATCH_COUNT_PER_REQUEST = 100
START_TIMESTAMP = 1756702800000  # Sep 1, 2025, in milliseconds
CURRENT_TIMESTAMP = int(datetime.now(timezone.utc).timestamp() * 1000)
SUMMONERS = ["TreywayHella#TWAY", "Ping is Skill#NA1", "Simpleist#Mewin", "TEAGUZZLER19#9810", "DFG#1v9", "Tuzlo#NA1", "Kanto#milk"]
CHAMPION_LISTS = {  # Contains core champions and total champions for each summoner
    "TreywayHella#TWAY": {
        "core_champions": ["LeeSin"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": ["LeeSin", "Volibear", "Kayn"]
    },
    "Ping is Skill#NA1": {
        "core_champions": ["Smolder", "Corki"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": ["Smolder", "Corki", "Viktor", "Aurora", "Veigar", "Galio", "Neeko", "Orianna", "Ahri"]
    },
    "Simpleist#Mewin": {
        "core_champions": ["Gragas", "Gwen"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": ["KSante", "Ambessa", "Mordekaiser", "DrMundo", "Malphite"]
    },
    "TEAGUZZLER19#9810": {
        "core_champions": ["Pantheon"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": ["Volibear", "Gangplank", "Ornn", "Malphite", "Chogath", "Mordekaiser"]
    },
    "DFG#1v9": {
        "core_champions": ["Nidalee"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": ["Skarner", "Gwen", "Viego", "MonkeyKing", "XinZhao", "Sejuani"]
    },
    "Tuzlo#NA1": {
        "core_champions": ["Yunara"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": ["Kaisa", "Sivir", "Xayah", "Jinx", "Smolder", "KogMaw", "Vayne"]
    },
    "Kanto#milk": {
        "core_champions": ["Braum"],
        "learning_games_required": 2,
        "total_games_required": 10,
        "total_champions": ["Rakan", "Janna", "Bard", "Nautilus", "Neeko"]
    }
}
queue_types = {  # Takes queue ID and returns queue name
    0: "Custom Game",
    400: "Normal Draft",
    420: "Ranked Solo",
    430: "Normal Blind",
    440: "Ranked Flex",
    450: "ARAM",
    700: "Clash",
    900: "URF",
    1020: "One for All",
    1300: "Nexus Blitz",
    1400: "Ultimate Spellbook",
    1700: "Arena",
    1710: "Arena (2v2v2v2v2v2v2v2)",
    1800: "Doom Bots",
    600: "Doom Bots",
    1900: "Pick URF",
    3130: "Unknown Mode"
}

# Validate environment variables
if not API_KEY:
    raise ValueError("RIOT_API_KEY not found in src/.env file")
if not CREDS_PATH:
    raise ValueError("GOOGLE_CREDS_PATH not found in src/.env file")

# If CREDS_PATH is a relative path, try to resolve it in a couple of sensible places
if CREDS_PATH and not os.path.isabs(CREDS_PATH):
    # repo root is one directory above this file's directory
    repo_root = os.path.dirname(os.path.dirname(__file__))
    # First candidate: relative to repo root (common when env paths are repo-root relative)
    candidate_repo = os.path.normpath(os.path.join(repo_root, CREDS_PATH))
    # Second candidate: relative to the src directory (in case the .env was written assuming src as CWD)
    src_dir = os.path.dirname(__file__)
    candidate_src = os.path.normpath(os.path.join(src_dir, CREDS_PATH))

    if os.path.exists(candidate_repo):
        CREDS_PATH = candidate_repo
    elif os.path.exists(candidate_src):
        CREDS_PATH = candidate_src
    else:
        # Prefer the repo-root candidate in the final error message (more explicit), but do not silently pick a wrong location
        CREDS_PATH = candidate_repo

# Provide a clearer error if the file still does not exist
if CREDS_PATH and not os.path.exists(CREDS_PATH):
    raise FileNotFoundError(f"Google credentials file not found at: {CREDS_PATH}\nTried: {candidate_repo} and {candidate_src}")