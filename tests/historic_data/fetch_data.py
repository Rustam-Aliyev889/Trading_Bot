import pandas as pd
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
import os

# Alpaca API credentials (replace with your own if necessary)
ALPACA_API_KEY = 'PKMVI5CXPN6CGPSUTMO2'
ALPACA_SECRET_KEY = 'yoB2K6D3gCvRepN3SkGFjSdzmeEXjxv6gZ0GNacw'
BASE_URL = 'https://paper-api.alpaca.markets'

# Initialize Alpaca API
api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, api_version='v2')

# Define the symbols and date range for historical data
symbols = ['AAPL', 'GOOG', 'AMZN', 'MSFT', 'META', 'TSLA', 'NFLX', 'NVDA', 'V', 'PYPL']
start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
end_date = datetime.now().strftime('%Y-%m-%d')

# Function to fetch historical data
def fetch_historical_data(symbols, start, end):
    historical_data = {}
    for symbol in symbols:
        try:
            bars = api.get_bars(symbol, tradeapi.TimeFrame.Day, start=start, end=end, adjustment='raw', feed='iex').df
            bars = bars.reset_index()
            bars['time'] = bars['timestamp'].dt.strftime('%Y-%m-%d')
            data = bars[['time', 'open', 'high', 'low', 'close', 'volume']]
            historical_data[symbol] = data
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
    return historical_data

# Fetch historical data
historical_data = fetch_historical_data(symbols, start_date, end_date)

# Create directory for historical data if it doesn't exist
os.makedirs('historic_data', exist_ok=True)

# Save the data to CSV files in the historic_data directory
for symbol, data in historical_data.items():
    file_path = os.path.join('tests/historic_data', f"{symbol}_historical_data.csv")
    data.to_csv(file_path, index=False)
    print(f"Saved data for {symbol} to {file_path}")

print("Historical data fetching complete.")
