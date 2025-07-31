import yfinance as yf
import pandas as pd
import alpaca_trade_api as tradeapi
import gspread

print("✅ main.py launched successfully")

# Alpaca dry-run
try:
    print("Attempting Alpaca API connection...")
    api = tradeapi.REST(base_url="https://paper-api.alpaca.markets")
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

# gspread test
try:
    print("Authenticating with Google Sheets...")
    gc = gspread.service_account(filename="credentials.json")

    print("Opening spreadsheet...")
    sh = gc.open("My Trading Log")  # 🔁 Replace with your actual spreadsheet name

    print("Opening worksheet...")
    worksheet = sh.worksheet("Sheet1")  # 🔁 Replace with your actual worksheet name

    print("Updating cell A1...")
    worksheet.update('A1', '✅ It works!')

except Exception as e:
    print("❌ Gspread operation failed:", e)
