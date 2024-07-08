import pandas as pd
import numpy as np
import os
import csv

PERFORMANCE_LOG_FILE = 'tests/logs/test_performance.csv'
TRADE_LOG_FILE = 'tests/logs/test_trade.csv'
FINAL_REPORT_FILE = 'tests/logs/final_report.txt'

# Initialize logs
def initialize_logs():
    if not os.path.exists(PERFORMANCE_LOG_FILE):
        os.makedirs(os.path.dirname(PERFORMANCE_LOG_FILE), exist_ok=True)
        with open(PERFORMANCE_LOG_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Timestamp', 'Portfolio Value', 'Cash Balance', 'Positions', 'Daily High', 'Daily Low', 'Daily Close', 'Volume'])
    if not os.path.exists(TRADE_LOG_FILE):
        with open(TRADE_LOG_FILE, 'w') as f:
            f.write('Date,Symbol,Action,Price,Quantity,Cash\n')

# Log trades
def log_trade(date, symbol, action, price, quantity, cash):
    with open(TRADE_LOG_FILE, 'a') as f:
        f.write(f'{date},{symbol},{action},{price},{quantity},{cash}\n')

# Log performance
def log_performance(date, portfolio_value, cash, positions, daily_high, daily_low, daily_close, volume):
    with open(PERFORMANCE_LOG_FILE, 'a') as f:
        writer = csv.writer(f)
        writer.writerow([date, portfolio_value, cash, positions, daily_high, daily_low, daily_close, volume])

# Calculate period metrics
def period_metrics(df, period='D'):
    df_resampled = df.resample(period).agg({'Portfolio Value': 'last'})
    df_resampled['Portfolio Value'] = pd.to_numeric(df_resampled['Portfolio Value'], errors='coerce')
    initial_value = df_resampled['Portfolio Value'].iloc[0]
    final_value = df_resampled['Portfolio Value'].iloc[-1]
    cumulative_return = (final_value / initial_value) - 1
    daily_returns = df['Portfolio Value'].pct_change().dropna()
    sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
    max_drawdown = (df_resampled['Portfolio Value'].cummax() - df_resampled['Portfolio Value']).max() / df_resampled['Portfolio Value'].cummax().max()
    return initial_value, final_value, cumulative_return, sharpe_ratio, max_drawdown

# Generate final report
def generate_final_report():
    if not os.path.exists(PERFORMANCE_LOG_FILE):
        raise FileNotFoundError(f"{PERFORMANCE_LOG_FILE} not found.")

    df = pd.read_csv(PERFORMANCE_LOG_FILE, parse_dates=['Timestamp'], index_col='Timestamp')
    df['Portfolio Value'] = pd.to_numeric(df['Portfolio Value'], errors='coerce')

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

    with open(FINAL_REPORT_FILE, 'w') as report:
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
        report.write(f"Sharpe Ratio: {daily_sharpe:.2f}\n")
        report.write(f"Max Drawdown: {daily_drawdown:.2%}\n\n")

        report.write(f"Weekly Performance:\n")
        report.write(f"{'-'*20}\n")
        report.write(f"Initial Portfolio Value: {weekly_initial:.2f}\n")
        report.write(f"Final Portfolio Value: {weekly_final:.2f}\n")
        report.write(f"Cumulative Return: {weekly_cum_return:.2%}\n")
        report.write(f"Sharpe Ratio: {weekly_sharpe:.2f}\n")
        report.write(f"Max Drawdown: {weekly_drawdown:.2%}\n\n")

        report.write(f"Monthly Performance:\n")
        report.write(f"{'-'*21}\n")
        report.write(f"Initial Portfolio Value: {monthly_initial:.2f}\n")
        report.write(f"Final Portfolio Value: {monthly_final:.2f}\n")
        report.write(f"Cumulative Return: {monthly_cum_return:.2%}\n")
        report.write(f"Sharpe Ratio: {monthly_sharpe:.2f}\n")
        report.write(f"Max Drawdown: {monthly_drawdown:.2%}\n\n")

        report.write(f"Yearly Performance:\n")
        report.write(f"{'-'*20}\n")
        report.write(f"Initial Portfolio Value: {yearly_initial:.2f}\n")
        report.write(f"Final Portfolio Value: {yearly_final:.2f}\n")
        report.write(f"Cumulative Return: {yearly_cum_return:.2%}\n")
        report.write(f"Sharpe Ratio: {yearly_sharpe:.2f}\n")
        report.write(f"Max Drawdown: {yearly_drawdown:.2%}\n\n")

        report.write(f"Note: Sharpe Ratio is displayed as 'Insufficient data' when there are not enough data points to calculate a meaningful value or if returns are constant.\n\n")

# If this script is run directly, generate the final report
if __name__ == "__main__":
    generate_final_report()

