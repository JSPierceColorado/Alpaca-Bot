import os
import json
import time
import re
import requests
import gspread
from datetime import datetime
import concurrent.futures
import yfinance as yf

# ========== CONFIGURATION ==========
SHEET_NAME = "Trading Log"
TICKERS_TAB = "tickers"
SCREENER_TAB = "screener"

RATE_LIMIT_DELAY = 0.1
REDDIT_RATE_LIMIT_DELAY = 1.0
MAX_WORKERS = 20
API_KEY = os.getenv("API_KEY")

# ========== GOOGLE SHEETS AUTH ==========
def get_google_client():
    creds = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    return gspread.service_account_from_dict(creds)

# ========== MULTI-SUBREDDIT TICKER SCRAPER ==========
def scrape_tickers_from_subreddit(subreddit):
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; Ticker-Screener/2.1)'}
    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
    params = {"limit": 100}
    after = None
    text_blocks = []
    total_posts = 0

    while True:
        if after:
            params["after"] = after
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 429:
            print(f"⚠️ Reddit rate-limited on r/{subreddit}! Sleeping for 5 seconds.")
            time.sleep(5)
            continue
        resp.raise_for_status()
        data = resp.json()
        posts = data["data"]["children"]
        if not posts:
            break
        for post in posts:
            title = post["data"].get("title", "")
            selftext = post["data"].get("selftext", "")
            text_blocks.append(title)
            if selftext:
                text_blocks.append(selftext)
        total_posts += len(posts)
        print(f"Scraped {total_posts} posts so far from r/{subreddit}...")
        after = data["data"].get("after")
        if not after:
            break
        time.sleep(REDDIT_RATE_LIMIT_DELAY)

    ticker_set = set()
    for text in text_blocks:
        matches = re.findall(r"\$?([A-Z]{2,5})\b", text)
        for match in matches:
            if match not in {"DD", "USA", "WSB", "CEO", "FOMO", "YOLO", "FD", "TOS", "ETF"}:
                ticker_set.add(match)
    print(f"🦍 Found {len(ticker_set)} tickers from r/{subreddit}: {', '.join(sorted(ticker_set))}")
    return ticker_set

# ========== GOOGLE SHEET HELPERS ==========
def update_tickers_sheet(gc, tickers):
    ws = gc.open(SHEET_NAME).worksheet(TICKERS_TAB)
    print(f"🧹 Clearing and writing {len(tickers)} tickers to the '{TICKERS_TAB}' tab...")
    ws.clear()
    ws.append_rows([[t] for t in tickers])
    return tickers

# ========== POLYGON INDICATOR FETCH FUNCTIONS ==========
def get_with_rate_limit(url, params=None):
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    time.sleep(RATE_LIMIT_DELAY)
    return resp

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

def get_volume_info(ticker):
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
    params = {"adjusted": "true", "apiKey": API_KEY}
    resp = get_with_rate_limit(url, params=params)
    results = resp.json().get("results", [])
    if results and "v" in results[0] and "av" in results[0]:
        return results[0]["v"], results[0]["av"]
    elif results and "v" in results[0]:
        return results[0]["v"], None
    return None, None

# ========== ANALYST CONSENSUS (YAHOO FINANCE/YFINANCE) ==========
def get_analyst_consensus(ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        # Use yfinance.info "recommendationKey" if available
        info = ticker_obj.info
        if "recommendationKey" in info:
            key = info["recommendationKey"]
            if key in ["buy", "strong_buy"]:
                return "buy"
        # Fallback: Use recommendations DataFrame
        recs = ticker_obj.recommendations
        if recs is not None and not recs.empty:
            latest = recs.iloc[-1]
            if "To Grade" in latest:
                grade = latest["To Grade"].lower()
                if "buy" in grade:
                    return "buy"
        return None
    except Exception as e:
        print(f"⚠️ {ticker} analyst consensus not found: {e}")
        return None

# ========== TECHNICAL ANALYSIS + BUY LOGIC ==========
def analyze_ticker(ticker):
    try:
        price = get_price(ticker)
        ema20 = get_ema20(ticker)
        rsi = get_rsi14(ticker)
        macd, signal = get_macd(ticker)
        vol, avg_vol = get_volume_info(ticker)

        if rsi is None or rsi < 15 or rsi > 80:
            return [
                ticker, price, ema20, rsi, macd, signal, "", "RSI out of range",
                datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            ]

        buy_signals = []
        if (
            ema20 is not None and ema20 > 0 and
            price is not None and
            rsi is not None and 25 < rsi < 65 and
            macd is not None and signal is not None and macd > signal and
            vol is not None and vol > 0 and
            (price > ema20 or rsi < 45)
        ):
            buy_signals.append("RSI 25-65, MACD crossover, Vol>0, Price>EMA20 or RSI<45")

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
            buy_reason if buy_reason else "Not all slightly-looser criteria met",
            datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        ]
    except Exception as e:
        print(f"⚠️ {ticker} failed: {e}")
        return [ticker, "", "", "", "", "", "", "", ""]

def analyze_ticker_threaded(ticker):
    print(f"🔍 {ticker}")
    return analyze_ticker(ticker)

def rank_row(row):
    try:
        price = float(row[1])
        ema20 = float(row[2])
        rsi = float(row[3])
        macd = float(row[4])
        signal = float(row[5])
        price_score = (price - ema20) / ema20 if ema20 > 0 else 0
        macd_score = macd - signal
        rsi_score = 60 - rsi  # prefer not-yet-overbought
        score = price_score * 2 + macd_score * 2 + rsi_score * 0.5
        return score
    except:
        return float('-inf')

# ========== FILTER: REMOVE ROWS WITH EXACTLY ZERO OR BLANK INDICATORS ==========
def any_indicator_zero_or_blank(row):
    for x in row[1:6]:
        if x == "" or x == 0 or x == 0.0 or x == "0" or x == "0.0" or x == "0.00":
            return True
    return False

# ========== MAIN ==========
def main():
    print("🚀 Launching Reddit multi-subreddit screener bot")
    gc = get_google_client()

    subreddits = ["wallstreetbets", "investing"]
    all_tickers = set()
    for sub in subreddits:
        all_tickers |= scrape_tickers_from_subreddit(sub)
    all_tickers = sorted(all_tickers)

    if not all_tickers:
        print("❌ No tickers found! Exiting.")
        return

    update_tickers_sheet(gc, all_tickers)

    print("📊 Analyzing tickers for buy signals...")
    rows = []
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(analyze_ticker_threaded, all_tickers)
        for row in results:
            if not any_indicator_zero_or_blank(row):
                rows.append(row)
            else:
                failures.append(row[0])

    # ========== ANALYST CONSENSUS FILTER ==========
    print("🧐 Filtering by analyst consensus ('buy' or better)...")
    filtered_rows = []
    for row in rows:
        ticker = row[0]
        if row[6] == "✅":
            consensus = get_analyst_consensus(ticker)
            if consensus == "buy":
                filtered_rows.append(row)

    print(f"✅ {len(filtered_rows)} stocks passed consensus filter.")

    # RANK AND FLAG TOP 5
    scored_rows = [(rank_row(row), row) for row in filtered_rows]
    scored_rows = [pair for pair in scored_rows if pair[0] != float('-inf')]
    scored_rows.sort(reverse=True, key=lambda x: x[0])
    top_5_indices = set(idx for idx, (_, _) in enumerate(scored_rows[:5]))

    # Add RankScore and TopPick columns
    output_rows = []
    for idx, (score, row) in enumerate(scored_rows):
        top_pick = "TOP 5" if idx in top_5_indices else ""
        output_rows.append(row + [round(score, 3), top_pick])

    ws = gc.open(SHEET_NAME).worksheet(SCREENER_TAB)
    print("🧹 Clearing screener tab of all existing data...")
    ws.clear()
    header = [
        "Ticker", "Price", "EMA_20", "RSI_14", "MACD", "Signal", 
        "Bullish Signal", "Buy Reason", "Timestamp", "RankScore", "TopPick"
    ]
    rows_to_write = [header] + output_rows
    ws.update(values=rows_to_write, range_name="A1")
    print(f"✅ Screener tab updated. Failed tickers: {len(failures)}")
    if failures:
        print("Some tickers failed to fetch all indicator data or had a zero value. See log above for details.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ Fatal error:", e)
