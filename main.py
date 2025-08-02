import os
import json
import time
import requests
import gspread

# === Config ===
API_KEY = os.getenv("API_KEY")  # ✔️ Ensure this is set in Railway
TICKER = "GOOGL"
SHEET_NAME = "Trading Log"
TAB_NAME = "screener"

# === Google Sheets client ===
def get_google_client():
    creds = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    return gspread.service_account_from_dict(creds)

# === Polygon indicator helpers ===

def fetch_indicator(indicator, params=None):
    url = f"https://api.polygon.io/v1/indicators/{indicator}/{TICKER}"
    query = {"apiKey": API_KEY, "timespan": "day", "order": "desc", "limit": 1}
    if params:
        query.update(params)
    r = requests.get(url, params=query)
    r.raise_for_status()
    d = r.json()
    return d.get("results", {}).get("values", [])

def get_ema20():
    vals = fetch_indicator("ema", {"window": 20, "series_type": "close"})
    return vals[0].get("value") if vals else None

def get_sma50():
    vals = fetch_indicator("sma", {"window": 50, "series_type": "close"})
    return vals[0].get("value") if vals else None

def get_rsi14():
    vals = fetch_indicator("rsi", {"window": 14, "series_type": "close"})
    return vals[0].get("value") if vals else None

def get_macd():
    vals = fetch_indicator("macd", {
        "short_window": 12, "long_window": 26, "signal_window": 9, "series_type": "close"
    })
    if vals:
        v = vals[0]
        return v.get("value"), v.get("signal"), v.get("histogram")
    return None, None, None

def get_price():
    url = f"https://api.polygon.io/v2/last/trade/stocks/{TICKER}"
    resp = requests.get(url, params={"apiKey": API_KEY})
    resp.raise_for_status()
    return resp.json().get("results", {}).get("p")  # 'p' = last price

# === Main ===

def main():
    print(f"🔍 Fetching indicators for {TICKER} via Polygon.io")

    price = get_price()
    ema20 = get_ema20()
    sma50 = get_sma50()
    rsi14 = get_rsi14()
    macd_val, macd_sig, macd_hist = get_macd()

    print(f"📊 Price: {price}, EMA20: {ema20}, SMA50: {sma50}, RSI14: {rsi14}")
    print(f"💹 MACD: {macd_val}, Signal: {macd_sig}, Histogram: {macd_hist}")

    gc = get_google_client()
    ws = gc.open(SHEET_NAME).worksheet(TAB_NAME)
    ws.clear()
    headers = ["Ticker", "Price", "EMA_20", "SMA_50", "RSI_14", "MACD", "Signal", "Histogram", "Timestamp"]
    ws.append_row(headers)

    row = [
        TICKER,
        round(price, 2) if price else "",
        round(ema20, 2) if ema20 else "",
        round(sma50, 2) if sma50 else "",
        round(rsi14, 2) if rsi14 else "",
        round(macd_val, 4) if macd_val else "",
        round(macd_sig, 4) if macd_sig else "",
        round(macd_hist, 4) if macd_hist else "",
        time.strftime("%Y-%m-%dT%H:%M:%SZ")
    ]
    ws.append_row(row)
    print("✅ Screener tab updated with fresh data.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ Error:", e)
