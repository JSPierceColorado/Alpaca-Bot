import os
print("🔐 API KEY:", repr(os.environ.get("ALPACA_API_KEY")))
print("🔐 SECRET:", repr(os.environ.get("ALPACA_SECRET_KEY")))
import yfinance as yf
import pandas as pd
from datetime import datetime
from alpaca_trade_api.rest import REST
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

def log_trade(symbol, price, notional, cash_left):
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")

    if not creds_json:
        print("❌ Google credentials not found in environment variables.")
        return

    creds_dict = json.loads(creds_json)

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    sheet = client.open("Trading Log").worksheet("log")

    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        symbol,
        "BUY",
        f"{price:.2f}",
        f"{notional:.2f}",
        f"{cash_left:.2f}"
    ]
    sheet.append_row(row)
    print("📋 Trade logged to Google Sheets.")

def main():
    print("🧪 Running test log...")

    # Alpaca setup
    API_KEY = os.environ["ALPACA_API_KEY"]
    SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]
    BASE_URL = os.environ.get("ALPACA_BASE_URL", "https://api.alpaca.markets")

    api = REST(API_KEY, SECRET_KEY, BASE_URL)

    # Simulated trade data
    current_price = 61000.00
    symbol = "BTC/USD"

    # Get available cash from Alpaca account
    account = api.get_account()
    available_cash = float(account.cash)
    amount_to_trade = round(available_cash * 0.10, 2)

    print(f"Simulated BTC price: ${current_price:.2f}")
    print(f"Available cash: ${available_cash:.2f}")
    print(f"Logging simulated trade of ${amount_to_trade:.2f}...")

    # Only log, no real order
    log_trade(symbol, current_price, amount_to_trade, available_cash)

if __name__ == "__main__":
    main()
