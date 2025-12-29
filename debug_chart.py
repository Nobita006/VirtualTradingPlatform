import yfinance as yf
import pandas as pd
import numpy as np
import datetime

def test_chart_logic():
    symbol = "RELIANCE.NS"
    period = "1mo"
    interval = "1d"
    
    print(f"Fetching data for {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            print("ERROR: yfinance returned empty dataframe.")
            return

        print(f"Raw rows: {len(hist)}")
        print(hist.head())

        # Mimic main.py logic
        hist = hist.sort_index()

        if len(hist) > 20:
            hist['SMA_20'] = hist['Close'].rolling(window=20).mean()
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            hist['RSI'] = 100 - (100 / (1 + rs))
        else:
            hist['SMA_20'] = np.nan
            hist['RSI'] = np.nan
        
        data = []
        for date, row in hist.iterrows():
            # Check for NaNs in OHLC
            if pd.isna(row['Open']) or pd.isna(row['Close']):
                continue
                
            ts = int(date.timestamp())
            
            sma_val = row.get('SMA_20')
            if pd.isna(sma_val):
                sma_val = None
                
            rsi_val = row.get('RSI')
            if pd.isna(rsi_val):
                rsi_val = None
            
            vol = row.get('Volume')
            if pd.isna(vol):
                vol = 0

            data.append({
                "time": ts,
                "open": row['Open'],
                "high": row['High'],
                "low": row['Low'],
                "close": row['Close'],
                "volume": vol,
                "sma": sma_val,
                "rsi": rsi_val
            })
            
        print(f"Processed rows: {len(data)}")
        if len(data) > 0:
            print("Sample row:", data[-1])
        else:
            print("ERROR: Processed data is empty.")
            
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_chart_logic()