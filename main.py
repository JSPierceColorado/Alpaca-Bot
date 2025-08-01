import requests
import gspread
import os
import json
from io import StringIO

print("✅ main.py launched successfully")

# Connect to Google Sheets
try:
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    creds_dict = json.load(StringIO(creds_json))
    gc = gspread.service_account_from_dict(creds_dict)
    sh = gc.open("Trading Log")
    worksheet = sh.worksheet("tickers")
    print("✅ Connected to Google Sheet tab 'tickers'")
except Exception as e:
    print("❌ Failed to connect to Google Sheet:", e)
    exit()

# Fetch from Google's internal JSON API
print("🌐 Fetching tickers from Google Finance API...")
try:
    url = "https://www.google.com/finance/_/GoogleFinanceUi/data/batchexecute"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
    }
    data = {
        "f.req": '[[["Mf2Ahd","[[null,[1]]]",null,"generic"]]]'
    }

    response = requests.post(url, headers=headers, data=data)
    text = response.text

    # Extract ticker symbols from the response
    tickers = list(set([
        item.split(":")[1].split(",")[0].strip('"')
        for item in text.split("\\n")
        if "ticker" in item and ":" in item
    ]))

    print(f"📊 Found {len(tickers)} tickers: {tickers}")
except Exception as e:
    print("❌ Failed to retrieve tickers:", e)
    exit()

# Add only new tickers
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
