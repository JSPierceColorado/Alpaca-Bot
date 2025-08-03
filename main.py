import os
import json
import time
import re
import requests
import gspread
import concurrent.futures
from datetime import datetime

# ===== CONFIGURATION =====
API_KEY = os.getenv("API_KEY")
SHEET_NAME = "Trading Log"
TICKERS_TAB = "tickers"
SCREENER_TAB = "screener"

RATE_LIMIT_DELAY = 0.6      # In seconds; adjust for your Polygon plan
MAX_WORKERS = 6             # Tune for your server/rate limits
EXCHANGES = {"XNYS", "XNAS", "ARCX"}

# ===== GOOGLE SHEETS AUTH =====
def get_google_client():
    creds = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    return gspread.service_account_from_dict(creds)

# ===== POLYGON API HELPERS =====
def get_with_rate_limit(url, params=None):
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    time.sleep(RATE_LIMIT_DELAY)
    return resp

def scrape_tickers():
    print("🌐 Fetching tickers from Polygon.io ticker API (MCAP > $750M)...")
    url = "https://api.polygon.io/v3/reference/tickers"
    params = {
        "market": "stocks",
        "active": "true",
        "limit": 1000,
        "apiKey": API_KEY
    }
    all_tickers = []
    total_raw = 0
    total_kept = 0
    next_url = url

    while next_url:
        if next_url == url:
            print(f"Requesting: {next_url} (params included)")
            resp = get_with_rate_limit(next_url, params=params)
        else:
            if next_url.startswith("/"):
                next_url = "https://api.polygon.io" + next_url
            if "apiKey=" not in next_url:
                sep = "&" if "?" in next_url else "?"
                next_url = f"{next_url}{sep}apiKey={API_KEY}"
            print(f"Requesting: {next_url}")
            resp = get_with_rate_limit(next_url)
        data = resp.json()
        for item in data["results"]:
            symbol = item["ticker"]
            exchange = item.get("primary_exchange")
            market_cap = item.get("market_cap", 0) or 0
            # Optional: filter by price (Polygon v3/reference/tickers returns "last_price" only if you ask for it)
            # price = item.get("last_price", 0) or 0

            if (
                exchange in EXCHANGES
                and market_cap > 750_000_000
                and re.match(r"^[A-Z]{1,5}$", symbol)
            ):
                all_tickers.append(symbol)
                total_kept += 1
        total_raw += len(data["results"])
        print(f"    Kept {total_kept} / {total_raw} so far (MCAP filter)")
        next_url = data.get("next_url")
    print(f"✅ Done. {len(all_tickers)} tickers with market cap > $750M.")
    return sorted(set(all_tickers))

# ===== GOOGLE SHEET HELPERS =====
def update_tickers_sheet(gc, tickers):
    ws = gc.open(SHEET_NAME).worksheet(TICKERS_TAB)
    print(f"📝 Writing {len(tickers)} tickers to the '{TICKERS_TAB}' tab...")
    ws.clear()
    ws.append_rows([[t] for t in tickers])
    return tickers

# ===== INDICATOR FETCH FUNCTIONS =====
def get_price(ticker):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
    params = {"adjusted": "true", "apiKey": API_KEY}
    resp = get_with_rate_limit(url, params=params)
    return resp.json().get("results", [{}])[0].get("c")

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
    resp = get_with_rate_limit(url, params=params)
    values = resp.json().get("results", {}).get("values", [])
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
    resp = get_with_rate_limit(url, params=params)
    values = resp.json().get("results", {}).get("values", [])
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
    resp = get_with_rate_limit(url, params=params)
    values = resp.json().get("results", {}).get("values", [])
    if values:
        return values[0].get("value"), values[0].get("signal")
    return None, None

def analyze_ticker(ticker):
    try:
        price = get_price(ticker)
        ema20 = get_ema20(ticker)
        rsi = get_rsi14(ticker)
        macd, signal = get_macd(ticker)
        
        buy_signals = []

        # Rule 1: Oversold + upturn
        if (rsi is not None and rsi < 35 and
            macd is not None and signal is not None and macd > signal and
            price is not None and ema20 is not None and price > ema20):
            buy_signals.append("Oversold + MACD + Price>EMA20")

        # Rule 2: Simple uptrend momentum
        if (price is not None and ema20 is not None and price > ema20 and
            macd is not None and signal is not None and macd > signal and
            rsi is not None and 35 <= rsi <= 65):
            buy_signals.append("Uptrend Momentum")

        # Rule 3: Very oversold only (for catching dips)
        if rsi is not None and rsi < 25:
            buy_signals.append("Very Oversold")

        # Add more rules here as needed!

        buy_reason = "; ".join(buy_signals)
        is_bullish = "✅" if buy_signals else ""

        return [
            ticker,
            round(price, 2) if price else "",
            round(ema20, 2) if ema20 else "",
            round(rsi, 2) if rsi else "",
            round(macd, 4) if macd else "",
            round(signal, 4) if signal else "",
            is_bullish,
            buy_reason,
            datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        ]
    except Exception as e:
        print(f"⚠️ {ticker} failed: {e}")
        return [ticker, "", "", "", "", "", "", "", ""]

def analyze_ticker_threaded(ticker):
    print(f"🔍 {ticker}")
    return analyze_ticker(ticker)

# ===== MAIN LOGIC =====
def main():
    print("🚀 Launching screener bot")
    gc = get_google_client()

    # 1. Scrape tickers from Polygon (with robust pagination)
    tickers = scrape_tickers()

    # 2. Write tickers to Google Sheet (tickers tab)
    update_tickers_sheet(gc, tickers)

    # 3. Analyze each ticker (concurrently) and collect indicator data
    print("📊 Analyzing tickers for bullish signals...")
    rows = []
    failures = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(analyze_ticker_threaded, tickers)
        for row in results:
            rows.append(row)
            if all(x == "" for x in row[1:6]):  # if all indicator columns failed
                failures.append(row[0])

    # 4. Clear and update screener tab with fresh indicator data
    ws = gc.open(SHEET_NAME).worksheet(SCREENER_TAB)
    print("🧹 Clearing screener tab of all existing data...")
    ws.clear()
    ws.append_row(["Ticker", "Price", "EMA_20", "RSI_14", "MACD", "Signal", "Bullish Signal", "Timestamp"])
    ws.append_rows(rows)
    print(f"✅ Screener tab updated. Failed tickers: {len(failures)}")
    if failures:
        print("Some tickers failed to fetch. See log above for details.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ Fatal error:", e)
