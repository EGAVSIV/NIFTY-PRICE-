import threading
import time
from collections import deque
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import pandas as pd
import yfinance as yf

# -------------------------------------------------------------------
# 1. NIFTY 50 CONSTITUENT DATA (Ticker, Sector, Shares Cr, IWF)
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

TICKERS_LIST = [item[0] for item in NIFTY_STOCKS]


class NiftyTrackerApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Nifty 50 Real-Time Sector & Live Trend Tracker")
        self.root.geometry("1300x900")
        self.root.configure(bg="#1e1e2e")

        self.baseline_data = {}
        self.total_prev_ff_mcap = 0.0
        self.sector_baselines = {}
        self.sector_stock_counts = {}

        # Real-time streaming history buffer (stores up to last 60 live ticks)
        self.live_ticks_time = deque(maxlen=60)
        self.live_ticks_mcap = deque(maxlen=60)

        # Cache for current table rows to allow fast header sorting
        self.current_rows_data = []
        self.sort_state = {}

        self.setup_styles()
        self.build_ui()

        self.lbl_status.config(
            text="Fetching historical 10-day trend and baseline data..."
        )
        threading.Thread(target=self.initialize_baseline, daemon=True).start()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#2a2a3c",
            foreground="#ffffff",
            fieldbackground="#2a2a3c",
            rowheight=26,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background="#3b3b54",
            foreground="#00d8ff",
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Treeview", background=[("selected", "#45475a")])

    def build_ui(self):
        # Header Container
        header = tk.Frame(self.root, bg="#1e1e2e")
        header.pack(fill="x", padx=15, pady=8)

        title = tk.Label(
            header,
            text="NIFTY 50 LIVE SECTOR & REAL-TIME STREAM MONITOR",
            font=("Segoe UI", 14, "bold"),
            fg="#00d8ff",
            bg="#1e1e2e",
        )
        title.pack(anchor="w")

        # Cards Frame
        cards_frame = tk.Frame(self.root, bg="#1e1e2e")
        cards_frame.pack(fill="x", padx=15, pady=5)

        card1 = tk.Frame(cards_frame, bg="#2a2a3c")
        card1.pack(side="left", expand=True, fill="both", padx=4)
        tk.Label(
            card1,
            text="MONITORED STOCKS",
            font=("Segoe UI", 8, "bold"),
            fg="#a6adc8",
            bg="#2a2a3c",
        ).pack(pady=4)
        self.lbl_stocks_count = tk.Label(
            card1,
            text=f"{len(NIFTY_STOCKS)} Stocks",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#2a2a3c",
        )
        self.lbl_stocks_count.pack(pady=4)

        card2 = tk.Frame(cards_frame, bg="#2a2a3c")
        card2.pack(side="left", expand=True, fill="both", padx=4)
        tk.Label(
            card2,
            text="PREV DAY FREE FLOAT MCAP",
            font=("Segoe UI", 8, "bold"),
            fg="#a6adc8",
            bg="#2a2a3c",
        ).pack(pady=4)
        self.lbl_prev_mcap = tk.Label(
            card2,
            text="₹ -- Cr",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#2a2a3c",
        )
        self.lbl_prev_mcap.pack(pady=4)

        card3 = tk.Frame(cards_frame, bg="#2a2a3c")
        card3.pack(side="left", expand=True, fill="both", padx=4)
        tk.Label(
            card3,
            text="OVERALL GAIN / LOSS",
            font=("Segoe UI", 8, "bold"),
            fg="#a6adc8",
            bg="#2a2a3c",
        ).pack(pady=4)
        self.lbl_overall_change = tk.Label(
            card3,
            text="-- (0.00%)",
            font=("Segoe UI", 12, "bold"),
            fg="#ffffff",
            bg="#2a2a3c",
        )
        self.lbl_overall_change.pack(pady=4)

        # Table Frame
        table_frame = tk.Frame(self.root, bg="#1e1e2e")
        table_frame.pack(fill="both", expand=True, padx=15, pady=5)

        columns = ("sector", "count", "prev_cap", "live_cap", "diff", "pct")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=7,
        )

        headers = {
            "sector": "Sector Name ↕",
            "count": "Stocks ↕",
            "prev_cap": "Prev Cap (₹ Cr) ↕",
            "live_cap": "Live Cap (₹ Cr) ↕",
            "diff": "Gain/Loss (₹ Cr) ↕",
            "pct": "% Change ↕",
        }

        for col, text in headers.items():
            self.tree.heading(
                col,
                text=text,
                command=lambda c=col: self.sort_column_header(c),
            )
            self.sort_state[col] = False  # False = Descending/Default

        self.tree.column("sector", width=180, anchor="w")
        self.tree.column("count", width=80, anchor="center")
        self.tree.column("prev_cap", width=140, anchor="e")
        self.tree.column("live_cap", width=140, anchor="e")
        self.tree.column("diff", width=140, anchor="e")
        self.tree.column("pct", width=100, anchor="e")

        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("green", foreground="#a6e3a1")
        self.tree.tag_configure("red", foreground="#f38ba8")

        # Matplotlib Charts Container (3 Charts Grid Layout)
        self.chart_frame = tk.Frame(self.root, bg="#1e1e2e", height=320)
        self.chart_frame.pack(fill="both", expand=True, padx=15, pady=5)

        # Status Bar
        self.lbl_status = tk.Label(
            self.root,
            text="Initializing...",
            font=("Segoe UI", 9),
            fg="#a6adc8",
            bg="#1e1e2e",
            anchor="w",
        )
        self.lbl_status.pack(fill="x", padx=15, pady=4)

    def initialize_baseline(self):
        """Fetch 10 Days Close Prices to compute baselines and set up historical charts."""
        try:
            hist_data = yf.download(
                TICKERS_LIST, period="1mo", interval="1d", progress=False
            )["Close"]

            valid_tickers = [t for t in TICKERS_LIST if t in hist_data.columns]
            hist_10d = hist_data[valid_tickers].tail(10)

            nifty_idx = yf.download(
                "^NSEI", period="1mo", interval="1d", progress=False
            )["Close"].tail(10)

            mcap_daily_10d = pd.Series(0.0, index=hist_10d.index)

            self.total_prev_ff_mcap = 0.0
            prev_close_series = hist_10d.iloc[-2]

            for ticker, sector, shares_cr, iwf in NIFTY_STOCKS:
                if ticker in hist_10d.columns:
                    mcap_daily_10d += (
                        hist_10d[ticker] * shares_cr * iwf
                    ).fillna(0)

                    prev_price = float(prev_close_series[ticker])
                    ff_mcap_cr = shares_cr * prev_price * iwf

                    self.baseline_data[ticker] = {
                        "sector": sector,
                        "shares_cr": shares_cr,
                        "iwf": iwf,
                        "prev_close": prev_price,
                        "prev_ff_mcap": ff_mcap_cr,
                    }

                    self.total_prev_ff_mcap += ff_mcap_cr
                    self.sector_baselines[sector] = (
                        self.sector_baselines.get(sector, 0.0) + ff_mcap_cr
                    )
                    self.sector_stock_counts[sector] = (
                        self.sector_stock_counts.get(sector, 0) + 1
                    )

            self.root.after(
                0,
                lambda: self.lbl_prev_mcap.config(
                    text=f"₹ {self.total_prev_ff_mcap:,.2f} Cr"
                ),
            )

            # Store baseline charts parameters
            self.hist_dates = [d.strftime("%b %d") for d in hist_10d.index]
            self.mcap_10d_vals = mcap_daily_10d.values
            self.nifty_10d_vals = nifty_idx.values

            # Initialize Matplotlib Figure with 3 Subplots
            self.root.after(0, self.setup_matplotlib_canvas)

            # Start real-time stream
            self.start_fast_monitoring_loop()

        except Exception as e:
            self.root.after(
                0,
                lambda: self.lbl_status.config(
                    text=f"Error fetching baseline: {e}"
                ),
            )

    def setup_matplotlib_canvas(self):
        plt.style.use("dark_background")
        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(
            1, 3, figsize=(13, 3.2), facecolor="#1e1e2e"
        )
        self.fig.tight_layout(pad=2.5)

        # Plot 1: 10-Day Market Cap Trend
        self.ax1.set_facecolor("#2a2a3c")
        self.ax1.plot(
            self.hist_dates,
            self.mcap_10d_vals,
            color="#00d8ff",
            marker="o",
            linewidth=1.8,
            markersize=3,
        )
        self.ax1.set_title(
            "10-Day Nifty Free Float MCap (₹ Cr)",
            fontsize=8.5,
            color="#00d8ff",
            weight="bold",
        )
        self.ax1.tick_params(axis="x", rotation=30, labelsize=7)
        self.ax1.tick_params(axis="y", labelsize=7)
        self.ax1.grid(True, linestyle="--", alpha=0.25)

        # Plot 2: 10-Day Nifty Close Price
        self.ax2.set_facecolor("#2a2a3c")
        self.ax2.plot(
            self.hist_dates,
            self.nifty_10d_vals,
            color="#a6e3a1",
            marker="s",
            linewidth=1.8,
            markersize=3,
        )
        self.ax2.set_title(
            "10-Day NIFTY 50 Index Close",
            fontsize=8.5,
            color="#a6e3a1",
            weight="bold",
        )
        self.ax2.tick_params(axis="x", rotation=30, labelsize=7)
        self.ax2.tick_params(axis="y", labelsize=7)
        self.ax2.grid(True, linestyle="--", alpha=0.25)

        # Plot 3: Real-time Live Tick Stream Graph (Updates continuously every 2-3 seconds)
        self.ax3.set_facecolor("#2a2a3c")
        self.ax3.set_title(
            "LIVE Intraday MCap Stream (Every 3s)",
            fontsize=8.5,
            color="#f9e2af",
            weight="bold",
        )
        self.ax3.tick_params(axis="x", rotation=30, labelsize=7)
        self.ax3.tick_params(axis="y", labelsize=7)
        self.ax3.grid(True, linestyle="--", alpha=0.25)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def update_live_chart(self):
        """Redraws Subplot 3 with live streaming ticks."""
        if len(self.live_ticks_mcap) < 2:
            return

        self.ax3.clear()
        self.ax3.set_facecolor("#2a2a3c")
        self.ax3.set_title(
            "LIVE Intraday MCap Stream (Every 3s)",
            fontsize=8.5,
            color="#f9e2af",
            weight="bold",
        )

        times = list(self.live_ticks_time)
        mcaps = list(self.live_ticks_mcap)

        # Line color reflects positive/negative live move
        line_color = "#a6e3a1" if mcaps[-1] >= mcaps[0] else "#f38ba8"

        self.ax3.plot(
            times,
            mcaps,
            color=line_color,
            marker=".",
            linewidth=1.5,
            markersize=4,
        )
        self.ax3.tick_params(axis="x", rotation=35, labelsize=6.5)
        self.ax3.tick_params(axis="y", labelsize=7)
        self.ax3.grid(True, linestyle="--", alpha=0.25)

        self.canvas.draw_idle()

    def start_fast_monitoring_loop(self):
        """Continuous thread collecting prices every 2-3 seconds."""

        def loop_worker():
            while True:
                try:
                    batch_data = yf.download(
                        TICKERS_LIST, period="1d", interval="1m", progress=False
                    )["Close"]

                    if not batch_data.empty:
                        latest_prices = batch_data.iloc[-1]

                        sector_live_mcaps = {
                            s: 0.0 for s in self.sector_baselines.keys()
                        }
                        total_live_ff_mcap = 0.0

                        for ticker in TICKERS_LIST:
                            if ticker in latest_prices and not np.isnan(
                                latest_prices[ticker]
                            ):
                                current_price = float(latest_prices[ticker])
                            else:
                                current_price = self.baseline_data[ticker][
                                    "prev_close"
                                ]

                            meta = self.baseline_data[ticker]
                            live_mcap = (
                                meta["shares_cr"] * current_price * meta["iwf"]
                            )

                            sector = meta["sector"]
                            sector_live_mcaps[sector] += live_mcap
                            total_live_ff_mcap += live_mcap

                        # Record live tick
                        current_time_str = time.strftime("%H:%M:%S")
                        self.live_ticks_time.append(current_time_str)
                        self.live_ticks_mcap.append(total_live_ff_mcap)

                        # Trigger UI Updates
                        self.root.after(
                            0,
                            self.update_gui_table,
                            sector_live_mcaps,
                            total_live_ff_mcap,
                        )
                        self.root.after(0, self.update_live_chart)

                except Exception as e:
                    print(f"Fetch error: {e}")

                time.sleep(2.5)

        threading.Thread(target=loop_worker, daemon=True).start()

    def update_gui_table(self, sector_live_mcaps, total_live_ff_mcap):
        overall_diff = total_live_ff_mcap - self.total_prev_ff_mcap
        overall_pct = (overall_diff / self.total_prev_ff_mcap) * 100

        color = "#a6e3a1" if overall_diff >= 0 else "#f38ba8"
        sign = "+" if overall_diff >= 0 else ""
        self.lbl_overall_change.config(
            text=f"₹ {overall_diff:+,.2f} Cr ({sign}{overall_pct:.2f}%)",
            fg=color,
        )

        # Store data structures internally for header sorting
        rows_data = []
        for sector in sector_live_mcaps.keys():
            prev_cap = self.sector_baselines[sector]
            live_cap = sector_live_mcaps[sector]
            diff = live_cap - prev_cap
            pct = (diff / prev_cap) * 100
            count = self.sector_stock_counts[sector]

            rows_data.append(
                {
                    "sector": sector,
                    "count": count,
                    "prev_cap": prev_cap,
                    "live_cap": live_cap,
                    "diff": diff,
                    "pct": pct,
                }
            )

        self.current_rows_data = rows_data
        self.render_table_rows()

        timestamp = time.strftime("%H:%M:%S")
        self.lbl_status.config(
            text=f"⚡ Live Tick Active | Last Updated: {timestamp} (Auto-refreshing every ~3s)"
        )

    def sort_column_header(self, col):
        """Sorts table dynamically when any column header is clicked."""
        self.sort_state[col] = not self.sort_state[col]
        reverse = self.sort_state[col]
        self.render_table_rows(sort_by=col, reverse=reverse)

    def render_table_rows(self, sort_by="pct", reverse=True):
        """Renders rows based on active sort column and direction."""
        if not self.current_rows_data:
            return

        sorted_rows = sorted(
            self.current_rows_data,
            key=lambda x: x[sort_by],
            reverse=reverse,
        )

        for row in self.tree.get_children():
            self.tree.delete(row)

        for item in sorted_rows:
            tag = "green" if item["diff"] >= 0 else "red"
            self.tree.insert(
                "",
                "end",
                values=(
                    item["sector"],
                    f"{item['count']}",
                    f"₹ {item['prev_cap']:,.2f}",
                    f"₹ {item['live_cap']:,.2f}",
                    f"{item['diff']:+,.2f}",
                    f"{item['pct']:+.2f}%",
                ),
                tags=(tag,),
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = NiftyTrackerApp(root)
    root.mainloop()
