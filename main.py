import os
import json
import time
import requests
import gspread

# === Configuration ===
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")  # You must set this in Railway env vars
TICKER = "GOOGL"
INTERVAL = "D"
SHEET_NAME = "Trading Log"
TAB_NAME = "screener"

# === Google Sheets ===
def get_google_client():
    creds = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    return gspread.service_account_from_dict(creds)

# === Finnhub API Calls ===
def fetch_price(ticker):
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json().get("c")  # current price

def fetch_indicator(ticker, indicator, params=None):
    url = f"https://finnhub.io/api/v1/indicator"
    query = {
        "symbol": ticker,
        "resolution": INTERVAL,
        "token": FINNHUB_API_KEY,
        "indicator": indicator,
    }
    if params:
        query.update(params)
    resp = requests.get(url, params=query)
    resp.raise_for_status()
    data = resp.json()
    return data

# === Main Logic ===
def main():
    print(f"🚀 Fetching indicators for {TICKER} using Finnhub...")

    # Fetch current price
    price = fetch_price(TICKER)
    print(f"💰 Current Price: {price}")

    # Fetch EMA(20)
    ema_data = fetch_indicator(TICKER, "ema", {"timeperiod": 20})
    ema_20 = ema_data.get("ema", [])[-1] if ema_data.get("ema") else "N/A"

    # Fetch RSI(14)
    rsi_data = fetch_indicator(TICKER, "rsi", {"timeperiod": 14})
    rsi_14 = rsi_data.get("rsi", [])[-1] if rsi_data.get("rsi") else "N/A"

    # Fetch MACD
    macd_data = fetch_indicator(TICKER, "macd", {"timeperiod": 12, "series_type": "close"})
    macd = (
        macd_data.get("macd", [])[-1] if macd_data.get("macd") else "N/A"
    )
    signal = (
        macd_data.get("macdSignal", [])[-1] if macd_data.get("macdSignal") else "N/A"
    )

    print(f"📈 EMA(20): {ema_20}, RSI(14): {rsi_14}, MACD: {macd}, Signal: {signal}")

    # Write to Google Sheet
    gc = get_google_client()
    ws = gc.open(SHEET_NAME).worksheet(TAB_NAME)
    ws.clear()
    ws.append_row(["Ticker", "Price", "EMA_20", "RSI_14", "MACD", "Signal", "Timestamp"])
    ws.append_row([
        TICKER,
        round(price, 2) if isinstance(price, (int, float)) else price,
        round(ema_20, 2) if isinstance(ema_20, (int, float)) else ema_20,
        round(rsi_14, 2) if isinstance(rsi_14, (int, float)) else rsi_14,
        round(macd, 2) if isinstance(macd, (int, float)) else macd,
        round(signal, 2) if isinstance(signal, (int, float)) else signal,
        time.strftime("%Y-%m-%dT%H:%M:%SZ")
    ])
    print("✅ Screener tab updated.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
