import os
import json
import datetime
import time
import re

import gspread
import pandas as pd
import numpy as np
from alpaca_trade_api.rest import REST, TimeFrame
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

print("✅ main.py launched successfully")

# === Setup ===

def get_google_client():
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON environment variable not set.")
    creds_dict = json.loads(creds_json)
    return gspread.service_account_from_dict(creds_dict)

def get_alpaca_client():
    api_key = os.getenv("APCA_API_KEY_ID")
    secret_key = os.getenv("APCA_API_SECRET_KEY")
    return REST(api_key, secret_key, base_url="https://paper-api.alpaca.markets")

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=9222")
    return webdriver.Chrome(options=chrome_options)

# === Scrape Tickers ===

def scrape_tickers_from_url(url):
    print(f"🌐 Scraping: {url}")
    driver = get_driver()
    driver.get(url)
    time.sleep(5)
    elements = driver.find_elements(By.TAG_NAME, "a")
    hrefs = [el.get_attribute("href") for el in elements if el.get_attribute("href")]
    driver.quit()

    pattern = re.compile(r'/quote/([A-Z.]+):[A-Z]+')
    tickers = set()
    for href in hrefs:
        match = pattern.search(href)
        if match:
            tickers.add(match.group(1))

    print(f"🔍 Found {len(tickers)} tickers")
    return tickers

def update_ticker_sheet(gc):
    sheet = gc.open("Trading Log").worksheet("tickers")
    existing = set(sheet.col_values(1))

    urls = [
        "https://www.google.com/finance/markets/most-active?hl=en",
        "https://www.google.com/finance/?hl=en",
        "https://www.google.com/finance/markets/gainers?hl=en",
        "https://www.google.com/finance/markets/losers?hl=en"
    ]

    combined = set()
    for url in urls:
        combined.update(scrape_tickers_from_url(url))

    new_tickers = [t for t in sorted(combined) if t not in existing]

    if not new_tickers:
        print("📭 No new tickers to add.")
    else:
        print(f"🆕 Adding {len(new_tickers)} new tickers.")
        rows = [[t] for t in new_tickers]
        sheet.append_rows(rows)

# === Indicators ===

def calculate_indicators(df):
    df["EMA_20"] = df["close"].ewm(span=20).mean()
    df["SMA_50"] = df["close"].rolling(window=50).mean()

    delta = df["close"].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=14).mean()
    avg_loss = pd.Series(loss).rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df["RSI_14"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9).mean()
    df["MACD_Crossover"] = (df["MACD"] > df["Signal"]) & (df["MACD"].shift() <= df["Signal"].shift())

    return df

def safe(val):
    if pd.isna(val):
        return ""
    return round(val, 2) if isinstance(val, (float, int)) else val

# === Analyze Tickers ===

def analyze_tickers(gc, client):
    sheet = gc.open("Trading Log")
    tickers_ws = sheet.worksheet("tickers")
    screener_ws = sheet.worksheet("screener")

    raw_tickers = tickers_ws.col_values(1)
    tickers = [t.strip().upper() for t in raw_tickers if re.match(r'^[A-Z.]+$', t.strip())]
    tickers = list(set(tickers))
    print(f"📈 Analyzing {len(tickers)} tickers...")

    results = []

    for ticker in tickers:
        try:
            bars = client.get_bars(ticker, TimeFrame.Day, limit=100).df
            if bars.empty:
                print(f"⚠️ No data for {ticker}")
                continue

            df = bars.reset_index()
            df = df[["timestamp", "open", "high", "low", "close", "volume"]]
            df = calculate_indicators(df)

            latest = df.iloc[-1]
            results.append([
                ticker,
                safe(latest.get("EMA_20")),
                safe(latest.get("SMA_50")),
                safe(latest.get("RSI_14")),
                safe(latest.get("MACD")),
                safe(latest.get("Signal")),
                "Yes" if latest.get("MACD_Crossover") else "No",
                latest["timestamp"].isoformat()
            ])
            print(f"✅ {ticker} analyzed.")
        except Exception as e:
            print(f"❌ Error with {ticker}: {e}")

    if results:
        headers = [
            "Ticker", "EMA_20", "SMA_50", "RSI_14", "MACD",
            "Signal", "MACD_Crossover", "Timestamp"
        ]
        screener_ws.clear()
        screener_ws.append_row(headers)
        screener_ws.append_rows(results)
        print(f"📝 Wrote {len(results)} results to 'screener' tab.")

# === Run ===

try:
    gc = get_google_client()
    client = get_alpaca_client()

    update_ticker_sheet(gc)
    analyze_tickers(gc, client)

    print("✅ All tasks complete.")
except Exception as e:
    print("❌ Fatal error:", e)
