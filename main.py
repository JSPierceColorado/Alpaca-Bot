import os
import json
import yfinance as yf
import pandas as pd
import alpaca_trade_api as tradeapi
import gspread

print("✅ main.py launched successfully")

# --- STEP 1: Write credentials.json from environment variable ---
if "GOOGLE_CREDS_JSON" in os.environ:
    try:
        with open("credentials.json", "w") as f:
            f.write(os.environ["GOOGLE_CREDS_JSON"])
        print("✅ credentials.json written from env var")
    except Exception as e:
        print("❌ Failed to write credentials.json:", e)
else:
    print("❌ GOOGLE_CREDS_JSON not found in environment variables")

# --- STEP 2: Check Alpaca API connectivity ---
try:
    print("Attempting Alpaca API connection...")
    api = tradeapi.REST(base_url="https://paper-api.alpaca.markets")  # No key/secret for dry run
    clock = api.get_clock()
    print("✅ Alpaca market clock:", clock)
except Exception as e:
    print("❌ Alpaca API check failed:", e)

# --- STEP 3: Check yfinance fetch ---
try:
    print("Fetching AAPL from yfinance...")
    data = yf.Ticker("AAPL").history(period="1d")
    print("✅ yfinance data fetched")
    print(data)
except Exception as e:
    print("❌ yfinance failed:", e)

# --- STEP 4: Attempt to open and write to Google Sheet ---
try:
    print("Attempting to open sheet...")
    gc = gspread.service_account(filename="credentials.json")
    sh = gc.open("Your Sheet Name")         # Replace with exact sheet name
    worksheet = sh.worksheet("Sheet1")      # Replace with correct tab n
