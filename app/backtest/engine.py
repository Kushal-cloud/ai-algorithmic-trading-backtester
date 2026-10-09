"""Long-only backtest engine with risk exits and ICT regime filtering."""

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
    use_ict_filter: bool = True  # reject signals against the MSS regime
    liquidate_at_end: bool = True  # close any open position on the last bar


TRADE_COLUMNS = [
    "entry_time", "exit_time", "side", "entry_price",
    "exit_price", "shares", "pnl", "reason",
]


def run_backtest(df: pd.DataFrame, signals: pd.Series, config: BacktestConfig):
    """Run a long-only backtest.

    Notes
    -----
    * Only ``+1`` (BUY) signals open positions; ``-1`` (SELL) signals are
      ignored by design (no shorting) and documented as such.
    * Positions exit on stop-loss / take-profit; optionally any open position
      is liquidated on the final bar so equity and trades stay consistent.
    """
    if df.empty:
        raise ValueError("Backtest DataFrame is empty.")
    if "Close" not in df.columns:
        raise ValueError("Backtest DataFrame requires a 'Close' column.")
    data = df.copy()
    data["signal"] = signals.reindex(data.index).fillna(0).astype(int)

    if config.use_ict_filter and "mss_123" in data.columns:
        mss = data["mss_123"]
        data["signal"] = np.where(
            (mss == 1) & (data["signal"] == -1),
            0,
            np.where((mss == -1) & (data["signal"] == 1), 0, data["signal"]),
        )

    cash = float(config.initial_capital)
    shares = 0.0
    entry_price: float | None = None
    entry_time = None
    timestamps: list = []
    equity_values: list[float] = []
    trades: list[dict] = []
    cost_rate = (config.transaction_cost_bps + config.slippage_bps) / 10_000

    def _close(timestamp, price: float, reason: str) -> None:
        nonlocal cash, shares, entry_price, entry_time
        if shares == 0 or entry_price is None:
            return
        proceeds = shares * price
        cost = abs(proceeds) * cost_rate
        cash += proceeds - cost
        pnl = shares * (price - entry_price) - cost
        trades.append(
            {
                "entry_time": entry_time,
                "exit_time": timestamp,
                "side": "LONG",
                "entry_price": entry_price,
                "exit_price": price,
                "shares": abs(shares),
                "pnl": pnl,
                "reason": reason,
            }
        )
        shares = 0.0
        entry_price = None
        entry_time = None

    for timestamp, row in data.iterrows():
        price = row["Close"]
        if pd.isna(price):
            timestamps.append(timestamp)
            equity_values.append(cash + shares * (entry_price or 0.0))
            continue
        price = float(price)
        signal = int(row["signal"])

        if shares != 0 and entry_price is not None:
            pnl_pct = (price - entry_price) / entry_price
            if pnl_pct <= -config.stop_loss_pct or pnl_pct >= config.take_profit_pct:
                _close(timestamp, price, "risk_exit")

        if shares == 0 and signal > 0:
            risk_budget = cash * config.risk_per_trade
            stop_distance = max(price * config.stop_loss_pct, 1e-8)
            quantity = max(risk_budget / stop_distance, 0.0)
            quantity = min(quantity, cash / price) if price > 0 else 0.0
            if quantity > 0:
                entry_cost = quantity * price
                fee = entry_cost * cost_rate
                if entry_cost + fee <= cash:
                    shares = quantity
                    entry_price = price * (1 + cost_rate)
                    entry_time = timestamp
                    cash -= entry_cost + fee

        timestamps.append(timestamp)
        equity_values.append(cash + shares * price)

    if config.liquidate_at_end and shares != 0 and entry_price is not None:
        last_ts = timestamps[-1] if timestamps else data.index[-1]
        last_price = float(data["Close"].iloc[-1])
        _close(last_ts, last_price, "eod_liquidation")

    equity = pd.Series(equity_values, index=pd.Index(timestamps), name="equity").sort_index()
    trades_df = pd.DataFrame(trades, columns=TRADE_COLUMNS) if trades else pd.DataFrame(columns=TRADE_COLUMNS)
    return equity, trades_df
