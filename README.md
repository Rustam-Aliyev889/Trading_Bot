# Trading Bot

## Description
The Momentum Trading Bot is a Python-based automated trading system that utilizes different indicators to make buy and sell decisions. The bot is designed to analyze real time data and make trading decisions based on calculated indicators such as RSI (Relative Strength Index) and ATR (Average True Range). It integrates with Alpaca's paper trading API for testing trading strategies in a risk-free environment.


## What is Momentum Investing?
Momentum investing is a trading strategy in which investors buy securities that are rising and sell them when they look to have peaked. The goal is to work with volatility by finding buying opportunities in short-term uptrends and then sell when the securities start to lose momentum. Then, the investor takes the cash and looks for the next short-term uptrend, or buying opportunity, and repeats the process.

### Key Points and Features
1. **Indicators Used**:
    - **Relative Strength Index (RSI)**: Measures the magnitude of recent price changes to evaluate overbought or oversold conditions by comparing the average of recent gains to recent losses over a specified period.
    - **Volume RSI**: Similar to RSI but applied to trading volume, indicating the strength of price movements based on volume data by comparing the size of recent gains to recent losses in trading volume over a specified period.
    - **Average True Range (ATR)**: A volatility indicator that shows the degree of price movement, helping to set stop-loss and take-profit levels.

2. **Signal Generation**:
    - **Buy Signal**: Generated when the price momentum is positive (price increase), the Volume RSI indicates strength (above 50), and the RSI suggests the asset is not overbought (below 70).
    - **Sell Signal**: Generated when the price momentum is negative (price decrease), the Volume RSI indicates weakness (below 50), and the RSI suggests the asset is not oversold (above 30).
    - **Neutral Signal**: If none of the above conditions are met, the strategy holds the current position without taking any action.

3. **Risk Management**: (Stop-loss and take-profit mechanisms to manage risk.)
    - **Stop-Loss**: A predefined price level set below the buy price to limit potential losses if the market moves against the position.
    - **Take-Profit**: A predefined price level set above the buy price to lock in profits once the target price is reached.
    - **Daily Loss Limit**: Limits the maximum loss the portfolio can incur in a single day to prevent significant drawdowns.

4. **Execution**:
    - The bot continuously monitors real-time market data for the selected symbols.
    - When a buy or sell signal is generated, the bot executes a trade based on the allocated capital per trade.
    - Positions are monitored and adjusted based on the defined stop-loss and take-profit levels.

5. **Logging and Performance Tracking**:
    - **Trade Logging**: Records all executed trades with details such as timestamp, symbol, action (buy/sell), quantity, price, order ID, and status for analysis. All executed trades are logged in a CSV file (`trade_log.csv`) located in the `logs/` directory.
    - **Performance Logging**: Tracks portfolio performance, including portfolio value, cash balance, positions, daily high, low, close prices, and trading volume for analysis. Portfolio performance metrics are logged in a CSV file (`performance_log.csv`) in the `logs/` directory.
    - 
6. **Real-time Data**: Utilizes Alpaca's real-time market data to make trading decisions.

7. **Asynchronous Execution**: Uses asyncio for handling real-time data and  make trades at the same time without waiting for one task to finish before starting another. This makes the bot faster and more efficient.

8. **Fractional Trading**: Supports fractional shares, allowing for more precise allocation of capital and better utilization of the portfolio.

9. **Performance Analysis**: Includes detailed performance metrics such as Sharpe ratio, maximum drawdown, and cumulative returns, providing insights into the strategy's effectiveness.
 
-  **calculate_metrics**
    ```python
    def calculate_metrics(df):
        """
        Calculates the Sharpe ratio and maximum drawdown from the given DataFrame of portfolio values.
        """
    ```
    - **period_metrics**
    ```python
    def period_metrics(df, period):
        """
        Calculates metrics for a given period by resampling the DataFrame.
        """
    ```

10. **Reporting**: Ability to generate reports on trading performance, including visualizations and summaries

11. **Backtesting Capability**: Allows for historical data backtesting to evaluate the strategy's performance over different time periods and market conditions.

## Configuration

- **Trading Parameters**: You can configure trading parameters such as window size (The number of past data points used to calculate indicators, such as averages or changes in price, to generate trading signals.), allocation per trade, stop-loss, and take-profit percentages in the `momentum_strategy.py` script.
- **Symbols**: Modify the list of symbols in `momentum_strategy.py` to trade different assets.

## Usage

1. **Run the Trading Bot**:
    ```sh
    python momentum_strategy.py
    ```

2. **Backtest the Strategy**:
    - You can run the backtest scripts located in the `tests/` directory to evaluate the performance of the strategy on historical data.
    ```sh
    python tests/momentum_strategy_backtest.py
    ```

## Important Notice

### Thorough Testing is Essential

While this trading bot implements a momentum-based strategy and has been designed with risk management features, it is crucial to understand that past performance in backtesting does not guarantee future results. The financial markets are unpredictable and can be highly volatile.

Before using this trading bot with real money, I strongly recommend that you:

1. **Conduct Extensive Backtesting**:
    - Perform backtesting on a wide range of historical data.
    - Test across different market conditions to understand how the strategy performs during various periods (e.g., bull markets, bear markets, high volatility).

2. **Paper Trading**:
    - Utilize paper trading (simulated trading) to observe how the bot performs in real-time without risking actual capital.
    - Monitor the bot's performance for an extended period to ensure consistency and reliability.

3. **Understand the Risks**:
    - Be aware that the bot can experience significant drawdowns and periods of poor performance.
    - Ensure that the strategy aligns with your risk tolerance and investment goals.

4. **Adjust and Optimize**:
    - Continuously refine and optimize the strategy based on the results from backtesting and paper trading.
    - Stay informed about market trends and adapt the strategy as necessary.

5. **Monitor Regularly (Minimum 1-2 months)**:
    - Regularly monitor the bot's performance and make adjustments if necessary.
    - Do not rely solely on the bot; human oversight is important to handle unexpected market events.

**Disclaimer**: Trading in financial markets involves significant risk and can result in the loss of your invested capital. The use of this trading bot is at your own risk. I do not provide any guarantees of profitability or financial gain. Always consult with a financial advisor before making any investment decisions.

By understanding these risks and taking the necessary precautions, you can better prepare for the inherent volatility and uncertainties of trading.


## Project Structure

- `momentum_strategy.py`: Main script to run the trading bot.
- `indicators.py`: Contains functions to calculate trading indicators (RSI, ATR).
- `performance_metrics.py`: Functions to calculate performance metrics like Sharpe ratio and maximum drawdown.
- `trade_log.py`: Functions to initialize and log trades to a CSV file.
- `tests/`: Contains test scripts and logs for backtesting and debugging.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/Rustam-Aliyev889/Trading_Bot.git
    cd trading-bot
    ```

2. Create and activate a virtual environment:

    #### On Windows:
    ```sh
    python -m venv venv
    venv\Scripts\activate
    ```

    #### On macOS/Linux:
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

4. Set up the environment variables:
    - Create a `.env` file in the root directory of the project:
      ```env
      ALPACA_API_KEY=your_alpaca_api_key
      ALPACA_SECRET_KEY=your_alpaca_secret_key
      ```
    - Alternatively, you can set the environment variables directly in your system.


## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.
