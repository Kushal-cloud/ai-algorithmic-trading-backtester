"""Application configuration loaded from environment variables.

All parsing is defensive: empty or malformed values fall back to safe
defaults instead of raising at import time.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _get_str(name: str, default: str) -> str:
    value = os.getenv(name, default)
    if value is None or not str(value).strip():
        return default
    return str(value).strip()


def _get_float(name: str, default: float) -> float:
    try:
        raw = os.getenv(name, None)
        if raw is None or not str(raw).strip():
            return default
        return float(raw)
    except (TypeError, ValueError):
        return default


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, None)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


VALID_ASSET_CLASSES = ("us_stocks", "crypto", "forex", "cfds")
VALID_PERIODS = ("1y", "2y", "5y", "10y")


@dataclass(frozen=True)
class Settings:
    default_ticker: str = field(default="AAPL")
    default_period: str = field(default="5y")
    default_asset_class: str = field(default="us_stocks")
    initial_capital: float = field(default=100_000.0)
    risk_per_trade: float = field(default=0.01)
    transaction_cost_bps: float = field(default=5.0)
    slippage_bps: float = field(default=2.0)
    stop_loss_pct: float = field(default=0.02)
    take_profit_pct: float = field(default=0.04)
    use_ict_filter: bool = field(default=True)
    train_fraction: float = field(default=0.70)
    label_horizon: int = field(default=5)
    label_threshold: float = field(default=0.01)

    def __post_init__(self) -> None:
        if self.default_period not in VALID_PERIODS:
            object.__setattr__(self, "default_period", "5y")
        if self.default_asset_class not in VALID_ASSET_CLASSES:
            object.__setattr__(self, "default_asset_class", "us_stocks")
        if not 0.0 < self.train_fraction < 1.0:
            object.__setattr__(self, "train_fraction", 0.70)
        if self.initial_capital <= 0:
            object.__setattr__(self, "initial_capital", 100_000.0)
        if not 0.0 < self.risk_per_trade <= 1.0:
            object.__setattr__(self, "risk_per_trade", 0.01)


def load_settings() -> Settings:
    """Build Settings from the current environment."""
    return Settings(
        default_ticker=_get_str("DEFAULT_TICKER", "AAPL").upper(),
        default_period=_get_str("DEFAULT_PERIOD", "5y"),
        default_asset_class=_get_str("DEFAULT_ASSET_CLASS", "us_stocks").lower(),
        initial_capital=_get_float("INITIAL_CAPITAL", 100_000.0),
        risk_per_trade=_get_float("RISK_PER_TRADE", 0.01),
        transaction_cost_bps=_get_float("TRANSACTION_COST_BPS", 5.0),
        slippage_bps=_get_float("SLIPPAGE_BPS", 2.0),
        stop_loss_pct=_get_float("STOP_LOSS_PCT", 0.02),
        take_profit_pct=_get_float("TAKE_PROFIT_PCT", 0.04),
        use_ict_filter=_get_bool("USE_ICT_FILTER", True),
        train_fraction=_get_float("TRAIN_FRACTION", 0.70),
        label_horizon=int(_get_float("LABEL_HORIZON", 5)),
        label_threshold=_get_float("LABEL_THRESHOLD", 0.01),
    )


settings = load_settings()
