from fastapi.testclient import TestClient
from main import app
from database import get_db_connection, init_db
import unittest
import os

client = TestClient(app)

class TestTradingPlatform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.username = f"testuser_{os.urandom(4).hex()}"
        self.password = "testpass"
        client.post("/register", json={"username": self.username, "password": self.password})
        response = client.post("/token", data={"username": self.username, "password": self.password})
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_history_apexcharts_format(self):
        symbol = "RELIANCE.NS"
        # Test default history fetch
        response = client.get(f"/api/history/{symbol}?period=1mo&interval=1d", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        if len(data) > 0:
            first_candle = data[0]
            # Check for ApexCharts keys
            self.assertIn("x", first_candle)
            self.assertIn("y", first_candle)
            
            # Check types
            self.assertIsInstance(first_candle["x"], int) # Timestamp in ms
            self.assertIsInstance(first_candle["y"], list)
            self.assertEqual(len(first_candle["y"]), 4) # [Open, High, Low, Close]
            
            # Check volume and indicators
            self.assertIn("volume", first_candle)
            self.assertIn("sma", first_candle)
            self.assertIn("rsi", first_candle)

if __name__ == "__main__":
    unittest.main()