import itertools
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import time
import logging

# Import necessary functions and variables from your main trading strategy file
from momentum_strategy_backtest import initialize_trade_log, initialize_performance_log, backtest_strategy, symbols
from test_performance_metrics import calculate_metrics

# Define the start and end date for the backtest
start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')  # 30 days back from today
end_date = datetime.now().strftime('%Y-%m-%d')

# Define a simplified parameter grid
param_grid = {
    'window': [15, 20, 25, 30],  # More granular
    'allocation_per_trade': [25, 50, 75, 100],
    'stop_loss_pct': [0.015, 0.02, 0.025, 0.03],
    'take_profit_pct': [0.04, 0.05, 0.06, 0.07],
}
# Reduce the number of symbols for faster testing
test_symbols = symbols[:1]  # Use only the first 3 symbols for quicker tests

# Function to run the backtest with given parameters and calculate performance metrics
def run_backtest(params):
    global window, allocation_per_trade, stop_loss_pct, take_profit_pct
    window = params['window']
    allocation_per_trade = params['allocation_per_trade']
    stop_loss_pct = params['stop_loss_pct']
    take_profit_pct = params['take_profit_pct']

    # Reset logs
    initialize_trade_log()
    initialize_performance_log()
    
    start_time = time.time()
    backtest_strategy(test_symbols, start_date, end_date)
    end_time = time.time()
    
    elapsed_time = end_time - start_time
    print(f"Backtest completed in {elapsed_time:.2f} seconds for parameters: {params}")

    # Assuming generate_report() logs the performance, we read it here
    performance_log = pd.read_csv('tests/logs/performance_log.csv')
    cumulative_return = (performance_log['Portfolio Value'].iloc[-1] - performance_log['Portfolio Value'].iloc[0]) / performance_log['Portfolio Value'].iloc[0]
    sharpe_ratio, max_dd = calculate_metrics(performance_log)
    
    return params, cumulative_return, sharpe_ratio, max_dd, elapsed_time

# Generate all combinations of parameters
param_combinations = [dict(zip(param_grid.keys(), values)) for values in itertools.product(*param_grid.values())]

# Evaluate each combination
results = []
total_time = 0
for idx, params in enumerate(param_combinations):
    print(f"Running backtest {idx+1}/{len(param_combinations)} with parameters: {params}")
    result = run_backtest(params)
    results.append(result)
    total_time += result[-1]

# Find the best parameters based on cumulative return
best_params, best_performance, best_sharpe, best_max_dd, _ = max(results, key=lambda x: x[1])
print(f"Best Parameters: {best_params}")
print(f"Best Performance (Cumulative Return): {best_performance}")
print(f"Best Sharpe Ratio: {best_sharpe}")
print(f"Best Max Drawdown: {best_max_dd}")
print(f"Total time taken: {total_time:.2f} seconds")

# Optional: Save the results to a file for further analysis
results_df = pd.DataFrame(results, columns=['Parameters', 'Cumulative Return', 'Sharpe Ratio', 'Max Drawdown', 'Time'])
results_df.to_csv('parameter_tuning_results.csv', index=False)
