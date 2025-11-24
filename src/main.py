# src/main.py
"""
LoL Dashboard – Entry Point
Automatically nukes all __pycache__ folders on every run
"""

import os
import shutil
from pathlib import Path

# ————————————————————————————————
# AUTO-NUKE ALL __pycache__ FOLDERS
# ————————————————————————————————
def nuke_pycache() -> None:
    project_root = Path(__file__).parent.parent  # D:\Projects\Coding Project\LOL_DashBoard
    deleted = 0
    for cache_dir in project_root.rglob("__pycache__"):
        try:
            shutil.rmtree(cache_dir)
            deleted += 1
        except Exception as e:
            print(f"[NUKE] Failed → {cache_dir} | {e}")
    if deleted == 0:
        print("[NUKE] No __pycache__ folders found")
    else:
        print(f"[NUKE] Cleaned {deleted} __pycache__ folder(s)\n")

# Main execution
if __name__ == "__main__":
    nuke_pycache()
    #
    from sheets import update_match_data, write_current_week, generate_champion_report
    from riot_api import get_summoner_puuid, get_match_ids, get_match_data

    print("Starting LoL Dashboard update...\n")

    update_match_data(
        get_summoner_puuid,
        get_match_ids,
        get_match_data
    )

    write_current_week()
    generate_champion_report()

    print("\nLoL Dashboard update complete!")