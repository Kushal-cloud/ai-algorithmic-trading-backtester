from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass
class BacktestConfig:
    initial_capital: float = 100_000
    risk_per_trade: float = 0.01
    transaction_cost_bps: float = 5
    slippage_bps: float = 2
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04

def run_backtest(df: pd.DataFrame, signals: pd.Series, config: BacktestConfig):
    data = df.copy()
    data["signal"] = signals.reindex(data.index).fillna(0).astype(int)

    cash = config.initial_capital
    shares = 0.0
    entry_price = None
    equity_values = []
    trades = []

    cost_rate = (config.transaction_cost_bps + config.slippage_bps) / 10_000

    for timestamp, row in data.iterrows():
        price = float(row["Close"])
        signal = int(row["signal"])

        if shares != 0 and entry_price is not None:
            pnl_pct = (price - entry_price) / entry_price * np.sign(shares)
            if pnl_pct <= -config.stop_loss_pct or pnl_pct >= config.take_profit_pct:
                side = np.sign(shares)
                cash += shares * price
                cash -= abs(shares * price) * cost_rate
                pnl = shares * (price - entry_price) - abs(shares * price) * cost_rate
                trades.append({
                    "entry_time": entry_time,
                    "exit_time": timestamp,
                    "side": "LONG" if side > 0 else "SHORT",
                    "entry_price": entry_price,
                    "exit_price": price,
                    "shares": abs(shares),
                    "pnl": pnl,
                    "reason": "risk_exit",
                })
                shares = 0
                entry_price = None

        if shares == 0 and signal != 0:
            risk_budget = cash * config.risk_per_trade
            stop_distance = max(price * config.stop_loss_pct, 1e-8)
            quantity = max(risk_budget / stop_distance, 0)
            quantity = min(quantity, cash / price) if signal > 0 else 0
            if quantity > 0:
                shares = quantity if signal > 0 else 0
                entry_price = price * (1 + cost_rate)
                entry_time = timestamp
                cash -= quantity * price
                cash -= quantity * price * cost_rate

        equity_values.append((timestamp, cash + shares * price))

    equity = pd.Series(dict(equity_values), name="equity")
    trades_df = pd.DataFrame(trades)
    return equity, trades_df
