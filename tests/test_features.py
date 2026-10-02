import numpy as np
import pandas as pd
from app.features.technical import add_features, FEATURE_COLUMNS

def test_feature_engineering():
    n = 100
    idx = pd.date_range("2025-01-01", periods=n)
    close = pd.Series(np.linspace(100, 120, n), index=idx)
    df = pd.DataFrame({
        "Open": close,
        "High": close + 1,
        "Low": close - 1,
        "Close": close,
        "Volume": np.full(n, 1000),
    }, index=idx)
    result = add_features(df)
    assert all(c in result.columns for c in FEATURE_COLUMNS)
    assert len(result) == n
