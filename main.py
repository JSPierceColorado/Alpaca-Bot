import yfinance as yf
import alpaca_trade_api as tradeapi
import gspread
import os
import json
from datetime import datetime
from io import StringIO

print("✅ main.py launched successfully")

# Optional: Check Alpaca live connection
try:
    print("🔌 Connecting to Alpaca LIVE environment...")
    api = tradeapi.REST(
        key_id=os.getenv("APCA_API_KEY_ID"),
        secret_key=os.getenv("APCA_API_SECRET_KEY"),
        base_url="https://api.alpaca.markets"
    )
    clock = api.get_clock()
    print("📅 Alpaca market clock:", clock)
except Exception as e:
    print("❌ Alpaca API connection failed:", e)

# Optional: Basic yfinance check
try:
    print("📈 Fetching AAPL data...")
    aapl = yf.Ticker("AAPL").history(period="1d")
    print(aapl.head())
except Exception as e:
    print("❌ yfinance failed:", e)

# Google Sheets test
try:
    print("📊 Connecting to Google Sheet...")
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("Missing GOOGLE_CREDS_JSON environment variable.")
    
    creds_dict = json.loads(creds_json)
    gc = gspread.service_account_from_dict(creds_dict)

    sh = gc.open("Trading Log")
    worksheet = sh.worksheet("log")
    worksheet.update(values=[["✅ Setup test", datetime.utcnow().isoformat()]], range_name="A1")
    print("✅ Google Sheet updated successfully.")
except Exception as e:
    print("❌ Google Sheets access failed:", e)
