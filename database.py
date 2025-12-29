import sqlite3
import time

DB_NAME = "trading_platform.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        cash REAL DEFAULT 100000.0
    )''')
    
    # Portfolio Table
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio (
        user_id INTEGER,
        symbol TEXT,
        quantity INTEGER,
        PRIMARY KEY (user_id, symbol),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Transactions History
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        symbol TEXT,
        type TEXT,  -- 'BUY' or 'SELL'
        quantity INTEGER,
        price REAL,
        timestamp REAL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Watchlist
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (
        user_id INTEGER,
        symbol TEXT,
        PRIMARY KEY (user_id, symbol),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Limit Orders
    c.execute('''CREATE TABLE IF NOT EXISTS limit_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        symbol TEXT,
        target_price REAL,
        quantity INTEGER,
        type TEXT, -- 'BUY' or 'SELL'
        status TEXT DEFAULT 'PENDING', -- 'PENDING', 'EXECUTED', 'CANCELLED'
        created_at REAL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()