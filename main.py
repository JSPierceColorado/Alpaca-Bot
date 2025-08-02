import os
import json
import time
import requests
import gspread

# === Config ===
API_KEY = os.getenv("API_KEY")  # Make sure this is set in Railway env vars
TICKER = "GOOG"  # Changed from GOOGL to GOOG for better API compatibility
SHEET_NAME = "Trading Log"
TAB_NAME = "screener"

# === Google Sheets client ===
def get_google_client():
    creds = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    return gspread.service_account_from_dict(creds)

# === Polygon indicator helpers ===

def fetch_indicator(indicator, params=None):
    url = f"https://api.polygon.io/v1/indicators/{indicator}/{TICKER}"
    query = {"apiKey": API_KEY, "timespan": "day", "order": "desc", "limit": 1}
    if params:
        query.update(params)
    r = requests.get(url, params=query)
    r.raise_for_status()
    d = r.json()
    return d.get("results", {}).get("values", [])

def get_ema20():
    vals = fetch_indicator("ema", {"window":_
