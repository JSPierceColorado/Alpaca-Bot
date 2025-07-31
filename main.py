import yfinance as yf
import pandas as pd
import alpaca_trade_api as tradeapi
import gspread
import os
import json
from io import StringIO

print("✅ main.py launched successfully")

# Optional: Set custom User-Agent for yfinance
import yfinance.shared
yfinance.shared._USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64)"

# 1. Alpaca LIVE Trade Execution for $1 BTC/USD
try:
    print("Connecting to Alpaca LIVE environment...")
    api = tradeapi.REST(
        key_id=os.getenv("APCA_API_KEY_ID"),
        secret_key=os.getenv("APCA_API_SECRET_KEY"),
        base_url="https://api.alpaca.markets"  # ✅ LIVE endpoint
    )

    clock = api.get_clock()
    print("Alpaca market clock:", clock)

    print("Submitting $1 fractional crypto order (BTC/USD)...")
    order = api.submit_order(
        symbol="BTC/USD",
        notional=1,             # ✅ $1 fractional buy
        side="buy",
        type="market",
        time_in_force="gtc"
    )
    print("✅ Trade submitted:", order.id)

except Exception as e:
    print("❌ Alpaca LIVE trade failed:", e)
    order = None

# 2. Google Sheets logging
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

    if order:
        worksheet.append_row([
            "BTC/USD",
            "buy",
            "$1",
            str(order.id),
            pd.Timestamp.now().isoformat()
        ])
        print("✅ Trade logged to Google Sheet.")
    else:
        print("ℹ️ No order to log.")

except Exception as e:
    print("❌ Gspread operation failed:", e)
