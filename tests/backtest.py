import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import csv
import logging
from test_indicators import calculate_volume_rsi, calculate_atr, calculate_macd, calculate_rsi, calculate_sma
from reporting import log_trade, log_performance, initialize_logs, generate_final_report

# Configure logging
logging.basicConfig(level=logging.INFO, filename='logs/momentum_strategy.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Parameters
symbols = ['AAPL', 'GOOG', 'AMZN', 'MSFT', 'META', 'TSLA', 'NFLX', 'NVDA', 'V', 'PYPL']
initial_capital = 100000.0
window = 5
allocation_per_trade = 10  # $10 allocation per trade
stop_loss_pct = 0.02  # 2% stop loss
take_profit_pct = 0.05  # 5% take profit

max_daily_loss = 0.05  # 5% of portfolio
max_drawdown = 0.15  # 15% of portfolio

# Function to load historical data
def load_historical_data(symbol):
    try:
        data = pd.read_csv(f'tests/historic_data/{symbol}_historical_data.csv', parse_dates=['time'], index_col='time')
        if 'open' not in data.columns or 'close' not in data.columns or 'volume' not in data.columns or 'high' not in data.columns or 'low' not in data.columns:
            raise ValueError(f"CSV file for {symbol} is missing required columns.")
        return data
    except Exception as e:
        print(f"Error loading data for {symbol}: {e}")
        return pd.DataFrame()

# Function to generate trading signals
def generate_signals(price_history, volume_history, high_history, low_history):
    if len(price_history) < window or len(volume_history) < window:
        return 0  # Neutral signal if not enough data

    data = pd.DataFrame({
        'price': price_history,
        'volume': volume_history,
        'high': high_history,
        'low': low_history
    })
    data['returns'] = data['price'].pct_change()
    data['volume_rsi'] = calculate_volume_rsi(data['volume'], window)
    data['atr'] = calculate_atr(data['high'], data['low'], data['price'], window)
    data['macd'], data['signal_line'] = calculate_macd(data['price'])
    data['rsi'] = calculate_rsi(data['price'], window)
    data['sma'] = calculate_sma(data['price'], window)

    # Combining multiple indicators to generate a signal
    if data['returns'].iloc[-1] > 0 and data['volume_rsi'].iloc[-1] > 50 and data['macd'].iloc[-1] > data['signal_line'].iloc[-1] and data['price'].iloc[-1] > data['sma'].iloc[-1]:
        return 1  # Buy signal
    elif data['returns'].iloc[-1] < 0 and data['volume_rsi'].iloc[-1] < 50 and data['macd'].iloc[-1] < data['signal_line'].iloc[-1] and data['price'].iloc[-1] < data['sma'].iloc[-1]:
        return -1  # Sell signal
    else:
        return 0  # Neutral signal

# Function to set stop loss and take profit levels
def set_stop_loss_take_profit(price):
    stop_loss_price = round(price * (1 - stop_loss_pct), 2)
    take_profit_price = round(price * (1 + take_profit_pct), 2)
    return stop_loss_price, take_profit_price

# Function to simulate trading
def simulate_trading(data, symbol):
    cash = initial_capital
    holdings = 0
    portfolio_value = initial_capital
    stop_loss = None
    take_profit = None
    current_daily_loss = 0
    initial_portfolio_value = initial_capital

    price_history = []
    volume_history = []
    high_history = []
    low_history = []

    data['portfolio_value'] = initial_capital

    for i in range(1, len(data)):
        date = data.index[i]
        price = data['close'].iloc[i]
        volume = data['volume'].iloc[i]
        high = data['high'].iloc[i]
        low = data['low'].iloc[i]

        price_history.append(price)
        volume_history.append(volume)
        high_history.append(high)
        low_history.append(low)

        if len(price_history) > window:
            price_history.pop(0)
            volume_history.pop(0)
            high_history.pop(0)
            low_history.pop(0)

        signal = generate_signals(price_history, volume_history, high_history, low_history)

        # Check for stop loss or take profit triggers
        if stop_loss is not None and price <= stop_loss:
            cash += holdings * price
            log_trade(date, symbol, 'STOP LOSS', price, holdings, cash)
            holdings = 0
            stop_loss = None
            take_profit = None
        elif take_profit is not None and price >= take_profit:
            cash += holdings * price
            log_trade(date, symbol, 'TAKE PROFIT', price, holdings, cash)
            holdings = 0
            stop_loss = None
            take_profit = None

        # Execute trades based on signal
        if signal == 1 and cash >= allocation_per_trade:
            quantity = allocation_per_trade / price
            cash -= quantity * price
            holdings += quantity
            stop_loss, take_profit = set_stop_loss_take_profit(price)
            log_trade(date, symbol, 'BUY', price, quantity, cash)
        elif signal == -1 and holdings > 0:
            cash += holdings * price
            log_trade(date, symbol, 'SELL', price, holdings, cash)
            holdings = 0
            stop_loss = None
            take_profit = None

        portfolio_value = cash + holdings * price
        data.at[date, 'portfolio_value'] = portfolio_value
        log_performance(date, portfolio_value, cash, holdings, high, low, price, volume)

    return data

# Run the backtest
initialize_logs()
for symbol in symbols:
    data = load_historical_data(symbol)
    if data.empty:
        continue  # Skip this symbol if data could not be loaded
    data = simulate_trading(data, symbol)
    total_return = (data['portfolio_value'].iloc[-1] / initial_capital) - 1
    final_portfolio_value = data['portfolio_value'].iloc[-1]
    print(f'Total Return for {symbol}: {total_return:.2%}')
    print(f'Final Portfolio Value for {symbol}: ${final_portfolio_value:.2f}')

# Generate and save the final report
generate_final_report()
