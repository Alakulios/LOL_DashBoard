README.md
APILOLDataSync
Welcome to APILOLDataSync, a Python-based automation tool I developed to import League of Legends match data from the Riot API and seamlessly update a Google Sheet with detailed analytics. I built this to improve my skills and explore my passion for finding insights in data through computer automation, making it a perfect showcase of my capabilities as an aspiring automation engineer at Humana. Originally created for my old college esports team, this tool helps them quickly access past match data in a Google Sheet, which I then integrate into a Power BI dashboard to provide actionable insights and support their improvement.
Project Overview
This script automates the process of fetching player match data, aggregating it, and generating reports, demonstrating my ability to create efficient data pipelines. It’s designed to track performance metrics for multiple summoners, offering a practical application of automation engineering principles like process optimization and real-time data integration. The end goal is to feed this data into a Power BI dashboard, enabling the esports team to visualize trends and refine their strategies.
Skills and Tools
I’ve leveraged a variety of tools and techniques to build this project, highlighting my employability:

Python: The core language, showcasing my proficiency in scripting and logic implementation.
GitHub Version Control: This repository contains all versions of the script, reflecting my experience with Git for tracking changes and collaborating on code.
Modular File Organization: I split the codebase into multiple Python files (config.py, riot_api.py, sheets.py, main.py) to keep it organized and maintainable, a key skill in large-scale automation projects.
Pandas: Used for data manipulation and analysis, proving my ability to handle and process structured data efficiently.
API Integration: I integrated the Riot API to pull match data and the Google Sheets API to write results, demonstrating my expertise in connecting external services.
Error Handling and Rate Limiting: The script includes robust error management and rate limit handling, ensuring reliability in automated workflows.
Automation Deployment: I’ve set it up to run on a home server, showcasing my ability to deploy and manage automated processes.

How It Works
The script fetches match data for a list of summoners using the Riot API, processes it with pandas, and updates a Google Sheet ("LOL_Tracker") with details like wins, kills, and champion performance. It also generates weekly reports to track progress against learning and total game requirements, which are then visualized in Power BI for the esports team.
Features

Data Pipeline Creation: Automates data collection from the Riot API and updates Google Sheets, a valuable skill for streamlining business processes.
Report Generation: Produces detailed champion tracking reports, highlighting my data analysis and visualization capabilities.
Scalability: Designed to handle multiple summoners and match data, showing my ability to scale automation solutions.
Debugging: Includes print statements for troubleshooting, reflecting my problem-solving skills in automation.
Power BI Integration: Transforms the Google Sheet data into a dashboard, demonstrating my ability to deliver actionable insights for team improvement.

Setup and Installation
To get started with APILOLDataSync, follow these steps:

Clone the Repository: Download the code from this GitHub repository.
Set Up a Virtual Environment:

Create a virtual environment: python -m venv .venv
Activate it: .venv\Scripts\activate (Windows) or source .venv/bin/activate (Linux/Mac)


Install Dependencies: Run pip install -r requirements.txt to install all required packages.
Configure Credentials:

Move the .env file to the credentials folder (e.g., D:\Projects\Coding Project\LOL_Dashboard\credentials\.env).
Edit .env with your Riot API key and Google service account path:
textRIOT_API_KEY=your-riot-api-key
GOOGLE_CREDS_PATH=service_account.json

Place your Google service account JSON file (e.g., service_account.json) in the credentials folder.


Run the Script: Execute python src/main.py to start the automation process.

Automated Deployment
For a production-like setup, I’ve configured this script to run every 4 hours on my home server using cron and Docker. Here’s a general overview of the approach:

Docker: The script is containerized to ensure consistency across environments, demonstrating my knowledge of containerization for automation.
Cron: A cron job (e.g., 0 */4 * * * python /app/src/main.py) schedules the script, showcasing my ability to automate recurring tasks.
This setup runs on my home server, proving my capability to deploy and maintain automated solutions in a real-world context.

Why This Matters for Humana
As an automation engineer, I bring skills in building robust data pipelines, integrating APIs, and deploying automated processes—key assets for optimizing Humana’s workflows. This project reflects my hands-on experience with process automation, error handling, and scalable data solutions, including Power BI integration for data-driven decision-making, making me a strong candidate to contribute to your team.
