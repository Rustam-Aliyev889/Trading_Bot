import pandas as pd
import numpy as np

def calculate_volume_rsi(volume_history, window):
    series = pd.Series(volume_history)
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).sum()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).sum()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calculate_atr(high_history, low_history, close_history, window):
    high_series = pd.Series(high_history)
    low_series = pd.Series(low_history)
    close_series = pd.Series(close_history)

    tr1 = high_series - low_series
    tr2 = (high_series - close_series.shift()).abs()
    tr3 = (low_series - close_series.shift()).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=window).mean()

    return atr.iloc[-1]
