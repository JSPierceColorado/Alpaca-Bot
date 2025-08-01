import os
import re
import time
import datetime
import json

import gspread
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from io import StringIO

# 🟢 Startup confirmation
print("✅ main.py launched successfully")

# 📅 Daily tracking logic
today = datetime.datetime.utcnow().date()
TICKER_SOURCE_URL = "https://www.google.com/finance/markets/most-active"

# 🔐 Load credentials from env
try:
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("Missing GOOGLE_CREDS_JSON")

    creds_dict = json.load(StringIO(creds_json))
    gc = gspread.service_account_from_dict(creds_dict)
    sh = gc.open("Trading Log")
    worksheet = sh.worksheet("tickers")
    print("✅ Connected to Google Sheet tab 'tickers'")
except Exception as e:
    print("❌ Google Sheet connection failed:", e)
    exit(1)

# 🧠 Load existing tickers
existing = worksheet.col_values(1)
if existing and existing[0] == "date":
    existing = existing[1:]

# 🌐 Set up headless Chrome browser
print("🌐 Launching headless browser...")
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

# 🧭 Navigate to Google Finance
print("🌐 Navigating to Google Finance...")
try:
    driver.get(TICKER_SOURCE_URL)
    time.sleep(3)  # Let page load

    soup = BeautifulSoup(driver.page_source, "html.parser")
    anchors = soup.find_all("a", href=True)

    tickers = set()
    for a in anchors:
        match = re.match(r"^/quote/([A-Z.]+):[A-Z]+", a["href"])
        if match:
            ticker = match.group(1)
            tickers.add(ticker)

    tickers = sorted(tickers)
    print(f"📊 Found {len(tickers)} tickers: {tickers}")

except Exception as e:
    print("❌ Failed to extract tickers:", e)
    driver.quit()
    exit(1)

driver.quit()

# 📝 Add new tickers
new_tickers = [t for t in tickers if t not in existing]
if not new_tickers:
    print("ℹ️ No new tickers to add today.")
else:
    rows = [[today.isoformat(), t] for t in new_tickers]
    worksheet.append_rows(rows, value_input_option="RAW")
    print(f"✅ Added {len(rows)} new tickers to sheet.")
