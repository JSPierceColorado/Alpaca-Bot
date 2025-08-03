import os
import json
import time
import re
import requests
import gspread
import tempfile
import shutil
from datetime import datetime
import concurrent.futures

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ========== CONFIGURATION ==========
SHEET_NAME = "Trading Log"
TICKERS_TAB = "tickers"
SCREENER_TAB = "screener"

RATE_LIMIT_DELAY = 0.1
REDDIT_RATE_LIMIT_DELAY = 1.0
MAX_WORKERS = 20
API_KEY = os.getenv("API_KEY")
EXCHANGES = {"XNYS", "XNAS", "ARCX"}

# ========== BULLETPROOF CHROMEDRIVER FINDER + CHMOD FIX ==========
def get_chromedriver_service():
    ChromeDriverManager().install()
    root_dir = "/root/.wdm/drivers/chromedriver/"
    for root, dirs, files in os.walk(root_dir):
        for fname in files:
            path = os.path.join(root, fname)
            if fname == 'chromedriver':
                try:
                    with open(path, "rb") as f:
                        header = f.read(4)
                    if header == b'\x7fELF':
                        os.chmod(path, 0o755)
                        print(f"✅ Using ChromeDriver binary: {path}")
                        return Service(path)
                except Exception:
                    continue
    raise RuntimeError("Could not find a usable chromedriver ELF binary!")

# ========== GOOGLE SHEETS AUTH ==========
def get_google_client():
    creds = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    return gspread.service_account_from_dict(creds)

# ========== WSB TICKER SCRAPER ==========
def scrape_wsb_tickers_all():
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; WSB-Ticker-Screener/2.0)'}
    url = "https://www.reddit.com/r/wallstreetbets/hot.json"
    params = {"limit": 100}
    after = None
    text_blocks = []
    total_posts = 0

    while True:
        if after:
            params["after"] = after
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 429:
            print("⚠️ Reddit rate-limited us! Sleeping for 5 seconds.")
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
        print(f"Scraped {total_posts} WSB posts so far...")
        after = data["data"].get("after")
        if not after:
            break
        time.sleep(REDDIT_RATE_LIMIT_DELAY)

    # Regex for tickers: $AAPL or GME (1–5 uppercase letters)
    ticker_set = set()
    for text in text_blocks:
        matches = re.findall(r"\$?([A-Z]{2,5})\b", text)
        for match in matches:
            if match not in {"DD", "USA", "WSB", "CEO", "FOMO", "YOLO", "FD", "TOS", "ETF"}:
                ticker_set.add(match)
    tickers = sorted(ticker_set)
    print(f"🦍 Found {len(tickers)} tickers from r/wallstreetbets: {', '.join(tickers)}")
    return tickers

# ========== GOOGLE FINANCE SCRAPERS WITH ROBUST TEMP USER PROFILE ==========
def scrape_google_finance_most_active():
    print("🌐 Scraping Google Finance Most Active...")
    options = Options()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--single-process')
    user_data_dir = tempfile.mkdtemp(prefix="chrome_", dir="/tmp")
    options.add_argument(f'--user-data-dir={user_data_dir}')
    service = get_chromedriver_service()
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        url = "https://www.google.com/finance/markets/most-active"
        driver.get(url)
        time.sleep(2)
        anchors = driver.find_elements("css selector", "a[href*='/quote/']")
        tickers = set()
        for a in anchors:
            href = a.get_attribute("href")
            match = re.search(r"/quote/([A-Z.]+):[A-Z]+", href)
            if match:
                ticker = match.group(1)
                if ticker not in {"USD", "EUR", "JPY"}:
                    tickers.add(ticker)
        print(f"🔎 Found {len(tickers)} from Google Most Active: {', '.join(sorted(tickers))}")
        return list(tickers)
    finally:
        if driver:
            driver.quit()
        shutil.rmtree(user_data_dir, ignore_errors=True)

def scrape_google_finance_trending():
    print("🌐 Scraping Google Finance Trending...")
    options = Options()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--single-process')
    user_data_dir = tempfile.mkdtemp(prefix="chrome_", dir="/tmp")
    options.add_argument(f'--user-data-dir={user_data_dir}')
    service = get_chromedriver_service()
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        url = "https://www.google.com/finance/"
        driver.get(url)
        time.sleep(2.5)
        try:
            trending_tab = driver.find_element("xpath", "//button[contains(., 'Trending')]")
            trending_tab.click()
            time.sleep(1.5)
        except Exception as e:
            print("Trending tab may already be open or not found:", e)
        anchors = driver.find_elements("css selector", "a[href*='/quote/']")
        tickers = set()
        for a in anchors:
            href = a.get_attribute("href")
            match = re.search(r"/quote/([A-Z.]+):[A-Z]+", href)
            if match:
                ticker = match.group(1)
                if ticker not in {"USD", "EUR", "JPY"}:
                    tickers.add(ticker)
        print(f"🔎 Found {len(tickers)} from Google Trending: {', '.join(sorted(tickers))}")
        return list(tickers)
    finally:
        if driver:
            driver.quit()
        shutil.rmtree(user_data_dir, ignore_errors=True)

# ========== GOOGLE SHEET HELPERS ==========
def update_tickers_sheet(gc, tickers):
    ws = gc.open(SHEET_NAME).worksheet(TICKERS_TAB)
    print(f"📝 Writing {len(tickers)} tickers to the '{TICKERS_TAB}' tab...")
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

# ========== TECHNICAL ANALYSIS + BUY LOGIC ==========
def analyze_ticker(ticker):
    try:
        price = get_price(ticker)
        ema20 = get_ema20(ticker)
        rsi = get_rsi14(ticker)
        macd, signal = get_macd(ticker)
        
        buy_signals = []

        # Rule 1: Oversold bounce
        if (rsi is not None and rsi < 35 and
            macd is not None and signal is not None and macd > signal and
            price is not None and ema20 is not None and price > ema20):
            buy_signals.append("Oversold + MACD + Price>EMA20")

        # Rule 2: Uptrend momentum
        if (price is not None and ema20 is not None and price > ema20 and
            macd is not None and signal is not None and macd > signal and
            rsi is not None and 35 <= rsi <= 65):
            buy_signals.append("Uptrend Momentum")

        # Rule 3: Very oversold only
        if rsi is not None and rsi < 25:
            buy_signals.append("Very Oversold")

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

# ========== MAIN ==========
def main():
    print("🚀 Launching WSB + Google Finance screener bot")
    gc = get_google_client()

    # 1. Get tickers from WSB
    wsb_tickers = scrape_wsb_tickers_all()

    # 2. Get Google Finance Most Active
    google_active = scrape_google_finance_most_active()

    # 3. Get Google Finance Trending
    google_trending = scrape_google_finance_trending()

    # 4. Combine and deduplicate
    all_tickers = sorted(set(wsb_tickers + google_active + google_trending))
    print(f"✅ Total combined tickers: {len(all_tickers)}")

    if not all_tickers:
        print("❌ No tickers found! Exiting.")
        return

    # 5. Write tickers to Google Sheet (tickers tab)
    update_tickers_sheet(gc, all_tickers)

    # 6. Analyze each ticker and collect indicator data (parallelized)
    print("📊 Analyzing tickers for buy signals...")
    rows = []
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(analyze_ticker_threaded, all_tickers)
        for row in results:
            if all(str(x) != "" for x in row[1:6]):
                rows.append(row)
            else:
                failures.append(row[0])

    # 7. Clear and update screener tab with fresh indicator data
    ws = gc.open(SHEET_NAME).worksheet(SCREENER_TAB)
    print("🧹 Clearing screener tab of all existing data...")
    ws.clear()
    ws.append_row([
        "Ticker", "Price", "EMA_20", "RSI_14", "MACD", "Signal", 
        "Bullish Signal", "Buy Reason", "Timestamp"
    ])
    ws.append_rows(rows)
    print(f"✅ Screener tab updated. Failed tickers: {len(failures)}")
    if failures:
        print("Some tickers failed to fetch all indicator data. See log above for details.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ Fatal error:", e)
