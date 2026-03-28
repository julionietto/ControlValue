import yfinance as yf
ticker = yf.Ticker("BTC")
history = ticker.history(period="1d")
print("Ticker BTC history:")
print(history)
if not history.empty:
    print(f"Close: {history['Close'].iloc[-1]}")

ticker_btc_usd = yf.Ticker("BTC-USD")
history_btc_usd = ticker_btc_usd.history(period="1d")
print("\nTicker BTC-USD history:")
print(history_btc_usd)
if not history_btc_usd.empty:
    print(f"Close: {history_btc_usd['Close'].iloc[-1]}")
