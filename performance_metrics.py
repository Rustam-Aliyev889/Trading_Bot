import csv
import os
from datetime import datetime
import pandas as pd
import numpy as np
import alpaca_trade_api as tradeapi

PERFORMANCE_LOG_FILE = 'performance_log.csv'

ALPACA_API_KEY = 'PKQL7W0WXZV1RKPTYRUG'
ALPACA_SECRET_KEY = 'C37Utl7xvx5SLibmTKveTgnzH0D4CPIfVO62xiwl'
BASE_URL = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, api_version='v2')

def initialize_performance_log():
    if not os.path.exists(PERFORMANCE_LOG_FILE):
        print(f"Creating new performance log file: {PERFORMANCE_LOG_FILE}")
        with open(PERFORMANCE_LOG_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Timestamp', 'Portfolio Value', 'Daily High', 'Daily Low', 'Daily Close', 'Volume'])
        print("Initialized performance log with headers.")

def log_portfolio_value():
    account = api.get_account()
    portfolio_value = account.equity
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    bars = api.get_bars('SPY', tradeapi.rest.TimeFrame.Day, limit=1).df
    daily_high = bars['high'].iloc[0]
    daily_low = bars['low'].iloc[0]
    daily_close = bars['close'].iloc[0]
    volume = bars['volume'].iloc[0]

    with open(PERFORMANCE_LOG_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, portfolio_value, daily_high, daily_low, daily_close, volume])
    print(f"Logged portfolio value at {timestamp}")

def check_performance_log_file():
    if os.path.exists(PERFORMANCE_LOG_FILE):
        with open(PERFORMANCE_LOG_FILE, mode='r') as file:
            content = file.read()
            print(f"Contents of {PERFORMANCE_LOG_FILE}:\n{content}")

def calculate_performance_metrics():
    if not os.path.exists(PERFORMANCE_LOG_FILE):
        raise FileNotFoundError(f"{PERFORMANCE_LOG_FILE} not found.")

    df = pd.read_csv(PERFORMANCE_LOG_FILE, parse_dates=['Timestamp'], index_col='Timestamp')
    if df.index.name != 'Timestamp':
        raise ValueError("Missing 'Timestamp' index in the DataFrame.")

    df['Daily Return'] = df['Portfolio Value'].pct_change()

    # Calculate cumulative return
    df['Cumulative Return'] = (1 + df['Daily Return']).cumprod() - 1

    # Calculate Sharpe Ratio
    mean_return = df['Daily Return'].mean()
    std_return = df['Daily Return'].std()
    sharpe_ratio = (mean_return / std_return) * np.sqrt(252)  # Assuming 252 trading days in a year

    # Calculate max drawdown
    roll_max = df['Portfolio Value'].cummax()
    drawdown = df['Portfolio Value'] / roll_max - 1
    max_drawdown = drawdown.min()

    metrics = {
        'Cumulative Return': df['Cumulative Return'].iloc[-1],
        'Sharpe Ratio': sharpe_ratio,
        'Max Drawdown': max_drawdown
    }

    return metrics

# Example usage
if __name__ == "__main__":
    initialize_performance_log()
    log_portfolio_value()
    check_performance_log_file()
    metrics = calculate_performance_metrics()
    print(metrics)
