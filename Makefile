.PHONY: install test train run docker-build docker-run compose-up

install:
	python -m pip install -r requirements.txt

test:
	pytest -q

train:
	PYTHONPATH=. python scripts/train.py --ticker AAPL --period 5y

run:
	streamlit run app/dashboard.py

docker-build:
	docker build -t ai-trading-backtester:latest .

docker-run:
	docker run --rm -p 8501:8501 ai-trading-backtester:latest

compose-up:
	docker compose up --build
