import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from test_indicators import calculate_volume_rsi, calculate_atr
from itertools import product


class Backtester:
    def __init__(self, data, symbol, window=10, stop_loss_pct=0.02, take_profit_pct=0.05, trade_allocation=10):
        self.symbol = symbol
        self.data = data
        self.window = window
        self.initial_capital = 1000
        self.capital = self.initial_capital
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trade_allocation = trade_allocation
        self.positions = 0
        self.position_price = 0
        self.trade_log = []
        self.equity_curve = [self.initial_capital] * len(data)

    def generate_signals(self):
        self.data['returns'] = self.data['close'].pct_change()
        self.data['volume_rsi'] = calculate_volume_rsi(self.data['volume'], self.window)
        self.data['atr'] = calculate_atr(self.data['high'], self.data['low'], self.data['close'], self.window)
        self.data['signal'] = 0

        buy_signal = (self.data['returns'] > 0) & (self.data['volume_rsi'] > 50)
        sell_signal = (self.data['returns'] < 0) & (self.data['volume_rsi'] < 50)

        self.data.loc[buy_signal, 'signal'] = 1
        self.data.loc[sell_signal, 'signal'] = -1

    def execute_trades(self):
        for i, row in enumerate(self.data.itertuples()):
            current_price = row.close
            if self.positions > 0:
                if current_price <= self.position_price * (1 - self.stop_loss_pct):
                    self.capital += self.positions * current_price
                    self.positions = 0
                    self.trade_log.append((self.symbol, 'stop_loss', row.Index, current_price, self.capital))
                elif current_price >= self.position_price * (1 + self.take_profit_pct):
                    self.capital += self.positions * current_price
                    self.positions = 0
                    self.trade_log.append((self.symbol, 'take_profit', row.Index, current_price, self.capital))

            if row.signal == 1 and self.capital >= self.trade_allocation:
                investment_amount = self.trade_allocation
                self.positions = investment_amount / current_price
                self.position_price = current_price
                self.capital -= investment_amount
                self.trade_log.append((self.symbol, 'buy', row.Index, current_price, self.positions))
            elif row.signal == -1 and self.positions > 0:
                self.capital += self.positions * current_price
                self.positions = 0
                self.position_price = 0
                self.trade_log.append((self.symbol, 'sell', row.Index, current_price, self.capital))

            self.equity_curve[i] = self.capital + (self.positions * current_price)

    def run_backtest(self):
        self.generate_signals()
        self.execute_trades()

def optimize_parameters(data, symbol, param_grid):
    best_params = None
    best_performance = float('-inf')
    all_results = []

    for params in product(*param_grid.values()):
        param_dict = dict(zip(param_grid.keys(), params))
        bt = Backtester(data, symbol, **param_dict)
        bt.run_backtest()

        final_capital = bt.capital + (bt.positions * bt.data['close'].iloc[-1] if bt.positions > 0 else 0)
        performance = (final_capital - bt.initial_capital) / bt.initial_capital * 100

        all_results.append((param_dict, performance))

        if performance > best_performance:
            best_performance = performance
            best_params = param_dict

    return best_params, best_performance, all_results

def generate_portfolio_performance_report(backtesters, best_params_all_symbols):
    total_initial_capital = sum(bt.initial_capital for bt in backtesters)
    final_capitals = [bt.capital + (bt.positions * bt.data['close'].iloc[-1] if bt.positions > 0 else 0) for bt in backtesters]
    total_final_capital = sum(final_capitals)

    total_return = (total_final_capital - total_initial_capital) / total_initial_capital * 100
    combined_equity_curve = np.sum([bt.equity_curve for bt in backtesters], axis=0)
    daily_returns = np.diff(combined_equity_curve) / combined_equity_curve[:-1]

    sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) != 0 else np.nan
    max_drawdown = np.max(1 - (combined_equity_curve / np.maximum.accumulate(combined_equity_curve))) * 100

    total_trades = sum(len(bt.trade_log) for bt in backtesters)
    total_buys = sum(1 for bt in backtesters for trade in bt.trade_log if trade[1] == 'buy')
    total_sells = sum(1 for bt in backtesters for trade in bt.trade_log if trade[1] == 'sell')
    wins = sum([1 for bt in backtesters for trade in bt.trade_log if trade[1] == 'take_profit' or 
                (trade[1] == 'sell' and isinstance(trade[2], (int, float)) and isinstance(trade[3], (int, float)) and trade[3] > trade[2])])
    losses = sum([1 for bt in backtesters for trade in bt.trade_log if trade[1] == 'stop_loss' or 
                  (trade[1] == 'sell' and isinstance(trade[2], (int, float)) and isinstance(trade[3], (int, float)) and trade[3] <= trade[2])])
    win_rate = wins / total_trades if total_trades else 0

    print("Portfolio Performance Summary:")
    print(f"Total Initial Capital: ${total_initial_capital:.2f}")
    print(f"Final Total Capital: ${total_final_capital:.2f}")
    print(f"Total Return: {total_return:.2f}%")
    print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"Max Drawdown: {max_drawdown:.2f}%")
    print(f"Total Trades: {total_trades}")
    print(f"Total Buys: {total_buys}")
    print(f"Total Sells: {total_sells}")
    print(f"Win Rate: {win_rate * 100:.2f}%")

    print("\nBest Parameters for Each Stock:")
    for symbol, best_params, best_performance in best_params_all_symbols:
        print(f"{symbol}: {best_params} with performance: {best_performance:.2f}%")

if __name__ == "__main__":
    symbols = ['AAPL', 'GOOG', 'AMZN', 'MSFT', 'META', 'TSLA', 'NFLX', 'NVDA', 'V', 'PYPL']
    param_grid = {
        'window': [5, 10, 15, 20, 25],
        'stop_loss_pct': [0.01, 0.02, 0.03],
        'take_profit_pct': [0.03, 0.05, 0.07],
        'trade_allocation': [10]
    }
    best_params_all_symbols = []

    for symbol in symbols:
        data = pd.read_csv(f'tests/historic_data/{symbol}_historical_data.csv', parse_dates=['time'], index_col='time')
        best_params, best_performance, _ = optimize_parameters(data, symbol, param_grid)
        best_params_all_symbols.append((symbol, best_params, best_performance))

    backtesters = []
    for symbol, best_params, _ in best_params_all_symbols:
        data = pd.read_csv(f'tests/historic_data/{symbol}_historical_data.csv', parse_dates=['time'], index_col='time')
        bt = Backtester(data, symbol, **best_params)
        bt.run_backtest()
        backtesters.append(bt)

    generate_portfolio_performance_report(backtesters, best_params_all_symbols)




#     file_path = f'tests/historic_data/{symbol}_historical_data.csv'