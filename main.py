import os
import json
import requests
import pandas as pd
import yfinance as yf
import gspread
from io import StringIO
from bs4 import BeautifulSoup

print("✅ main.py launched successfully")

# Setup Google Sheet
try:
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON not set")

    creds_dict = json.load(StringIO(creds_json))
    gc = gspread.service_account_from_dict(creds_dict)
    sheet = gc.open("Trading Log")
    screener_ws = sheet.worksheet("screener")
    print("✅ Connected to Google Sheet tab 'screener'")
except Exception as e:
    print("❌ Failed to connect to Google Sheet:", e)
    screener_ws = None

# Scrape Finviz page 1
url = "https://finviz.com/screener.ashx?v=111&f=an_recom_buybetter%2Cexch_nyse%2Cfa_opermargin_pos%2Cnews_date_today&ft=4"
headers = {"User-Agent": "Mozilla/5.0"}

try:
    print("📈 Scraping Finviz...")
    html = requests.get(url, headers=headers).text
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="table-light")
    rows = table.find_all("tr")[1:]  # Skip header row

    tickers = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 2:
            ticker = cols[1].text.strip()
            tickers.append(ticker)

    print(f"✅ Found {len(tickers)} tickers on page 1")
except Exception as e:
    print("❌ Failed to scrape Finviz:", e)
    tickers = []

# Analyze each ticker
results = []
for symbol in tickers:
    try:
        data = yf.Ticker(symbol).history(period="3mo")
        if len(data) < 30:
            continue

        close = data["Close"]
        rsi = 100 - (100 / (1 + close.pct_change().dropna().rolling(14).mean() /
                           abs(close.pct_change().dropna().rolling(14).mean())))
        rsi_val = round(rsi.iloc[-1], 2)

        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9, adjust=False).mean()
        macd_signal = round(macd.iloc[-1] - signal.iloc[-1], 4)

        ma50 = close.rolling(50).mean().iloc[-1]
        current_price = round(close.iloc[-1], 2)

        results.append([
            symbol,
            current_price,
            rsi_val,
            macd_signal,
            "Yes" if current_price > ma50 else "No"
        ])
    except Exception as e:
        print(f"⚠️ Failed to analyze {symbol}: {e}")

# Write to Google Sheet
if screener_ws and results:
    headers = ["Symbol", "Price", "RSI", "MACD Signal", "Above MA50"]
    screener_ws.clear()
    screener_ws.append_row(headers)
    for row in results:
        screener_ws.append_row(row)
    print("✅ Screener data written to sheet")
else:
    print("⚠️ No screener data to write")
