import pandas as pd
import numpy as np

"""Args I use in functions:
        high (pd.Series): Series of high prices.
        low (pd.Series): Series of low prices.
        close (pd.Series): Series of close prices.
        close_prices (pd.Series): Series of closing prices.
        volume (pd.Series): Series of volume data.
        window (int): The period over which to calculate the ATR."""

def calculate_volume_rsi(volume, window):
    """Calculates the Volume RSI by comparing the size of recent gains to recent losses in trading volume over a specified period.
    It helps to identify overbought or oversold conditions based on volume data."""

    delta = volume.diff()  # Calculate the difference between consecutive volume values
    gain = (delta.where(delta > 0, 0)).rolling(window).sum()  # Sum of gains over the window
    loss = (-delta.where(delta < 0, 0)).rolling(window).sum()  # Sum of losses over the window
    rs = gain / loss  # Relative Strength (RS)
    volume_rsi = 100 - (100 / (1 + rs))  # Volume RSI calculation
    return volume_rsi

def calculate_atr(high, low, close, window):
    """
    Calculates the Average True Range (ATR) to measure market volatility by averaging the true range (difference between high, low, and previous close) over a specified period.
    It indicates how much an asset typically moves over a given time frame.
    """
    high_low = high - low  # High minus Low
    high_close = np.abs(high - close.shift())  # High minus previous close
    low_close = np.abs(low - close.shift())  # Low minus previous close
    tr = high_low.combine(high_close, np.maximum).combine(low_close, np.maximum)  # True Range (TR)
    atr = tr.rolling(window).mean()  # ATR is the rolling mean of the TR
    return atr

def calculate_rsi(close_prices, window=14):
    """ Calculates the Relative Strength Index (RSI) based on the average price gains and losses over a specified period.
    Volume RSI - uses volume data, RSI uses price data to identify overbought or oversold conditions in the asset's price."""

    delta = close_prices.diff()  # Calculate the difference between consecutive closing prices
    gain = (delta.where(delta > 0, 0)).rolling(window).mean()  # Average gain over the window
    loss = (-delta.where(delta < 0, 0)).rolling(window).mean()  # Average loss over the window
    rs = gain / loss  # Relative Strength (RS)
    rsi = 100 - (100 / (1 + rs))  # RSI calculation
    return rsi