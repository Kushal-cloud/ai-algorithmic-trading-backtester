import argparse
from pathlib import Path

from app.data.market_data import download_ohlcv
from app.features.technical import add_features
from app.models.signal_model import SignalModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--period", default="5y")
    parser.add_argument("--output", default="models/signal_model.joblib")
    args = parser.parse_args()

    df = add_features(
        download_ohlcv(
            args.ticker,
            args.period,
        )
    )

    model = SignalModel().fit(df)
    model.save(args.output)

    print(f"Saved model to {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()