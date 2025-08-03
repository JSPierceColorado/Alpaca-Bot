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
    # Get hot posts from subreddit using Reddit's public API
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
                # Ticker: all uppercase, 1-5 letters, not a common English word
                if (word.isalpha() and 1 <= len(word) <= 5 and word == word.upper()
                        and word not in {"A", "I", "US", "CEO", "YOLO", "ETF", "FOR", "BUY", "SELL", "ALL", "BIG", "AND", "THE", "IN", "OUT", "ON"}):
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
    data = ws.col_values(1)[1:]  # Skip header
    return set(t.strip().upper() for t in data if t.strip())

def main():
    print("🚀 Launching Reddit + S&P 1500 screener bot")
    gc = get_google_client()

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

    # Placeholder: perform your technical analysis, indicator calculation, and screener tab update here
    # For now, we just print out the eligible tickers:
    for ticker in eligible_tickers:
        print(f"🔍 {ticker}")

    # Add your analysis + screener sheet update logic below this point as in your previous code

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("❌ Fatal error:", e)
        traceback.print_exc()
