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
    print("❌ Alpaca API check failed:", repr(e))

# yfinance check with fallback
try:
    print("Fetching AAPL from yfinance...")
    ticker = yf.Ticker("AAPL")
    data = ticker.history(period="1d", interval="1m")
    if data.empty:
        raise ValueError("AAPL: No data returned, symbol may be delisted or request failed.")
    print(data.head())
except Exception as e:
    print("❌ yfinance failed:", repr(e))

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

    worksheet.update("A1", "✅ Connected at runtime!")  # ✅ Fixed: Added value to write
    print("✅ Google Sheet up
