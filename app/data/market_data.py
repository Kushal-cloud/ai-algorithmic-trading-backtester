from __future__ import annotations
import pandas as pd
import yfinance as yf

def download_ohlcv(ticker: str, period: str = "5y", interval: str = "1d") -> pd.DataFrame:
    df = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
    )
    if df.empty:
        raise ValueError(f"No market data returned for ticker={ticker!r}.")
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    return df[required].dropna().copy()
