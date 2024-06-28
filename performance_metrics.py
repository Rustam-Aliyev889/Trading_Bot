import csv
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import alpaca_trade_api as tradeapi

# Path to the performance metrics log file
PERFORMANCE_LOG_FILE = 'logs/performance_log.csv'
REPORT_FILE = 'logs/trading_strategy_report.txt'

# Alpaca API credentials (replace with your own)
ALPACA_API_KEY = 'PK6UA3MS4473Y9NFBJRC'
ALPACA_SECRET_KEY = 'BVclZK6KgCegMeBS6lPLt4Ezi4k6IRhE7OCmzuh3'
BASE_URL = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, api_version='v2')

def initialize_performance_log():
    if not os.path.exists(PERFORMANCE_LOG_FILE):
        os.makedirs(os.path.dirname(PERFORMANCE_LOG_FILE), exist_ok=True)
        with open(PERFORMANCE_LOG_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Timestamp', 'Portfolio Value', 'Cash Balance', 'Positions', 'Daily High', 'Daily Low', 'Daily Close', 'Volume'])

def log_portfolio_value():
    try:
        account = api.get_account()
        portfolio_value = account.equity
        cash_balance = account.cash
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Get positions
        positions = api.list_positions()
        positions_str = '; '.join([f"{position.symbol}: {position.qty}" for position in positions])

        bars = api.get_bars('SPY', tradeapi.rest.TimeFrame.Day, limit=1).df
        daily_high = bars['high'].iloc[0]
        daily_low = bars['low'].iloc[0]
        daily_close = bars['close'].iloc[0]
        volume = bars['volume'].iloc[0]

        with open(PERFORMANCE_LOG_FILE, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, portfolio_value, cash_balance, positions_str, daily_high, daily_low, daily_close, volume])

        print(f"Logged portfolio value at {timestamp}")
    except Exception as e:
        print(f"Error logging portfolio value: {e}")


def calculate_metrics(df):
    df['Daily Return'] = df['Portfolio Value'].pct_change()
    df['Cumulative Return'] = (1 + df['Daily Return']).cumprod() - 1

    mean_return = df['Daily Return'].mean()
    std_return = df['Daily Return'].std()

    # Check for zero standard deviation to avoid division by zero
    if std_return == 0 or np.isnan(std_return):
        sharpe_ratio = 'Insufficient data'
    else:
        sharpe_ratio = (mean_return / std_return) * np.sqrt(252)

    roll_max = df['Portfolio Value'].cummax()
    drawdown = df['Portfolio Value'] / roll_max - 1
    max_drawdown = drawdown.min()

    return sharpe_ratio, max_drawdown

def period_metrics(df, period):
    resampled_df = df.resample(period).last()
    resampled_df['Daily Return'] = resampled_df['Portfolio Value'].pct_change()
    resampled_df['Cumulative Return'] = (1 + resampled_df['Daily Return']).cumprod() - 1

    initial_value = resampled_df['Portfolio Value'].iloc[0]
    final_value = resampled_df['Portfolio Value'].iloc[-1]
    cumulative_return = (final_value / initial_value) - 1
    sharpe_ratio, max_drawdown = calculate_metrics(resampled_df)

    return initial_value, final_value, cumulative_return, sharpe_ratio, max_drawdown

def generate_report():
    if not os.path.exists(PERFORMANCE_LOG_FILE):
        raise FileNotFoundError(f"{PERFORMANCE_LOG_FILE} not found.")

    df = pd.read_csv(PERFORMANCE_LOG_FILE, parse_dates=['Timestamp'], index_col='Timestamp')

    start_time = df.index.min()
    end_time = df.index.max()
    duration = end_time - start_time

    # Ensure sufficient data points
    if len(df) < 2:
        raise ValueError("Not enough data to generate report")

    # Metrics for each period
    daily_initial, daily_final, daily_cum_return, daily_sharpe, daily_drawdown = period_metrics(df, 'D')
    weekly_initial, weekly_final, weekly_cum_return, weekly_sharpe, weekly_drawdown = period_metrics(df, 'W')
    monthly_initial, monthly_final, monthly_cum_return, monthly_sharpe, monthly_drawdown = period_metrics(df, 'MS')
    yearly_initial, yearly_final, yearly_cum_return, yearly_sharpe, yearly_drawdown = period_metrics(df, 'YS')

    with open(REPORT_FILE, 'w') as report:
        report.write(f"Trading Strategy Report\n")
        report.write(f"{'='*23}\n\n")
        
        report.write(f"Running Period:\n")
        report.write(f"{'-'*16}\n")
        report.write(f"Start Time: {start_time}\n")
        report.write(f"End Time: {end_time}\n")
        report.write(f"Total Duration: {duration}\n\n")

        report.write(f"Daily Performance:\n")
        report.write(f"{'-'*19}\n")
        report.write(f"Initial Portfolio Value: {daily_initial:.2f}\n")
        report.write(f"Final Portfolio Value: {daily_final:.2f}\n")
        report.write(f"Cumulative Return: {daily_cum_return:.2%}\n")
        report.write(f"Sharpe Ratio: {daily_sharpe} (if applicable)\n")
        report.write(f"Max Drawdown: {daily_drawdown:.2%}\n\n")

        report.write(f"Weekly Performance:\n")
        report.write(f"{'-'*20}\n")
        report.write(f"Initial Portfolio Value: {weekly_initial:.2f}\n")
        report.write(f"Final Portfolio Value: {weekly_final:.2f}\n")
        report.write(f"Cumulative Return: {weekly_cum_return:.2%}\n")
        report.write(f"Sharpe Ratio: {weekly_sharpe} (if applicable)\n")
        report.write(f"Max Drawdown: {weekly_drawdown:.2%}\n\n")

        report.write(f"Monthly Performance:\n")
        report.write(f"{'-'*21}\n")
        report.write(f"Initial Portfolio Value: {monthly_initial:.2f}\n")
        report.write(f"Final Portfolio Value: {monthly_final:.2f}\n")
        report.write(f"Cumulative Return: {monthly_cum_return:.2%}\n")
        report.write(f"Sharpe Ratio: {monthly_sharpe} (if applicable)\n")
        report.write(f"Max Drawdown: {monthly_drawdown:.2%}\n\n")

        report.write(f"Yearly Performance:\n")
        report.write(f"{'-'*20}\n")
        report.write(f"Initial Portfolio Value: {yearly_initial:.2f}\n")
        report.write(f"Final Portfolio Value: {yearly_final:.2f}\n")
        report.write(f"Cumulative Return: {yearly_cum_return:.2%}\n")
        report.write(f"Sharpe Ratio: {yearly_sharpe} (if applicable)\n")
        report.write(f"Max Drawdown: {yearly_drawdown:.2%}\n\n")

        report.write(f"Note: Sharpe Ratio is displayed as 'Insufficient data' when there are not enough data points to calculate a meaningful value or if returns are constant.\n\n")

    # Ensure 'Cumulative Return' exists in the DataFrame for plotting
    df['Daily Return'] = df['Portfolio Value'].pct_change()
    df['Cumulative Return'] = (1 + df['Daily Return']).cumprod() - 1
    generate_charts(df)



def generate_charts(df):
    plt.figure(figsize=(10, 6))
    df['Cumulative Return'].plot()
    plt.title('Cumulative Return')
    plt.savefig('logs/cumulative_return.png')
    plt.close()

    plt.figure(figsize=(10, 6))
    df['Daily Return'].plot()
    plt.title('Daily Return')
    plt.savefig('logs/daily_return.png')
    plt.close()

    df['Drawdown'] = df['Portfolio Value'] / df['Portfolio Value'].cummax() - 1
    plt.figure(figsize=(10, 6))
    df['Drawdown'].plot()
    plt.title('Drawdown')
    plt.savefig('logs/drawdown.png')
    plt.close()

# Example usage
if __name__ == "__main__":
    initialize_performance_log()
    log_portfolio_value()
    generate_report()
    print(f"Report generated: {REPORT_FILE}")
