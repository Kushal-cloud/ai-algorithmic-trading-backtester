# AI-Powered Algorithmic Trading Strategy Backtester

A modular Python application for historical-market-data ingestion, technical-feature engineering, ML-based signal generation, backtesting, risk metrics, and an interactive Streamlit dashboard.

> This project is a research/backtesting system. It is not financial advice and does not execute live trades.

## Architecture

```text
Market Data (yfinance)
        |
        v
Data Loader --> Feature Engineering --> ML Signal Model
                                      |
                                      v
                               Backtest Engine
                                      |
                              +-------+-------+
                              |               |
                              v               v
                         Risk Metrics     Trade Log
                              |               |
                              +-------+-------+
                                      |
                                      v
                              Streamlit Dashboard
```

## Repository structure

```text
ai_algorithmic_trading_backtester/
├── app/
│   ├── __init__.py
│   ├── dashboard.py
│   ├── config.py
│   ├── data/
│   │   ├── __init__.py
│   │   └── market_data.py
│   ├── features/
│   │   ├── __init__.py
│   │   └── technical.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── signal_model.py
│   ├── backtest/
│   │   ├── __init__.py
│   │   └── engine.py
│   ├── risk/
│   │   ├── __init__.py
│   │   └── metrics.py
│   └── pipeline.py
├── tests/
│   ├── test_features.py
│   └── test_backtest.py
├── scripts/
│   └── train.py
├── data/.gitkeep
├── models/.gitkeep
├── outputs/.gitkeep
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ingress.yaml
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
├── Jenkinsfile
├── .dockerignore
├── .gitignore
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/train.py --ticker AAPL --period 5y
streamlit run app/dashboard.py
```

Open `http://localhost:8501`.

## Docker

```bash
docker build -t ai-trading-backtester:latest .
docker run --rm -p 8501:8501 ai-trading-backtester:latest
```

Or:

```bash
docker compose up --build
```

## Kubernetes

Build/push the image to your registry and update the image reference in `k8s/deployment.yaml`.

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl -n trading get pods
```

For a local cluster such as Minikube:

```bash
minikube addons enable ingress
kubectl -n trading port-forward svc/trading-dashboard 8501:8501
```

## Jenkins

The included `Jenkinsfile` implements:

1. Checkout
2. Python dependency installation
3. Unit tests
4. Docker image build
5. Docker registry push
6. Kubernetes deployment

Configure these Jenkins credentials/environment values:

- `DOCKER_REGISTRY`
- `DOCKER_IMAGE`
- Docker registry credentials with ID `docker-registry`
- Kubernetes kubeconfig with ID `kubeconfig`

The Kubernetes deployment is deliberately separated from application configuration so secrets and infrastructure settings are not committed.

## GitHub

Push the repository:

```bash
git init
git add .
git commit -m "Initial trading backtester"
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

GitHub Actions runs tests and builds the Docker image on pushes and pull requests.

## ML methodology

The default model is XGBoost multiclass classification:

- `BUY`
- `HOLD`
- `SELL`

Features include:

- SMA 10 / 20 / 50
- EMA 12 / 26
- RSI
- MACD and signal
- Bollinger Bands
- ATR
- rolling volatility
- volume change

Labels are generated from a configurable forward-return threshold. The backtest intentionally applies signals to the next bar to reduce look-ahead bias.

## Risk metrics

The engine reports:

- Total return
- CAGR
- Sharpe ratio
- Sortino ratio
- Maximum drawdown
- Calmar ratio
- Win rate
- Profit factor
- Number of trades
- Final equity

## Important research caveats

Backtests can be misleading because of data revisions, survivorship bias, look-ahead leakage, transaction costs, slippage, regime changes, and overfitting. Before any real-world use, add walk-forward validation, realistic transaction-cost models, out-of-sample testing, and broker/execution simulation.
