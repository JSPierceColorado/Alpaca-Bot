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
    time.sleep(5)  # Let JS load

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
    print("📗 Accessing 'tickers' tab...")
    sh = gc.open("Trading Log")
    sheet = sh.worksheet("tickers")

    existing = set(sheet.col_values(1))
    print(f"📄 {len(existing)} existing tickers in sheet")

    urls = [
        "https://www.google.com/finance/markets/most-active?hl=en",
        "https://www.google.com/finance/?hl=en",
        "https://www.google.com/finance/markets/gainers?hl=en",
        "https://www.google.com/finance/markets/losers?hl=en"
    ]

    combined_tickers = set()
    for url in urls:
        tickers = scrape_tickers_from_url(url)
        combined_tickers.update(tickers)

    new_tickers = [t for t in sorted(combined_tickers) if t not in existing]

    if not new_tickers:
        print("📭 No new tickers to add.")
    else:
        print(f"🆕 Adding {len(new_tickers)} new tickers to sheet.")
        rows = [[t] for t in new_tickers]
        sheet.append_rows(rows)

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
