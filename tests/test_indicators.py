import pandas as pd
import numpy as np

def calculate_volume_rsi(volume, window):
    delta = volume.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window).sum()
    loss = (-delta.where(delta < 0, 0)).rolling(window).sum()
    rs = gain / loss
    volume_rsi = 100 - (100 / (1 + rs))
    return volume_rsi

def calculate_atr(high, low, close, window):
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    tr = high_low.combine(high_close, np.maximum).combine(low_close, np.maximum)
    atr = tr.rolling(window).mean()
    return atr

def calculate_macd(close_prices, fastperiod=12, slowperiod=26, signalperiod=9):
    exp1 = close_prices.ewm(span=fastperiod, adjust=False).mean()
    exp2 = close_prices.ewm(span=slowperiod, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signalperiod, adjust=False).mean()
    return macd, signal_line

def calculate_rsi(close_prices, window=14):
    delta = close_prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_sma(close_prices, window):
    return close_prices.rolling(window=window).mean()

def calculate_momentum(close_prices, window):
    return close_prices.diff(window)
