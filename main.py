from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Set up headless browser
print("🌐 Launching headless browser...")
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=chrome_options)

try:
    print("🌐 Navigating to Google Finance...")
    url = "https://www.google.com/finance/markets/most-active"
    driver.get(url)

    # Wait for tickers to appear in DOM
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.YMlKec.fxKbKc'))
    )

    time.sleep(1.5)  # Just in case rendering is still happening

    # Extract symbols
    ticker_elements = driver.find_elements(By.CSS_SELECTOR, 'div.iLEcy div.zzDege')
    tickers = [el.text.strip() for el in ticker_elements if el.text.strip()]

    print(f"📊 Found {len(tickers)} tickers: {tickers}")

except Exception as e:
    print("❌ Failed to extract tickers:", e)
    print("🔍 Page Source for Debugging:")
    print(driver.page_source[:1000])  # Log first 1000 characters of page HTML

finally:
    driver.quit()
