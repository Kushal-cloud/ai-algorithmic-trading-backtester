import numpy as np
import pandas as pd
import pytest

from app.backtest.engine import BacktestConfig, run_backtest
from app.data.market_data import ASSET_CLASSES, get_asset_class
from app.features.technical import (
    FEATURE_COLUMNS,
    FULL_FEATURE_COLUMNS,
    add_black_box_signals,
    add_features,
    add_ict_smc_features,
    add_market_structure,
)
from app.models.signal_model import SignalModel
from app.risk.metrics import performance_metrics


def _ohlcv(n=100, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2025-01-01", periods=n, freq="D")
    close = pd.Series(np.linspace(100, 120, n) + rng.normal(0, 0.5, n), index=idx)
    return pd.DataFrame(
        {
            "Open": close - 0.2,
            "High": close + 1,
            "Low": close - 1,
            "Close": close,
            "Volume": np.full(n, 1000.0),
        },
        index=idx,
    )


def test_feature_engineering():
    df = _ohlcv()
    result = add_features(df)
    assert all(c in result.columns for c in FEATURE_COLUMNS)
    assert len(result) == len(df)


def test_ict_smc_features_present():
    df = _ohlcv(120)
    result = add_ict_smc_features(df)
    for col in FULL_FEATURE_COLUMNS:
        assert col in result.columns, f"missing {col}"
    assert result["mss_123"].notna().sum() > 0
    assert set(result["bb_signal"].dropna().unique()) <= {-1.0, 0.0, 1.0}
    assert len(result) == len(df)


def test_market_structure_values():
    result = add_market_structure(_ohlcv(60))
    assert set(result["mss_123"].unique()) <= {-1, 0, 1}


def test_black_box_requires_ict_columns():
    with pytest.raises(ValueError):
        add_black_box_signals(_ohlcv(30))


def test_backtest_returns_equity():
    idx = pd.date_range("2025-01-01", periods=10)
    prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
    df = pd.DataFrame({
        "Open": prices, "High": [p + 1 for p in prices],
        "Low": [p - 1 for p in prices], "Close": prices,
        "Volume": [1000] * 10,
    }, index=idx)
    signals = pd.Series([0, 1, 0, 0, 0, 0, 0, 0, 0, 0], index=idx)
    equity, trades = run_backtest(df, signals, BacktestConfig())
    assert len(equity) == 10
    assert equity.iloc[0] > 0


def test_backtest_liquidates_open_position():
    idx = pd.date_range("2025-01-01", periods=10)
    prices = list(range(100, 110))
    df = pd.DataFrame({
        "Open": prices, "High": [p + 1 for p in prices],
        "Low": [p - 1 for p in prices], "Close": prices,
        "Volume": [1000] * 10,
    }, index=idx)
    signals = pd.Series([0, 1, 0, 0, 0, 0, 0, 0, 0, 0], index=idx)
    cfg = BacktestConfig(stop_loss_pct=0.99, take_profit_pct=0.99)
    _, trades = run_backtest(df, signals, cfg)
    assert not trades.empty
    assert trades.iloc[0]["reason"] == "eod_liquidation"


def test_backtest_ict_filter_blocks_counter_trend():
    idx = pd.date_range("2025-01-01", periods=6)
    df = pd.DataFrame({
        "Open": [100] * 6, "High": [101] * 6, "Low": [99] * 6,
        "Close": [100] * 6, "Volume": [1000] * 6, "mss_123": [1] * 6,
    }, index=idx)
    signals = pd.Series([-1] * 6, index=idx)  # shorts in uptrend
    _, trades = run_backtest(df, signals, BacktestConfig(use_ict_filter=True))
    assert trades.empty  # engine is long-only + filter blocks shorts in uptrend


def test_signal_model_fit_predict_real_labels():
    df = add_ict_smc_features(_ohlcv(200))
    split = int(len(df) * 0.7)
    model = SignalModel().fit(df.iloc[:split])
    assert model.feature_names_, "model must record training features"
    preds = model.predict(df.iloc[split:])
    assert len(preds) == len(df) - split
    assert set(preds.unique()) <= {-1, 0, 1}


def test_signal_model_save_load(tmp_path):
    df = add_ict_smc_features(_ohlcv(200))
    model = SignalModel().fit(df.iloc[:140])
    path = tmp_path / "m.joblib"
    model.save(path)
    preds_before = model.predict(df.iloc[140:145])
    loaded = SignalModel().load(path)
    pd.testing.assert_series_equal(loaded.predict(df.iloc[140:145]), preds_before)


def test_metrics_always_full_dict():
    empty_eq = pd.Series(dtype=float)
    m = performance_metrics(empty_eq, pd.DataFrame())
    assert m["Trades"] == 0 and m["Final Equity"] == 0.0
    idx = pd.date_range("2025-01-01", periods=5)
    eq = pd.Series([100, 101, 102, 101, 103], index=idx)
    trades = pd.DataFrame([{"pnl": 10.0}, {"pnl": -5.0}])
    m2 = performance_metrics(eq, trades)
    assert m2["Trades"] == 2 and m2["Calmar Ratio"] >= 0


def test_asset_ticker_formatting():
    assert get_asset_class("crypto").format_ticker("BTC") == "BTC-USD"
    assert get_asset_class("crypto").format_ticker("SOL") == "SOL-USD"
    assert get_asset_class("forex").format_ticker("EURUSD") == "EURUSD=X"
    assert get_asset_class("forex").format_ticker("AUDCAD") == "AUDCAD=X"
    assert get_asset_class("us_stocks").format_ticker("aapl") == "AAPL"
    assert set(ASSET_CLASSES) == {"us_stocks", "crypto", "forex", "cfds"}
