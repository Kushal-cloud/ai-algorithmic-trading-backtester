from __future__ import annotations
import numpy as np
import pandas as pd

def performance_metrics(equity: pd.Series, trades: pd.DataFrame) -> dict:
    equity = equity.dropna()
    if len(equity) < 2:
        return {}

    daily = equity.pct_change().dropna()
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1 / 365.25)
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1

    sharpe = np.sqrt(252) * daily.mean() / daily.std() if daily.std() > 0 else 0.0
    downside = daily[daily < 0].std()
    sortino = np.sqrt(252) * daily.mean() / downside if downside and downside > 0 else 0.0

    peak = equity.cummax()
    drawdown = equity / peak - 1
    max_dd = drawdown.min()

    wins = trades.loc[trades["pnl"] > 0, "pnl"].sum() if not trades.empty else 0
    losses = -trades.loc[trades["pnl"] < 0, "pnl"].sum() if not trades.empty else 0
    win_rate = (trades["pnl"] > 0).mean() if not trades.empty else 0
    profit_factor = wins / losses if losses > 0 else float("inf") if wins > 0 else 0

    return {
        "Total Return": float(total_return),
        "CAGR": float(cagr),
        "Sharpe Ratio": float(sharpe),
        "Sortino Ratio": float(sortino),
        "Max Drawdown": float(max_dd),
        "Win Rate": float(win_rate),
        "Profit Factor": float(profit_factor),
        "Trades": int(len(trades)),
        "Final Equity": float(equity.iloc[-1]),
    }
