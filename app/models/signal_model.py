"""XGBoost multiclass signal model (SELL/HOLD/BUY)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from app.features.technical import FEATURE_COLUMNS

LABEL_MAP = {-1: "SELL", 0: "HOLD", 1: "BUY"}
_TO_MODEL = {-1: 0, 0: 1, 1: 2}
_FROM_MODEL = {0: -1, 1: 0, 2: 1}


def _numeric_feature_columns(df: pd.DataFrame, exclude: set[str]) -> list[str]:
    return [
        c for c in df.columns
        if c not in exclude and pd.api.types.is_numeric_dtype(df[c])
    ]


@dataclass
class SignalModel:
    model: XGBClassifier | None = None
    feature_names_: list[str] = field(default_factory=list)
    num_class: int = 3
    label_to_index_: dict[int, int] = field(default_factory=dict)
    index_to_label_: dict[int, int] = field(default_factory=dict)

    def fit(self, df: pd.DataFrame, horizon: int = 5, threshold: float = 0.01) -> "SignalModel":
        if "Close" not in df.columns:
            raise ValueError("fit() requires a 'Close' column.")
        work = df.copy()
        future_return = work["Close"].shift(-horizon) / work["Close"] - 1
        work["target"] = 0
        work.loc[future_return > threshold, "target"] = 1
        work.loc[future_return < -threshold, "target"] = -1
        work = work.dropna(subset=["target"])
        if work.empty:
            raise ValueError("Not enough rows to build training labels.")

        feature_cols = _numeric_feature_columns(work, {"target"})
        if not feature_cols:
            feature_cols = [c for c in FEATURE_COLUMNS if c in work.columns]
        if not feature_cols:
            raise ValueError("No numeric feature columns available for training.")

        # Preserve labels BEFORE dropping non-feature columns (previous bug:
        # overwriting X dropped 'target' and the model trained on random labels).
        y_raw = work["target"].astype(int)
        X = work[feature_cols].copy()
        mask = X.notna().any(axis=1)
        X, y_raw = X.loc[mask], y_raw.loc[mask]
        if X.empty:
            raise ValueError("All feature rows are NaN; cannot train.")

        classes = sorted(int(v) for v in y_raw.unique())
        if len(classes) < 2:
            raise ValueError(
                f"Need at least 2 label classes to train, found {classes}. "
                "Try a smaller threshold or longer history."
            )
        # Remap only the classes actually present to 0..k-1 so XGBoost never
        # sees a gap (e.g. synthetic steady-uptrend data with no SELL class).
        self.label_to_index_ = {label: i for i, label in enumerate(classes)}
        self.index_to_label_ = {i: label for label, i in self.label_to_index_.items()}
        self.num_class = len(classes)
        self.feature_names_ = list(feature_cols)

        self.model = XGBClassifier(
            n_estimators=250,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            objective="multi:softmax",
            num_class=len(classes),
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
        )
        y = y_raw.map(self.label_to_index_)
        self.model.fit(X.fillna(0), y)
        return self

    def predict(self, df: pd.DataFrame) -> pd.Series:
        if self.model is None:
            raise RuntimeError("Model has not been fitted.")
        cols = self.feature_names_ or [c for c in FEATURE_COLUMNS if c in df.columns]
        if not cols:
            raise RuntimeError("No feature columns available for prediction.")
        X = df.reindex(columns=cols).fillna(0)
        raw = np.asarray(self.model.predict(X)).astype(int)
        mapping = self.index_to_label_ or _FROM_MODEL
        mapped = pd.Series(raw, index=df.index).map(mapping).fillna(0).astype(int)
        # Clamp to the known signal domain in case of stale models.
        return mapped.where(mapped.isin([-1, 0, 1]), 0).rename("signal")

    def save(self, path: str | Path) -> None:
        if self.model is None:
            raise RuntimeError("Cannot save an unfitted model.")
        payload = {
            "model": self.model,
            "feature_names": self.feature_names_,
            "num_class": self.num_class,
            "label_to_index": self.label_to_index_,
            "index_to_label": self.index_to_label_,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(payload, path)

    def load(self, path: str | Path) -> "SignalModel":
        payload = joblib.load(path)
        if isinstance(payload, dict) and "model" in payload:
            self.model = payload["model"]
            self.feature_names_ = list(payload.get("feature_names", []))
            self.num_class = int(payload.get("num_class", 3))
            self.label_to_index_ = dict(payload.get("label_to_index", {}))
            self.index_to_label_ = {int(k): int(v) for k, v in payload.get("index_to_label", {}).items()}
        else:  # backwards compatible with bare-model files
            self.model = payload
            self.feature_names_ = []
            self.num_class = 3
            self.label_to_index_ = {}
            self.index_to_label_ = {}
        return self
