import yfinance as yf
import pandas as pd

def test_fetch():
    symbol = "RELIANCE.NS"
    print(f"--- Testing Data Fetch for {symbol} ---")
    
    # Test History
    try:
        print("Fetching History...")
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo", interval="1d")
        if hist.empty:
            print("ERROR: History is empty.")
        else:
            print(f"SUCCESS: Fetched {len(hist)} rows of history.")
            print(hist.head(2))
    except Exception as e:
        print(f"ERROR fetching history: {e}")

    # Test News
    try:
        print("\nFetching News...")
        news = ticker.news
        if not news:
            print("WARNING: News list is empty.")
        else:
            print(f"SUCCESS: Fetched {len(news)} news items.")
            print(news[0])
    except Exception as e:
        print(f"ERROR fetching news: {e}")

if __name__ == "__main__":
    test_fetch()