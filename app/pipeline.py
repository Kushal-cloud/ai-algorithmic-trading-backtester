"""End-to-end pipeline: data -> ICT/SMC features -> model -> backtest -> metrics."""

from __future__ import annotations

from app.backtest.engine import BacktestConfig, run_backtest
from app.config import settings
from app.data.market_data import download_ohlcv
from app.features.technical import add_ict_smc_features
from app.models.signal_model import SignalModel
from app.risk.metrics import performance_metrics

MIN_ROWS = 60


def execute(
    ticker: str,
    period: str = "5y",
    capital: float = 100_000,
    asset_class: str = "us_stocks",
    use_ict_filter: bool = True,
    stop_loss_pct: float | None = None,
    take_profit_pct: float | None = None,
    train_fraction: float | None = None,
    label_horizon: int | None = None,
    label_threshold: float | None = None,
):
    """Run the full research pipeline.

    Returns ``(featured, equity, trades, metrics, model)`` where *featured* is
    the full feature frame (train + test) and the backtest covers the test
    slice only.
    """
    if not ticker or not ticker.strip():
        raise ValueError("Ticker symbol must not be empty.")
    if capital is None or capital <= 0:
        raise ValueError("Capital must be positive.")
    frac = settings.train_fraction if train_fraction is None else train_fraction
    if not 0.0 < frac < 1.0:
        raise ValueError("train_fraction must be in (0, 1).")

    raw = download_ohlcv(ticker.strip().upper(), period, asset_class=asset_class)
    if len(raw) < MIN_ROWS:
        raise ValueError(
            f"Only {len(raw)} rows for {ticker!r}; need at least {MIN_ROWS} "
            "for indicator warmup."
        )
    featured = add_ict_smc_features(raw)

    split = int(len(featured) * frac)
    if split < 30 or len(featured) - split < 10:
        raise ValueError("Not enough rows to split into train/test sets.")
    train = featured.iloc[:split].copy()
    test = featured.iloc[split:].copy()

    model = SignalModel().fit(
        train,
        horizon=settings.label_horizon if label_horizon is None else label_horizon,
        threshold=settings.label_threshold if label_threshold is None else label_threshold,
    )
    signals = model.predict(test)

    config = BacktestConfig(
        initial_capital=capital,
        risk_per_trade=settings.risk_per_trade,
        transaction_cost_bps=settings.transaction_cost_bps,
        slippage_bps=settings.slippage_bps,
        stop_loss_pct=settings.stop_loss_pct if stop_loss_pct is None else stop_loss_pct,
        take_profit_pct=settings.take_profit_pct if take_profit_pct is None else take_profit_pct,
        use_ict_filter=use_ict_filter,
    )
    equity, trades = run_backtest(test, signals, config)
    metrics = performance_metrics(equity, trades)
    return featured, equity, trades, metrics, model
