import os
import json
import datetime
import gspread

print("✅ main.py launched successfully")

# Google Sheets check using environment variable
try:
    print("Attempting to open Google Sheet...")

    creds_json = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDS_JSON environment variable not set.")

    creds_dict = json.loads(creds_json)
    gc = gspread.service_account_from_dict(creds_dict)

    sh = gc.open("Trading Log")      # Your actual sheet title
    worksheet = sh.worksheet("log")  # Your actual tab name
    worksheet.update(
        values=[["✅ Setup test", datetime.datetime.now(datetime.UTC).isoformat()]],
        range_name="A1"
    )
    print("✅ Google Sheet updated successfully.")

except Exception as e:
    print("❌ Gspread operation failed:", e)
