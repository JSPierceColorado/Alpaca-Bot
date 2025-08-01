import os
import json
import datetime
import gspread
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import re

print("✅ main.py launched successfully")

# === 1. Setup Google Sheet connection ===
try:
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON environment variable not set")

    creds_dict = json.loads(creds_json)
    gc = gspread.service_account_from_dict(creds_dict)

    sh = gc.open("Trading Log")
    worksheet = sh.worksheet("tickers")
    print("✅ Connected to Google Sheet tab 'tickers'")
except Exception as e:
    print("❌ Failed to connect to Google Sheet:", e)
    exit()

# === 2. Check if today's date already logged ===
today = datetime.datetime.utcnow().date().isoformat()
try:
    existing_dates = worksheet.col_values(2)
    if today in existing_dates:
        print("ℹ️ Already updated today. Exiting.")
        exit()
except Exception as e:
    print("⚠️ Could not check for existing dates:", e)

# === 3. Launch headless Chrome and scrape tickers ===
print("🌐 Launching headless browser...")
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.binary_location = "/usr/bin/chromium"

try:
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    print("🌐 Navigating to Google Finance...")
    driver.get("https://www.google.com/finance/markets/most-active")
    driver.implicitly_wait(10)

    # Extract ticker symbols using href pattern
    elements = driver.find_elements(By.CSS_SELECTOR, 'a[href^="/finance/quote/"]')
    tickers = set()
    for el in elements:
        href = el.get_attribute("href")
        match = re.search(r'/finance/quote/([A-Z.-]+):', href)
        if match:
            tickers.add(match.group(1))

    driver.quit()

    tickers = sorted(tickers)
    print(f"📊 Found {len(tickers)} tickers: {tickers}")

    if not tickers:
        print("⚠️ No tickers found.")
        exit()

except Exception as e:
    print("❌ Failed to extract tickers:", e)
    exit()

# === 4. Append new tickers to the sheet with today’s date ===
try:
    existing_tickers = worksheet.col_values(1)
    new_rows = []
    for ticker in tickers:
        if ticker not in existing_tickers:
            new_rows.append([ticker, today])

    if new_rows:
        worksheet.append_rows(new_rows)
        print(f"✅ Added {len(new_rows)} new tickers to sheet.")
    else:
        print("ℹ️ No new tickers to add today.")

except Exception as e:
    print("❌ Failed to update Google Sheet:", e)
