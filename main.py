import os
import json
import time
import re
import requests
import gspread
import pandas as pd
from datetime import datetime
import concurrent.futures

print(">>>> RUNNING SCREENER-ONLY MAIN.PY <<<<")

SHEET_NAME = "Trading Log"
TICKERS_TAB = "tickers"
SP500_TAB = "sp500"
SCREENER_TAB = "screener"

RATE_LIMIT_DELAY = 0.1
REDDIT_RATE_LIMIT_DELAY = 1.0
MAX_WORKERS = 20
API_KEY = os.getenv("API_KEY")

def get_google_client():
    creds = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    return gspread.service_account_from_dict(creds)

def update_sp500_sheet(gc):
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    sp500_df = tables[0]
    tickers = [t.replace('.', '-') for t in sp500_df["Symbol"].tolist()]
    ws = gc.open(SHEET_NAME).worksheet(SP500_TAB)
    ws.clear()
    ws.append_row(["Symbol"])
    ws.append_rows([[t] for t in tickers])
    print(f"✅ Updated S&P 500 list in '{SP500_TAB}' tab ({len(tickers)} tickers).")
    return set(tickers)

def get_tickers_from_sheet(gc, tabname):
    ws = gc.open(SHEET_NAME).worksheet(tabname)
    return set([t.strip() for t in ws.col_values(1)[1:] if t.strip()])

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
        posts = data["da]()
