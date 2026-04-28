"""
DEMO: How live OI integrates with Lifeline Strategy
====================================================
Synthetic data dikhata hai actual flow.
Live market me ye file run karne se REAL OI signals milenge.
"""

from live_oi_module import analyze_oi, oi_filter_for_trade, print_oi_card
import pandas as pd

# ─── Synthetic option chain data (simulating live NSE response) ───
def make_demo_chain(spot, scenario="bullish"):
    strikes = list(range(int(spot - 100), int(spot + 100), 10))
    rows = []
    for s in strikes:
        dist = abs(s - spot)
        if scenario == "bullish":
            # Heavy PE writing below, CE unwinding above
            ce_oi = max(50000 - dist * 200, 5000)
            pe_oi = max(80000 - dist * 250, 8000) if s < spot else max(20000 - dist * 100, 1000)
            ce_chg = -2000 if s > spot else 500
            pe_chg = 5000 if s < spot else 200
        elif scenario == "bearish":
            ce_oi = max(80000 - dist * 250, 8000) if s > spot else max(20000 - dist * 100, 1000)
            pe_oi = max(50000 - dist * 200, 5000)
            ce_chg = 5000 if s > spot else 200
            pe_chg = -2000 if s < spot else 500
        else:  # neutral
            ce_oi = max(40000 - dist * 200, 3000)
            pe_oi = max(40000 - dist * 200, 3000)
            ce_chg = 100
            pe_chg = 100
        rows.append({
            "strike": s,
            "ce_oi": ce_oi, "ce_chg_oi": ce_chg, "ce_iv": 25, "ce_volume": 1000, "ce_ltp": 10,
            "pe_oi": pe_oi, "pe_chg_oi": pe_chg, "pe_iv": 25, "pe_volume": 1000, "pe_ltp": 10,
        })
    return pd.DataFrame(rows)


def run_demo():
    print("=" * 72)
    print(" DEMO: Lifeline Strategy + Live OI Integration")
    print("=" * 72)

    # ─── Scenario 1: Bullish stock with bullish OI ──────────────────
    print("\n[CASE 1] HDFCBANK -- Strategy says LONG, OI bullish")
    print("-" * 72)
    df = make_demo_chain(1620, "bullish")
    oi = analyze_oi(df, 1620, "HDFCBANK")
    print_oi_card(oi)

    allow, reason = oi_filter_for_trade(oi, "LONG")
    print(f"\nStrategy signal:  LONG @ 1620")
    print(f"OI filter:        {'PASS  -> ENTER TRADE' if allow else 'FAIL  -> SKIP'}")
    print(f"Reason:           {reason}")

    # ─── Scenario 2: Bullish stock but OI bearish (TRAP) ────────────
    print("\n\n[CASE 2] RELIANCE -- Strategy says LONG, OI BEARISH (trap)")
    print("-" * 72)
    df = make_demo_chain(2850, "bearish")
    oi = analyze_oi(df, 2850, "RELIANCE")
    print_oi_card(oi)

    allow, reason = oi_filter_for_trade(oi, "LONG")
    print(f"\nStrategy signal:  LONG @ 2850")
    print(f"OI filter:        {'PASS  -> ENTER TRADE' if allow else 'FAIL  -> SKIP'}")
    print(f"Reason:           {reason}")
    print("  >>> Iska matlab: Entry skip karo. Yahi PDF rule bachata hai!")

    # ─── Scenario 3: Resistance too close ───────────────────────────
    print("\n\n[CASE 3] TCS -- Resistance only 0.5% away (1:1 RRR fail)")
    print("-" * 72)
    df = make_demo_chain(4015, "neutral")
    # Force a strong CE OI just above spot
    df.loc[df["strike"] == 4020, "ce_oi"] = 200000
    oi = analyze_oi(df, 4015, "TCS")
    print_oi_card(oi)

    allow, reason = oi_filter_for_trade(oi, "LONG")
    print(f"\nStrategy signal:  LONG @ 4015")
    print(f"OI filter:        {'PASS  -> ENTER TRADE' if allow else 'FAIL  -> SKIP'}")
    print(f"Reason:           {reason}")
    print("  >>> Resistance 4020 = sirf 0.12% upar = 1:1 nahi mil sakta")

    # ─── Scenario 4: Bearish trade with confirming OI ───────────────
    print("\n\n[CASE 4] ICICIBANK -- Strategy says SHORT, OI bearish (confirm)")
    print("-" * 72)
    df = make_demo_chain(1240, "bearish")
    oi = analyze_oi(df, 1240, "ICICIBANK")
    print_oi_card(oi)

    allow, reason = oi_filter_for_trade(oi, "SHORT")
    print(f"\nStrategy signal:  SHORT @ 1240")
    print(f"OI filter:        {'PASS  -> ENTER TRADE' if allow else 'FAIL  -> SKIP'}")
    print(f"Reason:           {reason}")

    print("\n" + "=" * 72)
    print(" END OF DEMO")
    print("=" * 72)


if __name__ == "__main__":
    run_demo()
