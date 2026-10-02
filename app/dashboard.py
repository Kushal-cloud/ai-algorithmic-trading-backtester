import streamlit as st
import plotly.graph_objects as go
from app.pipeline import execute

st.set_page_config(page_title="AI Trading Backtester", page_icon="📈", layout="wide")
st.title("📈 AI-Powered Algorithmic Trading Strategy Backtester")
st.caption("Historical research dashboard — not a live trading system or financial advice.")

with st.sidebar:
    ticker = st.text_input("Ticker", "AAPL").upper().strip()
    period = st.selectbox("Historical period", ["1y", "2y", "5y", "10y"], index=2)
    capital = st.number_input("Initial capital", min_value=1000.0, value=100000.0, step=5000.0)
    run = st.button("Run backtest", type="primary")

if run:
    with st.spinner("Downloading data, training model and running backtest..."):
        data, equity, trades, metrics, model = execute(ticker, period, capital)

    cols = st.columns(4)
    cols[0].metric("Final Equity", f"${metrics['Final Equity']:,.0f}")
    cols[1].metric("Total Return", f"{metrics['Total Return']:.2%}")
    cols[2].metric("Sharpe", f"{metrics['Sharpe Ratio']:.2f}")
    cols[3].metric("Max Drawdown", f"{metrics['Max Drawdown']:.2%}")

    st.subheader("Equity Curve")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity.index, y=equity.values, mode="lines", name="Equity"))
    fig.update_layout(height=450, xaxis_title="Date", yaxis_title="Portfolio Value")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Performance Metrics")
    st.dataframe(
        {k: [v] for k, v in metrics.items()},
        use_container_width=True,
    )

    st.subheader("Trade Log")
    if trades.empty:
        st.info("No completed trades were generated under the selected configuration.")
    else:
        st.dataframe(trades, use_container_width=True)
else:
    st.info("Choose a ticker and period, then click **Run backtest**.")
