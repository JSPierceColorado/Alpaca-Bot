import os
import json
import time
import requests
import gspread

# === Config ===
TAAPI_SECRET = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbHVlIjoiNjg4ZDg3NDM4MDZmZjE2NTFlMjgyZmY1IiwiaWF0IjoxNzU0MTA1OTc4LCJleHAiOjMzMjU4NTY5OTc4fQ.x2UU7E29mtXu2sP6ykFqA1Tgo_bY2Lip6W9xT5ilKg0"
TICKER = "GOOGL"
INTERVAL = "1d"

# === Google Sheets ===
def get_google_client():
    creds = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    return gspread.service_account_from_dict(creds)

# === TAAPI.IO ===
def fetch_indicators(symbol: str):
    url = "https://api.taapi.io/bulk"
    payload = {
        "secret": TAAPI_SECRET,
        "construct": {
            "type": "stocks",
            "symbol": symbol,
            "interval": INTERVAL,
            "indicators": [
                {"indicator": "price"},
                {"indicator": "ema", "period": 20},
                {"indicator": "stochrsi", "period": 14}
            ]
        }
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    data = response.json()

    print("🔎 Raw TAAPI.IO response:")
    print(json.dumps(data, indent=2))

    if "value" not in data:
        raise ValueError(f"TAAPI.IO returned an error or invalid structure: {data}")

    return data["value"]

# === Main ===
def main():
    print("🚀 Fetching indicators for GOOGL...")
    data = fetch_indicators(TICKER)

    price = data.get("price", "N/A")
    ema20 = data.get("ema", "N/A")
    stochrsi = data.get("stochrsi", {}).get("value", "N/A")

    print(f"📊 Price: {price}, EMA20: {ema20}, StochRSI: {stochrsi}")

    gc = get_google_client()
    ws = gc.open("Trading Log").worksheet("screener")
    ws.clear()
    ws.append_row(["Ticker", "Price", "EMA_20", "StochRSI", "Timestamp"])
    ws.append_row([
        TICKER,
        round(price, 2) if isinstance(price, (float, int)) else price,
        round(ema20, 2) if isinstance(ema20, (float, int)) else ema20,
        round(stochrsi, 2) if isinstance(stochrsi, (float, int)) else stochrsi,
        time.strftime("%Y-%m-%dT%H:%M:%SZ")
    ])
    print("✅ Screener tab updated.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
