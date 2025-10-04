# APILOLDataSync

Welcome to APILOLDataSync, a Python-based automation tool I developed to import League of Legends match data from the Riot API and update a Google Sheet with analytics. I built this to improve my skills and explore my passion for finding insights in data through computer automation, originally for my old college esports team to access past data. The data feeds into a Power BI dashboard, providing actionable insights to help them improve.

## Project Overview

This script automates fetching match data, aggregating it, and generating reports, showcasing my ability to build efficient data pipelines. Designed for my college esports team, it tracks performance metrics for multiple summoners and integrates with Power BI for visualization. It reflects my automation engineering skills in process optimization and real-time data integration.

## Skills and Tools

- **Python**: Core language for scripting and logic.
- **GitHub Version Control**: This repository tracks all script versions, demonstrating my Git expertise.
- **Modular Organization**: Split into files (`config.py`, `riot_api.py`, `sheets.py`, `main.py`) for maintainability.
- **Pandas**: Used for data manipulation and analysis.
- **API Integration**: Connects to Riot API for data and Google Sheets API for updates.
- **Error Handling**: Includes robust error management and rate limiting.
- **Automation Deployment**: Configured for home server use with cron and Docker.

## Features

- **Data Pipeline Creation**: Automates Riot API data collection and Google Sheet updates.
- **Report Generation**: Produces champion tracking reports for analysis.
- **Scalability**: Handles multiple summoners and match data effectively.
- **Power BI Integration**: Transforms data into a dashboard for team improvement.
- **Debugging**: Features print statements for troubleshooting.

## Setup and Installation

1. **Clone the Repository**: Download from this GitHub repo.
2. **Set Up Virtual Environment**:
   - Create: `python -m venv .venv`
   - Activate: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Linux/Mac)
3. **Install Dependencies**: Run `pip install -r requirements.txt`.
4. **Configure Credentials**:
   - Move `.env` to `credentials` folder (e.g., `credentials/.env`).
   - Edit `.env` with:
   RIOT_API_KEY=your-riot-api-key
   GOOGLE_CREDS_PATH=service_account.json
   - Add Google service account JSON (e.g., `service_account.json`) to `credentials`.
5. **Run the Script**: Execute `python src/main.py`.

## Automated Deployment

I’ve set this to run every 4 hours on my home server using cron and Docker for a production-like setup. This includes containerization for consistency and scheduled execution (e.g., `0 */4 * * * python /app/src/main.py`), highlighting my automation deployment skills.

## Why This Matters for Humana

As an automation engineer, I offer expertise in building data pipelines, API integration, and automated processes—key for Humana’s workflows. This project demonstrates my hands-on experience with process automation, error handling, and Power BI for data-driven decisions, making me a strong fit for your team.

## Last Updated
04:08 PM CDT, Saturday, October 04, 2025
