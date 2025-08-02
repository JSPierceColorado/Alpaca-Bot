import os
import json
import datetime
import time

import gspread
import pandas as pd
import numpy as np
from alpaca_trade_api.rest import REST, TimeFrame
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

print("✅ main.py launched successfully")

# --- Setup ---

def get_alpaca_client():
    api_key = os.getenv("APCA_API_KEY_ID")
    secret_key = os.getenv("APCA_API_SECRET_KEY")
    return REST(api_key, secret_key, base_url="https://paper-api.alpaca.markets")

def get_google_client():
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON environment variable not set.")
    creds_dict = json.loads(creds_json)
    return gspread.service_account_from_dict(creds_dict)

# --- Indicator Functions ---

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

# --- Main Logic ---

def analyze_tickers():
    gc = get_google_client()
    sh = gc.open("Trading Log")
    tickers_ws = sh.worksheet("tickers")
    screener_ws = sh.worksheet("screener")

    tickers = tickers_ws.col_values(1)
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    print(f"📈 Analyzing {len(tickers)} tickers...")

    client = get_alpaca_client()
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
                round(latest["EMA_20"], 2),
                round(latest["SMA_50"], 2),
                round(latest["RSI_14"], 2),
                round(latest["MACD"], 2),
                round(latest["Signal"], 2),
                "Yes" if latest["MACD_Crossover"] else "No",
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

# --- Run ---
try:
    analyze_tickers()
except Exception as e:
    print("❌ Fatal error:", e)
