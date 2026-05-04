"""
ZERO-TOUCH AUTO TRADING BOT
============================
Tu kuch nahi karta. Bot sab khud:
  - Roz 9:15 AM auto start
  - Stocks scan, signals generate
  - OI check (live NSE)
  - Dhan paper account me order place
  - SL/Target/Trailing auto manage
  - 3:15 PM auto square-off
  - Telegram pe report
  - 3:30 PM auto close

FIRST-TIME SETUP (30 min, ek baar):
  1. Dhan account banao -> https://dhan.co (free, KYC)
  2. Paper trading enable -> Profile > Trading Preferences
  3. API access enable -> https://api.dhan.co (free)
  4. CLIENT_ID + ACCESS_TOKEN nikalo
  5. Telegram bot banao -> @BotFather -> /newbot -> token note
  6. Apne bot ko 'hi' bhejo, fir https://api.telegram.org/bot<TOKEN>/getUpdates
     se chat_id nikalo
  7. Niche credentials fill karo
  8. pip install dhanhq pandas yfinance requests
  9. Daily: py ZERO_TOUCH_BOT.py (ya Windows Task Scheduler se auto)
"""

import os
import time
import json
from datetime import datetime, time as dtime
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import warnings
warnings.filterwarnings("ignore")

def to_float(x):
    """Coerce scalar/Series/ndarray/0-d to a plain Python float.
    yfinance occasionally returns multi-index columns or duplicate columns,
    so df['Close'].iloc[-1] can be a Series instead of scalar — this handles it."""
    try:
        return float(x)
    except (TypeError, ValueError):
        try:
            arr = np.asarray(x).flatten()
            if arr.size == 0:
                return float("nan")
            return float(arr[0])
        except Exception:
            return float("nan")

# ─────────────────────────────────────────────────────────────────
# 🔑 CONFIG — Sirf 2 cheezein fill karna (Telegram)
# ─────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN    = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID  = os.environ.get("TELEGRAM_CHAT_ID", "")

# Pure paper mode -- Dhan/broker ki need nahi
PURE_PAPER = True
CAPITAL    = 100_000
RISK_PCT   = 0.01    # 1% per trade
MAX_TRADES_PER_DAY = 5
MAX_DAILY_LOSS_PCT = 0.03  # 3% daily loss = stop bot

# Dhan placeholders (PURE_PAPER mode me kuch nahi karte)
DHAN_CLIENT_ID    = ""
DHAN_ACCESS_TOKEN = ""
PAPER_MODE        = True

# ─────────────────────────────────────────────────────────────────
# WATCHLIST (high-quality F&O stocks)
# ─────────────────────────────────────────────────────────────────
WATCHLIST = [
    # (symbol, yf_ticker, dhan_security_id, sector)
    ("RELIANCE",   "RELIANCE.NS",   2885,  "ENERGY"),
    ("HDFCBANK",   "HDFCBANK.NS",   1333,  "BANK"),
    ("ICICIBANK",  "ICICIBANK.NS",  4963,  "BANK"),
    ("INFY",       "INFY.NS",       1594,  "IT"),
    ("TCS",        "TCS.NS",        11536, "IT"),
    ("SBIN",       "SBIN.NS",       3045,  "BANK"),
    ("AXISBANK",   "AXISBANK.NS",   5900,  "BANK"),
    ("KOTAKBANK",  "KOTAKBANK.NS",  1922,  "BANK"),
    ("LT",         "LT.NS",         11483, "INFRA"),
    ("BHARTIARTL", "BHARTIARTL.NS", 10604, "TELECOM"),
    ("BAJFINANCE", "BAJFINANCE.NS", 317,   "NBFC"),
    ("MARUTI",     "MARUTI.NS",     10999, "AUTO"),
    ("SUNPHARMA",  "SUNPHARMA.NS",  3351,  "PHARMA"),
    ("HCLTECH",    "HCLTECH.NS",    7229,  "IT"),
    ("WIPRO",      "WIPRO.NS",      3787,  "IT"),
]

# ─────────────────────────────────────────────────────────────────
# F&O Universe for dynamic morning scan (~72 liquid stocks)
# ─────────────────────────────────────────────────────────────────
FNO_UNIVERSE = [
    # BANK
    ("HDFCBANK",   "HDFCBANK.NS",    1333,  "BANK"),
    ("ICICIBANK",  "ICICIBANK.NS",   4963,  "BANK"),
    ("AXISBANK",   "AXISBANK.NS",    5900,  "BANK"),
    ("SBIN",       "SBIN.NS",        3045,  "BANK"),
    ("KOTAKBANK",  "KOTAKBANK.NS",   1922,  "BANK"),
    ("BANKBARODA", "BANKBARODA.NS",  0,     "BANK"),
    ("PNB",        "PNB.NS",         0,     "BANK"),
    ("CANBK",      "CANBK.NS",       0,     "BANK"),
    ("INDUSINDBK", "INDUSINDBK.NS",  0,     "BANK"),
    ("IDFCFIRSTB", "IDFCFIRSTB.NS",  0,     "BANK"),
    ("BANDHANBNK", "BANDHANBNK.NS",  0,     "BANK"),
    ("FEDERALBNK", "FEDERALBNK.NS",  0,     "BANK"),
    # NBFC
    ("BAJFINANCE", "BAJFINANCE.NS",  317,   "NBFC"),
    ("BAJAJFINSV", "BAJAJFINSV.NS",  0,     "NBFC"),
    ("CHOLAFIN",   "CHOLAFIN.NS",    0,     "NBFC"),
    ("MUTHOOTFIN", "MUTHOOTFIN.NS",  0,     "NBFC"),
    ("LICHSGFIN",  "LICHSGFIN.NS",   0,     "NBFC"),
    # IT
    ("TCS",        "TCS.NS",         11536, "IT"),
    ("INFY",       "INFY.NS",        1594,  "IT"),
    ("HCLTECH",    "HCLTECH.NS",     7229,  "IT"),
    ("WIPRO",      "WIPRO.NS",       3787,  "IT"),
    ("TECHM",      "TECHM.NS",       0,     "IT"),
    ("LTIM",       "LTIM.NS",        0,     "IT"),
    ("MPHASIS",    "MPHASIS.NS",     0,     "IT"),
    # AUTO
    ("MARUTI",     "MARUTI.NS",      10999, "AUTO"),
    ("TATAMOTORS", "TATAMOTORS.NS",  0,     "AUTO"),
    ("M&M",        "M&M.NS",         0,     "AUTO"),
    ("BAJAJ-AUTO", "BAJAJ-AUTO.NS",  0,     "AUTO"),
    ("EICHERMOT",  "EICHERMOT.NS",   0,     "AUTO"),
    ("HEROMOTOCO", "HEROMOTOCO.NS",  0,     "AUTO"),
    ("ASHOKLEY",   "ASHOKLEY.NS",    0,     "AUTO"),
    ("TVSMOTOR",   "TVSMOTOR.NS",    0,     "AUTO"),
    # METAL
    ("TATASTEEL",  "TATASTEEL.NS",   0,     "METAL"),
    ("JSWSTEEL",   "JSWSTEEL.NS",    0,     "METAL"),
    ("HINDALCO",   "HINDALCO.NS",    0,     "METAL"),
    ("VEDL",       "VEDL.NS",        0,     "METAL"),
    ("SAIL",       "SAIL.NS",        0,     "METAL"),
    ("JINDALSTEL", "JINDALSTEL.NS",  0,     "METAL"),
    # ENERGY
    ("RELIANCE",   "RELIANCE.NS",    2885,  "ENERGY"),
    ("ONGC",       "ONGC.NS",        0,     "ENERGY"),
    ("BPCL",       "BPCL.NS",        0,     "ENERGY"),
    ("IOC",        "IOC.NS",         0,     "ENERGY"),
    ("HINDPETRO",  "HINDPETRO.NS",   0,     "ENERGY"),
    ("GAIL",       "GAIL.NS",        0,     "ENERGY"),
    ("POWERGRID",  "POWERGRID.NS",   0,     "ENERGY"),
    ("NTPC",       "NTPC.NS",        0,     "ENERGY"),
    ("TATAPOWER",  "TATAPOWER.NS",   0,     "ENERGY"),
    ("ADANIGREEN", "ADANIGREEN.NS",  0,     "ENERGY"),
    # PHARMA
    ("SUNPHARMA",  "SUNPHARMA.NS",   3351,  "PHARMA"),
    ("DRREDDY",    "DRREDDY.NS",     0,     "PHARMA"),
    ("CIPLA",      "CIPLA.NS",       0,     "PHARMA"),
    ("DIVISLAB",   "DIVISLAB.NS",    0,     "PHARMA"),
    ("AUROPHARMA", "AUROPHARMA.NS",  0,     "PHARMA"),
    ("LUPIN",      "LUPIN.NS",       0,     "PHARMA"),
    # INFRA
    ("LT",         "LT.NS",          11483, "INFRA"),
    ("ADANIENT",   "ADANIENT.NS",    0,     "INFRA"),
    ("ADANIPORTS", "ADANIPORTS.NS",  0,     "INFRA"),
    ("DLF",        "DLF.NS",         0,     "INFRA"),
    ("GODREJPROP", "GODREJPROP.NS",  0,     "INFRA"),
    # FMCG
    ("HINDUNILVR", "HINDUNILVR.NS",  0,     "FMCG"),
    ("ITC",        "ITC.NS",         0,     "FMCG"),
    ("BRITANNIA",  "BRITANNIA.NS",   0,     "FMCG"),
    ("NESTLEIND",  "NESTLEIND.NS",   0,     "FMCG"),
    # TELECOM
    ("BHARTIARTL", "BHARTIARTL.NS",  10604, "TELECOM"),
]

# Sector → NSE index ticker (for sector momentum filter)
SECTOR_INDICES = {
    "BANK":    "^NSEBANK",
    "IT":      "^CNXIT",
    "AUTO":    "^CNXAUTO",
    "PHARMA":  "^CNXPHARMA",
    "NBFC":    "^CNXFIN",
    "INFRA":   "^CNXINFRA",
    "ENERGY":  "^CNXENERGY",
    "TELECOM": "^CNXMEDIA",
    "METAL":   "^CNXMETAL",
    "FMCG":    "^CNXFMCG",
}

# ─────────────────────────────────────────────────────────────────
# Strategy params
# ─────────────────────────────────────────────────────────────────
SL_PCT          = 0.01
TARGET_R        = 2.0
ENTRY_START     = dtime(9, 25)
ENTRY_CUTOFF    = dtime(14, 30)
SQUARE_OFF      = dtime(15, 15)
SCAN_INTERVAL   = 300  # 5 minutes
MAX_MOVEMENT    = 0.018
MARUBOZU_TH     = 0.85
NEUTRAL_TH      = 0.25
BIG_BODY_TH     = 0.80
DEAD_ZONE_START = dtime(11, 30)
DEAD_ZONE_END   = dtime(12, 30)
VOL_SPIKE_MULT  = 1.5

# ─────────────────────────────────────────────────────────────────
# State (persisted to disk so bot can resume)
# ─────────────────────────────────────────────────────────────────
STATE_FILE = "bot_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f: return json.load(f)
    return {"open_positions": {}, "alerted": [], "trades_today": 0,
            "daily_pnl": 0, "date": str(datetime.now().date())}

def save_state(s):
    with open(STATE_FILE, "w") as f: json.dump(s, f, indent=2, default=str)

# ─────────────────────────────────────────────────────────────────
# Telegram
# ─────────────────────────────────────────────────────────────────
def tg(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))
    if not TELEGRAM_TOKEN or "YOUR_" in TELEGRAM_TOKEN: return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10)
    except: pass

# ─────────────────────────────────────────────────────────────────
# Dhan SDK (paper or real)
# ─────────────────────────────────────────────────────────────────
def get_dhan():
    if PURE_PAPER:
        return None  # No broker needed -- pure internal simulation
    if not DHAN_CLIENT_ID:
        return None
    try:
        from dhanhq import dhanhq
        return dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
    except ImportError:
        tg("⚠️ pip install dhanhq for live mode")
        return None
    except Exception as e:
        tg(f"⚠️ Dhan connection failed: {e}")
        return None

def place_order(dhan, security_id, side, qty, price, sl, target):
    if dhan is None or PAPER_MODE:
        return f"PAPER-{datetime.now().strftime('%H%M%S')}"
    try:
        order = dhan.place_order(
            security_id=str(security_id),
            exchange_segment=dhan.NSE,
            transaction_type=dhan.BUY if side == "LONG" else dhan.SELL,
            quantity=qty,
            order_type=dhan.MARKET,
            product_type=dhan.INTRA,
            price=0
        )
        return order.get("data", {}).get("orderId", "UNKNOWN")
    except Exception as e:
        tg(f"❌ Order failed: {e}")
        return None

def square_off_all(dhan, state):
    for sym, pos in list(state["open_positions"].items()):
        try:
            if dhan and not PAPER_MODE:
                try:
                    dhan.place_order(
                        security_id=str(pos["security_id"]),
                        exchange_segment=dhan.NSE,
                        transaction_type=dhan.SELL if pos["side"] == "LONG" else dhan.BUY,
                        quantity=pos["qty"],
                        order_type=dhan.MARKET,
                        product_type=dhan.INTRA, price=0)
                except: pass
            df = fetch(pos["yf_ticker"])
            if df is not None and not df.empty:
                close_px = to_float(df["Close"].iloc[-1])
                if close_px != close_px:  # NaN check
                    raise ValueError("close price NaN")
                entry = to_float(pos["entry"])
                qty = to_float(pos["qty"])
                pnl = (close_px - entry) * qty if pos["side"] == "LONG" \
                      else (entry - close_px) * qty
                state["daily_pnl"] = to_float(state.get("daily_pnl", 0)) + pnl
                tg(f"🔚 {sym} squared off @ ₹{close_px:.2f} | P&L: ₹{pnl:+.0f}")
            else:
                tg(f"🔚 {sym} squared off (no live price)")
        except Exception as e:
            tg(f"⚠️ {sym} squareoff issue: {e} — position cleared")
        finally:
            state["open_positions"].pop(sym, None)
    save_state(state)

# ─────────────────────────────────────────────────────────────────
# Heikin Ashi
# ─────────────────────────────────────────────────────────────────
def ha(df):
    h = pd.DataFrame(index=df.index)
    h["C"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    o = [df["Open"].iloc[0]]
    for i in range(1, len(df)): o.append((o[i-1] + h["C"].iloc[i-1]) / 2)
    h["O"] = o
    h["color"] = np.where(h["C"] >= h["O"], "G", "R")
    return h

def body_ratio(o, h, l, c):
    rng = h - l if h > l else 1e-9
    return abs(c - o) / rng

# ─────────────────────────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────────────────────────
def fetch(ticker):
    try:
        df = yf.download(ticker, period="2d", interval="5m",
                         progress=False, auto_adjust=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # Drop duplicate columns (yfinance edge case: 'Close' + 'Adj Close' both flatten)
        df = df.loc[:, ~df.columns.duplicated()]
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_convert("Asia/Kolkata").tz_localize(None)
        needed = ["Open","High","Low","Close","Volume"]
        if not all(c in df.columns for c in needed):
            return None
        return df[needed].dropna()
    except: return None

# ─────────────────────────────────────────────────────────────────
# Sector Momentum — top 2 green sectors of the day
# ─────────────────────────────────────────────────────────────────
def get_top_sectors():
    """Fetch each sectoral index % change from open. Return top 2 positive sectors.
    Returns None if data unavailable (caller treats None = allow all sectors)."""
    perf = {}
    for sector, ticker in SECTOR_INDICES.items():
        df = fetch(ticker)
        if df is None or df.empty:
            continue
        today = df[df.index.date == datetime.now().date()]
        if len(today) < 2:
            continue
        open_px = to_float(today["Open"].iloc[0])
        last_px = to_float(today["Close"].iloc[-1])
        if open_px > 0:
            perf[sector] = (last_px - open_px) / open_px * 100
    if not perf:
        return None
    ranked = sorted(perf.items(), key=lambda x: x[1], reverse=True)
    top = [s for s, pct in ranked[:3] if pct > 0]
    result_str = ", ".join(f"{s}({pct:+.2f}%)" for s, pct in ranked[:4])
    print(f"  📊 Sector scan: {result_str}")
    return top if top else None

def calc_vwap(df_today):
    """VWAP = cumulative(typical_price * volume) / cumulative(volume)."""
    tp = (df_today["High"] + df_today["Low"] + df_today["Close"]) / 3
    vol = df_today["Volume"].replace(0, np.nan).fillna(1)
    vwap = (tp * vol).cumsum() / vol.cumsum()
    return to_float(vwap.iloc[-1])

def open_equals_low(df_today, tolerance=0.0015):
    """True if any of the last 4 candles had Open ≈ Low (no sellers from open)."""
    for _, row in df_today.iloc[-4:].iterrows():
        o, l = to_float(row["Open"]), to_float(row["Low"])
        if o > 0 and (o - l) / o <= tolerance:
            return True
    return False

# ─────────────────────────────────────────────────────────────────
# Trend
# ─────────────────────────────────────────────────────────────────
def nifty_trend():
    df = fetch("^NSEI")
    if df is None: return "UNKNOWN"
    today = df[df.index.date == datetime.now().date()]
    if len(today) < 5: return "UNKNOWN"
    h = ha(today)
    g, r = (h["color"]=="G").sum(), (h["color"]=="R").sum()
    if g > r * 1.3: return "BULL"
    if r > g * 1.3: return "BEAR"
    return "SIDE"

# ─────────────────────────────────────────────────────────────────
# Signal
# ─────────────────────────────────────────────────────────────────
def find_signal(symbol, yf_ticker, security_id, market_dir):
    df = fetch(yf_ticker)
    if df is None or len(df) < 30: return None
    today = df[df.index.date == datetime.now().date()].copy()
    if len(today) < 5: return None

    h = ha(today)
    today["color"] = h["color"]
    first = today.iloc[0]
    last = today.iloc[-1]

    # Filter 1: First candle not marubozu
    if body_ratio(first["Open"],first["High"],first["Low"],first["Close"]) >= MARUBOZU_TH:
        return None
    # Filter 2: Day hasn't moved too far already
    move = abs(last["Close"] - first["Open"]) / first["Open"]
    if move > MAX_MOVEMENT: return None

    # Filter 3: Last 3 candles balanced (no marubozu/big/neutral)
    for _, r in today.iloc[-4:-1].iterrows():
        ratio = body_ratio(r["Open"], r["High"], r["Low"], r["Close"])
        if ratio >= MARUBOZU_TH or ratio > BIG_BODY_TH or ratio < NEUTRAL_TH:
            return None

    # Filter 4: VWAP — close must be above VWAP for LONG (institutional bias)
    vwap = calc_vwap(today)
    entry_close = to_float(last["Close"])
    if market_dir == "BULL" and entry_close < vwap:
        return None
    if market_dir == "BEAR" and entry_close > vwap:
        return None

    # Filter 5: Open=Low on any recent candle (no sellers, clean bullish pressure)
    if market_dir == "BULL" and not open_equals_low(today):
        return None

    # Lifeline + HA BO
    colors = today["color"].tail(4).tolist()
    middle, last_c = colors[:-1], colors[-1]
    bull_ll = sum(c=="R" for c in middle) >= 2 and last_c == "G"
    bear_ll = sum(c=="G" for c in middle) >= 2 and last_c == "R"
    prior_h = today.iloc[:-1]["High"].max()
    prior_l = today.iloc[:-1]["Low"].min()
    bo_long  = last["Close"] > prior_h and last_c == "G"
    bo_short = last["Close"] < prior_l and last_c == "R"

    side = None
    if market_dir == "BULL" and (bull_ll or bo_long) and last_c == "G":
        side = "LONG"
    elif market_dir == "BEAR" and (bear_ll or bo_short) and last_c == "R":
        side = "SHORT"
    if not side: return None

    # Filter: EMA 9 > 21 trend confirmation (on full 2-day dataset)
    if len(df) >= 21:
        ema9  = df["Close"].ewm(span=9,  adjust=False).mean()
        ema21 = df["Close"].ewm(span=21, adjust=False).mean()
        if side == "LONG"  and to_float(ema9.iloc[-1]) <= to_float(ema21.iloc[-1]):
            return None
        if side == "SHORT" and to_float(ema9.iloc[-1]) >= to_float(ema21.iloc[-1]):
            return None

    # Filter: Volume spike on trigger candle (1.5x recent average)
    avg_vol  = today["Volume"].iloc[-11:-1].mean()
    last_vol = to_float(last["Volume"])
    if avg_vol > 0 and last_vol < avg_vol * VOL_SPIKE_MULT:
        return None

    entry = entry_close
    if side == "LONG":
        sl = max(min(prior_l, last["Low"])*0.999, entry*(1-SL_PCT))
        risk = entry - sl
        target = entry + TARGET_R * risk
    else:
        sl = min(max(prior_h, last["High"])*1.001, entry*(1+SL_PCT))
        risk = sl - entry
        target = entry - TARGET_R * risk

    sl_pct_actual = abs(risk) / entry
    if sl_pct_actual < 0.005 or sl_pct_actual > 0.018: return None

    qty = max(int((CAPITAL * RISK_PCT) / abs(risk)), 1)
    return {
        "symbol": symbol, "yf_ticker": yf_ticker, "security_id": security_id,
        "side": side, "entry": round(entry,2), "sl": round(float(sl),2),
        "target": round(float(target),2), "qty": qty,
        "sl_pct": round(sl_pct_actual*100, 2),
        "type": "LIFELINE" if (bull_ll or bear_ll) else "5MIN_BO",
    }

# ─────────────────────────────────────────────────────────────────
# Live OI check
# ─────────────────────────────────────────────────────────────────
NSE_HEADERS = {"User-Agent":"Mozilla/5.0","Accept":"application/json"}

def oi_session():
    s = requests.Session()
    s.headers.update(NSE_HEADERS)
    try:
        s.get("https://www.nseindia.com/", timeout=8)
        s.get("https://www.nseindia.com/option-chain", timeout=8)
        return s
    except: return None

def oi_check(sess, symbol, side):
    if sess is None: return True, "no-OI-session"
    try:
        url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
        r = sess.get(url, timeout=10)
        d = r.json()
        if "records" not in d: return True, "no-OI-data"
        spot = d["records"]["underlyingValue"]
        rows = [e for e in d["records"]["data"]
                if e.get("expiryDate") == d["records"]["expiryDates"][0]]
        ce_oi = sum(e.get("CE",{}).get("openInterest",0) for e in rows)
        pe_oi = sum(e.get("PE",{}).get("openInterest",0) for e in rows)
        ce_chg = sum(e.get("CE",{}).get("changeinOpenInterest",0) for e in rows)
        pe_chg = sum(e.get("PE",{}).get("changeinOpenInterest",0) for e in rows)
        pcr = pe_oi / ce_oi if ce_oi > 0 else 0

        if side == "LONG":
            if ce_chg > pe_chg * 1.5 and ce_chg > 0:
                return False, "OI bearish (CE writing > PE writing)"
            if pcr < 0.6: return False, f"PCR {pcr:.2f} too low"
        else:
            if pe_chg > ce_chg * 1.5 and pe_chg > 0:
                return False, "OI bullish (PE writing > CE writing)"
            if pcr > 1.4: return False, f"PCR {pcr:.2f} too high"
        return True, f"OI ok (PCR {pcr:.2f})"
    except Exception as e:
        return True, f"OI error: {e}"

# ─────────────────────────────────────────────────────────────────
# Manage open positions
# ─────────────────────────────────────────────────────────────────
def manage_positions(state):
    for sym, p in list(state["open_positions"].items()):
        try:
            df = fetch(p["yf_ticker"])
            if df is None: continue
            last = df.iloc[-1]
            c = to_float(last["Close"]); h = to_float(last["High"]); l = to_float(last["Low"])
            if any(v != v for v in (c, h, l)):  # NaN guard
                continue
            risk_per = to_float(p["entry_risk"])
        except Exception as e:
            print(f"⚠️ manage {sym} skip: {e}")
            continue

        if p["side"] == "LONG":
            R = (c - p["entry"]) / risk_per
            if R >= 2 and p["sl"] < p["entry"] + risk_per:
                p["sl"] = p["entry"] + risk_per; tg(f"⬆️ {sym} SL trail to 1:1 (₹{p['sl']:.2f})")
            elif R >= 1 and p["sl"] < p["entry"]:
                p["sl"] = p["entry"]; tg(f"⬆️ {sym} SL trail to cost (₹{p['sl']:.2f})")
            if l <= p["sl"]:
                exit_pnl = (p["sl"] - p["entry"]) * p["qty"]
                tg(f"🛑 {sym} SL hit @ ₹{p['sl']:.2f} | P&L ₹{exit_pnl:+.0f}")
                state["daily_pnl"] += exit_pnl
                del state["open_positions"][sym]
            elif h >= p["target"]:
                exit_pnl = (p["target"] - p["entry"]) * p["qty"]
                tg(f"🎯 {sym} TARGET hit @ ₹{p['target']:.2f} | P&L ₹{exit_pnl:+.0f}")
                state["daily_pnl"] += exit_pnl
                del state["open_positions"][sym]
        else:
            R = (p["entry"] - c) / risk_per
            if R >= 2 and p["sl"] > p["entry"] - risk_per:
                p["sl"] = p["entry"] - risk_per; tg(f"⬇️ {sym} SL trail to 1:1 (₹{p['sl']:.2f})")
            elif R >= 1 and p["sl"] > p["entry"]:
                p["sl"] = p["entry"]; tg(f"⬇️ {sym} SL trail to cost (₹{p['sl']:.2f})")
            if h >= p["sl"]:
                exit_pnl = (p["entry"] - p["sl"]) * p["qty"]
                tg(f"🛑 {sym} SL hit @ ₹{p['sl']:.2f} | P&L ₹{exit_pnl:+.0f}")
                state["daily_pnl"] += exit_pnl
                del state["open_positions"][sym]
            elif l <= p["target"]:
                exit_pnl = (p["entry"] - p["target"]) * p["qty"]
                tg(f"🎯 {sym} TARGET hit @ ₹{p['target']:.2f} | P&L ₹{exit_pnl:+.0f}")
                state["daily_pnl"] += exit_pnl
                del state["open_positions"][sym]
    save_state(state)

# ─────────────────────────────────────────────────────────────────
# Morning Scan — dynamic watchlist from F&O universe
# ─────────────────────────────────────────────────────────────────
def morning_scan():
    """Rank FNO_UNIVERSE by ATR + volume surge. Returns top-15 as today's watchlist."""
    tg("🔍 Morning scan — ranking 72 F&O stocks...")
    tickers = [yft for _, yft, _, _ in FNO_UNIVERSE]
    try:
        raw = yf.download(
            tickers, period="60d", interval="1d",
            group_by="ticker", auto_adjust=False,
            progress=False, threads=True
        )
    except Exception as e:
        tg(f"⚠️ Scan download failed ({e}) — using default watchlist")
        return list(WATCHLIST)

    scores = []
    for sym, yft, did, sector in FNO_UNIVERSE:
        try:
            df = raw[yft].dropna(subset=["Close", "Volume"])
            if len(df) < 22:
                continue
            px = float(df["Close"].iloc[-1])
            if px < 50:
                continue
            hl = df["High"] - df["Low"]
            hc = (df["High"] - df["Close"].shift(1)).abs()
            lc = (df["Low"]  - df["Close"].shift(1)).abs()
            atr_pct = float(
                pd.concat([hl, hc, lc], axis=1).max(axis=1)
                .rolling(14).mean().iloc[-1] / px * 100
            )
            if atr_pct < 1.5:
                continue
            avg_vol   = float(df["Volume"].iloc[-21:-1].mean())
            vol_ratio = float(df["Volume"].iloc[-1]) / avg_vol if avg_vol > 0 else 0
            prev_chg  = abs(float(df["Close"].pct_change().iloc[-1]) * 100)
            score     = atr_pct * 0.4 + vol_ratio * 0.3 + prev_chg * 0.3
            scores.append((score, sym, yft, did, sector,
                           round(atr_pct, 2), round(vol_ratio, 2)))
        except Exception:
            continue

    if not scores:
        tg("⚠️ Scan returned 0 results — using default watchlist")
        return list(WATCHLIST)

    scores.sort(reverse=True)
    top = scores[:15]
    wl  = [(s, y, d, sec) for _, s, y, d, sec, *_ in top]
    lines = ["🌅 <b>Today's Watchlist (Dynamic Scan)</b>"]
    for _, s, _, _, sec, atr, vol in top:
        lines.append(f"  {s} ({sec}) | ATR {atr}% | Vol {vol:.1f}x")
    tg("\n".join(lines))
    return wl

# ─────────────────────────────────────────────────────────────────
# MAIN BOT LOOP
# ─────────────────────────────────────────────────────────────────
def bot_loop():
    state = load_state()
    today_str = str(datetime.now().date())
    if state.get("date") != today_str:
        state = {"open_positions": {}, "alerted": [], "trades_today": 0,
                 "daily_pnl": 0, "date": today_str}
        save_state(state)

    dhan = get_dhan()
    sess = oi_session()
    mode = "PAPER" if PAPER_MODE else "LIVE"
    top_sectors = None        # populated at 9:30, refreshed every 30 min
    sector_checked_at = None  # timestamp of last sector scan
    tg(f"🤖 <b>Lifeline Bot Started</b> [{mode}]\n"
       f"Capital: ₹{CAPITAL:,} | Risk: {RISK_PCT*100:.0f}%\n"
       f"Universe: {len(FNO_UNIVERSE)} stocks | Running morning scan...\n"
       f"Time: {datetime.now().strftime('%H:%M:%S')}")
    watchlist_today = morning_scan()

    while True:
        try:
            now = datetime.now().time()

            # End of day square off
            if now >= SQUARE_OFF:
                try:
                    if state["open_positions"]:
                        tg("⏰ 3:15 PM — Squaring off all positions")
                        try:
                            square_off_all(dhan, state)
                        except Exception as e:
                            tg(f"⚠️ Squareoff inner error: {e}")
                        # Force-clear regardless so the loop can never re-enter this branch
                        state["open_positions"] = {}
                        save_state(state)
                    pnl_val = to_float(state.get("daily_pnl", 0))
                    if pnl_val != pnl_val:  # NaN
                        pnl_val = 0.0
                    tg(f"📊 <b>Day Summary</b>\n"
                       f"Trades: {state.get('trades_today', 0)}\n"
                       f"P&L: ₹{pnl_val:+,.2f}\n"
                       f"Bot stopping for the day.")
                except Exception as e:
                    print(f"⚠️ Summary error: {e}")
                break

            # Daily loss limit
            if state["daily_pnl"] <= -CAPITAL * MAX_DAILY_LOSS_PCT:
                tg(f"🚨 Daily loss limit hit (₹{state['daily_pnl']:+.0f}). Bot stopping.")
                if state["open_positions"]:
                    square_off_all(dhan, state)
                break

            # Wait for entry window
            if now < ENTRY_START:
                print(f"[{now.strftime('%H:%M')}] Pre-9:25 — waiting"); time.sleep(60); continue

            # Manage open positions every iteration
            if state["open_positions"]:
                manage_positions(state)

            # Look for new signals (only if under daily limit)
            if DEAD_ZONE_START <= now <= DEAD_ZONE_END:
                print(f"[{now.strftime('%H:%M')}] Dead zone (11:30-12:30) — no new entries")

            if (state["trades_today"] < MAX_TRADES_PER_DAY
                    and ENTRY_START <= now <= ENTRY_CUTOFF
                    and not (DEAD_ZONE_START <= now <= DEAD_ZONE_END)):
                trend = nifty_trend()
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Nifty={trend} | "
                      f"Trades today={state['trades_today']} | "
                      f"P&L=₹{state['daily_pnl']:+.0f}")

                if trend in ("BULL", "BEAR"):
                    # Refresh sector momentum every 30 min (first time after 9:30)
                    now_dt = datetime.now()
                    if (sector_checked_at is None or
                            (now_dt - sector_checked_at).seconds >= 1800):
                        top_sectors = get_top_sectors()
                        sector_checked_at = now_dt
                        if top_sectors:
                            tg(f"🏆 Leading sectors: {', '.join(top_sectors)}")
                        else:
                            print("  ⚠️ Sector data unavailable — scanning all sectors")

                    for sym, yft, secid, sector in watchlist_today:
                        if sym in state["open_positions"]: continue
                        if sym in state["alerted"]: continue

                        # Sector filter — skip stocks NOT in today's top sectors
                        if top_sectors and sector not in top_sectors:
                            continue

                        sig = find_signal(sym, yft, secid, trend)
                        if sig is None: continue

                        ok, why = oi_check(sess, sym, sig["side"])
                        if not ok:
                            print(f"  {sym} signal but OI rejected: {why}")
                            state["alerted"].append(sym)
                            continue

                        # PLACE ORDER
                        oid = place_order(dhan, secid, sig["side"], sig["qty"],
                                          sig["entry"], sig["sl"], sig["target"])
                        state["open_positions"][sym] = {
                            "side": sig["side"], "entry": sig["entry"],
                            "sl": sig["sl"], "target": sig["target"],
                            "qty": sig["qty"], "entry_risk": abs(sig["entry"]-sig["sl"]),
                            "yf_ticker": yft, "security_id": secid,
                            "order_id": oid, "type": sig["type"],
                            "sector": sector,
                        }
                        state["alerted"].append(sym)
                        state["trades_today"] += 1
                        tg(f"🔔 <b>{sig['side']}</b> {sym} ({sig['type']}) [{mode}]\n"
                           f"Sector: {sector} | Entry: ₹{sig['entry']} | SL: ₹{sig['sl']} ({sig['sl_pct']}%)\n"
                           f"Target: ₹{sig['target']} (1:{TARGET_R:.0f})\n"
                           f"Qty: {sig['qty']} | OrderID: {oid}\n"
                           f"OI: {why}")
                        save_state(state)
                        if state["trades_today"] >= MAX_TRADES_PER_DAY:
                            tg(f"📌 Max {MAX_TRADES_PER_DAY} trades reached for today")
                            break

            time.sleep(SCAN_INTERVAL)

        except KeyboardInterrupt:
            tg("⏹ Bot stopped manually")
            break
        except Exception as e:
            tg(f"⚠️ Error: {e}")
            # Safety net: if we hit an unhandled error past squareoff time,
            # bail instead of looping forever until GitHub Actions kills the job.
            if datetime.now().time() >= SQUARE_OFF:
                tg("🛑 Bot exiting — error past squareoff time, no point retrying")
                break
            time.sleep(60)

if __name__ == "__main__":
    bot_loop()
