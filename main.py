import os
import json
import time
import gspread
import pandas as pd
from datetime import datetime
import requests

SHEET_NAME = "Trading Log"
SCREENER_TAB = "screener"
TICKERS_TAB = "tickers"
SP1500_TAB = "sp1500"

REDDIT_SUBS = ["wallstreetbets", "investing"]
REDDIT_LIMIT = 400

def get_google_client():
    creds = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    return gspread.service_account_from_dict(creds)

def get_sp1500_tickers():
    urls = [
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
        "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
    ]
    tickers = set()
    for url in urls:
        df = pd.read_html(url)[0]
        col = "Symbol" if "Symbol" in df.columns else "Ticker symbol"
        for ticker in df[col]:
            ticker = str(ticker).strip().upper().replace(".", "-")  # Alpaca/Polygon format
            tickers.add(ticker)
    return sorted(tickers)

def update_sp1500_sheet(gc):
    ws = gc.open(SHEET_NAME).worksheet(SP1500_TAB)
    tickers = get_sp1500_tickers()
    ws.clear()
    ws.append_row(["Ticker"])
    ws.append_rows([[t] for t in tickers])
    print(f"✅ Updated S&P 1500 list in '{SP1500_TAB}' tab ({len(tickers)} tickers).")

def scrape_reddit_tickers(subreddit, limit=400):
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    headers = {"User-Agent": "Mozilla/5.0"}
    tickers = set()
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        for post in data["data"]["children"]:
            title = post["data"]["title"]
            words = [w.strip("$").upper() for w in title.split()]
            for word in words:
                if (
                    word.isalpha()
                    and 1 <= len(word) <= 5
                    and word == word.upper()
                    and word not in {"A", "I", "US", "CEO", "YOLO", "ETF", "FOR", "BUY", "SELL", "ALL", "BIG", "AND", "THE", "IN", "OUT", "ON"}
                ):
                    tickers.add(word)
    except Exception as e:
        print(f"❌ Reddit scrape failed for r/{subreddit}: {e}")
    print(f"🦍 Found {len(tickers)} tickers from r/{subreddit}: {', '.join(sorted(list(tickers))[:15])}...")
    return tickers

def update_tickers_sheet(gc, tickers):
    ws = gc.open(SHEET_NAME).worksheet(TICKERS_TAB)
    ws.clear()
    ws.append_row(["Ticker"])
    ws.append_rows([[t] for t in sorted(tickers)])
    print(f"🧹 Clearing and writing {len(tickers)} tickers to the '{TICKERS_TAB}' tab...")

def get_tickers_from_sheet(gc, tab):
    ws = gc.open(SHEET_NAME).worksheet(tab)
    data = ws.col_values(1)[1:]
    return set(t.strip().upper() for t in data if t.strip())

def get_price(ticker, api_key):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
    params = {"adjusted": "true", "apiKey": api_key}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("results", [{}])[0].get("c")
    except Exception as e:
        return None

def get_ema20(ticker, api_key):
    url = f"https://api.polygon.io/v1/indicators/ema/{ticker}"
    params = {
        "apiKey": api_key,
        "timespan": "day",
        "limit": 1,
        "order": "desc",
        "window": 20,
        "series_type": "close"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        values = resp.json().get("results", {}).get("values", [])
        return values[0].get("value") if values else None
    except Exception as e:
        return None

def get_rsi14(ticker, api_key):
    url = f"https://api.polygon.io/v1/indicators/rsi/{ticker}"
    params = {
        "apiKey": api_key,
        "timespan": "day",
        "limit": 1,
        "order": "desc",
        "window": 14,
        "series_type": "close"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        values = resp.json().get("results", {}).get("values", [])
        return values[0].get("value") if values else None
    except Exception as e:
        return None

def get_macd(ticker, api_key):
    url = f"https://api.polygon.io/v1/indicators/macd/{ticker}"
    params = {
        "apiKey": api_key,
        "timespan": "day",
        "limit": 1,
        "order": "desc",
        "short_window": 12,
        "long_window": 26,
        "signal_window": 9,
        "series_type": "close"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        values = resp.json().get("results", {}).get("values", [])
        if values:
            return values[0].get("value"), values[0].get("signal")
        return None, None
    except Exception as e:
        return None, None

def analyze_ticker(ticker, api_key):
    try:
        price = get_price(ticker, api_key)
        ema20 = get_ema20(ticker, api_key)
        rsi = get_rsi14(ticker, api_key)
        macd, signal = get_macd(ticker, api_key)

        # Slightly relaxed criteria for bullish signal
        is_bullish = (
            rsi is not None and 25 < rsi < 65 and
            macd is not None and signal is not None and macd > signal and
            price is not None and ema20 is not None and (price > ema20 or rsi < 45)
        )

        # RankScore sample: higher RSI (up to 65) and price above EMA and MACD crossover, sum for demo
        rank_score = 0
        if price and ema20 and price > ema20:
            rank_score += 10
        if rsi:
            rank_score += max(0, min(rsi - 25, 40))  # 0 to 40
        if macd and signal and macd > signal:
            rank_score += 5

        buy_reason = ""
        if is_bullish:
            buy_reason = "RSI 25-65, MACD crossover, Vol>0, Price>EMA20 or RSI<45"
        elif rsi is not None or macd is not None:
            buy_reason = "Not all slightly-looser criteria met"
        else:
            buy_reason = ""

        return [
            ticker,
            round(price, 2) if price else "",
            round(ema20, 2) if ema20 else "",
            round(rsi, 2) if rsi else "",
            round(macd, 4) if macd else "",
            round(signal, 4) if signal else "",
            "✅" if is_bullish else "",
            buy_reason,
            datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            round(rank_score, 3),
            "",  # TopPick placeholder
        ]
    except Exception as e:
        print(f"⚠️ {ticker} failed: {e}")
        return [ticker, "", "", "", "", "", "", "", "", "", ""]

def main():
    print("🚀 Launching Reddit + S&P 1500 screener bot")
    gc = get_google_client()
    API_KEY = os.getenv("API_KEY")

    # Update S&P 1500 list
    update_sp1500_sheet(gc)

    # Scrape tickers from Reddit
    all_tickers = set()
    for subreddit in REDDIT_SUBS:
        all_tickers |= scrape_reddit_tickers(subreddit, limit=REDDIT_LIMIT)
    update_tickers_sheet(gc, all_tickers)

    # Get S&P 1500 tickers from the sheet
    sp1500_tickers = get_tickers_from_sheet(gc, SP1500_TAB)
    reddit_tickers = get_tickers_from_sheet(gc, TICKERS_TAB)

    # Find overlap: only analyze those in S&P 1500 and mentioned on Reddit
    eligible_tickers = sorted(list(reddit_tickers & sp1500_tickers))
    print(f"🔎 {len(eligible_tickers)} tickers matched S&P 1500.")

    # Analyze tickers and collect rows
    rows = []
    for ticker in eligible_tickers:
        print(f"🔍 {ticker}")
        row = analyze_ticker(ticker, API_KEY)
        # Don't include tickers where any indicator is exactly 0 or missing
        if any(str(v) == "0" for v in row[1:6]) or any(str(v).strip() == "" for v in row[1:6]):
            continue
        rows.append(row)

    # Rank: sort by RankScore descending, Top 5 get "TOP 5" in TopPick column
    rows_sorted = sorted(rows, key=lambda r: r[9], reverse=True)
    for i, row in enumerate(rows_sorted):
        if i < 5:
            row[10] = "TOP 5"

    # Write to screener tab in safe batches to avoid hangs
    ws = gc.open(SHEET_NAME).worksheet(SCREENER_TAB)
    ws.clear()
    headers = ["Ticker", "Price", "EMA_20", "RSI_14", "MACD", "Signal", "Bullish Signal", "Buy Reason", "Timestamp", "RankScore", "TopPick"]
    ws.append_row(headers)
    batch_size = 50
    for i in range(0, len(rows_sorted), batch_size):
        ws.append_rows(rows_sorted[i:i+batch_size])
    print(f"✅ Screener tab updated. {len(rows_sorted)} rows written.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("❌ Fatal error:", e)
        traceback.print_exc()
