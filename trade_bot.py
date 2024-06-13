from sma.sma_strategy import run_sma_strategy
from momentum_strategy import run_momentum_strategy

def run_trading_bot(strategy_name='SMA'):
    if strategy_name == 'SMA':
        run_sma_strategy()
    elif strategy_name == 'Momentum':
        run_momentum_strategy()
    else:
        print(f"Strategy '{strategy_name}' is not supported.")

if __name__ == "__main__":
    # Example: Run the Momentum strategy
    run_trading_bot('Momentum')

