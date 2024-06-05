import numpy as np
import pandas as pd
from itertools import product
from trade_bot import generate_signals, backtest_strategy
from performance_visualization import calculate_sharpe_ratio, calculate_max_drawdown, calculate_cagr, calculate_win_loss_ratio

def optimize_parameters(data, short_window_range, long_window_range, initial_capital):
    best_sharpe = -np.inf
    best_params = None
    results = []

    for short_window, long_window in product(short_window_range, long_window_range):
        if short_window >= long_window:
            continue

        data_with_signals = generate_signals(data.copy(), short_window, long_window)
        backtested_data = backtest_strategy(data_with_signals, initial_capital)

        sharpe_ratio = calculate_sharpe_ratio(backtested_data)
        max_drawdown = calculate_max_drawdown(backtested_data)
        cagr = calculate_cagr(backtested_data)
        win_loss_ratio = calculate_win_loss_ratio(backtested_data)

        results.append((short_window, long_window, sharpe_ratio, max_drawdown, cagr, win_loss_ratio))

        if sharpe_ratio > best_sharpe:
            best_sharpe = sharpe_ratio
            best_params = (short_window, long_window)

    results_df = pd.DataFrame(results, columns=['Short Window', 'Long Window', 'Sharpe Ratio', 'Max Drawdown', 'CAGR', 'Win/Loss Ratio'])
    return best_params, results_df

if __name__ == "__main__":
    import yfinance as yf
    import matplotlib.pyplot as plt

    data = yf.download('SPY', start='2022-01-01', end='2024-05-30')
    short_window_range = range(10, 60, 10)
    long_window_range = range(100, 300, 50)
    initial_capital = 100000.0

    best_params, results_df = optimize_parameters(data, short_window_range, long_window_range, initial_capital)
    print(f"Best Parameters: Short Window = {best_params[0]}, Long Window = {best_params[1]}")
    print(results_df)

    plt.figure(figsize=(10, 6))
    plt.plot(results_df['Sharpe Ratio'], label='Sharpe Ratio')
    plt.xlabel('Parameter Set')
    plt.ylabel('Sharpe Ratio')
    plt.title('Parameter Optimization Results')
    plt.legend()
    plt.show()
