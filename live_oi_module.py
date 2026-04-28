"""
LIVE OI MODULE — Real-time Open Interest Analysis
==================================================
Sirf live market hours (9:15 AM - 3:30 PM) me kaam karta hai.
NSE official option-chain API se free me OI data nikalta hai.

USE CASE:
  Tumhari strategy (HA + Lifeline + 5-min) ek stock pe entry signal
  generate karti hai. Trade lene se PEHLE ye module check karta hai:

  1. OI-based RESISTANCE 1:1 ke andar to nahi? (PDF rule)
  2. OI buildup confirmation BULLISH/BEARISH bias se match karta hai?
  3. PCR (Put-Call Ratio) se sentiment confirm hota hai?
  4. Max Pain ke kis side hai stock?

  Agar OI confirms -> ENTRY, warna SKIP.

NSE API endpoints used:
  - https://www.nseindia.com/api/option-chain-equities?symbol=XXX
  - https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY

NOTE: NSE bots block karta hai. Proper session/cookie handling chahiye.
      Ye script automatically session establish karega.
"""

import requests
import pandas as pd
from datetime import datetime, time as dtime
import time
import json

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/option-chain",
    "Connection": "keep-alive",
}

# F&O stocks (subset of Nifty 50 — only these have option chains)
FNO_STOCKS = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN",
    "AXISBANK", "KOTAKBANK", "BAJFINANCE", "MARUTI", "TATAMOTORS",
    "SUNPHARMA", "HCLTECH", "WIPRO", "LT", "M&M", "ITC",
    "ASIANPAINT", "TITAN", "POWERGRID", "NTPC", "BHARTIARTL",
    "ULTRACEMCO", "TECHM", "HINDUNILVR", "NESTLEIND"
]


def is_market_open():
    """Market hours: 9:15 AM - 3:30 PM IST, Mon-Fri"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    open_t = dtime(9, 15)
    close_t = dtime(15, 30)
    return open_t <= now.time() <= close_t


def establish_session():
    """NSE blocks direct API hits without cookies. First hit homepage."""
    sess = requests.Session()
    sess.headers.update(NSE_HEADERS)
    try:
        sess.get("https://www.nseindia.com/", timeout=10)
        sess.get("https://www.nseindia.com/option-chain", timeout=10)
        return sess
    except Exception as e:
        print(f"[!] Session establish failed: {e}")
        return None


def fetch_option_chain(symbol, sess=None):
    """Fetch raw option chain from NSE for a stock or index."""
    if sess is None:
        sess = establish_session()
    if sess is None:
        return None

    is_index = symbol.upper() in ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY")
    base = "indices" if is_index else "equities"
    url = f"https://www.nseindia.com/api/option-chain-{base}?symbol={symbol.upper()}"

    try:
        r = sess.get(url, timeout=15)
        if r.status_code != 200:
            print(f"[!] {symbol}: HTTP {r.status_code}")
            return None
        return r.json()
    except Exception as e:
        print(f"[!] {symbol}: fetch error {e}")
        return None


def parse_oi_data(raw_json):
    """Convert NSE option chain JSON to a clean DataFrame + spot price."""
    if raw_json is None or "records" not in raw_json:
        return None, None

    records = raw_json["records"]
    spot = records.get("underlyingValue")
    expiries = records.get("expiryDates", [])
    if not expiries:
        return None, spot

    nearest_expiry = expiries[0]
    rows = []
    for entry in records.get("data", []):
        if entry.get("expiryDate") != nearest_expiry:
            continue
        strike = entry.get("strikePrice")
        ce = entry.get("CE", {}) or {}
        pe = entry.get("PE", {}) or {}
        rows.append({
            "strike": strike,
            "ce_oi": ce.get("openInterest", 0),
            "ce_chg_oi": ce.get("changeinOpenInterest", 0),
            "ce_iv": ce.get("impliedVolatility", 0),
            "ce_volume": ce.get("totalTradedVolume", 0),
            "ce_ltp": ce.get("lastPrice", 0),
            "pe_oi": pe.get("openInterest", 0),
            "pe_chg_oi": pe.get("changeinOpenInterest", 0),
            "pe_iv": pe.get("impliedVolatility", 0),
            "pe_volume": pe.get("totalTradedVolume", 0),
            "pe_ltp": pe.get("lastPrice", 0),
        })
    df = pd.DataFrame(rows).sort_values("strike").reset_index(drop=True)
    return df, spot


def analyze_oi(df, spot, symbol):
    """Compute key OI signals for the strategy."""
    if df is None or df.empty or spot is None:
        return None

    # Filter to ATM +/- 10 strikes (relevant zone)
    df["dist"] = abs(df["strike"] - spot)
    near = df.nsmallest(20, "dist").sort_values("strike").reset_index(drop=True)

    # Max OI strikes (resistance for CE, support for PE)
    max_ce_oi_strike = near.loc[near["ce_oi"].idxmax(), "strike"] if near["ce_oi"].max() > 0 else None
    max_pe_oi_strike = near.loc[near["pe_oi"].idxmax(), "strike"] if near["pe_oi"].max() > 0 else None

    # OI buildup (today's change)
    ce_oi_built = near["ce_chg_oi"].sum()
    pe_oi_built = near["pe_chg_oi"].sum()

    # PCR (only on near-the-money strikes)
    total_ce_oi = near["ce_oi"].sum()
    total_pe_oi = near["pe_oi"].sum()
    pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0

    # Max pain calculation
    max_pain_strike = compute_max_pain(near)

    # Distance to nearest resistance/support (CRITICAL for PDF rule)
    res_dist_pct = ((max_ce_oi_strike - spot) / spot * 100) if max_ce_oi_strike and max_ce_oi_strike > spot else None
    sup_dist_pct = ((spot - max_pe_oi_strike) / spot * 100) if max_pe_oi_strike and max_pe_oi_strike < spot else None

    # OI signal classification
    signal = classify_oi_signal(ce_oi_built, pe_oi_built, pcr)

    return {
        "symbol": symbol,
        "spot": round(spot, 2),
        "max_ce_oi_strike": max_ce_oi_strike,   # Resistance
        "max_pe_oi_strike": max_pe_oi_strike,   # Support
        "resistance_pct": round(res_dist_pct, 2) if res_dist_pct else None,
        "support_pct": round(sup_dist_pct, 2) if sup_dist_pct else None,
        "ce_oi_change": int(ce_oi_built),
        "pe_oi_change": int(pe_oi_built),
        "pcr": round(pcr, 2),
        "max_pain": max_pain_strike,
        "max_pain_dist_pct": round((max_pain_strike - spot) / spot * 100, 2) if max_pain_strike else None,
        "signal": signal,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }


def compute_max_pain(df):
    """Strike at which option writers lose minimum (price magnet)."""
    pain = {}
    strikes = df["strike"].tolist()
    for k in strikes:
        ce_pain = df[df["strike"] < k].apply(lambda r: (k - r["strike"]) * r["ce_oi"], axis=1).sum()
        pe_pain = df[df["strike"] > k].apply(lambda r: (r["strike"] - k) * r["pe_oi"], axis=1).sum()
        pain[k] = ce_pain + pe_pain
    if not pain:
        return None
    return min(pain, key=pain.get)


def classify_oi_signal(ce_built, pe_built, pcr):
    """
    OI buildup interpretation:
      CE OI up   = call writers active = bearish
      CE OI down = call writers exiting = bullish (short covering)
      PE OI up   = put writers active = bullish
      PE OI down = put writers exiting = bearish

    PCR > 1.3 = bearish (too many puts) -> contrarian bullish
    PCR < 0.7 = bullish (too few puts) -> contrarian bearish
    """
    if pe_built > 0 and ce_built < 0:
        return "STRONG_BULLISH"  # PE writing + CE unwinding
    if ce_built > 0 and pe_built < 0:
        return "STRONG_BEARISH"  # CE writing + PE unwinding
    if pe_built > ce_built * 1.5 and pe_built > 0:
        return "BULLISH"
    if ce_built > pe_built * 1.5 and ce_built > 0:
        return "BEARISH"
    if pcr > 1.3:
        return "OVERSOLD_BOUNCE"  # contrarian
    if pcr < 0.7:
        return "OVERBOUGHT_DROP"  # contrarian
    return "NEUTRAL"


def oi_filter_for_trade(oi_data, trade_direction):
    """
    Returns: (allow_entry: bool, reason: str)

    PDF Rule: "Ignore the stock which is not giving more than 1:1 RRR
              (Facing resistance as per OI data or vice versa)"

    Implementation:
      - For LONG: resistance must be > 1.0% away (room for 1:1 minimum)
      - For SHORT: support must be > 1.0% away
      - OI signal must align with trade direction
    """
    if oi_data is None:
        return False, "No OI data"

    sig = oi_data["signal"]
    res_pct = oi_data.get("resistance_pct")
    sup_pct = oi_data.get("support_pct")
    pcr = oi_data["pcr"]

    if trade_direction == "LONG":
        # Resistance check
        if res_pct is not None and res_pct < 1.0:
            return False, f"Resistance only {res_pct}% away (< 1.0%)"
        # Direction confirmation
        if sig in ("STRONG_BEARISH", "BEARISH"):
            return False, f"OI signal {sig} contradicts LONG"
        if sig == "OVERBOUGHT_DROP":
            return False, f"PCR {pcr} too low (overbought)"
        return True, f"OK: res={res_pct}%, sig={sig}, PCR={pcr}"

    elif trade_direction == "SHORT":
        if sup_pct is not None and sup_pct < 1.0:
            return False, f"Support only {sup_pct}% away (< 1.0%)"
        if sig in ("STRONG_BULLISH", "BULLISH"):
            return False, f"OI signal {sig} contradicts SHORT"
        if sig == "OVERSOLD_BOUNCE":
            return False, f"PCR {pcr} too high (oversold)"
        return True, f"OK: sup={sup_pct}%, sig={sig}, PCR={pcr}"

    return False, "Unknown direction"


def scan_all(symbols=None, sleep_between=1.5):
    """Scan multiple stocks for OI signals."""
    if not is_market_open():
        print(f"[!] Market closed (now: {datetime.now().strftime('%a %H:%M')})")
        print("    Live OI data only available 9:15 AM - 3:30 PM IST, Mon-Fri")
        # Still try to fetch — NSE returns last close-day snapshot

    if symbols is None:
        symbols = FNO_STOCKS

    sess = establish_session()
    if sess is None:
        print("[!] Could not establish NSE session")
        return None

    results = []
    for sym in symbols:
        raw = fetch_option_chain(sym, sess)
        df, spot = parse_oi_data(raw)
        if df is not None:
            analysis = analyze_oi(df, spot, sym)
            if analysis:
                results.append(analysis)
                print(f"  {sym:15s} spot={analysis['spot']:>8.2f}  "
                      f"signal={analysis['signal']:<18s}  "
                      f"PCR={analysis['pcr']:.2f}  "
                      f"R={analysis['resistance_pct']}%  "
                      f"S={analysis['support_pct']}%")
        else:
            print(f"  {sym:15s} -- FAILED")
        time.sleep(sleep_between)

    return pd.DataFrame(results) if results else None


def print_oi_card(oi_data):
    """Pretty-print a single stock's OI snapshot."""
    if oi_data is None:
        print("No data"); return
    print("=" * 60)
    print(f"  {oi_data['symbol']}  @  {oi_data['timestamp']}")
    print("=" * 60)
    print(f"  Spot:                  Rs. {oi_data['spot']}")
    print(f"  Resistance (Max CE OI): {oi_data['max_ce_oi_strike']}  "
          f"({oi_data['resistance_pct']}% away)")
    print(f"  Support    (Max PE OI): {oi_data['max_pe_oi_strike']}  "
          f"({oi_data['support_pct']}% away)")
    print(f"  Max Pain:               {oi_data['max_pain']}  "
          f"({oi_data['max_pain_dist_pct']}% from spot)")
    print(f"  PCR (near-the-money):   {oi_data['pcr']}")
    print(f"  CE OI change today:     {oi_data['ce_oi_change']:+,}")
    print(f"  PE OI change today:     {oi_data['pe_oi_change']:+,}")
    print(f"  >>>  SIGNAL: {oi_data['signal']}")
    print("=" * 60)


# ─────────────────────────────────────────────────────────────────
# DEMO / SELF-TEST
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("LIVE OI MODULE -- Self-Test")
    print(f"Time now: {datetime.now()}")
    print(f"Market open: {is_market_open()}")
    print()

    # Test 1: Single stock
    print(">> Test 1: Fetch RELIANCE option chain")
    sess = establish_session()
    raw = fetch_option_chain("RELIANCE", sess)
    if raw:
        df, spot = parse_oi_data(raw)
        analysis = analyze_oi(df, spot, "RELIANCE")
        print_oi_card(analysis)

        # Test the filter
        allow_long, reason_long = oi_filter_for_trade(analysis, "LONG")
        allow_short, reason_short = oi_filter_for_trade(analysis, "SHORT")
        print(f"\n  LONG  allowed: {allow_long}  -> {reason_long}")
        print(f"  SHORT allowed: {allow_short}  -> {reason_short}")
    else:
        print("  Could not fetch (network / NSE block)")

    print()
    print(">> Test 2: NIFTY index OI snapshot")
    raw = fetch_option_chain("NIFTY", sess)
    if raw:
        df, spot = parse_oi_data(raw)
        analysis = analyze_oi(df, spot, "NIFTY")
        print_oi_card(analysis)

    print("\n>> Test 3: Quick scan of 5 F&O stocks")
    scan_all(["RELIANCE", "HDFCBANK", "TCS", "ICICIBANK", "INFY"], sleep_between=2)
