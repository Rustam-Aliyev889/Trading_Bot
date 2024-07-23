import alpaca_trade_api as tradeapi
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import logging
from trade_log import initialize_trade_log, log_trade, wait_for_fill
from performance_metrics import initialize_performance_log, log_portfolio_value
from indicators import calculate_volume_rsi, calculate_atr

# Configure logging
logging.basicConfig(level=logging.INFO, filename='logs/momentum_strategy.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

ALPACA_API_KEY = 'PKZ2OWWB59IYQ5FLB0YO'
ALPACA_SECRET_KEY = '2EgGSwgaC4kCr4593ffJNh4S5UVfhAV00z73aMjS'
BASE_URL = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, api_version='v2')
conn = tradeapi.stream.Stream(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, data_feed='iex')

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
initial_portfolio_value = None
current_daily_loss = 0

def get_portfolio():
    try:
        account = api.get_account()
        cash = float(account.cash)
        portfolio = {position.symbol: float(position.qty) for position in api.list_positions()}
        portfolio_value = float(account.equity)
        return cash, portfolio, portfolio_value
    except Exception as e:
        logging.error(f"Error fetching portfolio: {e}")
        return 0, {}, 0

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

    if data['returns'].iloc[-1] > 0 and data['volume_rsi'].iloc[-1] > 50:
        signal = 1
    elif data['returns'].iloc[-1] < 0 and data['volume_rsi'].iloc[-1] < 50:
        signal = -1
    else:
        signal = 0  # Neutral signal

    print(f"Generated signal: {signal} for {price_history}, returns: {data['returns'].iloc[-1]}, volume_rsi: {data['volume_rsi'].iloc[-1]}, atr: {data['atr'].iloc[-1]}")
    return signal

def get_latest_price(symbol):
    try:
        bars = api.get_bars(symbol, tradeapi.rest.TimeFrame.Minute, limit=1).df
        latest_price = bars['close'].iloc[-1]
        return latest_price
    except Exception as e:
        logging.error(f"Error fetching latest price for {symbol}: {e}")
        return None

def set_stop_loss_take_profit(symbol, buy_price):
    stop_loss_price = round(buy_price * (1 - stop_loss_pct), 2)
    take_profit_price = round(buy_price * (1 + take_profit_pct), 2)
    stop_loss_levels[symbol] = stop_loss_price
    take_profit_levels[symbol] = take_profit_price

def cancel_existing_orders(symbol):
    try:
        orders = api.list_orders(status='open', symbols=[symbol])
        for order in orders:
            api.cancel_order(order.id)
    except Exception as e:
        logging.error(f"Error canceling orders for {symbol}: {e}")

def execute_trade(symbol, signal, portfolio, cash, portfolio_value):
    global last_log_time, current_daily_loss, initial_portfolio_value
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

        latest_price = get_latest_price(symbol)
        if (latest_price is None) or (latest_price <= 0):
            logging.error(f"Could not fetch latest price for {symbol}, trade not executed")
            return

        if signal == 1:
            # Calculate position size based on $10 allocation
            quantity = round(allocation_per_trade / latest_price, 6)  # Round to 6 decimal places for fractional trading
            # Check if there is enough cash for the trade
            if cash < allocation_per_trade:
                logging.info(f"Not enough cash to execute buy for {symbol}, cash available: {cash}")
                return
            print(f"Executing Buy for {symbol} at {latest_price}")
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

        elif signal == -1:
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
    symbol = bar.symbol
    price_histories[symbol].append(bar.close)
    volume_histories[symbol].append(bar.volume)
    high_histories[symbol].append(bar.high)
    low_histories[symbol].append(bar.low)
    print(f"Received new bar data for {symbol}: {bar.close}")

    if len(price_histories[symbol]) > window:
        price_histories[symbol].pop(0)
        volume_histories[symbol].pop(0)
        high_histories[symbol].pop(0)
        low_histories[symbol].pop(0)

    signal = generate_signals(price_histories[symbol], volume_histories[symbol], high_histories[symbol], low_histories[symbol])
    if signal is not None:
        cash, portfolio, portfolio_value = get_portfolio()  # Get updated portfolio and cash information
        execute_trade(symbol, signal, portfolio, cash, portfolio_value)

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

        # Start the WebSocket connection
        await conn._run_forever()
    except Exception as e:
        logging.error(f"Error running strategy: {e}")

async def main():
    print("Strategy started")
    await run_momentum_strategy()

if __name__ == "__main__":
    initialize_trade_log()
    initialize_performance_log()
    loop = asyncio.get_event_loop()
    loop.create_task(main())

    # Run the event loop
    loop.run_forever()
