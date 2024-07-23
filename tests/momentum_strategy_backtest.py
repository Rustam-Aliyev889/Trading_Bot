import alpaca_trade_api as tradeapi
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from test_trade_log import initialize_trade_log, log_trade, wait_for_fill
from test_performance_metrics import initialize_performance_log, log_portfolio_value, generate_report
from test_indicators import calculate_volume_rsi, calculate_atr

# Configure logging
logging.basicConfig(level=logging.INFO, filename='tests/logs/momentum_strategy_backtest.log', filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

ALPACA_API_KEY = 'PKZ2OWWB59IYQ5FLB0YO'
ALPACA_SECRET_KEY = '2EgGSwgaC4kCr4593ffJNh4S5UVfhAV00z73aMjS'
BASE_URL = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, api_version='v2')

symbols = ['AAPL', 'GOOG', 'AMZN', 'MSFT', 'META', 'TSLA', 'NFLX', 'NVDA', 'V', 'PYPL']
window = 10
price_histories = {symbol: [] for symbol in symbols}
volume_histories = {symbol: [] for symbol in symbols}
high_histories = {symbol: [] for symbol in symbols}
low_histories = {symbol: [] for symbol in symbols}
stop_loss_levels = {}
take_profit_levels = {}
active_trades = []
portfolio_values = []  # List to track portfolio value over time

# Risk management parameters
max_daily_loss = 0.05  # 5% of portfolio
max_drawdown = 0.15    # 15% of portfolio
allocation_per_trade = 10  # $10 allocation per trade
stop_loss_pct = 0.02   # 2% stop loss
take_profit_pct = 0.05 # 5% take profit
initial_portfolio_value = None
current_daily_loss = 0
cash, portfolio, portfolio_value = None, None, None  # Initialize portfolio variables
trade_count = 0  # Initialize trade count

def get_portfolio():
    # Simulated portfolio for backtesting
    global cash, portfolio, portfolio_value, initial_portfolio_value
    if initial_portfolio_value is None:
        initial_portfolio_value = 100000  # Starting with $100,000
    portfolio_value = initial_portfolio_value
    cash = portfolio_value if cash is None else cash
    portfolio = {} if portfolio is None else portfolio
    return cash, portfolio, portfolio_value

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

    logging.info(f"Generated signal: {signal} for {price_history[-1]}, returns: {data['returns'].iloc[-1]}, volume_rsi: {data['volume_rsi'].iloc[-1]}, atr: {data['atr'].iloc[-1]}")
    return signal

def set_stop_loss_take_profit(symbol, buy_price):
    stop_loss_price = round(buy_price * (1 - stop_loss_pct), 2)
    take_profit_price = round(buy_price * (1 + take_profit_pct), 2)
    stop_loss_levels[symbol] = stop_loss_price
    take_profit_levels[symbol] = take_profit_price
    logging.info(f"Set stop loss for {symbol} at {stop_loss_price}, take profit at {take_profit_price}")

def execute_trade(symbol, signal, portfolio, cash, portfolio_value):
    global current_daily_loss, initial_portfolio_value, trade_count
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
            logging.info(f"Neutral signal for {symbol}, no trade executed.")
            return

        latest_price = price_histories[symbol][-1]  # Use last price from price history
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

            cash -= quantity * latest_price
            portfolio[symbol] = portfolio.get(symbol, 0) + quantity
            order = {'symbol': symbol, 'qty': quantity, 'price': latest_price}
            log_trade(order, 'buy')
            logging.info(f"Executed buy for {symbol}: {quantity} shares at {latest_price}, remaining cash: {cash}")

            # Set global stop loss and take profit levels
            set_stop_loss_take_profit(symbol, latest_price)

        elif signal == -1:
            if symbol not in portfolio or portfolio[symbol] <= 0:
                logging.info(f"Not enough quantity to execute sell for {symbol}, available: {portfolio.get(symbol, 0)}")
                return

            quantity = portfolio[symbol]
            cash += quantity * latest_price
            order = {'symbol': symbol, 'qty': quantity, 'price': latest_price}
            log_trade(order, 'sell')
            del portfolio[symbol]
            logging.info(f"Executed sell for {symbol}: {quantity} shares at {latest_price}, updated cash: {cash}")

        # Update current daily loss
        current_daily_loss += quantity * latest_price if signal == -1 else -quantity * latest_price

        # Update portfolio value
        portfolio_value = cash + sum([quantity * price_histories[symbol][-1] for symbol, quantity in portfolio.items()])
        portfolio_values.append(portfolio_value)

        trade_count += 1
        # Log portfolio value every 10 trades
        if trade_count % 10 == 0:
            log_portfolio_value(portfolio_value, cash, portfolio)

    except Exception as e:
        logging.error(f"Error executing trade for {symbol}: {e}")

def backtest_strategy(symbols, start_date, end_date):
    global cash, portfolio, portfolio_value
    cash, portfolio, portfolio_value = get_portfolio()  # Initialize portfolio
    
    for symbol in symbols:
        bars = api.get_bars(symbol, tradeapi.rest.TimeFrame.Minute, start=start_date, end=end_date, feed='iex').df
        for i in range(len(bars)):
            bar = bars.iloc[i]
            price_histories[symbol].append(bar.close)
            volume_histories[symbol].append(bar.volume)
            high_histories[symbol].append(bar.high)
            low_histories[symbol].append(bar.low)

            if len(price_histories[symbol]) > window:
                price_histories[symbol].pop(0)
                volume_histories[symbol].pop(0)
                high_histories[symbol].pop(0)
                low_histories[symbol].pop(0)

            signal = generate_signals(price_histories[symbol], volume_histories[symbol], high_histories[symbol], low_histories[symbol])
            if signal is not None:
                logging.info(f"Current portfolio for {symbol}: {portfolio.get(symbol, 0)}, Cash: {cash}, Portfolio Value: {portfolio_value}")
                execute_trade(symbol, signal, portfolio, cash, portfolio_value)

            # Check for stop loss or take profit triggers
            if symbol in stop_loss_levels and symbol in take_profit_levels:
                latest_price = price_histories[symbol][-1]
                if latest_price is not None:
                    if latest_price <= stop_loss_levels[symbol] or latest_price >= take_profit_levels[symbol]:
                        execute_trade(symbol, -1, portfolio, cash, portfolio_value)

if __name__ == "__main__":
    initialize_trade_log()
    initialize_performance_log()
    
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')  # 30 days back from today
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    backtest_strategy(symbols, start_date, end_date)
    
    print("Backtesting completed")

    # Generate performance report
    generate_report()
