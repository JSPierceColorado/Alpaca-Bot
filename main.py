import requests
from bs4 import BeautifulSoup
import gspread
import os
import json
from io import StringIO
from datetime import datetime

print("✅ main.py launched successfully")

# Load credentials from environment variable
try:
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    creds_dict = json.load(StringIO(creds_json))
    gc = gspread.service_account_from_dict(creds_dict)

    # Open Google Sheet and get the 'tickers' worksheet
    sh = gc.open("Trading Log")
    worksheet = sh.worksheet("tickers")
    print("✅ Connected to Google Sheet tab 'tickers'")
except Exception as e:
    print("❌ Failed to connect to Google Sheet:", e)
    exit()

# Scrape Google Finance Most Active page
print("🌐 Scraping Google Finance most active page...")
try:
    url = "https://www.google.com/finance/markets/most-active"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")

    tickers = []
    for tag in soup.select("div.YMlKec.fxKbKc"):
        text = tag.text.strip()
        if text and text.isupper() and len(text) <= 5:
            tickers.append(text)

    tickers = list(set(tickers))  # Remove duplicates
    print(f"📊 Found {len(tickers)} tickers.")
except Exception as e:
    print("❌ Failed to scrape Google Finance:", e)
    exit()

# Add only new tickers to the sheet
try:
    existing_values = worksheet.col_values(1)
    existing_tickers = set(existing_values)
    new_tickers = [t for t in tickers if t not in existing_tickers]

    if new_tickers:
        next_row = len(existing_values) + 1
        for i, ticker in enumerate(new_tickers):
            worksheet.update(f"A{next_row + i}", [[ticker]])
        print(f"✅ Added {len(new_tickers)} new tickers to sheet.")
    else:
        print("ℹ️ No new tickers to add today.")
except Exception as e:
    print("❌ Failed to write to Google Sheet:", e)
