import csv
import os
from datetime import datetime
import time
import alpaca_trade_api as tradeapi

# Path to the trade log file
LOG_FILE = 'logs/trade_log.csv'

def initialize_trade_log():
    if not os.path.exists(LOG_FILE):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Timestamp', 'Symbol', 'Action', 'Quantity', 'Price', 'Order ID', 'Status'])

def wait_for_fill(api, order_id):
    while True:
        order = api.get_order(order_id)
        if order.status == 'filled':
            return order
        time.sleep(1)  # Wait for 1 second before checking again

def log_trade(order, action):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    symbol = order.symbol
    qty = order.qty
    price = order.filled_avg_price  # Filled average price
    order_id = order.id
    status = order.status

    with open(LOG_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, symbol, action, qty, price, order_id, status])
