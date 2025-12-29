# Virtual Trading Platform (Indian Stocks)

## Screenshot

<img width="1920" height="1080" alt="{FA3449C0-34B7-4CD6-89C2-6A01D931BBBA}" src="https://github.com/user-attachments/assets/ad8f4032-9dd8-4173-9983-ec8cf0cca9c7" />


## 1. Project Overview
This is a comprehensive **Virtual Trading Platform** designed for the Indian Stock Market (NSE/BSE). It allows users to practice trading strategies using virtual money (Paper Trading) in a risk-free environment. The platform provides real-time stock data, interactive charts, portfolio tracking, and advanced trading features like Short Selling and Limit Orders.

## 2. Technology Stack
We chose a stack that ensures speed, portability, and ease of development:

*   **Backend:** Python **FastAPI** (High performance, async support).
*   **Database:** **SQLite** (Lightweight, serverless, built-in persistence).
*   **Frontend:** HTML5, JavaScript, **Bootstrap 5** (UI), **ApexCharts** (Financial Charting).
*   **Data Source:** `yfinance` library (Real-time market data from Yahoo Finance).
*   **Authentication:** JWT (JSON Web Tokens) with `bcrypt` for password hashing.

## 3. Features Implemented

### Core Trading
*   **Buy (Long):** Buy stocks expecting prices to rise.
*   **Sell (Short):** Sell stocks you don't own (Short Selling) to profit from falling prices.
*   **Limit Orders:** Set a target price. The system automatically executes the trade when the market hits your price (checked every 60s via background tasks).
*   **Portfolio Tracking:** Real-time calculation of holdings, average price, and total profit/loss.

### Market Analysis
*   **Interactive Charts:** Professional Candlestick charts with Zoom/Pan capabilities.
*   **Technical Indicators:** Toggleable **SMA (20)** (Simple Moving Average) and **RSI (14)** (Relative Strength Index).
*   **Multiple Timeframes:** View data for 1 Day (Intraday), 1 Week, 1 Month, 6 Months, or 1 Year.
*   **Live News Feed:** Real-time news headlines relevant to the selected stock.
*   **Watchlist:** Track favorite stocks without buying them.

### System Features
*   **User Authentication:** Secure Register/Login system.
*   **Data Persistence:** All trades, funds, and settings are saved in a database.
*   **Real-Time Updates:** The dashboard auto-refreshes prices every 5 seconds during market hours.
*   **PWA Support:** Can be installed as a native-like app on Android and Windows.

## 4. Challenges & Solutions

During development, we encountered and solved several critical technical challenges:

1.  **Chart Rendering Issues (Blank Chart)**
    *   *Problem:* The initial charting library (Lightweight Charts) struggled with gaps in daily data when using timestamps, and `yfinance` sometimes returned `NaN` (Not a Number) values which broke the JSON response.
    *   *Solution:* We switched to **ApexCharts** for better robustness. We also implemented strict data cleaning in the backend to filter out empty rows and explicitly convert `numpy` data types to standard Python `float/int`.

2.  **Yahoo Finance API Changes**
    *   *Problem:* The News feed suddenly stopped working because Yahoo changed their API response structure (nesting data inside a `content` object).
    *   *Solution:* We rewrote the news parsing logic in `main.py` to handle nested dictionaries safely and added fallback checks to prevent crashes.

3.  **JSON Serialization Errors**
    *   *Problem:* `yfinance` returns data using NumPy types (e.g., `np.float64`), which the standard Python JSON encoder cannot handle, causing API errors.
    *   *Solution:* We added a conversion layer in the API response to cast all numbers to native Python types before sending them to the frontend.

## 5. File Structure & Description

*   **`main.py`**: The heart of the application. Contains all API endpoints (`/buy`, `/sell`, `/history`), authentication logic, and background tasks for limit orders.
*   **`database.py`**: Handles SQLite database connection and table creation (`users`, `portfolio`, `transactions`, `limit_orders`).
*   **`static/`**: Contains frontend files served directly to the browser.
    *   **`index.html`**: The main dashboard interface with charts and trading controls.
    *   **`login.html`**: The user registration and login page.
    *   **`manifest.json` & `sw.js`**: Configuration files to make the app installable (PWA).
*   **`test_app.py`**: Automated unit tests to verify trading logic, math accuracy, and API availability.
*   **`requirements.txt`** (Implicit): List of dependencies (`fastapi`, `uvicorn`, `yfinance`, `pandas`, `bcrypt`, etc.).

## 6. Setup & Run Instructions

### Prerequisites
*   Python 3.8 or higher installed.

### Step 1: Installation
Open your terminal/command prompt in this folder and run:

```bash
# 1. Create a virtual environment
python -m venv venv

# 2. Activate the environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate

# 3. Install dependencies
pip install fastapi "uvicorn[standard]" yfinance requests pandas numpy passlib bcrypt python-jose python-multipart
```

### Step 2: Running the App
Start the server with hot-reloading enabled:

```bash
venv\Scripts\uvicorn main:app --reload
```

### Step 3: Using the Platform
1.  Open your browser and go to: `http://127.0.0.1:8000/login.html`
2.  **Register** a new account.
3.  **Login** to access the dashboard.
4.  **Add Funds** using the panel on the right.
5.  **Search** for a stock (e.g., `TCS.NS`, `RELIANCE.NS`).
6.  **Trade**: Buy or Sell stocks and watch your portfolio grow!

---
*Generated by Autonomous Coding Agent*
