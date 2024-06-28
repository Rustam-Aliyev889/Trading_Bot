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
logging.basicConfig(level=logging.INFO, filename='momentum_strategy.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

ALPACA_API_KEY = 'PK6UA3MS4473Y9NFBJRC'
ALPACA_SECRET_KEY = 'BVclZK6KgCegMeBS6lPLt4Ezi4k6IRhE7OCmzuh3'
BASE_URL = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, api_version='v2')
conn = tradeapi.stream.Stream(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, data_feed='iex')

symbols = ['AAPL', 'GOOG', 'AMZN', 'MSFT', 'META', 'TSLA', 'NFLX', 'NVDA', 'V', 'PYPL']
window = 4
price_histories = {symbol: [] for symbol in symbols}
volume_histories = {symbol: [] for symbol in symbols}
high_histories = {symbol: [] for symbol in symbols}
low_histories = {symbol: [] for symbol in symbols}
active_trades = []

def get_portfolio():
    try:
        account = api.get_account()
        cash = float(account.cash)
        portfolio = {position.symbol: float(position.qty) for position in api.list_positions()}
        return cash, portfolio
    except Exception as e:
        logging.error(f"Error fetching portfolio: {e}")
        return 0, {}

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

    logging.info(f"Generated signal: {signal} based on returns: {data['returns'].iloc[-1]}, volume_rsi: {data['volume_rsi'].iloc[-1]}, atr: {data['atr'].iloc[-1]}")
    return signal

def get_latest_price(symbol):
    try:
        bars = api.get_bars(symbol, tradeapi.rest.TimeFrame.Minute, limit=1).df
        latest_price = bars['close'].iloc[-1]
        return latest_price
    except Exception as e:
        logging.error(f"Error fetching latest price for {symbol}: {e}")
        return None

def execute_trade(symbol, signal, portfolio, cash):
    try:
        if signal == 0:
            logging.info(f"Neutral signal received for {symbol}, no trade executed")
            return

        latest_price = get_latest_price(symbol)
        if latest_price is None:
            logging.error(f"Could not fetch latest price for {symbol}, trade not executed")
            return

        # Calculate fractional quantity based on $10 allocation
        quantity = round(10 / latest_price, 6)  # Round to 6 decimal places for fractional trading

        if signal == 1:
            # Check if there is enough cash for the trade
            if cash < 10:
                logging.info(f"Not enough cash to execute buy for {symbol}, cash available: {cash}")
                return
            logging.info(f"Executing Buy for {symbol} at {latest_price}")
            order = api.submit_order(
                symbol=symbol,
                qty=quantity,
                side='buy',
                type='market',
                time_in_force='day'
            )
            active_trades.append(order.id)
        elif signal == -1:
            if symbol not in portfolio or portfolio[symbol] < quantity:
                logging.info(f"Not enough quantity to execute sell for {symbol}, available: {portfolio.get(symbol, 0)}")
                return
            logging.info(f"Executing Sell for {symbol} at {latest_price}")
            order = api.submit_order(
                symbol=symbol,
                qty=quantity,
                side='sell',
                type='market',
                time_in_force='day'
            )
            active_trades.append(order.id)
        logging.info(f"Order submitted: {order}")

        # Log portfolio value
        log_portfolio_value()

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
    logging.info(f"Received new bar data for {symbol}: {bar.close}")

    if len(price_histories[symbol]) > window:
        price_histories[symbol].pop(0)
        volume_histories[symbol].pop(0)
        high_histories[symbol].pop(0)
        low_histories[symbol].pop(0)

    signal = generate_signals(price_histories[symbol], volume_histories[symbol], high_histories[symbol], low_histories[symbol])
    if signal is not None:
        cash, portfolio = get_portfolio()  # Get updated portfolio and cash information
        execute_trade(symbol, signal, portfolio, cash)

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
    await run_momentum_strategy()

if __name__ == "__main__":
    initialize_trade_log()
    initialize_performance_log()
    loop = asyncio.get_event_loop()
    loop.create_task(main())

    # Run the event loop
    loop.run_forever()
