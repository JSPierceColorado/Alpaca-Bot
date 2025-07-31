import yfinance as yf
import pandas as pd
import alpaca_trade_api as tradeapi
import gspread

print("✅ main.py launched successfully")

# Optional: Dry-run Alpaca API check
try:
    print("Attempting Alpaca API connection...")
    api = tradeapi.REST(base_url="https://paper-api.alpaca.markets")  # No key/secret for dry run
    clock = api.get_clock()
    print("Alpaca market clock:", clock)
except Exception as e:
    print("❌ Alpaca API check failed:", e)

# Optional: Simple yfinance check
try:
    print("Fetching AAPL from yfinance...")
    data = yf.Ticker("AAPL").history(period="1d")
    print(data)
except Exception as e:
    print("❌ yfinance failed:", e)

# Optional: Gspread check (would need credentials to actually run)
try:
    print("Gspread loaded.")
except Exception as e:
    print("❌ Gspread failed:", e)
