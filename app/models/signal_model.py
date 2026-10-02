from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import joblib
import pandas as pd
from xgboost import XGBClassifier
from app.features.technical import FEATURE_COLUMNS

LABEL_MAP = {-1: "SELL", 0: "HOLD", 1: "BUY"}

@dataclass
class SignalModel:
    model: XGBClassifier | None = None

    def fit(self, df: pd.DataFrame, horizon: int = 5, threshold: float = 0.01) -> "SignalModel":
        x = df.copy()
        future_return = x["Close"].shift(-horizon) / x["Close"] - 1
        x["target"] = 0
        x.loc[future_return > threshold, "target"] = 1
        x.loc[future_return < -threshold, "target"] = -1
        x = x.dropna(subset=FEATURE_COLUMNS + ["target"])

        self.model = XGBClassifier(
            n_estimators=250,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            objective="multi:softmax",
            num_class=3,
            eval_metric="mlogloss",
            random_state=42,
        )
        # XGBoost classes must be non-negative contiguous integers.
        self.model.fit(x[FEATURE_COLUMNS], x["target"].map({-1: 0, 0: 1, 1: 2}))
        return self

    def predict(self, df: pd.DataFrame) -> pd.Series:
        if self.model is None:
            raise RuntimeError("Model has not been fitted.")
        x = df.dropna(subset=FEATURE_COLUMNS).copy()
        raw = self.model.predict(x[FEATURE_COLUMNS]).astype(int)
        inverse = {0: -1, 1: 0, 2: 1}
        return pd.Series(raw, index=x.index).map(inverse).rename("signal")

    def save(self, path: str | Path) -> None:
        if self.model is None:
            raise RuntimeError("Cannot save an unfitted model.")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)

    def load(self, path: str | Path) -> "SignalModel":
        self.model = joblib.load(path)
        return self
