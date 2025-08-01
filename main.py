import os
import json
import gspread
import requests
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO

FINVIZ_URL = "https://finviz.com/screener.ashx?v=111&f=an_recom_buybetter,exch_nyse,fa_opermargin_pos,news_date_today&ft=4"

print("✅ main.py launched successfully")

# Google Sheets setup
try:
    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    creds_dict = json.load(StringIO(creds_json))
    gc = gspread.service_account_from_dict(creds_dict)
    sh = gc.open("Trading Log")
    worksheet = sh.worksheet("screener")
    worksheet.clear()
    print("✅ Connected to Google Sheet tab 'screener'")
except Exception as e:
    print("❌ Google Sheets setup failed:", e)
    worksheet = None

# Scrape all pages
def scrape_all_finviz_pages():
    print("📈 Scraping Finviz...")
    headers = {"User-Agent": "Mozilla/5.0"}
    page = 1
    all_data = []

    while True:
        paged_url = f"{FINVIZ_URL}&r={(page - 1) * 20 + 1}"
        res = requests.get(paged_url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", class_="table-light")

        if not table:
            break

        rows = table.find_all("tr")[1:]  # Skip header
        for row in rows:
            cols = [col.text.strip() for col in row.find_all("td")]
            if cols:
                all_data.append(cols)

        print(f"✅ Scraped page {page} with {len(rows)} entries")
        page += 1

    return all_data

# Process and upload
data = scrape_all_finviz_pages()

if data and worksheet:
    df = pd.DataFrame(data)
    worksheet.update([df.columns.tolist()] + df.values.tolist())
    print(f"✅ Wrote {len(df)} rows to Google Sheet")
else:
    print("⚠️ No data to write")
