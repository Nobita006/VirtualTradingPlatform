from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import yfinance as yf
import requests
import sqlite3
import asyncio
import os
import bcrypt
import pandas as pd
import numpy as np
from jose import JWTError, jwt
from database import get_db_connection

# --- CONFIG ---
SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AUTH SECURITY ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    if user is None:
        raise credentials_exception
    return user

# --- MODELS ---
class UserRegister(BaseModel):
    username: str
    password: str

class TradeRequest(BaseModel):
    symbol: str
    quantity: int

class LimitOrderRequest(BaseModel):
    symbol: str
    quantity: int
    target_price: float
    type: str # BUY or SELL

class FundRequest(BaseModel):
    amount: float

class WatchlistRequest(BaseModel):
    symbol: str

# --- HELPER FUNCTIONS ---
def get_stock_price(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.fast_info.last_price
        if price is None:
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
        return price
    except:
        return None

def get_stock_data_full(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.fast_info.last_price
        prev_close = ticker.fast_info.previous_close
        return {"price": price, "prev_close": prev_close}
    except:
        return None

# --- BACKGROUND TASKS ---
async def check_limit_orders():
    while True:
        try:
            conn = get_db_connection()
            orders = conn.execute("SELECT * FROM limit_orders WHERE status='PENDING'").fetchall()
            
            for order in orders:
                price = get_stock_price(order['symbol'])
                if not price: continue
                
                execute = False
                if order['type'] == 'BUY' and price <= order['target_price']:
                    execute = True
                elif order['type'] == 'SELL' and price >= order['target_price']:
                    execute = True
                
                if execute:
                    user = conn.execute('SELECT * FROM users WHERE id = ?', (order['user_id'],)).fetchone()
                    cost = price * order['quantity']
                    
                    success = False
                    if order['type'] == 'BUY':
                        if user['cash'] >= cost:
                            conn.execute('UPDATE users SET cash = cash - ? WHERE id = ?', (cost, user['id']))
                            existing = conn.execute('SELECT quantity FROM portfolio WHERE user_id=? AND symbol=?', (user['id'], order['symbol'])).fetchone()
                            if existing:
                                conn.execute('UPDATE portfolio SET quantity = quantity + ? WHERE user_id=? AND symbol=?', (order['quantity'], user['id'], order['symbol']))
                            else:
                                conn.execute('INSERT INTO portfolio (user_id, symbol, quantity) VALUES (?, ?, ?)', (user['id'], order['symbol'], order['quantity']))
                            success = True
                    elif order['type'] == 'SELL':
                        conn.execute('UPDATE users SET cash = cash + ? WHERE id = ?', (cost, user['id']))
                        existing = conn.execute('SELECT quantity FROM portfolio WHERE user_id=? AND symbol=?', (user['id'], order['symbol'])).fetchone()
                        if existing:
                            new_qty = existing['quantity'] - order['quantity']
                            if new_qty == 0:
                                conn.execute('DELETE FROM portfolio WHERE user_id=? AND symbol=?', (user['id'], order['symbol']))
                            else:
                                conn.execute('UPDATE portfolio SET quantity = ? WHERE user_id=? AND symbol=?', (new_qty, user['id'], order['symbol']))
                        else:
                            conn.execute('INSERT INTO portfolio (user_id, symbol, quantity) VALUES (?, ?, ?)', (user['id'], order['symbol'], -order['quantity']))
                        success = True
                    
                    if success:
                        conn.execute('UPDATE limit_orders SET status="EXECUTED" WHERE id=?', (order['id'],))
                        conn.execute('INSERT INTO transactions (user_id, symbol, type, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?, ?)', 
                                     (user['id'], order['symbol'], order['type'], order['quantity'], price, datetime.now().timestamp()))
                        print(f"Executed Limit Order: {order['type']} {order['symbol']} @ {price}")
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Limit Order Error: {e}")
        
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_limit_orders())

# --- AUTH ENDPOINTS ---
@app.post("/register")
def register(user: UserRegister):
    conn = get_db_connection()
    try:
        hashed_pw = get_password_hash(user.password)
        conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (user.username, hashed_pw))
        conn.commit()
        return {"message": "User created successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    finally:
        conn.close()

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (form_data.username,)).fetchone()
    conn.close()
    if not user or not verify_password(form_data.password, user['password_hash']):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user['username']})
    return {"access_token": access_token, "token_type": "bearer"}

# --- API ENDPOINTS ---
@app.get("/api/me")
def read_users_me(current_user = Depends(get_current_user)):
    return {"username": current_user['username'], "cash": current_user['cash']}

@app.get("/api/search")
def search_stocks(q: str):
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {"q": q, "quotesCount": 10, "newsCount": 0}
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, params=params, headers=headers).json()
        results = []
        if "quotes" in res:
            for item in res["quotes"]:
                s = item.get("symbol", "")
                e = item.get("exchDisp", "").upper()
                if "NSE" in e or "BSE" in e or s.endswith(".NS") or s.endswith(".BO"):
                    results.append({"symbol": s, "name": item.get("shortname", s), "exch": e})
        return results
    except: return []

@app.get("/api/quote/{symbol}")
def get_quote(symbol: str):
    data = get_stock_data_full(symbol)
    if not data or data['price'] is None:
        raise HTTPException(status_code=404, detail="Stock not found")
    change = data['price'] - data['prev_close']
    change_p = (change / data['prev_close']) * 100 if data['prev_close'] else 0
    return {"symbol": symbol, "price": data['price'], "change": change, "change_percent": change_p}

@app.get("/api/history/{symbol}")
def get_history(symbol: str, period: str = "1mo", interval: str = "1d"):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        
        if hist is None or hist.empty:
            return []

        # Ensure sorted by date
        hist = hist.sort_index()

        # Calculate Indicators
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
            # Skip rows with NaN OHLC
            if pd.isna(row['Open']) or pd.isna(row['Close']):
                continue
            
            # ApexCharts expects Milliseconds
            ts = int(date.timestamp() * 1000)
            
            # Handle NaN indicators safely for JSON
            sma_val = row.get('SMA_20')
            if pd.isna(sma_val):
                sma_val = None
            else:
                sma_val = float(sma_val)
                
            rsi_val = row.get('RSI')
            if pd.isna(rsi_val):
                rsi_val = None
            else:
                rsi_val = float(rsi_val)
            
            # Handle Volume NaN
            vol = row.get('Volume')
            if pd.isna(vol):
                vol = 0
            else:
                vol = int(vol)

            # Format for ApexCharts: [timestamp, open, high, low, close]
            # We will return a dict to be flexible
            data.append({
                "x": ts,
                "y": [float(row['Open']), float(row['High']), float(row['Low']), float(row['Close'])],
                "volume": vol,
                "sma": sma_val,
                "rsi": rsi_val
            })
        return data
    except Exception as e:
        print(f"History Error: {e}")
        return []

@app.get("/api/news/{symbol}")
def get_news(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        raw_news = ticker.news
        clean_news = []
        
        if not raw_news:
            return []
            
        for item in raw_news:
            if not item:
                continue
                
            # Handle new Yahoo Finance structure
            content = item.get('content')
            
            title = None
            link = None
            
            if content:
                title = content.get('title')
                click_through = content.get('clickThroughUrl')
                if click_through and isinstance(click_through, dict):
                    link = click_through.get('url')
            
            # Fallback to old structure or top-level keys
            if not title:
                title = item.get('title')
            if not link:
                link = item.get('link') or item.get('url')
                
            if title and link:
                clean_news.append({"title": title, "link": link})
        return clean_news[:5]
    except Exception as e:
        print(f"News Error: {e}")
        return []

@app.post("/api/funds/add")
def add_funds(req: FundRequest, user = Depends(get_current_user)):
    if req.amount <= 0: raise HTTPException(status_code=400, detail="Invalid amount")
    conn = get_db_connection()
    conn.execute('UPDATE users SET cash = cash + ? WHERE id = ?', (req.amount, user['id']))
    conn.commit()
    conn.close()
    return {"message": "Funds added"}

@app.post("/api/funds/withdraw")
def withdraw_funds(req: FundRequest, user = Depends(get_current_user)):
    if req.amount <= 0: raise HTTPException(status_code=400, detail="Invalid amount")
    if user['cash'] < req.amount: raise HTTPException(status_code=400, detail="Insufficient funds")
    conn = get_db_connection()
    conn.execute('UPDATE users SET cash = cash - ? WHERE id = ?', (req.amount, user['id']))
    conn.commit()
    conn.close()
    return {"message": "Funds withdrawn"}

@app.get("/api/portfolio")
def get_portfolio(user = Depends(get_current_user)):
    conn = get_db_connection()
    rows = conn.execute('SELECT symbol, quantity FROM portfolio WHERE user_id = ?', (user['id'],)).fetchall()
    conn.close()
    
    holdings = []
    total_val = user['cash']
    
    for row in rows:
        data = get_stock_data_full(row['symbol'])
        price = data['price'] if data else 0
        val = price * row['quantity']
        total_val += val
        change_p = 0
        if data and data['prev_close']:
            change_p = ((price - data['prev_close']) / data['prev_close']) * 100
            
        holdings.append({
            "symbol": row['symbol'],
            "quantity": row['quantity'],
            "current_price": price,
            "total_value": val,
            "change_percent": change_p
        })
    return {"cash": user['cash'], "holdings": holdings, "total_portfolio_value": total_val}

@app.post("/api/buy")
def buy_stock(trade: TradeRequest, user = Depends(get_current_user)):
    if trade.quantity <= 0: raise HTTPException(status_code=400, detail="Invalid quantity")
    price = get_stock_price(trade.symbol)
    if not price: raise HTTPException(status_code=404, detail="Stock not found")
    
    cost = price * trade.quantity
    if user['cash'] < cost: raise HTTPException(status_code=400, detail="Insufficient funds")
    
    conn = get_db_connection()
    conn.execute('UPDATE users SET cash = cash - ? WHERE id = ?', (cost, user['id']))
    
    existing = conn.execute('SELECT quantity FROM portfolio WHERE user_id=? AND symbol=?', (user['id'], trade.symbol)).fetchone()
    if existing:
        conn.execute('UPDATE portfolio SET quantity = quantity + ? WHERE user_id=? AND symbol=?', (trade.quantity, user['id'], trade.symbol))
        new_qty = existing['quantity'] + trade.quantity
        if new_qty == 0:
            conn.execute('DELETE FROM portfolio WHERE user_id=? AND symbol=?', (user['id'], trade.symbol))
    else:
        conn.execute('INSERT INTO portfolio (user_id, symbol, quantity) VALUES (?, ?, ?)', (user['id'], trade.symbol, trade.quantity))
        
    conn.execute('INSERT INTO transactions (user_id, symbol, type, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?, ?)', 
                 (user['id'], trade.symbol, 'BUY', trade.quantity, price, datetime.now().timestamp()))
    conn.commit()
    conn.close()
    return {"message": f"Bought {trade.quantity} of {trade.symbol}"}

@app.post("/api/sell")
def sell_stock(trade: TradeRequest, user = Depends(get_current_user)):
    if trade.quantity <= 0: raise HTTPException(status_code=400, detail="Invalid quantity")
    price = get_stock_price(trade.symbol)
    if not price: raise HTTPException(status_code=404, detail="Stock not found")
    
    revenue = price * trade.quantity
    
    conn = get_db_connection()
    conn.execute('UPDATE users SET cash = cash + ? WHERE id = ?', (revenue, user['id']))
    
    existing = conn.execute('SELECT quantity FROM portfolio WHERE user_id=? AND symbol=?', (user['id'], trade.symbol)).fetchone()
    if existing:
        new_qty = existing['quantity'] - trade.quantity
        if new_qty == 0:
            conn.execute('DELETE FROM portfolio WHERE user_id=? AND symbol=?', (user['id'], trade.symbol))
        else:
            conn.execute('UPDATE portfolio SET quantity = ? WHERE user_id=? AND symbol=?', (new_qty, user['id'], trade.symbol))
    else:
        conn.execute('INSERT INTO portfolio (user_id, symbol, quantity) VALUES (?, ?, ?)', (user['id'], trade.symbol, -trade.quantity))
        
    conn.execute('INSERT INTO transactions (user_id, symbol, type, quantity, price, timestamp) VALUES (?, ?, ?, ?, ?, ?)', 
                 (user['id'], trade.symbol, 'SELL', trade.quantity, price, datetime.now().timestamp()))
    conn.commit()
    conn.close()
    return {"message": f"Sold {trade.quantity} of {trade.symbol}"}

@app.get("/api/transactions")
def get_transactions(user = Depends(get_current_user)):
    conn = get_db_connection()
    txs = conn.execute('SELECT * FROM transactions WHERE user_id=? ORDER BY timestamp DESC', (user['id'],)).fetchall()
    conn.close()
    return [dict(tx) for tx in txs]

@app.post("/api/limit-orders")
def create_limit_order(order: LimitOrderRequest, user = Depends(get_current_user)):
    conn = get_db_connection()
    conn.execute('INSERT INTO limit_orders (user_id, symbol, target_price, quantity, type, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                 (user['id'], order.symbol, order.target_price, order.quantity, order.type, datetime.now().timestamp()))
    conn.commit()
    conn.close()
    return {"message": "Limit order created"}

@app.get("/api/limit-orders")
def get_limit_orders(user = Depends(get_current_user)):
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM limit_orders WHERE user_id=? ORDER BY created_at DESC', (user['id'],)).fetchall()
    conn.close()
    return [dict(o) for o in orders]

@app.delete("/api/limit-orders/{order_id}")
def cancel_limit_order(order_id: int, user = Depends(get_current_user)):
    conn = get_db_connection()
    conn.execute('DELETE FROM limit_orders WHERE id=? AND user_id=?', (order_id, user['id']))
    conn.commit()
    conn.close()
    return {"message": "Order cancelled"}

@app.get("/api/watchlist")
def get_watchlist(user = Depends(get_current_user)):
    conn = get_db_connection()
    rows = conn.execute('SELECT symbol FROM watchlist WHERE user_id=?', (user['id'],)).fetchall()
    conn.close()
    results = []
    for row in rows:
        data = get_stock_data_full(row['symbol'])
        if data:
            change = data['price'] - data['prev_close']
            change_p = (change / data['prev_close']) * 100
            results.append({"symbol": row['symbol'], "price": data['price'], "change_percent": change_p})
    return results

@app.post("/api/watchlist")
def add_watchlist(req: WatchlistRequest, user = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO watchlist (user_id, symbol) VALUES (?, ?)', (user['id'], req.symbol))
        conn.commit()
    except: pass
    conn.close()
    return {"message": "Added"}

@app.delete("/api/watchlist/{symbol}")
def remove_watchlist(symbol: str, user = Depends(get_current_user)):
    conn = get_db_connection()
    conn.execute('DELETE FROM watchlist WHERE user_id=? AND symbol=?', (user['id'], symbol))
    conn.commit()
    conn.close()
    return {"message": "Removed"}

# Serve static
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/", StaticFiles(directory="static", html=True), name="static")