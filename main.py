import os
import json
import gspread
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

print("✅ main.py launched successfully")

# Set up gspread
try:
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON env var missing.")
    creds_dict = json.loads(creds_json)
    gc = gspread.service_account_from_dict(creds_dict)
    sh = gc.open("Trading Log")
    worksheet = sh.worksheet("tickers")
    print("✅ Connected to Google Sheet tab 'tickers'")
except Exception as e:
    print("❌ Failed to connect to Google Sheet:", e)
    exit(1)

# Determine if update is needed
now = datetime.datetime.utcnow()
today_str = now.strftime("%Y-%m-%d")

existing_dates = worksheet.col_values(2)
if today_str in existing_dates:
    print("ℹ️ Sheet already updated today.")
    exit(0)

# Start headless Chrome browser
try:
    print("🌐 Launching headless browser...")
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    print("🌐 Navigating to Google Finance...")
    driver.get("https://www.google.com/finance/markets/most-active")
    driver.implicitly_wait(10)

    rows = driver.find_elements(By.CSS_SELECTOR, 'div[jsname="pP5Yhb"] .SxcTic')
    tickers = []

    for row in rows:
        try:
            ticker = row.find_element(By.CSS_SELECTOR, ".COaKTb").text.strip()
            if ticker:
                tickers.append(ticker)
        except:
            continue

    driver.quit()
    print(f"📊 Found {len(tickers)} tickers: {tickers}")

    if not tickers:
        print("⚠️ No tickers found.")
        exit(0)

    # Get current list
    existing_tickers = set(worksheet.col_values(1))
    new_entries = [(ticker, today_str) for ticker in tickers if ticker not in existing_tickers]

    if new_entries:
        worksheet.append_rows(new_entries, value_input_option="RAW")
        print(f"✅ Added {len(new_entries)} new tickers.")
    else:
        print("ℹ️ No new tickers to add today.")

except Exception as e:
    print("❌ Scraper failed:", e)
    exit(1)
