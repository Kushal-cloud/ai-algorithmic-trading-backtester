"""Train and persist a SignalModel for a ticker."""

import argparse
from pathlib import Path

from app.config import settings
from app.data.market_data import download_ohlcv
from app.features.technical import add_ict_smc_features
from app.models.signal_model import SignalModel
from app.risk.metrics import performance_metrics
from app.backtest.engine import BacktestConfig, run_backtest


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the VSEC signal model.")
    parser.add_argument("--ticker", default=settings.default_ticker)
    parser.add_argument("--period", default=settings.default_period)
    parser.add_argument("--asset-class", default=settings.default_asset_class)
    parser.add_argument("--output", default="models/signal_model.joblib")
    args = parser.parse_args()

    raw = download_ohlcv(args.ticker.strip().upper(), args.period, asset_class=args.asset_class)
    featured = add_ict_smc_features(raw)
    split = int(len(featured) * settings.train_fraction)
    train, test = featured.iloc[:split].copy(), featured.iloc[split:].copy()

    model = SignalModel().fit(train, horizon=settings.label_horizon, threshold=settings.label_threshold)
    signals = model.predict(test)
    equity, trades = run_backtest(test, signals, BacktestConfig(use_ict_filter=settings.use_ict_filter))
    metrics = performance_metrics(equity, trades)
    model.save(args.output)
    print(f"Saved model to {Path(args.output).resolve()}")
    print(f"Test slice: {len(test)} bars, {len(trades)} trades, return={metrics['Total Return']:.2%}")


if __name__ == "__main__":
    main()
