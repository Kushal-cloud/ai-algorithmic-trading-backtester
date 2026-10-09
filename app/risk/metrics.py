"""Risk / performance metrics for backtest equity curves."""

from __future__ import annotations

import numpy as np
import pandas as pd

METRIC_KEYS = [
    "Total Return",
    "CAGR",
    "Sharpe Ratio",
    "Sortino Ratio",
    "Max Drawdown",
    "Calmar Ratio",
    "Win Rate",
    "Profit Factor",
    "Trades",
    "Final Equity",
]

_MAX_PROFIT_FACTOR = 1_000.0


def _empty_metrics() -> dict:
    return {
        "Total Return": 0.0,
        "CAGR": 0.0,
        "Sharpe Ratio": 0.0,
        "Sortino Ratio": 0.0,
        "Max Drawdown": 0.0,
        "Calmar Ratio": 0.0,
        "Win Rate": 0.0,
        "Profit Factor": 0.0,
        "Trades": 0,
        "Final Equity": 0.0,
    }


def performance_metrics(equity: pd.Series, trades: pd.DataFrame) -> dict:
    """Compute performance metrics; never raises on thin/empty input."""
    metrics = _empty_metrics()
    if equity is None or len(equity.dropna()) < 2:
        if equity is not None and len(equity.dropna()) == 1:
            metrics["Final Equity"] = float(equity.dropna().iloc[-1])
        if trades is not None and not trades.empty:
            metrics["Trades"] = int(len(trades))
        return metrics

    equity = equity.dropna().sort_index()
    daily = equity.pct_change().dropna()
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    days = max((equity.index[-1] - equity.index[0]).days, 1)
    years = days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1

    vol = daily.std()
    sharpe = float(np.sqrt(252) * daily.mean() / vol) if vol and vol > 0 else 0.0
    downside = daily[daily < 0].std()
    sortino = float(np.sqrt(252) * daily.mean() / downside) if downside and downside > 0 else 0.0

    peak = equity.cummax()
    max_dd = float((equity / peak - 1).min())
    calmar = float(cagr / abs(max_dd)) if max_dd < 0 else 0.0

    if trades is not None and not trades.empty and "pnl" in trades.columns:
        pnl = pd.to_numeric(trades["pnl"], errors="coerce").fillna(0)
        wins = pnl[pnl > 0].sum()
        losses = -pnl[pnl < 0].sum()
        win_rate = float((pnl > 0).mean())
        profit_factor = float(wins / losses) if losses > 0 else (_MAX_PROFIT_FACTOR if wins > 0 else 0.0)
        n_trades = int(len(trades))
    else:
        win_rate, profit_factor, n_trades = 0.0, 0.0, 0

    metrics.update(
        {
            "Total Return": float(total_return),
            "CAGR": float(cagr),
            "Sharpe Ratio": float(sharpe),
            "Sortino Ratio": float(sortino),
            "Max Drawdown": float(max_dd),
            "Calmar Ratio": float(calmar),
            "Win Rate": float(win_rate),
            "Profit Factor": float(min(profit_factor, _MAX_PROFIT_FACTOR)),
            "Trades": n_trades,
            "Final Equity": float(equity.iloc[-1]),
        }
    )
    return metrics
