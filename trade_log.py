import csv
import os
from datetime import datetime
import time
import alpaca_trade_api as tradeapi

# Path to the trade log file
LOG_FILE = 'logs/trade_log.csv'

def initialize_trade_log():
    # Trade log CSV file. Creates the file and writes the header if it doesn't already exist.
    if not os.path.exists(LOG_FILE):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)  # Create the directory if it doesn't exist
        with open(LOG_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Timestamp', 'Symbol', 'Action', 'Quantity', 'Price', 'Order ID', 'Status']) # Headers

def wait_for_fill(api, order_id): # Removed
    # Continuously checks the status of an order until it is filled.
    while True:
        order = api.get_order(order_id)  # Fetch the current status of the order
        if order.status == 'filled':
            return order  # Return the order if it is filled
        time.sleep(1)  # Wait for 1 second before checking again

def log_trade(order, action):
    # Logs the details of a trade to the trade log CSV file.
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # Current timestamp
    symbol = order.symbol
    qty = order.qty
    price = order.filled_avg_price  # Filled average price
    order_id = order.id
    status = order.status

    with open(LOG_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, symbol, action, qty, price, order_id, status]) # Log trade details
