"""Technical + ICT/SMC feature engineering.

Public API (stable):
    - add_features(df): classic indicators only (backwards compatible).
    - add_ict_smc_features(df): classic + ICT/SMC + black-box signals.
    - add_market_structure(df), add_black_box_signals(df): building blocks.
    - FEATURE_COLUMNS: classic indicator columns.
    - FULL_FEATURE_COLUMNS: every numeric model feature.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED_OHLCV = ("Open", "High", "Low", "Close", "Volume")


def _require_ohlcv(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_OHLCV if c not in df.columns]
    if missing:
        raise ValueError(f"Input DataFrame is missing columns: {missing}")
    if df.empty:
        raise ValueError("Input DataFrame is empty.")


def _as_arrays(high, low, close):
    """Return (h, l, c) as numpy arrays plus the source index."""
    index = None
    for s in (high, low, close):
        if isinstance(s, pd.Series):
            index = s.index
            break
    h = high.values if isinstance(high, pd.Series) else np.asarray(high)
    l = low.values if isinstance(low, pd.Series) else np.asarray(low)
    c = close.values if isinstance(close, pd.Series) else np.asarray(close)
    if index is None:
        index = pd.RangeIndex(len(c))
    return h, l, c, index


# ---------------------------------------------------------------------------
# Market structure
# ---------------------------------------------------------------------------
def _detect_market_structure(
    high,
    low,
    close,
    window: int = 5,  # kept for API compatibility; see note below
    look_left: int = 3,
    look_right: int = 3,
) -> pd.Series:
    """Classify each bar as uptrend (1), downtrend (-1) or range (0).

    Note: the legacy *window* parameter is unused; the regime is decided from
    the *look_left*/*look_right* neighbourhood. It is kept so existing callers
    do not break.
    """
    _ = window
    h, l, c, index = _as_arrays(high, low, close)
    n = len(c)
    structure = np.zeros(n, dtype=int)
    for i in range(n):
        h_i, l_i = float(h[i]), float(l[i])
        left_start = max(0, i - look_left)
        right_end = min(n, i + look_right + 1)
        higher_highs = sum(1 for j in range(left_start, right_end) if j != i and h[j] > h_i)
        lower_lows = sum(1 for j in range(left_start, right_end) if j != i and l[j] < l_i)
        if higher_highs > lower_lows:
            structure[i] = 1
        elif lower_lows > higher_highs:
            structure[i] = -1
    return pd.Series(structure, index=index)


# ---------------------------------------------------------------------------
# Order Blocks
# ---------------------------------------------------------------------------
def _find_order_blocks(high, low, close, open_: pd.Series | np.ndarray | None = None) -> pd.DataFrame:
    """Detect order blocks using real candle direction when available.

    Bullish OB: bearish candle (close < open) followed by a close above its
    high; level = that candle's low. Bearish OB mirrors this.
    """
    h, l, c, index = _as_arrays(high, low, close)
    if open_ is not None:
        o = open_.values if isinstance(open_, pd.Series) else np.asarray(open_)
    else:
        o = (h + l) / 2.0  # fallback midpoint proxy (documented heuristic)
    n = len(c)
    bullish_ob_level = np.full(n, np.nan)
    bearish_ob_level = np.full(n, np.nan)
    bullish_ob_bar_idx = np.full(n, -1, dtype=int)
    bearish_ob_bar_idx = np.full(n, -1, dtype=int)
    for i in range(1, n):
        prev_bearish = c[i - 1] < o[i - 1]
        prev_bullish = not prev_bearish
        if prev_bearish and c[i] > h[i - 1]:
            bullish_ob_level[i] = l[i - 1]
            bullish_ob_bar_idx[i] = i - 1
        if prev_bullish and c[i] < l[i - 1]:
            bearish_ob_level[i] = h[i - 1]
            bearish_ob_bar_idx[i] = i - 1
    return pd.DataFrame(
        {
            "bullish_ob_level": pd.Series(bullish_ob_level, index=index),
            "bearish_ob_level": pd.Series(bearish_ob_level, index=index),
            "bullish_ob_bar_idx": pd.Series(bullish_ob_bar_idx, index=index),
            "bearish_ob_bar_idx": pd.Series(bearish_ob_bar_idx, index=index),
        },
        index=index,
    )


# ---------------------------------------------------------------------------
# Fair Value Gaps
# ---------------------------------------------------------------------------
def _find_fvgs(high, low, close) -> pd.DataFrame:
    """Detect 3-candle fair value gaps.

    Bullish gap at bar i when low[i] > high[i-2]; the zone spans
    ``[high[i-2], low[i]]`` stored as (bottom=fvg_bottom, top=fvg_top).
    """
    h, l, c, index = _as_arrays(high, low, close)
    n = len(c)
    bullish_bottom = np.full(n, np.nan)
    bullish_top = np.full(n, np.nan)
    bearish_bottom = np.full(n, np.nan)
    bearish_top = np.full(n, np.nan)
    for i in range(2, n):
        if l[i] > h[i - 2]:
            bullish_bottom[i] = h[i - 2]
            bullish_top[i] = l[i]
        if h[i] < l[i - 2]:
            bearish_bottom[i] = h[i]
            bearish_top[i] = l[i - 2]
    return pd.DataFrame(
        {
            "bullish_fvg_low": pd.Series(bullish_bottom, index=index),
            "bullish_fvg_high": pd.Series(bullish_top, index=index),
            "bearish_fvg_low": pd.Series(bearish_bottom, index=index),
            "bearish_fvg_high": pd.Series(bearish_top, index=index),
        },
        index=index,
    )


# ---------------------------------------------------------------------------
# Liquidity sweeps
# ---------------------------------------------------------------------------
def _detect_liquidity_sweeps(high, low, close, swing_window: int = 10) -> pd.DataFrame:
    """Flag swing highs/lows whose extreme was retested and rejected."""
    h, l, c, index = _as_arrays(high, low, close)
    n = len(c)
    swing_highs: list[int] = []
    swing_lows: list[int] = []
    for i in range(swing_window, n - swing_window):
        if float(h[i]) == float(h[i - swing_window : i + swing_window + 1].max()):
            swing_highs.append(i)
        if float(l[i]) == float(l[i - swing_window : i + swing_window + 1].min()):
            swing_lows.append(i)
    sweep_high = np.full(n, np.nan)
    sweep_low = np.full(n, np.nan)
    sweep_direction = np.full(n, "", dtype=object)
    for idx in swing_highs:
        if idx + 1 < n and c[idx + 1] < h[idx]:
            sweep_high[idx] = h[idx]
            sweep_direction[idx] = "DOWN"
    for idx in swing_lows:
        if idx + 1 < n and c[idx + 1] > l[idx]:
            sweep_low[idx] = l[idx]
            sweep_direction[idx] = "UP"
    return pd.DataFrame(
        {
            "sweep_high": pd.Series(sweep_high, index=index),
            "sweep_low": pd.Series(sweep_low, index=index),
            "sweep_direction": pd.Series(sweep_direction, index=index),
        },
        index=index,
    )


# ---------------------------------------------------------------------------
# Market-structure + black-box rules
# ---------------------------------------------------------------------------
def add_market_structure(
    df: pd.DataFrame,
    structure_window: int = 5,
    look_left: int = 3,
    look_right: int = 3,
) -> pd.DataFrame:
    """Add ``mss_123`` market-regime classification (1/-1/0)."""
    _require_ohlcv(df)
    result = df.copy()
    mss_values = _detect_market_structure(
        result["High"], result["Low"], result["Close"],
        window=structure_window, look_left=look_left, look_right=look_right,
    ).to_numpy()
    result["mss_123"] = pd.Series(mss_values, index=result.index)
    return result


def add_black_box_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Add rule-based ``bb_signal`` confluence signals (1/-1/0)."""
    result = df.copy()
    for col in ("bullish_ob_level", "bearish_ob_level", "bullish_fvg_low", "bearish_fvg_high"):
        if col not in result.columns:
            raise ValueError(f"add_black_box_signals requires column {col!r}; run ICT builders first.")
    result["bb_signal"] = 0.0
    bullish = (result["Close"] > result["bullish_ob_level"]) & (
        result["bullish_fvg_low"].notna() & (result["bullish_fvg_low"] < result["Close"])
    )
    bearish = (result["Close"] < result["bearish_ob_level"]) & (
        result["bearish_fvg_high"].notna() & (result["bearish_fvg_high"] > result["Close"])
    )
    result.loc[bullish.fillna(False), "bb_signal"] = 1.0
    result.loc[bearish.fillna(False), "bb_signal"] = -1.0
    return result


# ---------------------------------------------------------------------------
# Shared classic indicators
# ---------------------------------------------------------------------------
def _add_classic_indicators(result: pd.DataFrame) -> pd.DataFrame:
    close = result["Close"]
    high, low, volume = result["High"], result["Low"], result["Volume"]
    result["sma_10"] = close.rolling(10).mean()
    result["sma_20"] = close.rolling(20).mean()
    result["sma_50"] = close.rolling(50).mean()
    result["ema_12"] = close.ewm(span=12, adjust=False).mean()
    result["ema_26"] = close.ewm(span=26, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    result["rsi_14"] = 100 - (100 / (1 + rs))
    result["macd"] = result["ema_12"] - result["ema_26"]
    result["macd_signal"] = result["macd"].ewm(span=9, adjust=False).mean()
    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    result["bb_mid"] = mid
    result["bb_upper"] = mid + 2 * std
    result["bb_lower"] = mid - 2 * std
    result["bb_width"] = (result["bb_upper"] - result["bb_lower"]) / mid
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    result["atr_14"] = tr.rolling(14).mean()
    result["volatility_20"] = close.pct_change().rolling(20).std() * np.sqrt(252)
    result["volume_change"] = volume.replace(0, np.nan).pct_change()
    return result


def _sanitize(result: pd.DataFrame) -> pd.DataFrame:
    with pd.option_context("future.no_silent_downcasting", True):
        return result.replace([np.inf, -np.inf], np.nan).infer_objects(copy=False)


def add_ict_smc_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add classic indicators + ICT/SMC + black-box signals."""
    _require_ohlcv(df)
    result = _add_classic_indicators(df.copy())
    high, low, close = result["High"], result["Low"], result["Close"]
    open_ = result["Open"]
    for block in (
        _find_order_blocks(high, low, close, open_),
        _find_fvgs(high, low, close),
        _detect_liquidity_sweeps(high, low, close),
    ):
        block.index = result.index
        result = result.join(block, how="left")
    result = add_market_structure(result)
    result = add_black_box_signals(result)
    return _sanitize(result)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Legacy classic-only feature engineering (backwards compatible)."""
    _require_ohlcv(df)
    return _sanitize(_add_classic_indicators(df.copy()))


FEATURE_COLUMNS = [
    "sma_10", "sma_20", "sma_50", "ema_12", "ema_26",
    "rsi_14", "macd", "macd_signal", "bb_mid", "bb_upper",
    "bb_lower", "bb_width", "atr_14", "volatility_20", "volume_change",
]

FULL_FEATURE_COLUMNS = FEATURE_COLUMNS + [
    "bullish_ob_level", "bearish_ob_level",
    "bullish_fvg_low", "bullish_fvg_high",
    "bearish_fvg_low", "bearish_fvg_high",
    "sweep_high", "sweep_low",
    "mss_123", "bb_signal",
]
