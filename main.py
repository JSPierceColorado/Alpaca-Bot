import os
import json
import datetime
import time
import re

import gspread
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

print("✅ main.py launched successfully")

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=chrome_options)

def scrape_tickers():
    url = "https://www.google.com/finance/markets/most-active?hl=en"
    driver = get_driver()
    driver.get(url)
    time.sleep(5)  # Let JS load
    elements = driver.find_elements(By.CSS_SELECTOR, "a[href^='/finance/quote/']")
    hrefs = [el.get_attribute("href") for el in elements if el.get_attribute("href")]
    driver.quit()

    pattern = re.compile(r'/quote/([A-Z.]+):')  # e.g., /quote/AAPL:NASDAQ
    tickers = set()
    for href in hrefs:
        match = pattern.search(href)
        if match:
            tickers.add(match.group(1))
    return sorted(tickers)

def update_tickers_tab(gc):
    print("🔍 Checking last scrape time...")
    sh = gc.open("Trading Log")
    sheet = sh.worksheet("tickers")

    try:
        last_scrape = sheet.acell("A1").value
        if last_scrape:
            last_dt = datetime.datetime.fromisoformat(last_scrape)
            if (datetime.datetime.utcnow() - last_dt).total_seconds() < 86400:
                print("⏳ Already scraped within 24 hours. Skipping update.")
                return
    except Exception as e:
        print("⚠️ Failed to check scrape time:", e)

    print("🌐 Scraping tickers from Google Finance...")
    tickers = scrape_tickers()
    print(f"✅ Found {len(tickers)} tickers.")

    existing = sheet.col_values(2)[1:]  # skip A1 timestamp and header row if exists
    new_tickers = [t for t in tickers if t not in existing]

    if not new_tickers:
        print("📭 No new tickers to add.")
    else:
        print(f"🆕 Appending {len(new_tickers)} new tickers.")
        rows = [[datetime.datetime.utcnow().isoformat(), t] for t in new_tickers]
        sheet.append_rows(rows)

    sheet.update("A1", datetime.datetime.utcnow().isoformat())  # update timestamp

# === Entry point ===
try:
    print("🔐 Authenticating Google Sheets...")
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON environment variable not set.")
    creds_dict = json.loads(creds_json)
    gc = gspread.service_account_from_dict(creds_dict)

    update_tickers_tab(gc)
    print("✅ Tickers updated successfully.")

except Exception as e:
    print("❌ Gspread or scrape operation failed:", e)
