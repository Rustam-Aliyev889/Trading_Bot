import alpaca_trade_api as tradeapi
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
import asyncio
import logging
from trade_log import initialize_trade_log, log_trade, wait_for_fill
from performance_metrics import initialize_performance_log, log_portfolio_value, calculate_metrics, generate_report

# Configure logging
logging.basicConfig(level=logging.INFO, filename='momentum_strategy.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

PERFORMANCE_LOG_FILE = 'performance_log.csv'

ALPACA_API_KEY = 'PKQL7W0WXZV1RKPTYRUG'
ALPACA_SECRET_KEY = 'C37Utl7xvx5SLibmTKveTgnzH0D4CPIfVO62xiwl'
BASE_URL = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, api_version='v2')
conn = tradeapi.stream.Stream(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, data_feed='iex')

symbol = 'SPY'
window = 20
price_history = []

# Define Market Hours
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)

def is_market_open():
    now = datetime.now().time()
    return MARKET_OPEN <= now <= MARKET_CLOSE

def is_market_close():
    now = datetime.now().time()
    return now >= MARKET_CLOSE

def generate_signals(price_history):
    if len(price_history) < window:
        return None

    data = pd.Series(price_history)
    returns = data.pct_change()
    signal = 1 if returns.iloc[-1] > 0 else -1
    logging.info(f"Generated signal: {signal} based on returns: {returns.iloc[-1]}")
    return signal

def execute_trade(symbol, signal):
    if not is_market_open():
        logging.info("Market is closed. Trade execution skipped.")
        return

    try:
        if signal == 1:
            logging.info(f"Executing Buy for {symbol}")
            order = api.submit_order(
                symbol=symbol,
                qty=1,
                side='buy',
                type='market',
                time_in_force='day'
            )
        elif signal == -1:
            logging.info(f"Executing Sell for {symbol}")
            order = api.submit_order(
                symbol=symbol,
                qty=1,
                side='sell',
                type='market',
                time_in_force='day'
            )
        logging.info(f"Order submitted: {order}")

        # Wait for the order to be filled and retrieve the filled order
        filled_order = wait_for_fill(api, order.id)

        # Log the trade to CSV
        log_trade(filled_order, 'buy' if signal == 1 else 'sell')

        # Log portfolio value
        log_portfolio_value()

    except tradeapi.rest.APIError as e:
        logging.error(f"API Error executing trade: {e}")
    except Exception as e:
        logging.error(f"Error executing trade: {e}")

def check_order_status(order_id):
    try:
        order = api.get_order(order_id)
        logging.info(f"Order Status for {order_id}: {order.status}")
    except Exception as e:
        logging.error(f"Error checking order status for {order_id}: {e}")

async def on_minute_bars(bar):
    if not is_market_open():
        logging.info("Market is closed. Skipping bar processing.")
        return

    price_history.append(bar.close)
    logging.info(f"Received new bar data: {bar.close}")

    if len(price_history) > window:
        price_history.pop(0)

    signal = generate_signals(price_history)
    if signal is not None:
        execute_trade(symbol, signal)

async def run_momentum_strategy():
    try:
        # Subscribe to minute bars
        conn.subscribe_bars(on_minute_bars, symbol)

        # Start the WebSocket connection
        await conn._run_forever()
    except Exception as e:
        logging.error(f"Error running strategy: {e}")

async def update_report_at_close():
    while True:
        now = datetime.now()
        market_close_time = datetime.combine(now.date(), MARKET_CLOSE)
        
        if now.time() >= MARKET_CLOSE:
            market_close_time += timedelta(days=1)  # Schedule for next day if market is already closed
        
        time_until_close = (market_close_time - now).total_seconds()
        await asyncio.sleep(time_until_close)
        
        # Update the report
        df = pd.read_csv(PERFORMANCE_LOG_FILE, parse_dates=['Timestamp'], index_col='Timestamp')
        generate_report()
        logging.info("Report updated at market close")
        
        # Sleep until the next market close
        await asyncio.sleep(24 * 60 * 60 - time_until_close)

async def main():
    await run_momentum_strategy()

if __name__ == "__main__":
    initialize_trade_log()
    initialize_performance_log()
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.create_task(update_report_at_close())

    # Manually test order submission
    try:
        if is_market_open():
            print("Testing manual order submission...")
            test_order = api.submit_order(
                symbol='SPY',
                qty=1,
                side='buy',
                type='market',
                time_in_force='day'
            )
            print(f"Manual order response: {test_order}")
            logging.info(f"Manual order response: {test_order}")
            
            # Wait for the order to be filled and retrieve the filled order
            filled_order = wait_for_fill(api, test_order.id)
            
            check_order_status(filled_order.id)
            
            # Log the trade to CSV
            log_trade(filled_order, 'buy')
            
            # Log portfolio value
            log_portfolio_value()
        else:
            logging.info("Market is closed. Manual order submission skipped.")
    except Exception as e:
        logging.error(f"Error in manual order submission: {e}")
        print(f"Error in manual order submission: {e}")

    # Run the event loop
    loop.run_forever()