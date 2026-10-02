from __future__ import annotations
from app.data.market_data import download_ohlcv
from app.features.technical import add_features
from app.models.signal_model import SignalModel
from app.backtest.engine import BacktestConfig, run_backtest
from app.risk.metrics import performance_metrics

def execute(ticker: str, period: str, capital: float = 100_000):
    raw = download_ohlcv(ticker, period)
    featured = add_features(raw)

    split = int(len(featured) * 0.70)
    train = featured.iloc[:split].copy()
    test = featured.iloc[split:].copy()

    model = SignalModel().fit(train)
    signals = model.predict(test)

    equity, trades = run_backtest(
        test,
        signals,
        BacktestConfig(initial_capital=capital),
    )
    metrics = performance_metrics(equity, trades)
    return test, equity, trades, metrics, model
