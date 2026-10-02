import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    default_ticker: str = os.getenv("DEFAULT_TICKER", "AAPL")
    default_period: str = os.getenv("DEFAULT_PERIOD", "5y")
    initial_capital: float = float(os.getenv("INITIAL_CAPITAL", "100000"))
    risk_per_trade: float = float(os.getenv("RISK_PER_TRADE", "0.01"))
    transaction_cost_bps: float = float(os.getenv("TRANSACTION_COST_BPS", "5"))
    slippage_bps: float = float(os.getenv("SLIPPAGE_BPS", "2"))

settings = Settings()
