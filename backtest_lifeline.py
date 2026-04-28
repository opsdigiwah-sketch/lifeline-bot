"""
LIFELINE STRATEGY — HISTORICAL BACKTEST
========================================

Tests core rules of Vinay Bhelkar's Lifeline strategy:
  * 5-min Heikin Ashi breakout
  * Lifeline N-pattern entry (simplified)
  * Movement < 1.80% filter
  * No 1st 5-min Marubozu filter
  * Trend filter (Nifty direction)
  * SL 1% / Target 1:2 / Trailing (1:1 → cost, 1:2 → 1:1)
  * Square off at 3:15 PM
  * Capital risk 1% per trade

NOT modeled (free historical data limitation):
  * OI data resistance/support
  * Sector heatmap A/B grading
  * Advance/Decline ratio (proxied by Nifty trend)
  * 52-week high/low filter (use top movers proxy)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import time as dtime
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────
NIFTY_TICKERS = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "TCS.NS",
    "ITC.NS", "LT.NS", "AXISBANK.NS", "SBIN.NS", "BHARTIARTL.NS",
    "KOTAKBANK.NS", "HINDUNILVR.NS", "BAJFINANCE.NS", "ASIANPAINT.NS",
    "MARUTI.NS", "TATAMOTORS.NS", "SUNPHARMA.NS", "WIPRO.NS",
    "HCLTECH.NS", "ULTRACEMCO.NS"
]
NIFTY_INDEX = "^NSEI"

PERIOD = "60d"        # yfinance 5-min limit ~60 days
INTERVAL = "5m"

CAPITAL = 100_000     # ₹1 lakh starting
RISK_PER_TRADE = 0.01 # 1% capital risk

SL_PCT = 0.01         # 1% stop loss (mid of 0.5–1.8% range)
TARGET_R = 2.0        # 1:2 RR target
TRAIL_TO_COST_AT = 1.0   # at 1:1 profit, move SL to entry
TRAIL_TO_1R_AT = 2.0     # at 1:2 profit, move SL to 1:1

ENTRY_START = dtime(9, 20)   # No entries before 9:20 AM
ENTRY_CUTOFF = dtime(14, 30) # No new entries after 2:30 PM
SQUARE_OFF = dtime(15, 15)   # Force exit by 3:15 PM

MAX_MOVEMENT = 0.018  # 1.80% max move from day open at entry

# ─────────────────────────────────────────────────────────────────
# HEIKIN ASHI
# ─────────────────────────────────────────────────────────────────
def heikin_ashi(df):
    ha = pd.DataFrame(index=df.index)
    ha["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_open = [df["Open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha["HA_Close"].iloc[i-1]) / 2)
    ha["HA_Open"] = ha_open
    ha["HA_High"] = pd.concat([df["High"], ha["HA_Open"], ha["HA_Close"]], axis=1).max(axis=1)
    ha["HA_Low"]  = pd.concat([df["Low"],  ha["HA_Open"], ha["HA_Close"]], axis=1).min(axis=1)
    ha["HA_Color"] = np.where(ha["HA_Close"] >= ha["HA_Open"], "G", "R")
    return ha

# ─────────────────────────────────────────────────────────────────
# LIFELINE PATTERN (simplified N-pattern detection)
# ─────────────────────────────────────────────────────────────────
# Bullish Lifeline: 2+ red candles forming pullback after uptrend, then green BO
# Bearish Lifeline: 2+ green candles forming pullback after downtrend, then red BD
def is_bullish_lifeline(ha_color_window):
    # Last 4 candles: at least 2 reds in middle, last must be green for entry trigger
    if len(ha_color_window) < 4:
        return False
    middle = ha_color_window[-4:-1]
    red_count = sum(1 for c in middle if c == "R")
    return red_count >= 2 and ha_color_window[-1] == "G"

def is_bearish_lifeline(ha_color_window):
    if len(ha_color_window) < 4:
        return False
    middle = ha_color_window[-4:-1]
    green_count = sum(1 for c in middle if c == "G")
    return green_count >= 2 and ha_color_window[-1] == "R"

# ─────────────────────────────────────────────────────────────────
# MARUBOZU CHECK (1st 5-min candle)
# ─────────────────────────────────────────────────────────────────
def is_marubozu(o, h, l, c, threshold=0.85):
    rng = h - l
    body = abs(c - o)
    return rng > 0 and (body / rng) >= threshold

# ─────────────────────────────────────────────────────────────────
# DATA FETCH
# ─────────────────────────────────────────────────────────────────
def fetch_data(ticker):
    df = yf.download(ticker, period=PERIOD, interval=INTERVAL,
                     progress=False, auto_adjust=False)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()

# ─────────────────────────────────────────────────────────────────
# NIFTY TREND PER DAY (simple HA-color majority of first 30 mins)
# ─────────────────────────────────────────────────────────────────
def nifty_trend_per_day(nifty_df):
    ha = heikin_ashi(nifty_df)
    nifty_df = nifty_df.copy()
    nifty_df["HA_Color"] = ha["HA_Color"]
    nifty_df["Date"] = nifty_df.index.date
    trend = {}
    for date, day in nifty_df.groupby("Date"):
        first = day.between_time("09:15", "09:45")
        if first.empty:
            continue
        greens = (first["HA_Color"] == "G").sum()
        reds = (first["HA_Color"] == "R").sum()
        if greens > reds * 1.2:
            trend[date] = "BULL"
        elif reds > greens * 1.2:
            trend[date] = "BEAR"
        else:
            trend[date] = "SIDE"
    return trend

# ─────────────────────────────────────────────────────────────────
# BACKTEST CORE
# ─────────────────────────────────────────────────────────────────
def backtest_stock(df, ticker, nifty_trend):
    ha = heikin_ashi(df)
    df = df.copy()
    df["HA_Color"] = ha["HA_Color"]
    df["HA_Open"] = ha["HA_Open"]
    df["HA_Close"] = ha["HA_Close"]
    df["Date"] = df.index.date
    df["Time"] = df.index.time

    trades = []

    for date, day in df.groupby("Date"):
        if date not in nifty_trend:
            continue
        market_dir = nifty_trend[date]
        if market_dir == "SIDE":
            continue  # only trade trending days

        day = day.sort_index().reset_index()
        if len(day) < 6:
            continue

        # 1st 5-min candle Marubozu filter
        first = day.iloc[0]
        if is_marubozu(first["Open"], first["High"], first["Low"], first["Close"]):
            continue

        day_open = first["Open"]
        in_trade = False
        trade = None
        ha_colors = []
        prior_high = -np.inf
        prior_low = np.inf

        for idx in range(len(day)):
            row = day.iloc[idx]
            t = row["Time"]
            price_high = row["High"]
            price_low = row["Low"]
            price_close = row["Close"]

            ha_colors.append(row["HA_Color"])

            # ─── Manage existing trade ───────────────────────────
            if in_trade:
                # Time exit
                if t >= SQUARE_OFF:
                    trade["exit_price"] = row["Open"]
                    trade["exit_reason"] = "TIME"
                    trade["exit_time"] = row["Datetime"]
                    trades.append(trade)
                    in_trade = False
                    trade = None
                    continue

                if trade["dir"] == "LONG":
                    # Trailing logic on close
                    profit_R = (price_close - trade["entry"]) / trade["risk_per_share"]
                    if profit_R >= TRAIL_TO_1R_AT and trade["sl"] < trade["entry"] + trade["risk_per_share"]:
                        trade["sl"] = trade["entry"] + trade["risk_per_share"]  # lock 1R
                    elif profit_R >= TRAIL_TO_COST_AT and trade["sl"] < trade["entry"]:
                        trade["sl"] = trade["entry"]  # breakeven

                    # SL/Target hit (intra-bar — assume SL hit first conservatively)
                    if price_low <= trade["sl"]:
                        trade["exit_price"] = trade["sl"]
                        trade["exit_reason"] = "SL/TRAIL"
                        trade["exit_time"] = row["Datetime"]
                        trades.append(trade)
                        in_trade = False
                        trade = None
                        continue
                    if price_high >= trade["target"]:
                        trade["exit_price"] = trade["target"]
                        trade["exit_reason"] = "TARGET"
                        trade["exit_time"] = row["Datetime"]
                        trades.append(trade)
                        in_trade = False
                        trade = None
                        continue
                else:  # SHORT
                    profit_R = (trade["entry"] - price_close) / trade["risk_per_share"]
                    if profit_R >= TRAIL_TO_1R_AT and trade["sl"] > trade["entry"] - trade["risk_per_share"]:
                        trade["sl"] = trade["entry"] - trade["risk_per_share"]
                    elif profit_R >= TRAIL_TO_COST_AT and trade["sl"] > trade["entry"]:
                        trade["sl"] = trade["entry"]

                    if price_high >= trade["sl"]:
                        trade["exit_price"] = trade["sl"]
                        trade["exit_reason"] = "SL/TRAIL"
                        trade["exit_time"] = row["Datetime"]
                        trades.append(trade)
                        in_trade = False
                        trade = None
                        continue
                    if price_low <= trade["target"]:
                        trade["exit_price"] = trade["target"]
                        trade["exit_reason"] = "TARGET"
                        trade["exit_time"] = row["Datetime"]
                        trades.append(trade)
                        in_trade = False
                        trade = None
                        continue

            # ─── Look for new entry ──────────────────────────────
            if not in_trade and ENTRY_START <= t <= ENTRY_CUTOFF:
                # Movement filter from day open
                move_pct = abs(price_close - day_open) / day_open
                if move_pct > MAX_MOVEMENT:
                    prior_high = max(prior_high, price_high)
                    prior_low = min(prior_low, price_low)
                    continue

                # Need at least 4 candles of HA history
                if len(ha_colors) < 4:
                    prior_high = max(prior_high, price_high)
                    prior_low = min(prior_low, price_low)
                    continue

                # LONG signal: bullish trend + bullish lifeline + HA breakout above prior high
                if (market_dir == "BULL"
                        and is_bullish_lifeline(ha_colors)
                        and price_close > prior_high
                        and row["HA_Color"] == "G"):
                    entry = price_close
                    sl = entry * (1 - SL_PCT)
                    risk = entry - sl
                    target = entry + TARGET_R * risk
                    qty = max(int((CAPITAL * RISK_PER_TRADE) / risk), 1)
                    trade = {
                        "ticker": ticker, "date": date, "dir": "LONG",
                        "entry_time": row["Datetime"], "entry": entry,
                        "sl": sl, "target": target, "risk_per_share": risk, "qty": qty,
                    }
                    in_trade = True

                # SHORT signal
                elif (market_dir == "BEAR"
                        and is_bearish_lifeline(ha_colors)
                        and price_close < prior_low
                        and row["HA_Color"] == "R"):
                    entry = price_close
                    sl = entry * (1 + SL_PCT)
                    risk = sl - entry
                    target = entry - TARGET_R * risk
                    qty = max(int((CAPITAL * RISK_PER_TRADE) / risk), 1)
                    trade = {
                        "ticker": ticker, "date": date, "dir": "SHORT",
                        "entry_time": row["Datetime"], "entry": entry,
                        "sl": sl, "target": target, "risk_per_share": risk, "qty": qty,
                    }
                    in_trade = True

            prior_high = max(prior_high, price_high)
            prior_low = min(prior_low, price_low)

        # End of day — close open trade
        if in_trade and trade is not None:
            last = day.iloc[-1]
            trade["exit_price"] = last["Close"]
            trade["exit_reason"] = "EOD"
            trade["exit_time"] = last["Datetime"]
            trades.append(trade)

    return trades

# ─────────────────────────────────────────────────────────────────
# REPORTING
# ─────────────────────────────────────────────────────────────────
def analyze_trades(trades):
    if not trades:
        print("No trades generated.")
        return
    df = pd.DataFrame(trades)
    df["pnl_per_share"] = np.where(df["dir"] == "LONG",
                                    df["exit_price"] - df["entry"],
                                    df["entry"] - df["exit_price"])
    df["pnl"] = df["pnl_per_share"] * df["qty"]
    df["R"] = df["pnl_per_share"] / df["risk_per_share"]

    total = len(df)
    wins = (df["pnl"] > 0).sum()
    losses = (df["pnl"] <= 0).sum()
    win_rate = wins / total * 100
    total_pnl = df["pnl"].sum()
    avg_win = df.loc[df["pnl"] > 0, "pnl"].mean() if wins else 0
    avg_loss = df.loc[df["pnl"] <= 0, "pnl"].mean() if losses else 0
    avg_R = df["R"].mean()
    max_win = df["pnl"].max()
    max_loss = df["pnl"].min()
    pf = abs(df.loc[df["pnl"] > 0, "pnl"].sum() / df.loc[df["pnl"] <= 0, "pnl"].sum()) if losses and df.loc[df["pnl"] <= 0, "pnl"].sum() != 0 else float("inf")

    # Equity curve & drawdown
    df_sorted = df.sort_values("entry_time").reset_index(drop=True)
    df_sorted["cum_pnl"] = df_sorted["pnl"].cumsum()
    df_sorted["equity"] = CAPITAL + df_sorted["cum_pnl"]
    df_sorted["peak"] = df_sorted["equity"].cummax()
    df_sorted["dd"] = df_sorted["equity"] - df_sorted["peak"]
    max_dd = df_sorted["dd"].min()
    max_dd_pct = (max_dd / df_sorted["peak"].max()) * 100 if df_sorted["peak"].max() else 0

    print("\n" + "="*70)
    print(" LIFELINE STRATEGY — BACKTEST RESULTS")
    print("="*70)
    print(f" Period:                {PERIOD}  ({INTERVAL} candles)")
    print(f" Universe:              {len(NIFTY_TICKERS)} Nifty 50 stocks")
    print(f" Starting capital:      ₹{CAPITAL:,}")
    print(f" Risk/trade:            {RISK_PER_TRADE*100:.1f}%   SL: {SL_PCT*100:.1f}%   Target: 1:{TARGET_R:.0f}")
    print("-"*70)
    print(f" Total trades:          {total}")
    print(f" Wins / Losses:         {wins} / {losses}")
    print(f" Win rate:              {win_rate:.2f}%")
    print(f" Avg R:                 {avg_R:.3f}R")
    print(f" Profit factor:         {pf:.2f}")
    print("-"*70)
    print(f" Total P&L:             ₹{total_pnl:,.2f}  ({total_pnl/CAPITAL*100:.2f}% of capital)")
    print(f" Avg win:               ₹{avg_win:,.2f}")
    print(f" Avg loss:              ₹{avg_loss:,.2f}")
    print(f" Best trade:            ₹{max_win:,.2f}")
    print(f" Worst trade:           ₹{max_loss:,.2f}")
    print(f" Max drawdown:          ₹{max_dd:,.2f}  ({max_dd_pct:.2f}%)")
    print("-"*70)
    print(" By exit reason:")
    print(df.groupby("exit_reason")["pnl"].agg(["count", "sum", "mean"]).to_string())
    print("-"*70)
    print(" By direction:")
    print(df.groupby("dir")["pnl"].agg(["count", "sum", "mean"]).to_string())
    print("-"*70)
    print(" Top 5 stocks by P&L:")
    print(df.groupby("ticker")["pnl"].sum().sort_values(ascending=False).head().to_string())
    print("="*70)

    # Save trade log
    df.to_csv(r"D:\Window\lifeline\backtest_trades.csv", index=False)
    print("\n[Saved trade log → backtest_trades.csv]")

    return df

# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
def main():
    print("Fetching Nifty index data...")
    nifty_df = fetch_data(NIFTY_INDEX)
    if nifty_df is None or nifty_df.empty:
        print("ERROR: Could not fetch Nifty data.")
        return
    print(f"  Got {len(nifty_df)} Nifty bars from {nifty_df.index.min()} to {nifty_df.index.max()}")

    nifty_trend = nifty_trend_per_day(nifty_df)
    print(f"  Trend classified for {len(nifty_trend)} days")
    print(f"    BULL: {sum(1 for v in nifty_trend.values() if v == 'BULL')}")
    print(f"    BEAR: {sum(1 for v in nifty_trend.values() if v == 'BEAR')}")
    print(f"    SIDE: {sum(1 for v in nifty_trend.values() if v == 'SIDE')}")

    all_trades = []
    print("\nFetching stock data & backtesting...")
    for ticker in NIFTY_TICKERS:
        df = fetch_data(ticker)
        if df is None or df.empty:
            print(f"  [SKIP] {ticker}: no data")
            continue
        trades = backtest_stock(df, ticker, nifty_trend)
        print(f"  {ticker:18s}: {len(df):4d} bars -> {len(trades):3d} trades")
        all_trades.extend(trades)

    analyze_trades(all_trades)

if __name__ == "__main__":
    main()
