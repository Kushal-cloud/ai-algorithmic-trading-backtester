from __future__ import annotations
import numpy as np
import pandas as pd

def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    close = x["Close"]
    high, low, volume = x["High"], x["Low"], x["Volume"]

    x["sma_10"] = close.rolling(10).mean()
    x["sma_20"] = close.rolling(20).mean()
    x["sma_50"] = close.rolling(50).mean()
    x["ema_12"] = close.ewm(span=12, adjust=False).mean()
    x["ema_26"] = close.ewm(span=26, adjust=False).mean()

    x["rsi_14"] = _rsi(close)
    x["macd"] = x["ema_12"] - x["ema_26"]
    x["macd_signal"] = x["macd"].ewm(span=9, adjust=False).mean()

    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    x["bb_mid"] = mid
    x["bb_upper"] = mid + 2 * std
    x["bb_lower"] = mid - 2 * std
    x["bb_width"] = (x["bb_upper"] - x["bb_lower"]) / mid

    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    x["atr_14"] = tr.rolling(14).mean()
    x["volatility_20"] = close.pct_change().rolling(20).std() * np.sqrt(252)
    x["volume_change"] = volume.pct_change()

    return x.replace([np.inf, -np.inf], np.nan)

FEATURE_COLUMNS = [
    "sma_10", "sma_20", "sma_50", "ema_12", "ema_26",
    "rsi_14", "macd", "macd_signal", "bb_mid", "bb_upper",
    "bb_lower", "bb_width", "atr_14", "volatility_20", "volume_change"
]
