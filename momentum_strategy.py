import alpaca_trade_api as tradeapi
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import logging
from trade_log import initialize_trade_log, log_trade, wait_for_fill
from performance_metrics import initialize_performance_log, log_portfolio_value
from indicators import calculate_volume_rsi, calculate_atr, calculate_rsi
from dotenv import load_dotenv
import os

load_dotenv()
# Configure logging
logging.basicConfig(level=logging.INFO, filename='logs/momentum_strategy.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
BASE_URL = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, api_version='v2')
conn = tradeapi.stream.Stream(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, data_feed='iex')

symbols = ['AAPL', 'MSFT', 'GOOG', 'NVDA', 'JPM', 'BAC', 'V', 'JNJ', 'PFE', 'PG', 'KO', 'SPY', 'QQQ', 'DIA', 'IWM', 'GLD', 'SLV', 'XOM', 'CVX']
window = 15
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
allocation_per_trade = 75  # $75 allocation per trade
stop_loss_pct = 0.015   # 1.5% stop loss
take_profit_pct = 0.05 # 6% take profit
initial_portfolio_value = None
current_daily_loss = 0

def get_portfolio():  # Retrieves the current portfolio details including cash, holdings, and total portfolio value.
    try:
        account = api.get_account() # Fetches account details using Alpaca API
        cash = float(account.cash)  # Available cash in the account
        portfolio = {position.symbol: float(position.qty) for position in api.list_positions()}  # Extracts positions into a dictionary with symbol as key and quantity as value
        portfolio_value = float(account.equity) # Total portfolio value (equity)
        return cash, portfolio, portfolio_value
    except Exception as e:
        logging.error(f"Error fetching portfolio: {e}")
        return 0, {}, 0  # Default values in case of error

def generate_signals(price_history, volume_history, high_history, low_history):
    """ Generates trading signals based on historical price, volume, high, and low data.
        Returns:
            int: Trading signal (-1 for sell, 0 for hold, 1 for buy)."""

    # Ensures if it has enough data to calculate indicators
    if len(price_history) < window or len(volume_history) < window:
        return 0  # Neutral signal if not enough data

    # Creates a DataFrame from the historical data
    data = pd.DataFrame({
        'price': price_history,       # List of historical closing prices
        'volume': volume_history,     # List of historical volume data
        'high': high_history,         # List of historical high prices
        'low': low_history            # List of historical low prices
    })
    # Additional indicators
    data['returns'] = data['price'].pct_change()
    data['volume_rsi'] = calculate_volume_rsi(data['volume'], window)
    data['atr'] = calculate_atr(data['high'], data['low'], data['price'], window)
    data['rsi'] = calculate_rsi(data['price'], window)

    # Determines the trading signal based on the calculated indicators
    if data['returns'].iloc[-1] > 0 and data['volume_rsi'].iloc[-1] > 50 and data['rsi'].iloc[-1] < 70:
        signal = 1 # Buy signal  (If the price return is positive, Volume RSI is above 50, and RSI is below 70)
    elif data['returns'].iloc[-1] < 0 and data['volume_rsi'].iloc[-1] < 50 and data['rsi'].iloc[-1] > 30:
        signal = -1 # Sell signal  (If the price return is negative, Volume RSI is below 50, and RSI is above 30)
    else:
        signal = 0  # Neutral signal (Otherwise)

    print(f"Generated signal: {signal} for {price_history[-1]}, returns: {data['returns'].iloc[-1]}, volume_rsi: {data['volume_rsi'].iloc[-1]}, atr: {data['atr'].iloc[-1]}, rsi: {data['rsi'].iloc[-1]}")
    return signal

def get_latest_price(symbol):  # Fetches the latest closing price for the given symbol.
    try:
        # Gets the most recent bar data for the symbol
        bars = api.get_bars(symbol, tradeapi.rest.TimeFrame.Minute, limit=1).df
        latest_price = bars['close'].iloc[-1]
        return latest_price
    except Exception as e:
        logging.error(f"Error fetching latest price for {symbol}: {e}")
        return None # In case of an error

def set_stop_loss_take_profit(symbol, buy_price):
    # Sets the stop-loss and take-profit levels for the given symbol based on the buy price.

    # # Calculate stop loss price as a percentage below the buy price
    stop_loss_price = round(buy_price * (1 - stop_loss_pct), 2)

    # Calculate take profit price as a percentage above the buy price
    take_profit_price = round(buy_price * (1 + take_profit_pct), 2)

    # Store the calculated stop loss and take profit prices
    stop_loss_levels[symbol] = stop_loss_price
    take_profit_levels[symbol] = take_profit_price

def cancel_existing_orders(symbol):  # Cancels all open orders for a given symbol.
    try:
        # Retrives all open orders for the symbol
        orders = api.list_orders(status='open', symbols=[symbol])

        # Cancels each open order
        for order in orders:
            api.cancel_order(order.id)
    except Exception as e:
        logging.error(f"Error canceling orders for {symbol}: {e}")

def execute_trade(symbol, signal, portfolio, cash, portfolio_value):
    # Executes a trade based on the given signal and updates the portfolio.

    global last_log_time, current_daily_loss, initial_portfolio_value
    # Initialize initial portfolio value if not set
    try:
        if initial_portfolio_value is None:
            initial_portfolio_value = portfolio_value

        # Calculate current drawdown
        drawdown = (initial_portfolio_value - portfolio_value) / initial_portfolio_value

        # Check daily loss limit and maximum drawdown
        if current_daily_loss >= max_daily_loss * initial_portfolio_value or drawdown >= max_drawdown:
            logging.info(f"Risk limits reached. Daily Loss: {current_daily_loss}, Drawdown: {drawdown}. No trades executed.")
            return

        if signal == 0:
            print(f"Neutral signal received for {symbol}, no trade executed")
            return

        # Get the latest price for the symbol
        latest_price = get_latest_price(symbol)
        if (latest_price is None) or (latest_price <= 0):
            logging.error(f"Could not fetch latest price for {symbol}, trade not executed")
            return

        if signal == 1: # Buy signal
            # Calculate position size based on allocation per trade
            quantity = round(allocation_per_trade / latest_price, 6)  # Round to 6 decimal places for fractional trading
            # Check if there is enough cash for the trade
            if cash < allocation_per_trade:
                logging.info(f"Not enough cash to execute buy for {symbol}, cash available: {cash}")
                return
            print(f"Executing Buy for {symbol} at {latest_price}")
            # Submit buy order
            order = api.submit_order(
                symbol=symbol,
                qty=quantity,
                side='buy',
                type='market',
                time_in_force='day'
            )
            active_trades.append(order.id)
            log_trade(order, 'buy')

            # Set global stop loss and take profit levels
            set_stop_loss_take_profit(symbol, latest_price)

        elif signal == -1: # Sell signal
            if symbol not in portfolio or portfolio[symbol] <= 0:
                logging.info(f"Not enough quantity to execute sell for {symbol}, available: {portfolio.get(symbol, 0)}")
                return

            # Cancel any existing stop loss or take profit orders
            cancel_existing_orders(symbol)

            # Fetch updated portfolio data to get accurate available quantity
            cash, portfolio, portfolio_value = get_portfolio()

            # Sell the entire available quantity
            quantity = portfolio[symbol]
            order = api.submit_order(
                symbol=symbol,
                qty=quantity,
                side='sell',
                type='market',
                time_in_force='day'
            )
            active_trades.append(order.id)
            log_trade(order, 'sell')

        # Update current daily loss
        current_daily_loss += quantity * latest_price if signal == -1 else -quantity * latest_price

        # Log portfolio value every 5 minutes
        current_time = datetime.now()
        if (current_time - last_log_time).total_seconds() >= 300:
            log_portfolio_value()
            last_log_time = current_time

    except tradeapi.rest.APIError as e:
        logging.error(f"API Error executing trade for {symbol}: {e}")
    except Exception as e:
        logging.error(f"Error executing trade for {symbol}: {e}")

async def on_minute_bars(bar):
    """ Handles new minute bar data and updates price, volume, high, and low histories.
    Generates and executes trading signals based on updated data."""
    symbol = bar.symbol # Get the symbol for the bar
    # Append the latest bar data to the historical lists
    price_histories[symbol].append(bar.close)
    volume_histories[symbol].append(bar.volume)
    high_histories[symbol].append(bar.high)
    low_histories[symbol].append(bar.low)
    print(f"Received new bar data for {symbol}: {bar.close}")

    # Maintain a fixed-size window of historical data
    if len(price_histories[symbol]) > window:
        price_histories[symbol].pop(0)
        volume_histories[symbol].pop(0)
        high_histories[symbol].pop(0)
        low_histories[symbol].pop(0)

    # Generate a trading signal based on updated historical data
    signal = generate_signals(price_histories[symbol], volume_histories[symbol], high_histories[symbol], low_histories[symbol])
    if signal is not None:
        cash, portfolio, portfolio_value = get_portfolio()  # Get updated portfolio and cash information
        execute_trade(symbol, signal, portfolio, cash, portfolio_value)  # Execute the trade based on the generated signal

    # Check for stop loss or take profit triggers
    if symbol in stop_loss_levels and symbol in take_profit_levels:
        latest_price = get_latest_price(symbol)
        if latest_price is not None:
            if latest_price <= stop_loss_levels[symbol] or latest_price >= take_profit_levels[symbol]:
                execute_trade(symbol, -1, portfolio, cash, portfolio_value)

async def run_momentum_strategy():
    try:
        # Subscribe to minute bars for each symbol individually
        for symbol in symbols:
            conn.subscribe_bars(on_minute_bars, symbol)

        # Start the WebSocket connection to receive real-time data
        await conn._run_forever()
    except Exception as e:
        logging.error(f"Error running strategy: {e}")

async def main():
    print("Strategy started")
    await run_momentum_strategy()

if __name__ == "__main__":
    initialize_trade_log()
    initialize_performance_log()
    loop = asyncio.get_event_loop()  # Create and start the event loop
    loop.create_task(main())  # Schedule the main function
    loop.run_forever()  # Run the event loop
