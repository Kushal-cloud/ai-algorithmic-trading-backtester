"""VSEC Streamlit dashboard: multi-asset ICT/SMC backtester UI."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import VALID_ASSET_CLASSES, VALID_PERIODS, settings
from app.pipeline import execute

# ----------------------------------------------------------------------------
# Modern "aurora on midnight" design tokens (single source of truth).
# Plotly cannot read CSS var(), so charts use these constants directly.
# ----------------------------------------------------------------------------
CYAN = "#22D3EE"
VIOLET = "#8B5CF6"
PINK = "#E879F9"
TEXT = "#E9EFF8"
MUTED = "#8B98AD"
GREEN = "#34D399"
RED = "#FB7185"
AMBER = "#FBBF24"
GRID = "rgba(148, 163, 184, 0.12)"
POS_FILL = "rgba(34, 211, 238, 0.10)"
FONT_FAMILY = "Inter, 'Space Grotesk', system-ui, sans-serif"

ASSET_LABELS = {
    "US Stocks": "us_stocks",
    "Crypto": "crypto",
    "Forex": "forex",
    "CFDs": "cfds",
}
ASSET_EXAMPLES = {
    "US Stocks": "AAPL, MSFT, NVDA",
    "Crypto": "BTC, ETH, SOL",
    "Forex": "EURUSD, GBPUSD, USDJPY",
    "CFDs": "Full symbol, e.g. XAUUSD / US30",
}
SIGNAL_LABELS = {-1: "Sell", 0: "Hold", 1: "Buy"}
SIGNAL_COLORS = {-1: RED, 0: MUTED, 1: GREEN}
REGIME_LABELS = {1: "Uptrend", -1: "Downtrend", 0: "Range"}
REGIME_COLORS = {1: GREEN, -1: RED, 0: AMBER}

st.set_page_config(
    page_title="Algorithmic Trading Terminal",
    page_icon="\U0001f4c8",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root {
        --bg: #070B14;
        --bg-2: #0B1220;
        --card: rgba(255, 255, 255, 0.032);
        --card-border: rgba(148, 163, 184, 0.16);
        --cyan: #22D3EE;
        --violet: #8B5CF6;
        --text: #E9EFF8;
        --muted: #8B98AD;
        --green: #34D399;
        --red: #FB7185;
        --amber: #FBBF24;
    }
    * { font-family: 'Inter', system-ui, sans-serif; }
    .stApp {
        background:
            radial-gradient(1100px 480px at 12% -8%, rgba(34, 211, 238, 0.13), transparent 60%),
            radial-gradient(1000px 520px at 88% -10%, rgba(139, 92, 246, 0.16), transparent 60%),
            radial-gradient(900px 600px at 50% 115%, rgba(232, 121, 249, 0.07), transparent 60%),
            linear-gradient(180deg, #070B14 0%, #0B1220 100%);
        color: var(--text);
    }
    h1, h2, h3 { font-family: 'Space Grotesk', 'Inter', sans-serif !important; letter-spacing: -0.02em; }
    h1, h2, h3, h4, h5, h6 { color: var(--text) !important; }

    .hero {
        position: relative; overflow: hidden;
        border: 1px solid var(--card-border);
        border-radius: 20px; padding: 2.2rem 2.4rem;
        margin-bottom: 1.6rem;
        background: linear-gradient(135deg, rgba(34,211,238,0.10), rgba(139,92,246,0.12) 55%, rgba(232,121,249,0.08));
        backdrop-filter: blur(8px);
    }
    .hero::after {
        content: ""; position: absolute; inset: 0 auto 0 0; width: 4px;
        background: linear-gradient(180deg, var(--cyan), var(--violet), var(--amber));
    }
    .hero h1 {
        font-size: 2rem; margin: 0 0 0.35rem 0;
        background: linear-gradient(92deg, #FFFFFF 20%, var(--cyan) 55%, var(--violet) 90%);
        -webkit-background-clip: text; background-clip: text; color: transparent !important;
    }
    .hero p { color: var(--muted); margin: 0; font-size: 0.95rem; }
    .pill {
        display: inline-block; font-size: 0.68rem; font-weight: 600; letter-spacing: 0.12em;
        padding: 0.28rem 0.7rem; border-radius: 999px; margin-right: 0.45rem;
        border: 1px solid var(--card-border); color: var(--cyan);
        background: rgba(34, 211, 238, 0.08);
    }
    .pill.violet { color: #C4B5FD; background: rgba(139, 92, 246, 0.10); }
    .pill.amber { color: var(--amber); background: rgba(251, 191, 36, 0.08); }

    .kpi {
        background: var(--card); border: 1px solid var(--card-border);
        border-radius: 16px; padding: 1.15rem 1.3rem; position: relative; overflow: hidden;
        backdrop-filter: blur(6px);
    }
    .kpi::before {
        content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, var(--accent, #22D3EE), transparent);
    }
    .kpi .k-label { font-size: 0.72rem; font-weight: 600; letter-spacing: 0.14em; color: var(--muted); }
    .kpi .k-value { font-family: 'Space Grotesk', sans-serif; font-size: 1.65rem; font-weight: 700; margin-top: 0.25rem; }
    .kpi .k-sub { font-size: 0.78rem; color: var(--muted); margin-top: 0.15rem; }

    .panel {
        background: var(--card); border: 1px solid var(--card-border);
        border-radius: 18px; padding: 1.4rem 1.5rem; margin-bottom: 1.1rem;
        backdrop-filter: blur(6px);
    }
    .panel h3 { font-size: 1.02rem; margin: 0 0 0.2rem 0; }
    .panel .sub { font-size: 0.8rem; color: var(--muted); margin-bottom: 0.9rem; }

    section[data-testid="stSidebar"] { background: rgba(7, 11, 20, 0.85); border-right: 1px solid var(--card-border); }
    .stButton > button {
        background: linear-gradient(92deg, #0EA5B7, #7C6CF6);
        color: #fff; border: none; padding: 0.8rem 1.5rem;
        border-radius: 12px; font-weight: 600; width: 100%;
        box-shadow: 0 8px 24px rgba(34, 211, 238, 0.22);
    }
    .stButton > button:hover { filter: brightness(1.1); color: #fff; }
    .stTabs [data-baseweb="tab-list"] { gap: 0.4rem; }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255,255,255,0.03); border: 1px solid var(--card-border);
        border-radius: 12px; padding: 0.55rem 1.1rem; color: var(--muted);
    }
    .stTabs [aria-selected="true"] { color: #fff !important; border-color: rgba(34,211,238,0.5); }
    .stDataFrame { border: 1px solid var(--card-border); border-radius: 12px; overflow: hidden; }
    hr { border-color: var(--card-border); }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
    <span class="pill">RESEARCH TERMINAL</span>
    <span class="pill violet">ICT \u2022 SMC</span>
    <span class="pill amber">MULTI-ASSET</span>
    <h1>Algorithmic Trading</h1>
    <p>Machine-learned signals fused with Smart-Money-Concepts structure across stocks, crypto, forex and CFDs.</p>
</div>
""",
    unsafe_allow_html=True,
)


def _chart_base(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_FAMILY, color=TEXT),
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False),
        margin=dict(l=8, r=8, t=28, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


@st.cache_data(ttl=3600, show_spinner=False)
def cached_execute(ticker: str, period: str, capital: float, asset_class: str, use_ict: bool):
    """Cache pipeline runs so rerenders do not refetch/retrain."""
    return execute(
        ticker=ticker, period=period, capital=capital,
        asset_class=asset_class, use_ict_filter=use_ict,
    )


def _kpi(label: str, value: str, sub: str = "", accent: str = CYAN) -> None:
    st.markdown(
        f"""
        <div class="kpi" style="--accent: {accent};">
            <div class="k-label">{label}</div>
            <div class="k-value" style="color: {accent};">{value}</div>
            {f'<div class="k-sub">{sub}</div>' if sub else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _panel_head(title: str, sub: str) -> None:
    st.markdown(f"<div class='panel'><h3>{title}</h3><div class='sub'>{sub}</div>", unsafe_allow_html=True)


def _panel_tail() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


with st.sidebar:
    st.markdown("### Terminal Setup")
    selected_asset = st.radio(
        "Market", list(ASSET_LABELS), index=0,
        help="Select the market type for your symbol",
    )
    asset_key = ASSET_LABELS[selected_asset]
    if asset_key not in VALID_ASSET_CLASSES:
        asset_key = "us_stocks"
    st.caption(f"Try: {ASSET_EXAMPLES[selected_asset]}")
    ticker = st.text_input("Symbol", settings.default_ticker).upper().strip()
    period_options = list(VALID_PERIODS)
    period = st.selectbox(
        "History",
        period_options,
        index=period_options.index(settings.default_period) if settings.default_period in period_options else 1,
    )
    capital = st.number_input(
        "Capital ($)", min_value=500.0,
        value=float(settings.initial_capital), step=5000.0,
    )
    use_ict = st.checkbox(
        "ICT regime filter", value=settings.use_ict_filter,
        help="Reject signals that fight the market-structure regime",
    )
    st.markdown("---")
    run = st.button("Run Backtest", type="primary", use_container_width=True)
    st.caption("Research system \u2014 not financial advice.")

if run:
    if not ticker:
        st.error("Please enter a symbol.")
        st.stop()
    with st.spinner("Fetching market data, engineering features, training model…"):
        try:
            featured, equity, trades, metrics, _model = cached_execute(
                ticker, period, float(capital), asset_key, bool(use_ict)
            )
        except ValueError as exc:
            st.error(f"Data error: {exc}")
            st.info("Try a different symbol or check the format for this market.")
            st.stop()
        except Exception as exc:  # noqa: BLE001 - surface any pipeline failure cleanly
            st.error(f"Unexpected error: {exc}")
            st.stop()

    get = lambda key, default=0.0: metrics.get(key, default)  # noqa: E731
    final_equity = float(get("Final Equity", float(capital)))
    total_return = float(get("Total Return", 0.0))
    sharpe = float(get("Sharpe Ratio", 0.0))
    max_dd = float(get("Max Drawdown", 0.0))
    ret_accent = GREEN if total_return >= 0 else RED
    dd_accent = GREEN if max_dd >= 0 else RED

    st.markdown(f"#### {ticker} \u00b7 {selected_asset} \u00b7 {period}")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        _kpi("FINAL EQUITY", f"${final_equity:,.0f}", f"from ${float(capital):,.0f}", CYAN)
    with k2:
        _kpi("TOTAL RETURN", f"{total_return:+.2%}", f"CAGR {float(get('CAGR')):+.2%}", ret_accent)
    with k3:
        _kpi("SHARPE", f"{sharpe:.2f}", f"Sortino {float(get('Sortino Ratio')):.2f}", VIOLET)
    with k4:
        _kpi("MAX DRAWDOWN", f"{max_dd:.2%}", f"Calmar {float(get('Calmar Ratio')):.2f}", dd_accent)

    tab_overview, tab_trades, tab_ict = st.tabs(["\U0001f4c8 Overview", "\U0001f4bc Trades", "\U0001f9e0 ICT Insights"])

    with tab_overview:
        _panel_head("Equity curve", "Portfolio value vs running peak, test slice")
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=equity.index, y=equity.values, mode="lines", name="Equity",
                line=dict(color=CYAN, width=2.5),
                fill="tonexty", fillcolor=POS_FILL,
            )
        )
        peak = equity.cummax()
        fig.add_trace(
            go.Scatter(
                x=equity.index, y=peak.values, mode="lines", name="Peak",
                line=dict(color=MUTED, width=1, dash="dash"), showlegend=False,
            )
        )
        fig.update_layout(
            hovermode="x unified",
            xaxis_title="Date", yaxis_title="Portfolio ($)",
        )
        st.plotly_chart(_chart_base(fig, 440), use_container_width=True)
        _panel_tail()

        _panel_head("Price action + executions", "Daily candles with backtest fills")
        px = featured.tail(len(equity))
        pfig = go.Figure(
            data=go.Candlestick(
                x=px.index, open=px["Open"], high=px["High"], low=px["Low"], close=px["Close"],
                name="Price",
                increasing_line_color=GREEN, decreasing_line_color=RED,
                increasing_fillcolor=GREEN, decreasing_fillcolor=RED, opacity=0.9,
            )
        )
        if trades is not None and not trades.empty:
            entries = trades[trades["reason"] != "eod_liquidation"]
            wins = trades[pd.to_numeric(trades["pnl"], errors="coerce").fillna(0) > 0]
            if not entries.empty:
                pfig.add_trace(
                    go.Scatter(
                        x=pd.to_datetime(entries["entry_time"], errors="coerce"),
                        y=pd.to_numeric(entries["entry_price"], errors="coerce"),
                        mode="markers", name="Entry",
                        marker=dict(symbol="triangle-up", size=10, color=CYAN,
                                    line=dict(width=1, color="#06202A")),
                    )
                )
            if not wins.empty:
                pfig.add_trace(
                    go.Scatter(
                        x=pd.to_datetime(wins["exit_time"], errors="coerce"),
                        y=pd.to_numeric(wins["exit_price"], errors="coerce"),
                        mode="markers", name="Profitable exit",
                        marker=dict(symbol="circle", size=8, color=GREEN,
                                    line=dict(width=1, color="#062A1D")),
                    )
                )
            losses = trades[pd.to_numeric(trades["pnl"], errors="coerce").fillna(0) <= 0]
            if not losses.empty:
                pfig.add_trace(
                    go.Scatter(
                        x=pd.to_datetime(losses["exit_time"], errors="coerce"),
                        y=pd.to_numeric(losses["exit_price"], errors="coerce"),
                        mode="markers", name="Loss exit",
                        marker=dict(symbol="x", size=8, color=RED, line=dict(width=2)),
                    )
                )
        pfig.update_layout(hovermode="x unified", xaxis_title="Date", yaxis_title="Price",
                           xaxis_rangeslider_visible=False)
        st.plotly_chart(_chart_base(pfig, 420), use_container_width=True)
        _panel_tail()

    with tab_trades:
        _panel_head("Trade history", f"{int(get('Trades', 0))} closed trades \u00b7 win rate {float(get('Win Rate')):.1%}")
        if trades is None or trades.empty:
            st.info("No completed trades under this configuration — try a longer history or different symbol.")
        else:
            trades_display = trades.copy()
            trades_display["entry_time"] = pd.to_datetime(trades_display["entry_time"], errors="coerce")
            trades_display["exit_time"] = pd.to_datetime(trades_display["exit_time"], errors="coerce")
            trades_display["Entry"] = trades_display["entry_time"].dt.strftime("%Y-%m-%d")
            trades_display["Exit"] = trades_display["exit_time"].dt.strftime("%Y-%m-%d")
            pnl_num = pd.to_numeric(trades_display["pnl"], errors="coerce").fillna(0)
            trades_display["PnL"] = pnl_num.apply(lambda x: f"${x:,.2f}")
            trades_display["Return"] = (pnl_num / float(capital) * 100).apply(lambda x: f"{x:+.1f}%")
            st.dataframe(
                trades_display[["Entry", "Exit", "side", "entry_price", "exit_price",
                                "shares", "PnL", "Return", "reason"]],
                column_config={
                    "Entry": st.column_config.TextColumn("Entry"),
                    "Exit": st.column_config.TextColumn("Exit"),
                    "entry_price": st.column_config.NumberColumn("Entry", format="$%.2f"),
                    "exit_price": st.column_config.NumberColumn("Exit", format="$%.2f"),
                    "shares": st.column_config.NumberColumn("Qty", format="%.1f"),
                    "PnL": st.column_config.TextColumn("PnL"),
                    "Return": st.column_config.TextColumn("Return"),
                },
                height=380,
                use_container_width=True,
            )
            t1, t2, t3 = st.columns(3)
            with t1:
                st.metric("Winners", f"{int((pnl_num > 0).sum())}/{len(trades)}")
            with t2:
                st.metric("Net PnL", f"${float(pnl_num.sum()):+,.2f}")
            with t3:
                st.metric("Avg trade", f"${float(pnl_num.mean()):+,.2f}" if len(trades) else "$0.00")
        _panel_tail()

    with tab_ict:
        f1, f2, f3 = st.columns(3)
        with f1:
            ob_count = int(featured["bullish_ob_level"].notna().sum() + featured["bearish_ob_level"].notna().sum())
            st.metric("Order blocks", ob_count)
        with f2:
            fvg_count = int(featured["bullish_fvg_low"].notna().sum() + featured["bearish_fvg_low"].notna().sum())
            st.metric("Fair value gaps", fvg_count)
        with f3:
            sweep_count = int((featured["sweep_direction"].astype(str).str.strip() != "").sum())
            st.metric("Liquidity sweeps", sweep_count)

        _panel_head("Signal mix", "Black-box confluence signals across full history")
        if "bb_signal" in featured.columns:
            sig_counts = featured["bb_signal"].value_counts().sort_index()
            labels = [SIGNAL_LABELS.get(int(k), str(k)) for k in sig_counts.index]
            colors = [SIGNAL_COLORS.get(int(k), MUTED) for k in sig_counts.index]
            fig2 = go.Figure(data=go.Bar(x=labels, y=sig_counts.values, marker_color=colors))
            fig2.update_layout(xaxis_title="Signal", yaxis_title="Bars")
            st.plotly_chart(_chart_base(fig2, 300), use_container_width=True)
        else:
            st.info("No black-box signals available.")
        _panel_tail()

        _panel_head("Market regime", "Structure classification share")
        if "mss_123" in featured.columns:
            mss_counts = featured["mss_123"].value_counts().sort_index()
            mss_counts = mss_counts[mss_counts.index.isin(list(REGIME_LABELS))]
            if not mss_counts.empty:
                fig3 = go.Figure(
                    data=go.Pie(
                        labels=[REGIME_LABELS[int(i)] for i in mss_counts.index],
                        values=mss_counts.values, hole=0.55,
                        marker=dict(colors=[REGIME_COLORS[int(i)] for i in mss_counts.index]),
                        textinfo="label+percent", textfont=dict(color=TEXT),
                    )
                )
                st.plotly_chart(_chart_base(fig3, 340), use_container_width=True)
            else:
                st.info("No regimes detected in this slice.")
        _panel_tail()

    st.markdown("---")
    st.caption("Trading research terminal \u2014 historical backtests only, not financial advice.")
else:
    st.markdown(
        """
    <div class="hero">
        <span class="pill">READY</span>
        <span class="pill violet">4 MARKETS</span>
        <span class="pill amber">AI + SMC</span>
        <h1>Pick a market, run a backtest</h1>
        <p>Choose a market and symbol in the sidebar, then hit <strong>Run Backtest</strong>.</p>
    </div>
    """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        _panel_head("01 \u00b7 Select", "Stocks, crypto, forex or CFDs"); st.write("Symbols auto-format per market (BTC \u2192 BTC-USD)."); _panel_tail()
    with c2:
        _panel_head("02 \u00b7 Backtest", "XGBoost signals + ICT regime filter"); st.write("Long-only engine with stop-loss / take-profit exits."); _panel_tail()
    with c3:
        _panel_head("03 \u00b7 Inspect", "Equity, fills, ICT structure"); st.write("Candles with entries and exits, signal mix, regime share."); _panel_tail()
