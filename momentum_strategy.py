import alpaca_trade_api as tradeapi
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, filename='momentum_strategy.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

ALPACA_API_KEY = 'PKQL7W0WXZV1RKPTYRUG'
ALPACA_SECRET_KEY = 'C37Utl7xvx5SLibmTKveTgnzH0D4CPIfVO62xiwl'
BASE_URL = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, api_version='v2')

def fetch_data(symbol, start, end, timeframe='1Min'):
    try:
        start = pd.Timestamp(start, tz='America/New_York').isoformat()
        end = pd.Timestamp(end, tz='America/New_York').isoformat()
        
        barset = api.get_bars(
            symbol,
            tradeapi.TimeFrame.Minute,
            start=start,
            end=end,
            adjustment='raw',
            feed='iex'
        ).df
        
        # Reset index and rename columns
        df = barset.reset_index().rename(columns={
            'timestamp': 'time',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        })
        
        # Handle missing data
        df = df.dropna().reset_index(drop=True)
        
        # Log the fetched data
        logging.info(f"Fetched data for {symbol} from {start} to {end}")
        return df
    except tradeapi.rest.APIError as e:
        logging.error(f"Error fetching data for {symbol}: {e}")
        if "Forbidden" in str(e):
            logging.warning("Forbidden Error: You might not have access to this data.")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

def generate_signals(data, window=20):
    try:
        data['returns'] = data['close'].pct_change()
        data['signal'] = np.where(data['returns'] > 0, 1, -1)
        data['positions'] = data['signal'].diff()
        logging.info("Signals generated")
        return data
    except Exception as e:
        logging.error(f"Error generating signals: {e}")
        return pd.DataFrame()

def execute_trade(symbol, signal):
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

        # Check order status
        check_order_status(order.id)

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

def run_momentum_strategy(symbol='SPY', window=20):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        data = fetch_data(symbol, start=start_date.isoformat(), end=end_date.isoformat())
        
        if not data.empty:
            data_with_signals = generate_signals(data, window)
            
            for i in range(1, len(data_with_signals)):
                if data_with_signals['positions'].iloc[i] == 1:
                    execute_trade(symbol, 1)
                elif data_with_signals['positions'].iloc[i] == -1:
                    execute_trade(symbol, -1)
            
            logging.info("Strategy executed")
        else:
            logging.warning(f"No data available to execute strategy for symbol: {symbol}")
    except Exception as e:
        logging.error(f"Error running strategy: {e}")

if __name__ == "__main__":
    run_momentum_strategy()
    
    # Manually test order submission
    try:
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
        
        check_order_status(test_order.id)
    except Exception as e:
        logging.error(f"Error in manual order submission: {e}")
        print(f"Error in manual order submission: {e}")
