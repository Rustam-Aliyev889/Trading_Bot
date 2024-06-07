# sma_strategy.py
import pandas as pd
import numpy as np
import yfinance as yf
from performance_visualization import performance_metrics, plot_performance

def generate_signals(data, short_window, long_window):
    data['SMA50'] = data['Close'].rolling(window=short_window, min_periods=1).mean()
    data['SMA200'] = data['Close'].rolling(window=long_window, min_periods=1).mean()

    data['signal'] = 0
    data.iloc[short_window:, data.columns.get_loc('signal')] = np.where(
        data['SMA50'].iloc[short_window:] > data['SMA200'].iloc[short_window:], 1, 0)
    data['positions'] = data['signal'].diff()

    return data

def backtest_strategy(data, initial_capital):
    data['equity'] = initial_capital
    position = 0
    shares = 0

    for i in range(1, len(data)):
        if data['positions'].iloc[i] == 1:
            shares = data['equity'].iloc[i - 1] // data['Close'].iloc[i]
            data.iloc[i, data.columns.get_loc('equity')] = data.iloc[i - 1, data.columns.get_loc('equity')] - (shares * data['Close'].iloc[i])
            position = shares
        elif data['positions'].iloc[i] == -1 and position > 0:
            data.iloc[i, data.columns.get_loc('equity')] = data.iloc[i - 1, data.columns.get_loc('equity')] + (shares * data['Close'].iloc[i])
            position = 0
            shares = 0
        else:
            data.iloc[i, data.columns.get_loc('equity')] = data.iloc[i - 1, data.columns.get_loc('equity')]

        if position > 0:
            data.iloc[i, data.columns.get_loc('equity')] += position * data['Close'].iloc[i]

    return data

def run_sma_strategy(symbol='SPY', start_date='2022-01-01', end_date='2024-05-30', short_window=50, long_window=200, initial_capital=100000.0):

    data = yf.download(symbol, start=start_date, end=end_date)
    data_with_signals = generate_signals(data, short_window, long_window)
    backtested_data = backtest_strategy(data_with_signals, initial_capital)
    
    print(backtested_data[['SMA50', 'SMA200', 'signal', 'positions']].dropna())
    print(backtested_data[['Open', 'High', 'Low', 'Close', 'signal', 'positions', 'equity']].dropna())
    print("Final equity:", backtested_data['equity'].iloc[-1])
    
    performance_metrics(backtested_data)
    plot_performance(backtested_data)
    
    return backtested_data
