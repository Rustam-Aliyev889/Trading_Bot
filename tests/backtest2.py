import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from indicators import calculate_volume_rsi, calculate_atr
from trade_log import initialize_trade_log, log_trade
from performance_metrics import log_portfolio_value, initialize_performance_log
import os

# Configure logging
logging.basicConfig(level=logging.INFO, filename='logs/momentum_strategy_test.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

symbols = ['AAPL', 'GOOG', 'AMZN', 'MSFT', 'META', 'TSLA', 'NFLX', 'NVDA', 'V', 'PYPL']
window = 10
price_histories = {symbol: [] for symbol in symbols}
volume_histories = {symbol: [] for symbol in symbols}
high_histories = {symbol: [] for symbol in symbols}
low_histories = {symbol: [] for symbol in symbols}
stop_loss_levels = {}
take_profit_levels = {}
active_trades = []
last_log_time = datetime.now() - timedelta(minutes=5)  # Initialize last log time to 5 minutes ago

# Risk management parameters
max_daily_loss = 0.05  # 5% of portfolio
max_drawdown = 0.15    # 15% of portfolio
allocation_per_trade = 10  # $10 allocation per trade
stop_loss_pct = 0.02   # 2% stop loss
take_profit_pct = 0.05 # 5% take profit
initial_portfolio_value = 10000  # Starting with $10,000
current_daily_loss = 0

def get_portfolio():
    try:
        cash = initial_portfolio_value - sum(trade['qty'] * trade['price'] for trade in active_trades if trade['type'] == 'buy')
        portfolio = {symbol: 0 for symbol in symbols}
        for trade in active_trades:
            if trade['type'] == 'buy':
                portfolio[trade['symbol']] += trade['qty']
            elif trade['type'] == 'sell':
                portfolio[trade['symbol']] -= trade['qty']
        portfolio_value = cash + sum([portfolio[symbol] * price_histories[symbol][-1] for symbol in symbols if symbol in price_histories and price_histories[symbol]])
        return cash, portfolio, portfolio_value
    except Exception as e:
        logging.error(f"Error in get_portfolio: {e}")
        logging.error(f"Active trades: {active_trades}")
        raise  # Re-raise the exception for further handling

def generate_signals(price_history, volume_history, high_history, low_history, portfolio, symbol):
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

    if data['returns'].iloc[-1] > 0 and data['volume_rsi'].iloc[-1] > 50:
        signal = 1
    elif data['returns'].iloc[-1] < 0 and data['volume_rsi'].iloc[-1] < 50:
        if portfolio[symbol] > 0:  # Only generate a sell signal if there are shares to sell
            signal = -1
        else:
            signal = 0  # Neutral signal if no shares to sell
    else:
        signal = 0  # Neutral signal

    return signal

def execute_trade(symbol, signal, portfolio, cash, portfolio_value):
    global last_log_time, current_daily_loss
    try:
        # Calculate current drawdown
        drawdown = (initial_portfolio_value - portfolio_value) / initial_portfolio_value

        # Check daily loss limit and maximum drawdown
        if current_daily_loss >= max_daily_loss * initial_portfolio_value or drawdown >= max_drawdown:
            logging.info(f"Risk limits reached. Daily Loss: {current_daily_loss}, Drawdown: {drawdown}. No trades executed.")
            return

        if signal == 0:
            return

        latest_price = price_histories[symbol][-1]
        if latest_price <= 0:
            logging.error(f"Invalid latest price for {symbol}, trade not executed")
            return

        if signal == 1:
            # Calculate position size based on $10 allocation
            quantity = round(allocation_per_trade / latest_price, 6)  # Round to 6 decimal places for fractional trading
            # Check if there is enough cash for the trade
            if cash < allocation_per_trade:
                logging.info(f"Not enough cash to execute buy for {symbol}, cash available: {cash}")
                return

            trade = {'symbol': symbol, 'qty': quantity, 'price': latest_price, 'type': 'buy'}
            active_trades.append(trade)
            portfolio[symbol] += quantity  # Update the portfolio with the new buy
            log_trade(trade, 'buy')

            # Set global stop loss and take profit levels
            set_stop_loss_take_profit(symbol, latest_price)

        elif signal == -1:
            if symbol not in portfolio or portfolio[symbol] <= 0:
                logging.info(f"Not enough quantity to execute sell for {symbol}, available: {portfolio.get(symbol, 0)}")
                return

            # Sell the entire available quantity
            quantity = portfolio[symbol]
            trade = {'symbol': symbol, 'qty': quantity, 'price': latest_price, 'type': 'sell'}
            active_trades.append(trade)
            portfolio[symbol] -= quantity  # Update the portfolio with the new sell
            log_trade(trade, 'sell')

        # Update current daily loss
        current_daily_loss += quantity * latest_price if signal == -1 else -quantity * latest_price

        # Log portfolio value every 5 minutes
        current_time = datetime.now()
        if (current_time - last_log_time).total_seconds() >= 300:
            log_portfolio_value()
            last_log_time = current_time

    except Exception as e:
        logging.error(f"Error executing trade for {symbol}: {e}")
        logging.error(f"Active trades: {active_trades}")
        logging.error(f"Current portfolio: {portfolio}")
        logging.error(f"Current cash: {cash}")
        logging.error(f"Current portfolio value: {portfolio_value}")
        raise  # Re-raise the exception for further handling

def set_stop_loss_take_profit(symbol, buy_price):
    stop_loss_price = round(buy_price * (1 - stop_loss_pct), 2)
    take_profit_price = round(buy_price * (1 + take_profit_pct), 2)
    stop_loss_levels[symbol] = stop_loss_price
    take_profit_levels[symbol] = take_profit_price

def simulate_strategy_on_historic_data():
    for symbol in symbols:
        file_path = f'tests/historic_data/{symbol}_historical_data.csv'
        if os.path.exists(file_path):
            data = pd.read_csv(file_path)
            for index, row in data.iterrows():
                price_histories[symbol].append(row['close'])
                volume_histories[symbol].append(row['volume'])
                high_histories[symbol].append(row['high'])
                low_histories[symbol].append(row['low'])

                if len(price_histories[symbol]) > window:
                    price_histories[symbol].pop(0)
                    volume_histories[symbol].pop(0)
                    high_histories[symbol].pop(0)
                    low_histories[symbol].pop(0)

                cash, portfolio, portfolio_value = get_portfolio()  # Get updated portfolio and cash information
                signal = generate_signals(price_histories[symbol], volume_histories[symbol], high_histories[symbol], low_histories[symbol], portfolio, symbol)
                execute_trade(symbol, signal, portfolio, cash, portfolio_value)

                # Check for stop loss or take profit triggers
                if symbol in stop_loss_levels and symbol in take_profit_levels:
                    latest_price = price_histories[symbol][-1]
                    if latest_price <= stop_loss_levels[symbol] or latest_price >= take_profit_levels[symbol]:
                        execute_trade(symbol, -1, portfolio, cash, portfolio_value)

if __name__ == "__main__":
    initialize_trade_log()
    initialize_performance_log()
    simulate_strategy_on_historic_data()
