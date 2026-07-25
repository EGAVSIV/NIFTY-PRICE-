from collections import deque
import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import yfinance as yf

# -------------------------------------------------------------------
# PAGE CONFIGURATION
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Nifty 50 Real-Time Sector Tracker",
    page_icon="📈",
    layout="wide",
)

# Dark theme for Matplotlib charts
plt.style.use("dark_background")

# -------------------------------------------------------------------
# NIFTY 50 CONSTITUENT DATA
# -------------------------------------------------------------------
NIFTY_STOCKS = [
    ("ADANIENT.NS", "Metals & Mining", 114.0, 0.274),
    ("ADANIPORTS.NS", "Services", 216.0, 0.341),
    ("APOLLOHOSP.NS", "Healthcare", 14.4, 0.707),
    ("ASIANPAINT.NS", "Consumer Durables", 95.9, 0.474),
    ("AXISBANK.NS", "Financial Services", 308.8, 0.918),
    ("BAJAJ-AUTO.NS", "Automobile", 27.9, 0.450),
    ("BAJFINANCE.NS", "Financial Services", 61.9, 0.441),
    ("BAJAJFINSV.NS", "Financial Services", 159.6, 0.392),
    ("BEL.NS", "Capital Goods", 731.0, 0.489),
    ("BHARTIARTL.NS", "Telecommunication", 569.2, 0.462),
    ("CIPLA.NS", "Healthcare", 80.7, 0.665),
    ("COALINDIA.NS", "Oil, Gas & Fuels", 616.3, 0.369),
    ("DRREDDY.NS", "Healthcare", 16.7, 0.733),
    ("EICHERMOT.NS", "Automobile", 27.4, 0.508),
    ("ETERNAL.NS", "Consumer Services", 882.0, 0.978),
    ("GRASIM.NS", "Construction Materials", 68.0, 0.572),
    ("HCLTECH.NS", "Information Technology", 271.4, 0.392),
    ("HDFCBANK.NS", "Financial Services", 761.5, 1.000),
    ("HDFCLIFE.NS", "Financial Services", 215.1, 0.496),
    ("HINDALCO.NS", "Metals & Mining", 224.7, 0.653),
    ("HINDUNILVR.NS", "FMCG", 234.9, 0.381),
    ("ICICIBANK.NS", "Financial Services", 703.1, 1.000),
    ("ITC.NS", "FMCG", 1248.5, 1.000),
    ("INFY.NS", "Information Technology", 415.1, 0.852),
    ("INDIGO.NS", "Services", 38.6, 0.322),
    ("JSWSTEEL.NS", "Metals & Mining", 244.5, 0.552),
    ("JIOFIN.NS", "Financial Services", 635.3, 0.529),
    ("KOTAKBANK.NS", "Financial Services", 198.8, 0.740),
    ("LT.NS", "Construction", 137.5, 1.000),
    ("M&M.NS", "Automobile", 120.3, 0.807),
    ("MARUTI.NS", "Automobile", 31.4, 0.418),
    ("MAXHEALTH.NS", "Healthcare", 97.2, 0.762),
    ("NTPC.NS", "Power", 969.7, 0.489),
    ("NESTLEIND.NS", "FMCG", 96.4, 0.372),
    ("ONGC.NS", "Oil, Gas & Fuels", 1258.0, 0.411),
    ("POWERGRID.NS", "Power", 930.1, 0.487),
    ("RELIANCE.NS", "Oil, Gas & Fuels", 676.6, 0.496),
    ("SBILIFE.NS", "Financial Services", 100.2, 0.445),
    ("SHRIRAMFIN.NS", "Financial Services", 37.6, 0.745),
    ("SBIN.NS", "Financial Services", 892.5, 0.425),
    ("SUNPHARMA.NS", "Healthcare", 239.9, 0.455),
    ("TCS.NS", "Information Technology", 361.8, 0.282),
    ("TATACONSUM.NS", "FMCG", 95.3, 0.655),
    ("TMPV.NS", "Automobile", 368.1, 0.536),
    ("TATASTEEL.NS", "Metals & Mining", 1248.4, 0.661),
    ("TECHM.NS", "Information Technology", 97.7, 0.648),
    ("TITAN.NS", "Consumer Durables", 88.8, 0.471),
    ("TRENT.NS", "Consumer Services", 35.5, 0.630),
    ("ULTRACEMCO.NS", "Construction Materials", 28.9, 0.400),
    ("WIPRO.NS", "Information Technology", 522.6, 0.271),
]

TICKERS = [item[0] for item in NIFTY_STOCKS]

# -------------------------------------------------------------------
# AUTOMATIC 3-SECOND REFRESH (Native Streamlit component)
# -------------------------------------------------------------------
st_autorefresh(interval=3000, limit=None, key="nifty_autorefresh")

# Live stream state buffers
if "live_ticks_time" not in st.session_state:
    st.session_state["live_ticks_time"] = deque(maxlen=60)
    st.session_state["live_ticks_mcap"] = deque(maxlen=60)


# -------------------------------------------------------------------
# CACHED HISTORICAL DATA
# -------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_baseline_data():
    hist_data = yf.download(
        TICKERS, period="1mo", interval="1d", progress=False
    )["Close"]
    valid_tickers = [t for t in TICKERS if t in hist_data.columns]
    hist_10d = hist_data[valid_tickers].tail(10)

    nifty_idx = yf.download(
        "^NSEI", period="1mo", interval="1d", progress=False
    )["Close"].tail(10)

    mcap_daily_10d = pd.Series(0.0, index=hist_10d.index)
    total_prev_ff_mcap = 0.0
    sector_baselines = {}
    sector_stock_counts = {}
    baseline_info = {}

    prev_close_series = hist_10d.iloc[-2]

    for ticker, sector, shares_cr, iwf in NIFTY_STOCKS:
        if ticker in hist_10d.columns:
            mcap_daily_10d += (hist_10d[ticker] * shares_cr * iwf).fillna(0)
            prev_price = float(prev_close_series[ticker])
            ff_mcap_cr = shares_cr * prev_price * iwf

            baseline_info[ticker] = {
                "sector": sector,
                "shares_cr": shares_cr,
                "iwf": iwf,
                "prev_close": prev_price,
                "prev_ff_mcap": ff_mcap_cr,
            }

            total_prev_ff_mcap += ff_mcap_cr
            sector_baselines[sector] = (
                sector_baselines.get(sector, 0.0) + ff_mcap_cr
            )
            sector_stock_counts[sector] = (
                sector_stock_counts.get(sector, 0) + 1
            )

    return (
        baseline_info,
        total_prev_ff_mcap,
        sector_baselines,
        sector_stock_counts,
        hist_10d.index,
        mcap_daily_10d,
        nifty_idx,
    )


(
    baseline_info,
    total_prev_ff_mcap,
    sector_baselines,
    sector_stock_counts,
    hist_dates,
    mcap_10d_vals,
    nifty_10d_vals,
) = load_baseline_data()


# -------------------------------------------------------------------
# LIVE INTRADAY PRICES
# -------------------------------------------------------------------
def fetch_live_prices():
    try:
        batch_data = yf.download(
            TICKERS, period="1d", interval="1m", progress=False
        )["Close"]
        if not batch_data.empty:
            return batch_data.iloc[-1]
    except Exception:
        pass
    return None


latest_prices = fetch_live_prices()

sector_live_mcaps = {s: 0.0 for s in sector_baselines.keys()}
total_live_ff_mcap = 0.0

for ticker in TICKERS:
    meta = baseline_info[ticker]
    if (
        latest_prices is not None
        and ticker in latest_prices
        and not np.isnan(latest_prices[ticker])
    ):
        current_price = float(latest_prices[ticker])
    else:
        current_price = meta["prev_close"]

    live_mcap = meta["shares_cr"] * current_price * meta["iwf"]
    sector_live_mcaps[meta["sector"]] += live_mcap
    total_live_ff_mcap += live_mcap

now_str = datetime.datetime.now().strftime("%H:%M:%S")
st.session_state["live_ticks_time"].append(now_str)
st.session_state["live_ticks_mcap"].append(total_live_ff_mcap)

# -------------------------------------------------------------------
# STREAMLIT UI LAYOUT
# -------------------------------------------------------------------
st.title("📈 NIFTY 50 Sector & Real-Time Tracker")

# Metrics Cards
overall_diff = total_live_ff_mcap - total_prev_ff_mcap
overall_pct = (overall_diff / total_prev_ff_mcap) * 100

col1, col2, col3 = st.columns(3)
col1.metric("Tracked Stocks", f"{len(NIFTY_STOCKS)} Stocks")
col2.metric("Prev Day Free Float Cap", f"₹ {total_prev_ff_mcap:,.2f} Cr")
col3.metric(
    "Live Market Cap Change",
    f"₹ {total_live_ff_mcap:,.2f} Cr",
    delta=f"₹ {overall_diff:+,.2f} Cr ({overall_pct:+.2f}%)",
)

st.divider()

# Interactive Data Table with Sorting
st.subheader("📊 Sector Market Cap Analysis")
st.caption("Click any column header to sort in ascending or descending order.")

table_data = []
for sector in sector_live_mcaps.keys():
    prev_cap = sector_baselines[sector]
    live_cap = sector_live_mcaps[sector]
    diff = live_cap - prev_cap
    pct = (diff / prev_cap) * 100
    count = sector_stock_counts[sector]

    table_data.append(
        {
            "Sector Name": sector,
            "Stocks": count,
            "Prev Cap (₹ Cr)": round(prev_cap, 2),
            "Live Cap (₹ Cr)": round(live_cap, 2),
            "Gain / Loss (₹ Cr)": round(diff, 2),
            "% Change": round(pct, 2),
        }
    )

df = pd.DataFrame(table_data)

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Prev Cap (₹ Cr)": st.column_config.NumberColumn(format="₹ %,.2f"),
        "Live Cap (₹ Cr)": st.column_config.NumberColumn(format="₹ %,.2f"),
        "Gain / Loss (₹ Cr)": st.column_config.NumberColumn(format="₹ %,.2f"),
        "% Change": st.column_config.NumberColumn(format="%.2f%%"),
    },
)

st.divider()

# Charts Grid
st.subheader("📉 Market Cap Trends & Real-Time Stream")

fig, (ax1, ax2, ax3) = plt.subplots(
    1, 3, figsize=(14, 3.8), facecolor="#0e1117"
)
fig.tight_layout(pad=3.0)

date_labels = [d.strftime("%b %d") for d in hist_dates]

# Chart 1
ax1.set_facecolor("#1e222a")
ax1.plot(
    date_labels,
    mcap_10d_vals,
    color="#00d8ff",
    marker="o",
    linewidth=1.8,
    markersize=3,
)
ax1.set_title(
    "10-Day Free Float MCap (₹ Cr)", fontsize=9, color="#00d8ff", weight="bold"
)
ax1.tick_params(axis="x", rotation=30, labelsize=7)
ax1.tick_params(axis="y", labelsize=7)
ax1.grid(True, linestyle="--", alpha=0.25)

# Chart 2
ax2.set_facecolor("#1e222a")
ax2.plot(
    date_labels,
    nifty_10d_vals,
    color="#a6e3a1",
    marker="s",
    linewidth=1.8,
    markersize=3,
)
ax2.set_title(
    "10-Day NIFTY 50 Close Index", fontsize=9, color="#a6e3a1", weight="bold"
)
ax2.tick_params(axis="x", rotation=30, labelsize=7)
ax2.tick_params(axis="y", labelsize=7)
ax2.grid(True, linestyle="--", alpha=0.25)

# Chart 3
ax3.set_facecolor("#1e222a")
ax3.set_title(
    "LIVE Intraday MCap Stream (Every 3s)",
    fontsize=9,
    color="#f9e2af",
    weight="bold",
)

times = list(st.session_state["live_ticks_time"])
mcaps = list(st.session_state["live_ticks_mcap"])

if len(mcaps) >= 2:
    line_color = "#a6e3a1" if mcaps[-1] >= mcaps[0] else "#f38ba8"
    ax3.plot(
        times,
        mcaps,
        color=line_color,
        marker=".",
        linewidth=1.5,
        markersize=4,
    )

ax3.tick_params(axis="x", rotation=35, labelsize=6.5)
ax3.tick_params(axis="y", labelsize=7)
ax3.grid(True, linestyle="--", alpha=0.25)

st.pyplot(fig)
st.caption(f"⚡ Live Monitoring Active | Last Updated: {now_str}")
