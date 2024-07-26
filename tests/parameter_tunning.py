import itertools
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
from momentum_strategy_backtest import initialize_trade_log, initialize_performance_log, backtest_strategy, symbols
from test_performance_metrics import calculate_metrics

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# start and end date for the backtest
start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')  # 30 days back from today
end_date = datetime.now().strftime('%Y-%m-%d')

param_grid = {
    'window': [15, 20, 25, 30],
    'allocation_per_trade': [25, 50, 75, 100],
    'stop_loss_pct': [0.015, 0.02, 0.025, 0.03],
    'take_profit_pct': [0.04, 0.05, 0.06, 0.07]
}

# Use only one symbol for initial tuning
initial_test_symbol = symbols[:1]

# Function to run the backtest with given parameters and calculate performance metrics
def run_backtest(params, test_symbols):
    global window, allocation_per_trade, stop_loss_pct, take_profit_pct
    window = params['window']
    allocation_per_trade = params['allocation_per_trade']
    stop_loss_pct = params['stop_loss_pct']
    take_profit_pct = params['take_profit_pct']

    # Reset logs
    initialize_trade_log()
    initialize_performance_log()

    logging.info(f"Running backtest for symbols: {test_symbols} with parameters: {params}")
    
    start_time = time.time()
    backtest_strategy(test_symbols, start_date, end_date)
    end_time = time.time()
    
    elapsed_time = end_time - start_time
    logging.info(f"Backtest completed in {elapsed_time:.2f} seconds for parameters: {params} with symbols: {test_symbols}")

    # Read performance log and calculate metrics
    performance_log = pd.read_csv('tests/logs/performance_log.csv')
    cumulative_return = (performance_log['Portfolio Value'].iloc[-1] - performance_log['Portfolio Value'].iloc[0]) / performance_log['Portfolio Value'].iloc[0]
    sharpe_ratio, max_dd = calculate_metrics(performance_log)
    
    return params, cumulative_return, sharpe_ratio, max_dd, elapsed_time

# Generate all combinations of parameters
param_combinations = [dict(zip(param_grid.keys(), values)) for values in itertools.product(*param_grid.values())]

# Evaluate each combination using the initial symbol
results = []
total_time = 0
for idx, params in enumerate(param_combinations):
    print(f"Running backtest {idx+1}/{len(param_combinations)} with parameters: {params}")
    result = run_backtest(params, initial_test_symbol)
    results.append(result)
    total_time += result[-1]

# the best parameters based on cumulative return
best_params, best_performance, best_sharpe, best_max_dd, _ = max(results, key=lambda x: x[1])
print(f"Best Parameters: {best_params}")
print(f"Best Performance (Cumulative Return): {best_performance}")
print(f"Best Sharpe Ratio: {best_sharpe}")
print(f"Best Max Drawdown: {best_max_dd}")
print(f"Total time taken: {total_time:.2f} seconds")

# Save initial results to a file for further analysis
results_df = pd.DataFrame(results, columns=['Parameters', 'Cumulative Return', 'Sharpe Ratio', 'Max Drawdown', 'Time'])
results_df.to_csv('parameter_tuning_results_initial.csv', index=False)

# Validate the best parameters across multiple symbols
def validate_across_symbols(best_params):
    validation_results = []
    for symbol in symbols:
        test_symbols = [symbol]
        print(f"Validating for symbol: {symbol} with parameters: {best_params}")
        logging.info(f"Validating for symbol: {symbol} with parameters: {best_params}")
        params, cumulative_return, sharpe_ratio, max_dd, elapsed_time = run_backtest(best_params, test_symbols)
        validation_results.append((symbol, params, cumulative_return, sharpe_ratio, max_dd, elapsed_time))
    
    return validation_results

validation_results = validate_across_symbols(best_params)

# Print validation results
for result in validation_results:
    symbol, params, cumulative_return, sharpe_ratio, max_dd, elapsed_time = result
    print(f"Symbol: {symbol}")
    print(f"Cumulative Return: {cumulative_return}")
    print(f"Sharpe Ratio: {sharpe_ratio}")
    print(f"Max Drawdown: {max_dd}")
    print(f"Time taken: {elapsed_time:.2f} seconds")

# Save validation results to a file for further analysis
validation_results_df = pd.DataFrame(validation_results, columns=['Symbol', 'Parameters', 'Cumulative Return', 'Sharpe Ratio', 'Max Drawdown', 'Time'])
validation_results_df.to_csv('tests/parameter_tuning_validation_results.csv', index=False)
