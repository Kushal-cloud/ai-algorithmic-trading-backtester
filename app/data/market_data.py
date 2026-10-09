"""Market-data downloading with multi-asset ticker handling."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import yfinance as yf

OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


@dataclass
class AssetClass:
    """Ticker conventions for one asset class."""

    name: str
    suffixes: dict[str, str] = field(default_factory=dict)
    auto_usd_suffix: str = ""
    auto_suffix: str = ""

    def format_ticker(self, symbol: str) -> str:
        """Map a user symbol to a yfinance-compatible ticker."""
        clean = symbol.strip().upper()
        if not clean:
            raise ValueError("Ticker symbol must not be empty.")
        if clean in self.suffixes:
            return self.suffixes[clean]
        # Already fully qualified (e.g. BTC-USD, EURUSD=X)? Keep as-is.
        if "-" in clean or "=" in clean or "." in clean:
            return clean
        if self.auto_usd_suffix and clean.isalpha():
            return f"{clean}{self.auto_usd_suffix}"
        if self.auto_suffix:
            return f"{clean}{self.auto_suffix}"
        return clean


ASSET_CLASSES: dict[str, AssetClass] = {
    "us_stocks": AssetClass(name="US Stocks"),
    "crypto": AssetClass(
        name="Crypto",
        suffixes={"BTC": "BTC-USD", "ETH": "ETH-USD"},
        auto_usd_suffix="-USD",
    ),
    "forex": AssetClass(
        name="Forex",
        suffixes={
            "EURUSD": "EURUSD=X",
            "GBPUSD": "GBPUSD=X",
            "USDJPY": "USDJPY=X",
        },
        auto_suffix="=X",
    ),
    "cfds": AssetClass(name="CFDs"),
}

DEFAULT_ASSET_CLASS = "us_stocks"


def get_asset_class(class_name: str | None = None) -> AssetClass:
    """Return the AssetClass for *class_name*, falling back to the default."""
    name = (class_name or DEFAULT_ASSET_CLASS).strip().lower()
    return ASSET_CLASSES.get(name, ASSET_CLASSES[DEFAULT_ASSET_CLASS])


def download_ohlcv(
    ticker: str,
    period: str = "5y",
    interval: str = "1d",
    asset_class: str | None = None,
) -> pd.DataFrame:
    """Download clean OHLCV data for *ticker*.

    The returned frame contains exactly the ``OHLCV_COLUMNS`` columns with a
    ``DatetimeIndex``.  No metadata columns are attached, so the frame can be
    passed straight into feature engineering.
    """
    if not ticker or not ticker.strip():
        raise ValueError("Ticker symbol must not be empty.")
    asset = get_asset_class(asset_class)
    formatted_ticker = asset.format_ticker(ticker)

    df = yf.download(
        formatted_ticker,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
    )
    if df is None or df.empty:
        raise ValueError(
            f"No market data returned for ticker={ticker!r} "
            f"(formatted: {formatted_ticker!r})."
        )
    # yfinance returns MultiIndex columns when downloading a single ticker
    # with newer versions; flatten them deterministically.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns {missing} for ticker={ticker!r}.")

    result = df[OHLCV_COLUMNS].copy()
    result.index = pd.to_datetime(result.index)
    result = result.sort_index()
    # Only require OHLC to be present; Volume can be missing/zero for FX.
    result = result.dropna(subset=["Open", "High", "Low", "Close"])
    if "Volume" in result.columns:
        result["Volume"] = result["Volume"].fillna(0)
    if result.empty:
        raise ValueError(f"No usable OHLCV rows for ticker={ticker!r}.")
    return result
