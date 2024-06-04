import yfinance as yf
import pandas as pd
import numpy as np

# Download historical data for SPY
data = yf.download('SPY', start='2022-01-01', end='2024-05-30')

# Initialize trading bot parameters
short_window = 50
long_window = 200
initial_capital = 100000.0

def generate_signals(data):
    # Create short and long simple moving averages
    data['SMA50'] = data['Close'].rolling(window=short_window, min_periods=1).mean()
    data['SMA200'] = data['Close'].rolling(window=long_window, min_periods=1).mean()

    # Create signals
    data['signal'] = 0
    data.iloc[short_window:, data.columns.get_loc('signal')] = np.where(
        data['SMA50'].iloc[short_window:] > data['SMA200'].iloc[short_window:], 1, 0)
    data['positions'] = data['signal'].diff()

    return data

def backtest_strategy(data):
    # Set initial capital and positions
    data['equity'] = initial_capital
    position = 0
    shares = 0  # Number of shares held

    for i in range(1, len(data)):
        if data['positions'].iloc[i] == 1:  # Buy signal
            shares = data['equity'].iloc[i - 1] // data['Close'].iloc[i]
            data.iloc[i, data.columns.get_loc('equity')] = data.iloc[i - 1, data.columns.get_loc('equity')] - (shares * data['Close'].iloc[i])
            position = shares
        elif data['positions'].iloc[i] == -1 and position > 0:  # Sell signal
            data.iloc[i, data.columns.get_loc('equity')] = data.iloc[i - 1, data.columns.get_loc('equity')] + (shares * data['Close'].iloc[i])
            position = 0
            shares = 0
        else:  # Hold position
            data.iloc[i, data.columns.get_loc('equity')] = data.iloc[i - 1, data.columns.get_loc('equity')]

        # Update equity with the value of held shares
        if position > 0:
            data.iloc[i, data.columns.get_loc('equity')] += position * data['Close'].iloc[i]

    return data

def run_trading_bot():
    data_with_signals = generate_signals(data)
    backtested_data = backtest_strategy(data_with_signals)
    print(backtested_data[['SMA50', 'SMA200', 'signal', 'positions']].dropna())
    print(backtested_data[['Open', 'High', 'Low', 'Close', 'signal', 'positions', 'equity']].dropna())
    print("Final equity:", backtested_data['equity'].iloc[-1])

run_trading_bot()
