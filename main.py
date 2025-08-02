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
    chrome_options.add_argument("--remote-debugging-port=9222")
    return webdriver.Chrome(options=chrome_options)

def scrape_tickers_from_url(url):
    print(f"🌐 Scraping: {url}")
    driver = get_driver()
    driver.get(url)
    time.sleep(5)  # Let the JavaScript render

    elements = driver.find_elements(By.TAG_NAME, "a")
    hrefs = [el.get_attribute("href") for el in elements if el.get_attribute("href")]
    driver.quit()

    pattern = re.compile(r'/quote/([A-Z.]+):[A-Z]+')  # Match /quote/AAPL:NASDAQ
    tickers = set()
    for href in hrefs:
        match = pattern.search(href)
        if match:
            tickers.add(match.group(1))

    print(f"🔍 Found {len(tickers)} tickers")
    return sorted(tickers)

def update_ticker_sheet(gc):
    print("📗 Updating 'tickers' tab...")
    sh = gc.open("Trading Log")
    sheet = sh.worksheet("tickers")

    # Get existing tickers from column A
    existing = set(sheet.col_values(1))
    print(f"📄 {len(existing)} existing tickers")

    # Scrape both sources
    most_active = scrape_tickers_from_url("https://www.google.com/finance/markets/most-active?hl=en")
    trending = scrape_tickers_from_url("https://www.google.com/finance/?hl=en")

    combined = set(most_active + trending)
    new_tickers = [t for t in combined if t not in existing]

    if not new_tickers:
        print("📭 No new tickers to add.")
    else:
        print(f"🆕 Appending {len(new_tickers)} new tickers.")
        values = [[t] for t in new_tickers]
        sheet.append_rows(values)

# === Entry point ===
try:
    print("🔐 Authenticating Google Sheets...")
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON environment variable not set.")
    creds_dict = json.loads(creds_json)
    gc = gspread.service_account_from_dict(creds_dict)

    update_ticker_sheet(gc)
    print("✅ Ticker scraping complete.")

except Exception as e:
    print("❌ Gspread or scrape operation failed:", e)
