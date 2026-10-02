import pandas as pd
from app.backtest.engine import BacktestConfig, run_backtest

def test_backtest_returns_equity():
    idx = pd.date_range("2025-01-01", periods=10)
    prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
    df = pd.DataFrame({
        "Open": prices, "High": [p+1 for p in prices],
        "Low": [p-1 for p in prices], "Close": prices,
        "Volume": [1000] * 10
    }, index=idx)
    signals = pd.Series([0, 1, 0, 0, 0, 0, 0, 0, 0, 0], index=idx)
    equity, trades = run_backtest(df, signals, BacktestConfig())
    assert len(equity) == 10
    assert equity.iloc[0] > 0
