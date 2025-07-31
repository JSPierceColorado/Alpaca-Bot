import yfinance as yf
import pandas as pd
import alpaca_trade_api as tradeapi
import gspread
import os
import json
from io import StringIO

print("✅ main.py launched successfully")

# Alpaca API connection check
try:
    print("Attempting Alpaca API connection...")
    api = tradeapi.REST(base_url="https://paper-api.alpaca.markets")  # No key/secret for dry run
    clock = api.get_clock()
    print("Alpaca market clock:", clock)
except Exception as e:
    print("❌ Alpaca API check failed:", e)

# yfinance check
try:
    print("Fetching AAPL from yfinance...")
    data = yf.Ticker("AAPL").history(period="1d")
    print(data)
except Exception as e:
    print("❌ yfinance failed:", e)

# Google Sheets check using environment variable
try:
    print("Attempting to open Google Sheet...")

    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON environment variable not set.")

    creds_dict = json.load(StringIO(creds_json))
    gc = gspread.service_account_from_dict(creds_dict)

    sh = gc.open("Trading Log")      # ✅ Your actual sheet title
    worksheet = sh.worksheet("log")  # ✅ Your actual tab name
    worksheet.update("A1", [["✅ Connected at runtime!"]])  # ✅ 2D list required
    print("✅ Google Sheet updated successfully.")

except Exception as e:
    print("❌ Gspread operation failed:", e)
