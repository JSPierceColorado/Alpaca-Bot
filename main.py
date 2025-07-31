import os
import yfinance as yf
import pandas as pd
from datetime import datetime
from alpaca_trade_api.rest import REST
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

def get_btc_price():
    btc = yf.Ticker("BTC-USD")
    hist = btc.history(period="2d", interval="5m")
    close_prices = hist["Close"]
    current_price = close_prices.iloc[-1]

    # Bollinger Bands
    rolling_mean = close_prices.rolling(window=20).mean()
    rolling_std = close_prices.rolling(window=20).std()
    lower_band = rolling_mean - 2 * rolling_std
    lower_bound = lower_band.iloc[-1]

    print(f"📊 Current BTC Price: ${current_price:.2f}")
    print(f"📉 Lower Bollinger Band: ${lower_bound:.2f}")

    return current_price, lower_bound

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

def place_buy_order(api, current_price, percent=0.10, min_trade=1.00):
    account = api.get_account()
    available_cash = float(account.cash)
    amount_to_trade = round(available_cash * percent, 2)

    if amount_to_trade < min_trade:
        print(f"⚠️ Skipping trade: ${amount_to_trade:.2f} is below minimum threshold (${min_trade})")
        return

    print(f"✅ Buying ${amount_to_trade:.2f} of BTC/USD with ${available_cash:.2f} available cash...")

    try:
        order = api.submit_order(
            symbol="BTC/USD",
            notional=amount_to_trade,
            side="buy",
            type="market",
            time_in_force="gtc"
        )
        print("🚀 Order placed:", order)
        log_trade("BTC/USD", current_price, amount_to_trade, available_cash)
    except Exception as e:
        print("❌ Error placing order:", str(e))

def main():
    print("🔁 Running trading bot...")

    API_KEY = os.environ["ALPACA_API_KEY"]
    SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]
    BASE_URL = os.environ.get("ALPACA_BASE_URL", "https://api.alpaca.markets")

    api = REST(API_KEY, SECRET_KEY, BASE_URL)

    current_price, lower_band = get_btc_price()

    if current_price < lower_band:
        print("📉 Dip detected — executing trade...")
        place_buy_order(api, current_price, percent=0.10, min_trade=1.00)
    else:
        print("🕊️ No trade signal — price is above lower Bollinger Band.")

if __name__ == "__main__":
    main()
