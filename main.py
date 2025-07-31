import yfinance as yf
import pandas as pd
import alpaca_trade_api as tradeapi
import gspread
import os
import json
from io import StringIO
from datetime import datetime

print("✅ main.py launched successfully")

# Set up User-Agent for yfinance to avoid blocking
import requests
yf.utils.requests_wraps.wraps = lambda f: f  # Patch for recent yfinance versions
headers = {'User-Agent': 'Mozilla/5.0'}
yf.pdr_override()

print("🔧 Setting up custom User-Agent for yfinance...")

# Connect to Alpaca LIVE account
try:
    print("Connecting to Alpaca LIVE environment...")

    ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
    ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")
    ALPACA_BASE_URL = "https://api.alpaca.markets"

    api = tradeapi.REST(ALPACA_KEY, ALPACA_SECRET, base_url=ALPACA_BASE_URL)

    clock = api.get_clock()
    print("Alpaca market clock:", clock)

    print("Submitting $1 fractional stock order (VIG)...")
    order = api.submit_order(
        symbol="VIG",
        notional=1,
        side="buy",
        type="market",
        time_in_force="day"  # ✅ REQUIRED for fractional orders
    )
    print("✅ Order submitted:", order.id)

except Exception as e:
    print("❌ Alpaca LIVE trade failed:", e)
    order = None

# yfinance check
try:
    print("Fetching AAPL from yfinance...")
    data = yf.Ticker("AAPL").history(period="1d")
    print(data)
except Exception as e:
    print("❌ yfinance failed:", e)

# Google Sheets logging
try:
    print("Attempting to open Google Sheet...")

    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON environment variable not set.")

    creds_dict = json.load(StringIO(creds_json))
    gc = gspread.service_account_from_dict(creds_dict)

    sh = gc.open("Trading Log")
    worksheet = sh.worksheet("log")

    if order:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.append_row([
            now,
            order.symbol,
            order.side,
            order.notional,
            order.filled_qty if order.filled_qty else "PENDING",
            order.id
        ])
        print("✅ Order logged to Google Sheet.")
    else:
        worksheet.update(values=[["ℹ️ No order to log."]], range_name="A1")
        print("ℹ️ No order to log.")

except Exception as e:
    print("❌ Gspread operation failed:", e)
