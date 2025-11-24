# src/sheets.py
"""
FINAL VERSION — Perfect week logic (Sunday belongs to current week)
- Only advances on Monday 00:00 UTC
- No more early zeros
"""

from __future__ import annotations

import pandas as pd
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Callable, Optional
import pytz

from supabase import create_client, Client

# ----------------------------------------------------------------------
# Central Time helper
# ----------------------------------------------------------------------
central_tz = pytz.timezone("US/Central")
def ms_to_central(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).astimezone(central_tz)

# ----------------------------------------------------------------------
# Config import
# ----------------------------------------------------------------------
from config import (
    SUPABASE_URL,
    SUPABASE_KEY,
    SUMMONERS,
    CHAMPION_LISTS,
    START_TIMESTAMP,
)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----------------------------------------------------------------------
# Current week helper — ONLY advances on Monday
# ----------------------------------------------------------------------
def _ensure_current_week() -> str:
    today = datetime.now(timezone.utc).date()
    current_monday = today - timedelta(days=today.weekday())  # Mon=0, Sun=6 → Sunday stays in current week

    res = supabase.table("current_week").select("week_start").execute()

    if not res.data:
        supabase.table("current_week").insert({"id": 1, "week_start": str(current_monday)}).execute()
        print(f"[INIT] current_week → {current_monday}")
        return str(current_monday)

    db_week_str = res.data[0]["week_start"]
    db_week = datetime.strptime(db_week_str, "%Y-%m-%d").date()

    if current_monday > db_week:
        # Only advance when we actually enter a new week (Monday+)
        supabase.table("current_week").update({"week_start": str(current_monday)}).eq("id", 1).execute()
        print(f"[ADVANCE] week {db_week} → {current_monday}")
        return str(current_monday)
    else:
        print(f"[CURRENT] Still in week {db_week} (today {today}, Sunday belongs here)")
        return db_week_str


# ----------------------------------------------------------------------
# 1. FETCH & UPSERT MATCHES 
# ----------------------------------------------------------------------
def update_match_data(
    get_puuid: Callable[[str, str], str],
    get_ids: Callable[[str, Optional[int]], List[str]],
    get_data: Callable[[str, str], Dict[str, Any]],
) -> None:
    total_new = 0

    for s in SUMMONERS:
        name = s["summonerName"]
        tag = s["tagLine"]
        puuid = get_puuid(name, tag)

        # Resume logic
        resume = supabase.table("last_fetched_match").select("lastMatchID").eq("summonerName", name).execute()
        start_time = START_TIMESTAMP
        if resume.data and resume.data[0]["lastMatchID"]:
            last_id = resume.data[0]["lastMatchID"]
            check = supabase.table("matches").select("gamecreation").eq("match_id", last_id).execute()
            if check.data:
                start_time = int(pd.Timestamp(check.data[0]["gamecreation"]).timestamp() * 1000) + 1
                print(f"[RESUME] {name} → after {ms_to_central(start_time):%Y-%m-%d %I:%M %p %Z}")
            else:
                print(f"[RESUME] Last match not found → starting from config")
        else:
            print(f"[START] {name} → from {ms_to_central(START_TIMESTAMP):%Y-%m-%d %I:%M %p %Z}")

        all_ids: List[str] = []
        current = start_time

        while True:
            print(f"\n[BATCH] startTime = {current}")
            batch = get_ids(puuid, current)
            print(f"[BATCH] Got {len(batch)} match IDs")

            if not batch:
                print("[DONE] No more matches")
                break

            all_ids.extend(batch)

            try:
                oldest_data = get_data(batch[-1], puuid)
                if oldest_data:
                    next_ts = int(pd.Timestamp(oldest_data["gamecreation"]).timestamp() * 1000) + 1
                    print(f"[JUMP] Next batch after → {ms_to_central(next_ts):%Y-%m-%d %I:%M %p %Z}")
                    if next_ts <= current:
                        print("[STOP] No progress → finished")
                        break
                    current = next_ts
                else:
                    print("[STOP] Oldest match has no data → stopping")
                    break
            except:
                break

            time.sleep(0.25)
            if len(all_ids) >= 2000:
                print("[CAP] 2000 matches reached")
                break

        print(f"[FETCH] Total IDs collected: {len(all_ids)}")

        # Remove Riot duplicate match IDs
        unique_ids = list(dict.fromkeys(all_ids))  # preserves order
        all_ids = unique_ids
        print(f"[DE-DUPE] Riot sent duplicates → reduced to {len(all_ids)} unique match IDs")

        # DB duplicate check
        if all_ids:
            existing = supabase.table("matches")\
                .select("match_id")\
                .eq("summonername", name.lower())\
                .in_("match_id", all_ids)\
                .execute()
            existing_ids = {row["match_id"] for row in existing.data} if existing.data else set()
            new_ids = [mid for mid in all_ids if mid not in existing_ids]
        else:
            new_ids = []

        print(f"[NEW] {len(new_ids)} truly new matches to insert")

        for mid in new_ids:
            try:
                data = get_data(mid, puuid)
                if not data:
                    print(f"  [SKIP] {mid} → deleted or fake")
                    continue

                clean = {k: v for k, v in data.items() if v is not None}
                clean["summonername"] = clean["summonername"].lower()
                clean.pop("id", None)

                supabase.table("matches").upsert(
                    clean,
                    on_conflict="match_id,summonername",
                    ignore_duplicates=True
                ).execute()

                total_new += 1
                print(f"  Inserted {mid} | {data.get('champion')} | {data.get('kills')}/{data.get('deaths')}/{data.get('assists')} | {'Win' if data.get('win') else 'Loss'}")

            except Exception as e:
                print(f"  [ERROR] {mid} → {e}")

        # Save resume point
        if all_ids:
            latest = all_ids[0]
            supabase.table("last_fetched_match").upsert(
                {"summonerName": name, "lastMatchID": latest},
                on_conflict="summonerName"
            ).execute()
            print(f"[RESUME POINT] {name} → {latest}")

    print(f"\nSUCCESS → {total_new} real matches inserted\n")


# ----------------------------------------------------------------------
# 2. weekly_requirements
# ----------------------------------------------------------------------
def write_current_week() -> None:
    week = _ensure_current_week()
    print(f"[REQUIREMENTS] Creating weekly_requirements for week {week}")

    rows = []
    for s in SUMMONERS:
        player = s["summonerName"].lower()
        key = f"{s['summonerName']}#{s['tagLine']}"
        cfg = CHAMPION_LISTS.get(key)
        if not cfg:
            continue

        for champ in cfg["core_champions"]:
            rows.append({
                "week_start": week,
                "summonername": player,
                "champion": champ,
                "required_games": cfg["learning_games_required"],
                "requirement_type": "Core Champion"
            })

        for champ in cfg["total_champions"]:
            if champ not in cfg["core_champions"]:
                rows.append({
                    "week_start": week,
                    "summonername": player,
                    "champion": champ,
                    "required_games": cfg["total_games_required"],
                    "requirement_type": "Practice Champion"
                })

    if rows:
        supabase.table("weekly_requirements").upsert(rows, on_conflict="week_start,summonername,champion").execute()

    print(f"[REQUIREMENTS] Done — {len(rows)} rows\n")


# ----------------------------------------------------------------------
# 3. champion_tracker 
# ----------------------------------------------------------------------
def generate_champion_report() -> None:
    print("[REPORT] Building champion_tracker — ALL real matches from START_TIMESTAMP")

    raw = supabase.table("matches").select("summonername, champion, gamecreation").execute().data
    if not raw:
        print("[REPORT] No matches yet")
        return

    df = pd.DataFrame(raw)
    df["gamecreation"] = pd.to_datetime(df["gamecreation"])
    start_dt = datetime.fromtimestamp(START_TIMESTAMP / 1000, tz=timezone.utc)
    df = df[df["gamecreation"] >= start_dt].copy()

    if df.empty:
        print("[REPORT] No matches after START_TIMESTAMP")
        return

    df["week_start"] = (df["gamecreation"] - pd.to_timedelta(df["gamecreation"].dt.weekday, unit='D')).dt.strftime('%Y-%m-%d')
    weekly_counts = df.groupby(["week_start", "summonername", "champion"]).size().to_dict()
    all_weeks = sorted(df["week_start"].unique())

    print(f"[REPORT] Found {len(df)} real matches across {len(all_weeks)} weeks")

    report = []
    for week in all_weeks:
        for s in SUMMONERS:
            player = s["summonerName"].lower()
            key = f"{s['summonerName']}#{s['tagLine']}"
            cfg = CHAMPION_LISTS.get(key)
            if not cfg:
                continue

            core_played = sum(weekly_counts.get((week, player, c), 0) for c in cfg["core_champions"])
            pool_played = sum(weekly_counts.get((week, player, c), 0) for c in cfg["total_champions"])

            report.extend([
                {"week_start": week, "summonername": player, "champion_type": "Learning Games (Core)", "games_played": core_played, "required_games": cfg["learning_games_required"], "difference": core_played - cfg["learning_games_required"], "met_requirement": "Yes" if core_played >= cfg["learning_games_required"] else "No"},
                {"week_start": week, "summonername": player, "champion_type": "Total Pool Games", "games_played": pool_played, "required_games": cfg["total_games_required"], "difference": pool_played - cfg["total_games_required"], "met_requirement": "Yes" if pool_played >= cfg["total_games_required"] else "No"},
            ])

    if report:
        supabase.table("champion_tracker").upsert(report, on_conflict="week_start,summonername,champion_type").execute()
        print(f"[REPORT] SUCCESS → {len(all_weeks)} weeks | {len(df)} matches | {len(report)//2} players updated")


# ----------------------------------------------------------------------
# 4. weekly_summary — clean "this week" view
# ----------------------------------------------------------------------
def generate_weekly_summary() -> None:
    week = _ensure_current_week()
    print(f"[SUMMARY] Generating weekly_summary for {week}")

    tracker_data = supabase.table("champion_tracker")\
        .select("summonername", "champion_type", "games_played", "required_games", "met_requirement")\
        .eq("week_start", week)\
        .execute().data

    summary_rows = []
    for s in SUMMONERS:
        player = s["summonerName"].lower()
        key = f"{s['summonerName']}#{s['tagLine']}"
        cfg = CHAMPION_LISTS.get(key)
        if not cfg:
            continue

        core_row = next((r for r in tracker_data if r["summonername"] == player and r["champion_type"] == "Learning Games (Core)"), None)
        pool_row = next((r for r in tracker_data if r["summonername"] == player and r["champion_type"] == "Total Pool Games"), None)

        summary_rows.append({
            "week_start": week,
            "summonername": player,
            "core_games_played": core_row["games_played"] if core_row else 0,
            "core_required": cfg["learning_games_required"],
            "pool_games_played": pool_row["games_played"] if pool_row else 0,
            "pool_required": cfg["total_games_required"],
        })

    if summary_rows:
        supabase.table("weekly_summary")\
            .upsert(summary_rows, on_conflict="week_start,summonername")\
            .execute()
        print(f"[SUMMARY] Updated {len(summary_rows)} players in weekly_summary")
    else:
        print("[SUMMARY] No players configured")