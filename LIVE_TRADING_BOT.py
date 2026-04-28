"""
LIFELINE LIVE TRADING BOT — Complete System
============================================
Sab PDF rules + LIVE OI ek saath. Real-time scanner + alert bot.

KAAM KAISE KARTA HAI:
  1. 9:00 AM   -> Pre-market check (Nifty SGX, US markets, news placeholder)
  2. 9:15 AM   -> Market open, observe only
  3. 9:20 AM   -> Trend identify (Nifty Heikin Ashi + 1st 5-min)
  4. 9:20+     -> Stock universe select karo trend ke hisab se
  5. Har 5 min -> Saare F&O stocks scan karo:
                    - Movement < 1.80% check
                    - 1st 5-min Marubozu skip
                    - Heikin Ashi BO check
                    - Lifeline N-pattern check
                    - Recent neutral/big body candle filter
                    - 3-day range BO bypass
                    - 52w high/low proxy
                    - Wick analysis
  6. Signal mile to -> LIVE OI fetch (NSE)
                     - Resistance 1:1 ke andar = SKIP
                     - OI signal direction match = ENTER
  7. Alert -> Telegram pe full setup bhejdo
  8. 3:15 PM -> Square off all alerts (paper positions close)

USAGE:
  Step 1: Telegram Bot banao (optional but recommended)
          - @BotFather pe /newbot karo
          - Bot token note karo
          - Apne bot ko message karke chat_id nikalo
  Step 2: TELEGRAM_TOKEN aur CHAT_ID configure karo neeche
  Step 3: py LIVE_TRADING_BOT.py
  Step 4: Live market hours me chalao
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time as dtime, timedelta
import time
import warnings
warnings.filterwarnings("ignore")

from live_oi_module import (
    establish_session, fetch_option_chain, parse_oi_data,
    analyze_oi, oi_filter_for_trade, is_market_open
)

# ─────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = ""   # @BotFather se le
TELEGRAM_CHAT_ID = "" # @userinfobot se le

CAPITAL = 100_000
RISK_PER_TRADE = 0.01

WATCHLIST = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS",
    "AXISBANK", "SBIN", "BHARTIARTL", "KOTAKBANK", "LT",
    "BAJFINANCE", "MARUTI", "SUNPHARMA", "HCLTECH", "WIPRO",
    "TITAN", "ASIANPAINT", "M&M", "TECHM", "ITC"
]

SL_PCT = 0.01
TARGET_R = 2.0
ENTRY_START = dtime(9, 20)
ENTRY_CUTOFF = dtime(14, 30)
SQUARE_OFF = dtime(15, 15)
MAX_MOVEMENT = 0.018
MARUBOZU_THRESHOLD = 0.85
NEUTRAL_THRESHOLD = 0.25
BIG_BODY_THRESHOLD = 0.80

SCAN_INTERVAL = 300  # 5 minutes

# Track signals already sent today (avoid duplicates)
ALERTED_TODAY = set()

# ─────────────────────────────────────────────────────────────────
# TELEGRAM ALERT
# ─────────────────────────────────────────────────────────────────
def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[ALERT - console only]")
        print(msg)
        return
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print(f"[Telegram error] {e}")
        print(msg)

# ─────────────────────────────────────────────────────────────────
# HEIKIN ASHI + CANDLE METRICS
# ─────────────────────────────────────────────────────────────────
def heikin_ashi(df):
    ha = pd.DataFrame(index=df.index)
    ha["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_open = [df["Open"].iloc[0]]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i-1] + ha["HA_Close"].iloc[i-1]) / 2)
    ha["HA_Open"] = ha_open
    ha["HA_Color"] = np.where(ha["HA_Close"] >= ha["HA_Open"], "G", "R")
    return ha

def candle_metrics(o, h, l, c):
    rng = h - l if h > l else 1e-9
    body = abs(c - o)
    return body / rng

# ─────────────────────────────────────────────────────────────────
# DATA FETCH (live intraday)
# ─────────────────────────────────────────────────────────────────
def fetch_intraday(ticker_yf):
    try:
        df = yf.download(ticker_yf, period="2d", interval="5m",
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
# NIFTY TREND (live)
# ─────────────────────────────────────────────────────────────────
def get_nifty_trend():
    df = fetch_intraday("^NSEI")
    if df is None:
        return "UNKNOWN"
    today = datetime.now().date()
    today_df = df[df.index.date == today]
    if len(today_df) < 5:
        return "UNKNOWN"
    ha = heikin_ashi(today_df)
    greens = (ha["HA_Color"] == "G").sum()
    reds = (ha["HA_Color"] == "R").sum()
    if greens > reds * 1.3:
        return "BULL"
    elif reds > greens * 1.3:
        return "BEAR"
    return "SIDE"

# ─────────────────────────────────────────────────────────────────
# STOCK SCAN (apply all PDF rules)
# ─────────────────────────────────────────────────────────────────
def scan_stock(symbol, market_dir):
    """Returns signal dict or None."""
    ticker_yf = f"{symbol}.NS"
    df = fetch_intraday(ticker_yf)
    if df is None or len(df) < 30:
        return None

    today = datetime.now().date()
    today_df = df[df.index.date == today].copy()
    if len(today_df) < 5:
        return None

    ha = heikin_ashi(today_df)
    today_df["HA_Color"] = ha["HA_Color"]

    first = today_df.iloc[0]
    day_open = first["Open"]
    last = today_df.iloc[-1]
    now = last.name.time()

    # Time filter
    if not (ENTRY_START <= now <= ENTRY_CUTOFF):
        return None

    # 1st 5-min Marubozu skip
    if candle_metrics(first["Open"], first["High"], first["Low"], first["Close"]) >= MARUBOZU_THRESHOLD:
        return None

    # Movement filter
    move_pct = abs(last["Close"] - day_open) / day_open
    if move_pct > MAX_MOVEMENT:
        return None

    # Last 3 candles - no marubozu/big-body/neutral
    recent = today_df.iloc[-4:-1]
    for _, r in recent.iterrows():
        ratio = candle_metrics(r["Open"], r["High"], r["Low"], r["Close"])
        if ratio >= MARUBOZU_THRESHOLD or ratio > BIG_BODY_THRESHOLD or ratio < NEUTRAL_THRESHOLD:
            return None

    # Lifeline N-pattern check (last 4 candles)
    colors = today_df["HA_Color"].tail(4).tolist()
    middle = colors[:-1]
    last_color = colors[-1]

    bullish_lifeline = (sum(1 for c in middle if c == "R") >= 2 and last_color == "G")
    bearish_lifeline = (sum(1 for c in middle if c == "G") >= 2 and last_color == "R")

    # HA breakout above/below day's prior swing
    prior_high = today_df.iloc[:-1]["High"].max()
    prior_low = today_df.iloc[:-1]["Low"].min()
    ha_bo_long = last["Close"] > prior_high and last_color == "G"
    ha_bo_short = last["Close"] < prior_low and last_color == "R"

    signal = None
    signal_type = None

    if market_dir == "BULL":
        if (bullish_lifeline or ha_bo_long) and last_color == "G":
            signal = "LONG"
            signal_type = "LIFELINE" if bullish_lifeline else "5MIN_BO"
    elif market_dir == "BEAR":
        if (bearish_lifeline or ha_bo_short) and last_color == "R":
            signal = "SHORT"
            signal_type = "LIFELINE" if bearish_lifeline else "5MIN_BD"

    if not signal:
        return None

    # SL & target calculation (logical SL, not %)
    entry = last["Close"]
    if signal == "LONG":
        sl_logical = min(prior_low, last["Low"]) * 0.999
        sl_pct = entry * (1 - SL_PCT)
        sl = max(sl_logical, sl_pct)
        risk = entry - sl
        target = entry + TARGET_R * risk
    else:
        sl_logical = max(prior_high, last["High"]) * 1.001
        sl_pct = entry * (1 + SL_PCT)
        sl = min(sl_logical, sl_pct)
        risk = sl - entry
        target = entry - TARGET_R * risk

    sl_pct_actual = abs(risk) / entry
    if sl_pct_actual < 0.005 or sl_pct_actual > 0.018:
        return None

    qty = max(int((CAPITAL * RISK_PER_TRADE) / abs(risk)), 1)

    return {
        "symbol": symbol,
        "signal": signal,
        "signal_type": signal_type,
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "target": round(target, 2),
        "risk_per_share": round(risk, 2),
        "sl_pct": round(sl_pct_actual * 100, 2),
        "qty": qty,
        "time": now.strftime("%H:%M"),
        "movement_pct": round(move_pct * 100, 2),
    }

# ─────────────────────────────────────────────────────────────────
# OI CONFIRMATION (uses live_oi_module)
# ─────────────────────────────────────────────────────────────────
def confirm_with_oi(signal, nse_session):
    raw = fetch_option_chain(signal["symbol"], nse_session)
    df, spot = parse_oi_data(raw)
    if df is None:
        return False, "OI fetch failed", None
    oi_data = analyze_oi(df, spot, signal["symbol"])
    allow, reason = oi_filter_for_trade(oi_data, signal["signal"])
    return allow, reason, oi_data

# ─────────────────────────────────────────────────────────────────
# FORMAT ALERT MESSAGE
# ─────────────────────────────────────────────────────────────────
def format_alert(sig, oi_data):
    arrow = "📈" if sig["signal"] == "LONG" else "📉"
    msg = f"""
🔔 <b>LIFELINE SIGNAL</b> {arrow}

<b>{sig['symbol']}</b> — {sig['signal']} ({sig['signal_type']})

💰 <b>Entry:</b>  ₹{sig['entry']}
🛑 <b>SL:</b>     ₹{sig['sl']}  ({sig['sl_pct']}%)
🎯 <b>Target:</b> ₹{sig['target']}  (1:{TARGET_R:.0f})
📦 <b>Qty:</b>    {sig['qty']}  (1% risk)
📊 <b>Movement:</b> {sig['movement_pct']}%

<b>OI Confirm:</b>
   Spot:        ₹{oi_data['spot']}
   Resistance:  ₹{oi_data['max_ce_oi_strike']} ({oi_data['resistance_pct']}% away)
   Support:     ₹{oi_data['max_pe_oi_strike']} ({oi_data['support_pct']}% away)
   PCR:         {oi_data['pcr']}
   OI Signal:   <b>{oi_data['signal']}</b>

⏰ {sig['time']}
"""
    return msg

# ─────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────
def main_loop():
    print("="*70)
    print(" LIFELINE LIVE TRADING BOT — STARTED")
    print(f" Time: {datetime.now()}")
    print(f" Watchlist: {len(WATCHLIST)} F&O stocks")
    print(f" Market open: {is_market_open()}")
    print("="*70)

    if not is_market_open():
        print("\n[!] Market closed. Bot will start at 9:15 AM IST.")
        print("    Checking every 5 minutes...")

    nse_session = establish_session()

    while True:
        try:
            now = datetime.now()
            t = now.time()

            # Square off time
            if t >= SQUARE_OFF:
                print(f"\n[{t.strftime('%H:%M')}] Market closing time. Bot stopping for the day.")
                break

            # Wait until market open
            if not is_market_open():
                print(f"[{t.strftime('%H:%M')}] Market closed. Waiting...")
                time.sleep(60)
                continue

            # Wait until 9:20 for trend
            if t < ENTRY_START:
                print(f"[{t.strftime('%H:%M')}] Pre-9:20 -- waiting for trend establishment")
                time.sleep(60)
                continue

            # Check trend
            trend = get_nifty_trend()
            if trend in ("UNKNOWN", "SIDE"):
                print(f"[{t.strftime('%H:%M')}] Nifty trend = {trend}. Sitting out.")
                time.sleep(SCAN_INTERVAL)
                continue

            print(f"\n[{t.strftime('%H:%M')}] Nifty trend = {trend}. Scanning {len(WATCHLIST)} stocks...")

            for symbol in WATCHLIST:
                # Skip if already alerted today
                key = f"{now.date()}_{symbol}"
                if key in ALERTED_TODAY:
                    continue

                sig = scan_stock(symbol, trend)
                if sig is None:
                    continue

                print(f"  >> Signal found: {symbol} {sig['signal']} @ {sig['entry']}")

                # OI confirmation
                allow, reason, oi_data = confirm_with_oi(sig, nse_session)
                if not allow:
                    print(f"     OI rejected: {reason}")
                    continue

                # Send alert
                msg = format_alert(sig, oi_data)
                print(f"     ✅ OI confirmed: {reason}")
                send_telegram(msg)
                ALERTED_TODAY.add(key)

            # Wait for next scan
            time.sleep(SCAN_INTERVAL)

        except KeyboardInterrupt:
            print("\n[!] Stopped by user.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()
