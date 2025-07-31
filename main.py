import yfinance as yf
import pandas as pd
import alpaca_trade_api as tradeapi
import gspread
import os
import json
from io import StringIO

print("✅ main.py launched successfully")

# yfinance User-Agent workaround
print("🔧 Setting up custom User-Agent for yfinance...")
yf.utils.get_yf_rh = lambda: {"User-Agent": "Mozilla/5.0"}

# Alpaca API connection check
try:
    print("Attempting Alpaca API connection...")
    api = tradeapi.REST(base_url="https://paper-api.alpaca.markets")  # No keys for dry run
    clock = api.get_clock()
    print("Alpaca market clock:", clock)
except Exception as e:
    print("❌ Alpaca API check failed:", e)

# yfinance check using download()
try:
    print("Fetching AAPL from yfinance...")
    data = yf.download("AAPL", period="1d")
    if data.empty:
        print("AAPL: No price data found, symbol may be delisted (period=1d)")
    else:
        print("AAPL price data:")
        print(data)
except Exception as e:
    print("❌ yfinance failed:", e)

# Google Sheets check using gspread with env var
try:
    print("Attempting to open Google Sheet...")

    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON environment variable not set.")

    creds_dict = json.load(StringIO(creds_json))
    gc = gspread.service_account_from_dict(creds_dict)

    sh = gc.open("Trading Log")      # ✅ Sheet title
    worksheet = sh.worksheet("log")  # ✅ Tab name

    worksheet.update(range_name="A1", values=[["✅ Connected at runtime!"]])
    print("✅ Google Sheet updated successfully.")
except Exception as e:
    print("❌ Gspread operation failed:", e)
