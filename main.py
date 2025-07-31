import os
import yfinance as yf
from alpaca_trade_api.rest import REST, TimeFrame

def get_btc_price():
    btc = yf.Ticker("BTC-USD")
    hist = btc.history(period="2d", interval="5m")
    close_prices = hist["Close"]
    current_price = close_prices[-1]

    # Bollinger Bands
    rolling_mean = close_prices.rolling(window=20).mean()
    rolling_std = close_prices.rolling(window=20).std()
    lower_band = rolling_mean - 2 * rolling_std
    lower_bound = lower_band[-1]

    print(f"Price: {current_price:.2f}, Lower Band: {lower_bound:.2f}")

    return current_price, lower_bound

def place_buy_order(api, percent=0.10):
    account = api.get_account()
    available_cash = float(account.cash)
    amount_to_trade = round(available_cash * percent, 2)

    print(f"Available cash: ${available_cash:.2f}")
    print(f"Buying ${amount_to_trade:.2f} worth of BTC/USD")

    if amount_to_trade < 1:
        print("Not enough funds to place a trade.")
        return

    order = api.submit_order(
        symbol="BTC/USD",
        notional=amount_to_trade,
        side="buy",
        type="market",
        time_in_force="gtc"
    )
    print("Order placed:", order)

def main():
    # Alpaca credentials from environment
    API_KEY = os.environ["ALPACA_API_KEY"]
    SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]
    BASE_URL = os.environ.get("ALPACA_BASE_URL", "https://api.alpaca.markets")  # Use paper endpoint if needed

    api = REST(API_KEY, SECRET_KEY, BASE_URL)

    current_price, lower_band = get_btc_price()

    if current_price < lower_band:
    print("Dip detected. Placing order.")
    place_buy_order(api, percent=0.10)  # ← 10% of cash

    else:
        print("No trade signal.")

if __name__ == "__main__":
    main()
