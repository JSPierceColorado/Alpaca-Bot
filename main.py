import os
import json
import time
import re
import requests
import gspread

API_KEY = os.getenv("API_KEY")
SHEET_NAME = "Trading Log"
TICKERS_TAB = "tickers"
SCREENER_TAB = "screener"

def get_google_client():
    creds = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    return gspread.service_account_from_dict(creds)

def scrape_tickers():
    print("🌐 Fetching tickers from Polygon.io ticker API...")
    url = "https://api.polygon.io/v3/reference/tickers"
    params = {
        "market": "stocks",
        "active": "true",
        "limit": 1000,
        "apiKey": API_KEY
    }
    all_tickers = set()
    total = 0
    next_url = url

    while next_url:
        if next_url == url:
            resp = requests.get(next_url, params=params)
        else:
            # Always ensure next_url is a full URL
            if next_url.startswith("/"):
                next_url = "https://api.polygon.io" + next_url
            resp = requests.get(next_url)
        resp.raise_for_status()
        data = resp.json()
        tickers = [item["ticker"] for item in data["results"]
                   if item.get("primary_exchange") in {"XNYS", "XNAS", "ARCX"}]
        tickers = [t for t in tickers if re.match(r"^[A-Z]{1,5}$", t)]
        all_tickers.update(tickers)
        total += len(tickers)
        print(f"    Fetched {len(tickers)} tickers, total so far: {total}")
        next_url = data.get("next_url")
    print(f"✅ Fetched {len(all_tickers)} total tickers from Polygon")
    return sorted(all_tickers)

def update_tickers_sheet(gc, tickers):
    ws = gc.open(SHEET_NAME).worksheet(TICKERS_TAB)
    existing = ws.col_values(1)
    new_tickers = [t for t in tickers if t not in existing]
    if new_tickers:
        ws.append_rows([[t] for t in new_tickers])
    return list(set(existing + new_tickers))

def get_all_tickers_from_sheet(gc):
    ws = gc.open(SHEET_NAME).worksheet(TICKERS_TAB)
    tickers = ws.col_values(1)
    print(f"📒 Loaded {len(tickers)} tickers from sheet.")
    return tickers

def get_price(ticker):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
    response = requests.get(url, params={"adjusted": "true", "apiKey": API_KEY})
    response.raise_for_status()
    return response.json().get("results", [{}])[0].get("c")

def get_ema20(ticker):
    url = f"https://api.polygon.io/v1/indicators/ema/{ticker}"
    params = {
        "apiKey": API_KEY,
        "timespan": "day",
        "limit": 1,
        "order": "desc",
        "window": 20,
        "series_type": "close"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    values = response.json().get("results", {}).get("values", [])
    return values[0].get("value") if values else None

def get_rsi14(ticker):
    url = f"https://api.polygon.io/v1/indicators/rsi/{ticker}"
    params = {
        "apiKey": API_KEY,
        "timespan": "day",
        "limit": 1,
        "order": "desc",
        "window": 14,
        "series_type": "close"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    values = response.json().get("results", {}).get("values", [])
    return values[0].get("value") if values else None

def get_macd(ticker):
    url = f"https://api.polygon.io/v1/indicators/macd/{ticker}"
    params = {
        "apiKey": API_KEY,
        "timespan": "day",
        "limit": 1,
        "order": "desc",
        "short_window": 12,
        "long_window": 26,
        "signal_window": 9,
        "series_type": "close"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    values = response.json().get("results", {}).get("values", [])
    if values:
        return values[0].get("value"), values[0].get("signal")
    return None, None

def analyze_ticker(ticker):
    try:
        price = get_price(ticker)
        ema20 = get_ema20(ticker)
        rsi = get_rsi14(ticker)
        macd, signal = get_macd(ticker)

        is_bullish = (
            rsi is not None and rsi < 35 and
            macd is not None and signal is not None and macd > signal and
            price is not None and ema20 is not None and price > ema20
        )

        return [
            ticker,
            round(price, 2) if price else "",
            round(ema20, 2) if ema20 else "",
            round(rsi, 2) if rsi else "",
            round(macd, 4) if macd else "",
            round(signal, 4) if signal else "",
            "✅" if is_bullish else "",
            time.strftime("%Y-%m-%dT%H:%M:%SZ")
        ]
    except Exception as e:
        print(f"⚠️ {ticker} failed: {e}")
        return [ticker, "", "", "", "", "", "", ""]

def main():
    print("🚀 Launching screener bot")
    gc = get_google_client()

    # Fetch latest tickers from Polygon
    tickers = scrape_tickers()

    # Write tickers to tickers tab, avoid duplicates
    tickers = update_tickers_sheet(gc, tickers)

    print("📊 Analyzing tickers for bullish signals...")
    rows = []
    for t in tickers:
        print(f"🔍 {t}")
        row = analyze_ticker(t)
        rows.append(row)

    # Clear screener tab and update with new data
    ws = gc.open(SHEET_NAME).worksheet(SCREENER_TAB)
    print("🧹 Clearing screener tab of all existing data...")
    ws.clear()
    ws.append_row(["Ticker", "Price", "EMA_20", "RSI_14", "MACD", "Signal", "Bullish Signal", "Timestamp"])
    ws.append_rows(rows)
    print("✅ Screener tab updated.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ Fatal error:", e)
