import yfinance as yf
import pandas as pd
import alpaca_trade_api as tradeapi
import gspread
import os
import json
from io import StringIO
import requests

print("✅ main.py launched successfully")

# -------------------------------
# Fix for yfinance blocked requests
# -------------------------------
print("🔧 Setting up custom User-Agent for yfinance...")
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})
yf.utils.requests = session

# -------------------------------
# Alpaca API check (will fail until keys added)
# -------------------------------
try:
    print("Attempting Alpaca API connection...")
    api = tradeapi.REST()  # Will auto-read APCA_API_KEY_ID and APCA_API_SECRET_KEY from env
    clock = api.get_clock()
    print("Alpaca market clock:", clock)
except Exception as e:
    print("❌ Alpaca API check failed:", e)

# -------------------------------
# yfinance check
# -------------------------------
try:
    print("Fetching AAPL from yfinance...")
    data = yf.Ticker("AAPL").history(period="1d")
    if data.empty:
        print("AAPL: No price data found, symbol may be delisted (period=1d)")
    else:
        print(data)
except Exception as e:
    print("❌ yfinance failed:", e)

# -------------------------------
# Google Sheets check via env var
# -------------------------------
try:
    print("Attempting to open Google Sheet...")

    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON environment variable not set.")

    creds_dict = json.load(StringIO(creds_json))
    gc = gspread.service_account_from_dict(creds_dict)

    sh = gc.open("Trading Log")      # ✅ Your actual sheet title
    worksheet = sh.worksheet("log")  # ✅ Your actual tab name
    worksheet.update("A1", [["✅ Connected at runtime!"]])  # ✅ 2D list format for gspread
    print("✅ Google Sheet updated successfully.")

except Exception as e:
    print("❌ Gspread operation failed:", e)
