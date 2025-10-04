from sheets import initialize_sheets, update_match_data, write_current_week, generate_champion_report
from riot_api import get_summoner_puuid, get_match_ids, get_match_data

if __name__ == "__main__":
    sheet, worksheet, last_fetched_sheet = initialize_sheets()
    update_match_data(sheet, worksheet, last_fetched_sheet, get_summoner_puuid, get_match_ids, get_match_data)
    generate_champion_report(sheet, worksheet)
    write_current_week(sheet)