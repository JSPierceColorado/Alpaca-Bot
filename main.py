from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Headless Chrome with stealth options
print("🌐 Launching headless browser...")
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/114.0.5735.199 Safari/537.36")

driver = webdriver.Chrome(options=chrome_options)

try:
    print("🌐 Navigating to Google Finance...")
    url = "https://www.google.com/finance/markets/most-active"
    driver.get(url)

    # Let JS execute
    time.sleep(5)

    # Try again to grab ticker elements
    ticker_elements = driver.find_elements(By.CSS_SELECTOR, 'div[role="row"] a')
    tickers = []

    for el in ticker_elements:
        href = el.get_attribute("href")
        if "/quote/" in href:
            symbol = href.split("/quote/")[-1].split(":")[-1].split("?")[0]
            tickers.append(symbol.strip())

    tickers = list(set(tickers))  # Remove duplicates

    print(f"📊 Found {len(tickers)} tickers: {tickers}")

except Exception as e:
    print("❌ Failed to extract tickers:", e)
    print("🔍 Page Source for Debugging:")
    print(driver.page_source[:1000])

finally:
    driver.quit()
