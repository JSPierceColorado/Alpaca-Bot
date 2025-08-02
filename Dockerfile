import os
import json
import time
import re
import requests
import gspread
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# === CONFIG ===
API_KEY = os.getenv("API_KEY")
SHEET_NAME = "Trading Log"
TICKERS_TAB = "tickers"
SCREENER_TAB = "screener"
GOOGLE_FINANCE_URLS = [
    "https://www.google.com/finance/markets/most-active?hl=en",
    "https://www.google.com/finance/markets/gainers?hl=en",
    "https://www.google.com/finance/markets/losers?hl=en",
]

# === SETUP GOOGLE SHEETS ===
def get_google_client():
    creds = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    return gspread.service_account_from_dict(creds)

# === TICKER SCRAPER ===
def scrape_tickers():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    tickers = set()
    pattern = re.compile(r"/quote/([A-Z.]+):NASDAQ")

    for url in GOOGLE_FINANCE_URLS:
        driver.get(url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for a in soup.find_all("a", href=True):
            match = pattern.search(a["href"])
            if match:
                tickers.add(match.group(1))

    driver.quit()
    return sorted(tickers)

def update_tickers_sheet(gc, tickers):
    ws = gc.open(SHEET_NAME).worksheet(TICKERS_TAB)
    existing = ws.col_values(1)
    new_tickers = [t for t in tickers if t not in existing]
    if new_tickers:
        ws.append_rows([[t] for t in new_tickers])
    return list(set(existing + new_tickers))

# === POLYGON API CALLS ===
def get_price(ticker):
    time.sleep(16)
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev"
    data = requests.get(url, params={"adjusted": "true", "apiKey": API_KEY})
    data.raise_for_status()
    return data.json().get("results", [{}])[0].get("c")

def get_ema20(ticker):
    time.sleep(16)
    url = f"https://api.polygon.io/v1/indicators/ema/{ticker}"
    params = {
        "apiKey": API_KEY,
        "timespan": "day",
        "limit": 1,
        "order": "desc",
        "window": 20,
        "series_type": "close"
    }
    data = requests.get(url, params=params)
    data.raise_for_status()
    values = data.json().get("results", {}).get("values", [])
    return values[0].get("value") if values else None

def get_rsi14(ticker):
    time.sleep(16)
    url = f"https://api.polygon.io/v1/indicators/rsi/{ticker}"
    params = {
        "apiKey": API_KEY,
        "timespan": "day",
        "limit": 1,
        "order": "desc",
        "window": 14,
        "series_type": "close"
    }
    data = requests.get(url, params=params)
    data.raise_for_status()
    values = data.json().get("results", {}).get("values", [])
    return values[0].get("value") if values else None

def get_macd(ticker):
    time.sleep(16)
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
    data = requests.get(url, params=params)
    data.raise_for_status()
    values = data.json().get("results", {}).get("values", [])
    if values:
        return values[0].get("value"), values[0].get("signal")
    return None, None

# === ANALYSIS ===
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

# === MAIN ===
def main():
    print("🚀 Launching screener bot")
    gc = get_google_client()

    print("🌐 Scraping Google Finance...")
    scraped = scrape_tickers()
    print(f"✅ Scraped {len(scraped)} tickers")

    tickers = update_tickers_sheet(gc, scraped)
    print(f"🧾 Tracking {len(tickers)} tickers in sheet")

    print("📊 Analyzing tickers for bullish signals...")
    rows = []
    for t in tickers:
        print(f"🔍 {t}")
        row = analyze_ticker(t)
        rows.append(row)

    ws = gc.open(SHEET_NAME).worksheet(SCREENER_TAB)
    ws.clear()
    ws.append_row(["Ticker", "Price", "EMA_20", "RSI_14", "MACD", "Signal", "Bullish Signal", "Timestamp"])
    ws.append_rows(rows)
    print("✅ Screener tab updated.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ Fatal error:", e)
