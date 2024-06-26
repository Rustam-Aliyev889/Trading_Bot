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
