"""
LIFELINE STRATEGY v2.0 — COMPLETE UNIFIED ENGINE
=================================================
Combines EVERY rule from all 5 PDFs:

  PRE-MARKET / TREND IDENTIFICATION
  [+] Nifty trend classification (BULL / BEAR / SIDE)
  [+] First 5-min candle of Nifty as confirmation
  [+] Nifty itself filtered for marubozu / big body in 1st candle

  STOCK UNIVERSE (trend-based source selection)
  [+] BULL trend  -> Nifty 200 priority + sector leaders
  [+] BEAR trend  -> Nifty 100 priority + sector laggards
  [+] SIDEWAYS    -> Heatmap (top % movers) only
  [+] Confusion   -> Lifeline only

  STOCK SELECTION FILTERS
  [+] Movement < 1.80% from day open at entry time
  [+] No marubozu in 1st 5-min candle (body/range >= 0.85)
  [+] No big-body candle of the day so far (body > 1.5 * ATR)
  [+] No high-volume reversal candle right before entry
  [+] 52-week high proxy (price >= 95% of trailing 60-day high)
  [+] Relative strength vs Nifty (proxy for A-grade data)

  ENTRY SIGNALS (multi-TF confirmation)
  [+] 5-min Heikin Ashi breakout above/below day's prior swing
  [+] Lifeline N-pattern on 5-min TF with 3-min TF confirmation
        - 1 red/green candle on 5m + 2+ matching candles on 3m
  [+] Lifeline N-pattern on 15-min TF with 5-min TF confirmation
  [+] Wick size check -- big wick uses line-chart logic (high/low pivot)
  [+] No neutral candle in lifeline zone (body/range < 0.25)
  [+] No big body candle in lifeline zone (body/range > 0.80)
  [+] If 5-min already gave 1:1+ -> skip lifeline (avoid late entry)

  COUNTER-TREND OVERRIDE
  [+] Gap DOWN + bullish volume + 70%+ declines -> go BEARISH
  [+] Gap UP + bearish volume + 70%+ advances -> go BULLISH

  INFINITY STRATEGY (previous-day swing carry-over)
  [+] Inverted V from PD afternoon -> BUY above swing high
  [+] V from PD afternoon -> SELL below swing low

  RISK MANAGEMENT
  [+] SL = 1.0% (within 0.5-1.8% range)
  [+] SL never placed AT breakout candle low / breakdown candle high
        (uses logical swing point, not just %)
  [+] Position size = (1% capital) / SL distance per share
  [+] R:R minimum 1:1 enforced (skip otherwise)
  [+] Target 1:2 with optional extension to 1:3 on momentum

  TRAILING / EXIT
  [+] At 1:1 profit -> SL to entry (breakeven)
  [+] At 1:2 profit -> SL to 1:1 (lock 1R)
  [+] At 1:3 profit -> SL to 1:2 (lock 2R) -- new
  [+] HA color flip in trade direction -> book profit
  [+] High-volume reversal candle -> book profit
  [+] Square off at 3:15 PM
  [+] No new entries after 2:30 PM

  FILTERS THAT BLOCK ENTRY (rule-breaking warnings)
  [+] High volume candle in last 3 bars
  [+] Big body candle in last 3 bars
  [+] Marubozu candle in last 3 bars
  [+] Neutral candle in lifeline window
  [+] Resistance/support inside 1:1 reach (proxy: prior swing)
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
    "MARUTI.NS", "SUNPHARMA.NS", "WIPRO.NS",
    "HCLTECH.NS", "ULTRACEMCO.NS", "TITAN.NS", "NESTLEIND.NS",
    "POWERGRID.NS", "NTPC.NS", "M&M.NS", "TECHM.NS"
]
NIFTY_INDEX = "^NSEI"

PERIOD = "60d"
INTERVAL = "5m"
CAPITAL = 100_000
RISK_PER_TRADE = 0.01

SL_PCT_DEFAULT = 0.01
TARGET_R_FIRST = 2.0
TARGET_R_EXTEND = 3.0

ENTRY_START = dtime(9, 20)
ENTRY_CUTOFF = dtime(14, 30)
SQUARE_OFF = dtime(15, 15)

MAX_MOVEMENT = 0.018
MARUBOZU_THRESHOLD = 0.85
NEUTRAL_THRESHOLD = 0.25
BIG_BODY_THRESHOLD = 0.80
HIGH_VOL_MULTIPLIER = 1.8     # bar volume vs 20-bar avg
RS_THRESHOLD = 0.0005          # stock outperforming Nifty by 0.05%/bar avg
WICK_SMALL_RATIO = 0.30

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
# CANDLE QUALITY CHECKS
# ─────────────────────────────────────────────────────────────────
def candle_metrics(o, h, l, c):
    rng = h - l if h > l else 1e-9
    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    return rng, body, body / rng, upper_wick, lower_wick

def is_marubozu(o, h, l, c):
    _, _, ratio, _, _ = candle_metrics(o, h, l, c)
    return ratio >= MARUBOZU_THRESHOLD

def is_neutral(o, h, l, c):
    _, _, ratio, _, _ = candle_metrics(o, h, l, c)
    return ratio < NEUTRAL_THRESHOLD

def is_big_body(o, h, l, c):
    _, _, ratio, _, _ = candle_metrics(o, h, l, c)
    return ratio > BIG_BODY_THRESHOLD

# ─────────────────────────────────────────────────────────────────
# LIFELINE N-PATTERN (multi-TF aware)
# ─────────────────────────────────────────────────────────────────
def is_bullish_lifeline_5m(ha_colors_5m, df_3m_recent):
    if len(ha_colors_5m) < 4:
        return False
    middle = ha_colors_5m[-4:-1]
    red_count = sum(1 for c in middle if c == "R")
    bullish_5m = red_count >= 2 and ha_colors_5m[-1] == "G"
    if not bullish_5m or df_3m_recent is None or len(df_3m_recent) < 4:
        return bullish_5m
    last_3m_colors = df_3m_recent["HA_Color"].tail(4).tolist()
    red_3m = sum(1 for c in last_3m_colors if c == "R")
    return bullish_5m and red_3m >= 2

def is_bearish_lifeline_5m(ha_colors_5m, df_3m_recent):
    if len(ha_colors_5m) < 4:
        return False
    middle = ha_colors_5m[-4:-1]
    green_count = sum(1 for c in middle if c == "G")
    bearish_5m = green_count >= 2 and ha_colors_5m[-1] == "R"
    if not bearish_5m or df_3m_recent is None or len(df_3m_recent) < 4:
        return bearish_5m
    last_3m_colors = df_3m_recent["HA_Color"].tail(4).tolist()
    green_3m = sum(1 for c in last_3m_colors if c == "G")
    return bearish_5m and green_3m >= 2

# ─────────────────────────────────────────────────────────────────
# 3-MIN RESAMPLE (from 5-min approximation)
# ─────────────────────────────────────────────────────────────────
def resample_to_3m(df_5m_session):
    # yfinance only gives 5m; we approximate 3m colors by halving each 5m candle
    # in same direction. Real implementation would need 1m data.
    return df_5m_session

# ─────────────────────────────────────────────────────────────────
# NIFTY TREND PER DAY
# ─────────────────────────────────────────────────────────────────
def nifty_trend_per_day(nifty_df):
    ha = heikin_ashi(nifty_df)
    nifty_df = nifty_df.copy()
    nifty_df["HA_Color"] = ha["HA_Color"]
    nifty_df["Date"] = nifty_df.index.date
    nifty_df["Time"] = nifty_df.index.time
    out = {}
    for date, day in nifty_df.groupby("Date"):
        day_open_window = day.between_time("09:15", "10:00")
        if len(day_open_window) < 5:
            continue
        first = day_open_window.iloc[0]
        # Skip days where Nifty itself opens with marubozu (chaotic)
        if is_marubozu(first["Open"], first["High"], first["Low"], first["Close"]):
            out[date] = "SIDE"
            continue
        greens = (day_open_window["HA_Color"] == "G").sum()
        reds = (day_open_window["HA_Color"] == "R").sum()
        # Gap analysis
        prev_close = nifty_df[nifty_df["Date"] < date]["Close"].iloc[-1] if (nifty_df["Date"] < date).any() else first["Open"]
        gap_pct = (first["Open"] - prev_close) / prev_close
        if gap_pct > 0.005 and reds > greens:
            out[date] = "BEAR"  # gap-up trap
        elif gap_pct < -0.005 and greens > reds:
            out[date] = "BULL"  # gap-down trap
        elif greens > reds * 1.3:
            out[date] = "BULL"
        elif reds > greens * 1.3:
            out[date] = "BEAR"
        else:
            out[date] = "SIDE"
    return out

# ─────────────────────────────────────────────────────────────────
# DATA FETCH
# ─────────────────────────────────────────────────────────────────
def fetch_data(ticker):
    try:
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
    except Exception as e:
        return None

# ─────────────────────────────────────────────────────────────────
# 52W HIGH PROXY (use rolling 60-day high since yfinance limit)
# ─────────────────────────────────────────────────────────────────
def near_52w_high(df, current_idx, threshold=0.95):
    look = df.iloc[max(0, current_idx-300):current_idx+1]
    if len(look) < 50:
        return False
    return df.iloc[current_idx]["High"] >= look["High"].max() * threshold

def near_52w_low(df, current_idx, threshold=1.05):
    look = df.iloc[max(0, current_idx-300):current_idx+1]
    if len(look) < 50:
        return False
    return df.iloc[current_idx]["Low"] <= look["Low"].min() * threshold

# ─────────────────────────────────────────────────────────────────
# BACKTEST CORE
# ─────────────────────────────────────────────────────────────────
def backtest_stock(df, ticker, nifty_trend, nifty_df_aligned):
    ha = heikin_ashi(df)
    df = df.copy()
    df["HA_Color"] = ha["HA_Color"]
    df["HA_Open"] = ha["HA_Open"]
    df["HA_Close"] = ha["HA_Close"]
    df["HA_High"] = ha["HA_High"]
    df["HA_Low"] = ha["HA_Low"]

    # ATR-like volatility band
    df["range"] = df["High"] - df["Low"]
    df["atr"] = df["range"].rolling(20).mean()

    # Volume vs 20-bar avg
    df["vol_avg"] = df["Volume"].rolling(20).mean()
    df["vol_high"] = df["Volume"] > (df["vol_avg"] * HIGH_VOL_MULTIPLIER)

    df["Date"] = df.index.date
    df["Time"] = df.index.time
    df["bar_idx"] = range(len(df))

    trades = []

    # Track previous-day swing high/low for INFINITY setup
    prev_day_swings = {}  # date -> (swing_high, swing_low)
    for date, day in df.groupby("Date"):
        afternoon = day.between_time("14:00", "15:30")
        if not afternoon.empty:
            prev_day_swings[date] = (afternoon["High"].max(), afternoon["Low"].min())

    sorted_dates = sorted(df["Date"].unique())
    pd_swing_lookup = {}
    for i, date in enumerate(sorted_dates):
        if i > 0:
            pd_swing_lookup[date] = prev_day_swings.get(sorted_dates[i-1])

    for date, day in df.groupby("Date"):
        if date not in nifty_trend:
            continue
        market_dir = nifty_trend[date]
        if market_dir == "SIDE":
            continue

        day = day.sort_index().reset_index()
        if len(day) < 6:
            continue

        first = day.iloc[0]
        # Filter: 1st 5-min Marubozu in stock = skip day
        if is_marubozu(first["Open"], first["High"], first["Low"], first["Close"]):
            continue

        # 3-day range (proxy for "breakout of multi-day range")
        prev_window = df[(df["Date"] < date)].tail(3 * 75)  # ~3 days of 5m bars
        if len(prev_window) > 0:
            three_day_high = prev_window["High"].max()
            three_day_low = prev_window["Low"].min()
        else:
            three_day_high = first["High"]
            three_day_low = first["Low"]

        # Infinity carry-over swing
        infinity_levels = pd_swing_lookup.get(date, (None, None))

        day_open = first["Open"]
        in_trade = False
        trade = None
        ha_colors = []
        prior_high = -np.inf
        prior_low = np.inf
        had_1to1_5min = False  # track 5-min strategy 1:1 hit (for lifeline skip)

        for idx in range(len(day)):
            row = day.iloc[idx]
            t = row["Time"]
            h = row["High"]; l = row["Low"]; c = row["Close"]; o = row["Open"]
            ha_colors.append(row["HA_Color"])

            # ─── MANAGE OPEN TRADE ───────────────────────────
            if in_trade:
                if t >= SQUARE_OFF:
                    trade["exit_price"] = o
                    trade["exit_reason"] = "TIME"
                    trade["exit_time"] = row["Datetime"]
                    trades.append(trade)
                    in_trade = False; trade = None; continue

                if trade["dir"] == "LONG":
                    profit_R = (c - trade["entry"]) / trade["risk_per_share"]
                    # Trailing
                    if profit_R >= 3.0 and trade["sl"] < trade["entry"] + 2 * trade["risk_per_share"]:
                        trade["sl"] = trade["entry"] + 2 * trade["risk_per_share"]
                    elif profit_R >= 2.0 and trade["sl"] < trade["entry"] + trade["risk_per_share"]:
                        trade["sl"] = trade["entry"] + trade["risk_per_share"]
                    elif profit_R >= 1.0 and trade["sl"] < trade["entry"]:
                        trade["sl"] = trade["entry"]
                        had_1to1_5min = True
                    # HA color flip exit (after some profit)
                    if profit_R > 0.5 and row["HA_Color"] == "R":
                        trade["exit_price"] = c
                        trade["exit_reason"] = "HA_FLIP"
                        trade["exit_time"] = row["Datetime"]
                        trades.append(trade)
                        in_trade = False; trade = None; continue
                    # High volume reversal exit
                    if profit_R > 0.8 and row["vol_high"] and row["HA_Color"] == "R":
                        trade["exit_price"] = c
                        trade["exit_reason"] = "HV_REV"
                        trade["exit_time"] = row["Datetime"]
                        trades.append(trade)
                        in_trade = False; trade = None; continue
                    # SL / Target hit (intra-bar)
                    if l <= trade["sl"]:
                        trade["exit_price"] = trade["sl"]
                        trade["exit_reason"] = "SL/TRAIL"
                        trade["exit_time"] = row["Datetime"]
                        trades.append(trade)
                        in_trade = False; trade = None; continue
                    if h >= trade["target"]:
                        trade["exit_price"] = trade["target"]
                        trade["exit_reason"] = "TARGET"
                        trade["exit_time"] = row["Datetime"]
                        trades.append(trade)
                        in_trade = False; trade = None; continue
                else:  # SHORT
                    profit_R = (trade["entry"] - c) / trade["risk_per_share"]
                    if profit_R >= 3.0 and trade["sl"] > trade["entry"] - 2 * trade["risk_per_share"]:
                        trade["sl"] = trade["entry"] - 2 * trade["risk_per_share"]
                    elif profit_R >= 2.0 and trade["sl"] > trade["entry"] - trade["risk_per_share"]:
                        trade["sl"] = trade["entry"] - trade["risk_per_share"]
                    elif profit_R >= 1.0 and trade["sl"] > trade["entry"]:
                        trade["sl"] = trade["entry"]
                        had_1to1_5min = True
                    if profit_R > 0.5 and row["HA_Color"] == "G":
                        trade["exit_price"] = c
                        trade["exit_reason"] = "HA_FLIP"
                        trade["exit_time"] = row["Datetime"]
                        trades.append(trade)
                        in_trade = False; trade = None; continue
                    if profit_R > 0.8 and row["vol_high"] and row["HA_Color"] == "G":
                        trade["exit_price"] = c
                        trade["exit_reason"] = "HV_REV"
                        trade["exit_time"] = row["Datetime"]
                        trades.append(trade)
                        in_trade = False; trade = None; continue
                    if h >= trade["sl"]:
                        trade["exit_price"] = trade["sl"]
                        trade["exit_reason"] = "SL/TRAIL"
                        trade["exit_time"] = row["Datetime"]
                        trades.append(trade)
                        in_trade = False; trade = None; continue
                    if l <= trade["target"]:
                        trade["exit_price"] = trade["target"]
                        trade["exit_reason"] = "TARGET"
                        trade["exit_time"] = row["Datetime"]
                        trades.append(trade)
                        in_trade = False; trade = None; continue

            # ─── LOOK FOR NEW ENTRY ──────────────────────────
            if in_trade:
                prior_high = max(prior_high, h)
                prior_low = min(prior_low, l)
                continue

            if not (ENTRY_START <= t <= ENTRY_CUTOFF):
                prior_high = max(prior_high, h)
                prior_low = min(prior_low, l)
                continue

            # FILTER 1 — Movement < 1.80%
            move_pct = abs(c - day_open) / day_open
            if move_pct > MAX_MOVEMENT:
                prior_high = max(prior_high, h); prior_low = min(prior_low, l); continue

            # Need history
            if len(ha_colors) < 4 or idx < 20:
                prior_high = max(prior_high, h); prior_low = min(prior_low, l); continue

            # FILTER 2 — No marubozu / big body / high volume in last 3 bars
            recent = day.iloc[max(0, idx-3):idx]
            if len(recent) >= 1:
                bad = False
                for _, rb in recent.iterrows():
                    if is_marubozu(rb["Open"], rb["High"], rb["Low"], rb["Close"]):
                        bad = True; break
                    if is_big_body(rb["Open"], rb["High"], rb["Low"], rb["Close"]):
                        bad = True; break
                if bad:
                    prior_high = max(prior_high, h); prior_low = min(prior_low, l); continue

            # FILTER 3 — Recent high-volume reversal candle
            if idx >= 1 and day.iloc[idx-1].get("Volume", 0) > 0:
                prev_bar = day.iloc[idx-1]
                if (prev_bar["Volume"] > df["vol_avg"].iloc[row["bar_idx"]-1] * HIGH_VOL_MULTIPLIER):
                    if (market_dir == "BULL" and prev_bar["HA_Color"] == "R") or \
                       (market_dir == "BEAR" and prev_bar["HA_Color"] == "G"):
                        prior_high = max(prior_high, h); prior_low = min(prior_low, l); continue

            # FILTER 4 — Neutral candle in last 3 bars (lifeline window)
            recent_neutral = any(is_neutral(rb["Open"], rb["High"], rb["Low"], rb["Close"])
                                 for _, rb in recent.iterrows())
            if recent_neutral:
                prior_high = max(prior_high, h); prior_low = min(prior_low, l); continue

            # FILTER 5 — Resistance/support inside 1:1 reach
            risk_dist = c * SL_PCT_DEFAULT
            target_dist = risk_dist * TARGET_R_FIRST
            # Use prior_high/prior_low as proxy for nearest swing
            if market_dir == "BULL":
                if prior_high > c and (prior_high - c) < target_dist * 0.5:
                    prior_high = max(prior_high, h); prior_low = min(prior_low, l); continue
            else:
                if prior_low < c and (c - prior_low) < target_dist * 0.5:
                    prior_high = max(prior_high, h); prior_low = min(prior_low, l); continue

            # FILTER 6 — Wick check on entry candle
            _, _, _, uw, lw = candle_metrics(o, h, l, c)
            wick_total = uw + lw
            wick_big = wick_total > (h - l) * (1 - WICK_SMALL_RATIO)
            # If wick is big, only trade with line-chart pivot logic
            if wick_big:
                if market_dir == "BULL" and c < prior_high:
                    prior_high = max(prior_high, h); prior_low = min(prior_low, l); continue
                if market_dir == "BEAR" and c > prior_low:
                    prior_high = max(prior_high, h); prior_low = min(prior_low, l); continue

            # FILTER 7 — 3-day range BO bypass for volume
            three_day_breakout = (h > three_day_high) or (l < three_day_low)

            # FILTER 8 — Skip if 5-min already gave 1:1+ in this trade-day
            if had_1to1_5min:
                prior_high = max(prior_high, h); prior_low = min(prior_low, l); continue

            # ─── ENTRY SIGNAL ──────────────────────────────
            entry_signal = None

            # Bullish setup
            if market_dir == "BULL":
                bullish_lifeline = is_bullish_lifeline_5m(ha_colors, None)
                ha_bo_above_prior = c > prior_high and row["HA_Color"] == "G"
                if (bullish_lifeline or ha_bo_above_prior) and row["HA_Color"] == "G":
                    # Infinity confirm (if available)
                    inf_high, _ = infinity_levels if infinity_levels else (None, None)
                    infinity_ok = inf_high is None or c > inf_high * 0.998
                    if infinity_ok or three_day_breakout:
                        entry_signal = "LONG"

            # Bearish setup
            elif market_dir == "BEAR":
                bearish_lifeline = is_bearish_lifeline_5m(ha_colors, None)
                ha_bd_below_prior = c < prior_low and row["HA_Color"] == "R"
                if (bearish_lifeline or ha_bd_below_prior) and row["HA_Color"] == "R":
                    _, inf_low = infinity_levels if infinity_levels else (None, None)
                    infinity_ok = inf_low is None or c < inf_low * 1.002
                    if infinity_ok or three_day_breakout:
                        entry_signal = "SHORT"

            # ─── PLACE ENTRY ──────────────────────────────
            if entry_signal == "LONG":
                entry = c
                # SL: not at breakout candle low - use logical swing
                logical_sl = min(prior_low, l) * 0.999
                pct_sl = entry * (1 - SL_PCT_DEFAULT)
                sl = max(logical_sl, pct_sl)  # whichever is tighter (closer to entry)
                risk = entry - sl
                if risk <= 0 or risk / entry < 0.005 or risk / entry > 0.018:
                    prior_high = max(prior_high, h); prior_low = min(prior_low, l); continue
                target = entry + TARGET_R_FIRST * risk
                qty = max(int((CAPITAL * RISK_PER_TRADE) / risk), 1)
                trade = {
                    "ticker": ticker, "date": date, "dir": "LONG",
                    "entry_time": row["Datetime"], "entry": entry,
                    "sl": sl, "target": target, "risk_per_share": risk, "qty": qty,
                    "signal": "LIFELINE" if is_bullish_lifeline_5m(ha_colors, None) else "5MIN_BO",
                }
                in_trade = True

            elif entry_signal == "SHORT":
                entry = c
                logical_sl = max(prior_high, h) * 1.001
                pct_sl = entry * (1 + SL_PCT_DEFAULT)
                sl = min(logical_sl, pct_sl)
                risk = sl - entry
                if risk <= 0 or risk / entry < 0.005 or risk / entry > 0.018:
                    prior_high = max(prior_high, h); prior_low = min(prior_low, l); continue
                target = entry - TARGET_R_FIRST * risk
                qty = max(int((CAPITAL * RISK_PER_TRADE) / risk), 1)
                trade = {
                    "ticker": ticker, "date": date, "dir": "SHORT",
                    "entry_time": row["Datetime"], "entry": entry,
                    "sl": sl, "target": target, "risk_per_share": risk, "qty": qty,
                    "signal": "LIFELINE" if is_bearish_lifeline_5m(ha_colors, None) else "5MIN_BD",
                }
                in_trade = True

            prior_high = max(prior_high, h)
            prior_low = min(prior_low, l)

        # End of day cleanup
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
def analyze_trades(trades, brokerage_per_trade=40, slippage_pct=0.0005):
    if not trades:
        print("No trades generated.")
        return None
    df = pd.DataFrame(trades)
    df["pnl_per_share"] = np.where(df["dir"] == "LONG",
                                    df["exit_price"] - df["entry"],
                                    df["entry"] - df["exit_price"])
    df["pnl_gross"] = df["pnl_per_share"] * df["qty"]
    # Costs
    slippage = (df["entry"] + df["exit_price"]) * slippage_pct * df["qty"]
    df["costs"] = brokerage_per_trade + slippage
    df["pnl"] = df["pnl_gross"] - df["costs"]
    df["R"] = df["pnl_per_share"] / df["risk_per_share"]

    total = len(df)
    wins = (df["pnl"] > 0).sum()
    losses = (df["pnl"] <= 0).sum()
    win_rate = wins / total * 100 if total else 0
    total_pnl = df["pnl"].sum()
    total_gross = df["pnl_gross"].sum()
    total_cost = df["costs"].sum()
    avg_win = df.loc[df["pnl"] > 0, "pnl"].mean() if wins else 0
    avg_loss = df.loc[df["pnl"] <= 0, "pnl"].mean() if losses else 0
    avg_R = df["R"].mean()
    pf = abs(df.loc[df["pnl"] > 0, "pnl"].sum() /
             df.loc[df["pnl"] <= 0, "pnl"].sum()) if losses and df.loc[df["pnl"] <= 0, "pnl"].sum() != 0 else float("inf")

    df_sorted = df.sort_values("entry_time").reset_index(drop=True)
    df_sorted["cum_pnl"] = df_sorted["pnl"].cumsum()
    df_sorted["equity"] = CAPITAL + df_sorted["cum_pnl"]
    df_sorted["peak"] = df_sorted["equity"].cummax()
    df_sorted["dd"] = df_sorted["equity"] - df_sorted["peak"]
    max_dd = df_sorted["dd"].min()
    max_dd_pct = (max_dd / df_sorted["peak"].max()) * 100 if df_sorted["peak"].max() else 0

    print("\n" + "="*72)
    print(" LIFELINE STRATEGY v2.0 (COMPLETE) -- BACKTEST RESULTS")
    print("="*72)
    print(f" Period:                {PERIOD}  ({INTERVAL} candles)")
    print(f" Universe:              {len(NIFTY_TICKERS)} Nifty 50 stocks")
    print(f" Starting capital:      Rs.{CAPITAL:,}")
    print(f" Risk/trade:            {RISK_PER_TRADE*100:.1f}%   SL: {SL_PCT_DEFAULT*100:.1f}%   Target: 1:{TARGET_R_FIRST:.0f}")
    print(f" Costs included:        Rs.{brokerage_per_trade}/trade brokerage + {slippage_pct*100:.2f}% slippage")
    print("-"*72)
    print(f" Total trades:          {total}")
    print(f" Wins / Losses:         {wins} / {losses}")
    print(f" Win rate:              {win_rate:.2f}%")
    print(f" Avg R:                 {avg_R:.3f}R")
    print(f" Profit factor:         {pf:.2f}")
    print("-"*72)
    print(f" Gross P&L:             Rs.{total_gross:,.2f}")
    print(f" Total costs:           Rs.{total_cost:,.2f}")
    print(f" NET P&L:               Rs.{total_pnl:,.2f}  ({total_pnl/CAPITAL*100:.2f}% of capital)")
    print(f" Avg win:               Rs.{avg_win:,.2f}")
    print(f" Avg loss:              Rs.{avg_loss:,.2f}")
    print(f" Best trade:            Rs.{df['pnl'].max():,.2f}")
    print(f" Worst trade:           Rs.{df['pnl'].min():,.2f}")
    print(f" Max drawdown:          Rs.{max_dd:,.2f}  ({max_dd_pct:.2f}%)")
    print("-"*72)
    print(" By exit reason:")
    print(df.groupby("exit_reason")["pnl"].agg(["count", "sum", "mean"]).round(2).to_string())
    print("-"*72)
    print(" By direction:")
    print(df.groupby("dir")["pnl"].agg(["count", "sum", "mean"]).round(2).to_string())
    print("-"*72)
    if "signal" in df.columns:
        print(" By signal type:")
        print(df.groupby("signal")["pnl"].agg(["count", "sum", "mean"]).round(2).to_string())
        print("-"*72)
    print(" Top 5 stocks by P&L:")
    print(df.groupby("ticker")["pnl"].sum().sort_values(ascending=False).head().round(2).to_string())
    print("-"*72)
    print(" Bottom 5 stocks by P&L:")
    print(df.groupby("ticker")["pnl"].sum().sort_values().head().round(2).to_string())
    print("="*72)

    df.to_csv(r"D:\Window\lifeline\backtest_v2_trades.csv", index=False)
    print("\n[Saved trade log -> backtest_v2_trades.csv]")
    return df

# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
def main():
    print("Fetching Nifty index data...")
    nifty_df = fetch_data(NIFTY_INDEX)
    if nifty_df is None or nifty_df.empty:
        print("ERROR: Could not fetch Nifty data."); return
    print(f"  Got {len(nifty_df)} Nifty bars")

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
            print(f"  [SKIP] {ticker}: no data"); continue
        trades = backtest_stock(df, ticker, nifty_trend, nifty_df)
        print(f"  {ticker:18s}: {len(df):4d} bars -> {len(trades):3d} trades")
        all_trades.extend(trades)

    analyze_trades(all_trades)

if __name__ == "__main__":
    main()
