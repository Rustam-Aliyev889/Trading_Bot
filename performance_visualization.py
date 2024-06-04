import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def calculate_sharpe_ratio(data, risk_free_rate=0.01):
    daily_returns = data['equity'].pct_change().dropna()
    excess_returns = daily_returns - risk_free_rate / 252
    sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns)
    annualized_sharpe_ratio = sharpe_ratio * np.sqrt(252)
    return annualized_sharpe_ratio

def calculate_max_drawdown(data):
    cumulative_returns = data['equity'] / data['equity'].iloc[0]
    rolling_max = cumulative_returns.cummax()
    drawdown = cumulative_returns - rolling_max
    max_drawdown = drawdown.min()
    return max_drawdown

def calculate_cagr(data):
    start_value = data['equity'].iloc[0]
    end_value = data['equity'].iloc[-1]
    num_years = (data.index[-1] - data.index[0]).days / 365.25
    cagr = (end_value / start_value) ** (1 / num_years) - 1
    return cagr

def calculate_win_loss_ratio(data):
    trades = data[data['positions'] != 0]
    wins = trades[trades['equity'].diff() > 0]
    losses = trades[trades['equity'].diff() <= 0]
    win_loss_ratio = len(wins) / len(losses)
    return win_loss_ratio

def plot_performance(data):
    plt.figure(figsize=(12, 6))
    plt.plot(data['equity'], label='Equity Curve')
    plt.xlabel('Date')
    plt.ylabel('Equity')
    plt.title('Equity Curve Over Time')
    plt.legend()
    plt.show()

def performance_metrics(data):
    sharpe_ratio = calculate_sharpe_ratio(data)
    max_drawdown = calculate_max_drawdown(data)
    cagr = calculate_cagr(data)
    win_loss_ratio = calculate_win_loss_ratio(data)

    print(f'Sharpe Ratio: {sharpe_ratio:.2f}')
    print(f'Max Drawdown: {max_drawdown:.2f}')
    print(f'CAGR: {cagr:.2%}')
    print(f'Win/Loss Ratio: {win_loss_ratio:.2f}')

