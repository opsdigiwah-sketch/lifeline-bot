# LIFELINE MASTER STRATEGY — Unified Intraday System

> Vinay Bhelkar setup ka complete unified version. Sab strategies (5-min, 1-min, Lifeline, Infinity) ek single decision flow me. Ek baar padho, roz follow karo.

---

## ⏰ DAILY TIMELINE (Single Workflow)

```
8:30–9:00 AM  →  PRE-MARKET PREP
9:00–9:15 AM  →  PRE-OPEN ANALYSIS
9:15–9:16 AM  →  MARKET OPENS — OBSERVE ONLY
9:16–9:20 AM  →  GAP & VOLUME ASSESSMENT (1-min play window)
9:20–9:30 AM  →  TREND CONFIRMATION (5-min play window opens)
9:30–9:40 AM  →  PRIMARY ENTRY ZONE (5-min strategy)
9:40–9:45 AM  →  SECTOR-BASED ENTRY (Lifeline starts)
9:45–10:30 AM →  HEATMAP ENTRIES (Best window)
10:30–11:30   →  CONTINUATION TRADES
11:30–1:30 PM →  AVOID (low volume, lunch)
1:30–2:30 PM  →  AFTERNOON SETUPS
2:00 PM       →  CHECK INFINITY SETUP for next day
2:30–3:00 PM  →  LAST ENTRIES (only A-grade)
3:00–3:15 PM  →  SQUARE OFF ALL POSITIONS
3:15–3:30 PM  →  JOURNAL + REVIEW
```

---

## 🧭 STEP 1 — PRE-MARKET (8:30–9:15 AM)

**Checklist:**
- [ ] SGX Nifty / GIFT Nifty — gap up/down kitna?
- [ ] US markets close (Dow, Nasdaq, S&P)
- [ ] Crude oil + USD/INR
- [ ] Overnight news (RBI, Fed, geopolitical, results)
- [ ] FII/DII previous day data
- [ ] **Pichli raat ka Infinity setup** (2 PM ke baad ka Inverted-V / V pattern) ready hai?

**Output:** Bias note likh — *"Aaj market bullish/bearish/sideways/confused lag raha hai"*

---

## 🧭 STEP 2 — TREND IDENTIFICATION (9:15–9:20 AM)

Trend confirm karne ke liye **2 out of 3** signals match hone chahiye:

| Signal | Check |
|---|---|
| **Volume Analysis** | Nifty 50 ka 5-min volume — bullish/bearish bias |
| **Advance/Decline** | NSE site pe A/D ratio (70–80% one side?) |
| **Sector Performance** | 70–80% sectors green ya red? |

### Trend → Stock Universe Mapping

| Market State | Stock Source (Priority) | Strategy |
|---|---|---|
| 🟢 **BULLISH TREND** | Nifty 200 → Sector → Heatmap/Top 3 → FnO | 5-min Continuation + Lifeline |
| 🟢 **BULLISH→SIDEWAYS** | Sector → Heatmap → FnO | Lifeline only |
| 🔴 **BEARISH TREND** | Nifty 100 → Sector → Heatmap → FnO | 5-min Continuation + Lifeline |
| 🔴 **BEARISH→SIDEWAYS** | Sector → Heatmap → FnO | Lifeline only |
| 🟡 **CONFUSION** | Sector → Heatmap → FnO | Lifeline only |
| ⚡ **Nifty 1st 5-min BO before 9:30** | Midcap 150 → Sector → Heatmap → FnO | 5-min Continuation + Lifeline |

> **Sector decide kaise?** Nifty 50 ke top 2 / bottom 2 stocks dekho — unka sector lo.

---

## 🧭 STEP 3 — STOCK SHORTLIST (9:20–9:40 AM)

Universe se 3-5 stocks pick karo using filters:

### Filter Layer 1 — Movement & Value
- ✅ **High value/volume** stock
- ✅ **Total movement < 1.80%** so far (warna missed move)
- ✅ Sector ka **1st stock 1.80%+** chala gaya → **2nd stock** lo
- ❌ 1st 5-min me **Marubozu candle** wala stock skip
- ✅ **3-day range breakout** ho raha hai → volume analysis skip kar sakte ho

### Filter Layer 2 — Data Grade

| Grade | Criteria |
|---|---|
| **A-Data** | 52-week NEW high + Top 2 high value + OI data NEGATIVE (for buy) |
| **B-Data** | 52-week high + High value Top 2 + OI data POSITIVE |

### Filter Layer 3 — Technical Grade

**A-Tech ke 9 rules:**

1. **Volume rule** — Flat/Gap up-down ka 1st 5-min volume **previous day se kam** hona chahiye
   - Buy: green-with-green compare karo
   - Sell: red-with-red compare karo
2. **Candle rule** — Gap up/down case me 1st 5-min candle body **PD se chhoti** ho (5-min ya 1-min TF)
3. Sideways open ho to candle analysis skip
4. **2-day range BO** ho raha hai → volume analysis skip
5. **1st LL Heikin Ashi BO ke pehle bana** to entry HA-BO pe ya **2nd LL** pe lo
6. Lifeline me high volume / big candle / **neutral candle** ho → AVOID
   - Buy: red neutral candle nahi chahiye
   - Sell: green neutral candle nahi chahiye
7. LL me entry nahi mil rahi → chart pattern dekho, par entry **day's high ke upar** Heikin Ashi BO se
8. **1:1 ke andar koi resistance/support nahi hona chahiye** (OI data, PDH/PDL, swing high/low)
9. **BO/BD stock** me Heikin Ashi BO ke baad direct entry — LL ka wait nahi

### Final Priority

```
1st Pick:  A-Data + A-Tech    ⭐⭐⭐
2nd Pick:  A-Data + B-Tech    ⭐⭐
3rd Pick:  B-Data + A-Tech    ⭐
SKIP:      B-Data + B-Tech    ❌
```

---

## 🎯 STEP 4 — ENTRY DECISION TREE

Stock select ho gaya. Ab entry kaise leni hai:

```
                    [STOCK SHORTLISTED]
                            │
                            ▼
         ┌──────────────────────────────────────┐
         │  Heikin Ashi pe 5-min BO hua?        │
         └──────────────────────────────────────┘
                  │                    │
                YES                   NO
                  │                    │
                  ▼                    ▼
       ┌──────────────────┐   ┌──────────────────┐
       │ BO/BD stock hai? │   │ Wait for HA BO    │
       └──────────────────┘   │ ya Lifeline form  │
            │       │         └──────────────────┘
          YES      NO
            │       │
            ▼       ▼
    DIRECT     LIFELINE BANA?
    ENTRY      (N-pattern)
   (5-MIN          │
   STRATEGY)    YES│         NO
                   │          │
                   ▼          ▼
              LIFELINE    SKIP / WAIT
              ENTRY
              (5/15 TF)
```

### Entry Type 1 — **5-MIN STRATEGY (Continuation)**
- After 9:20 AM
- A-Tech grade mandatory
- Multi-TF confirmation: **5-min + 3-min**
- Heikin Ashi BO ke baad entry
- Use this in **trending markets only**

### Entry Type 2 — **LIFELINE STRATEGY (N-Pattern)**
**Lifeline criteria:**
- **5-min TF**: 1 red/green candle hai + 3-min TF me **2+ matching candles**
- **15-min TF**: 1 red/green candle hai + 5-min TF me **2+ matching candles**
- **Wick chhota** → candlestick se entry
- **Wick bada** → line chart se entry (high/low mark karke)
- Source timing:
  - Sector se: **9:40 AM ke baad**
  - Heatmap se: **9:45 AM ke baad**
- Agar 5-min strategy ne already 1:1+ target de diya → **Lifeline mat lo**

### Entry Type 3 — **1-MIN STRATEGY (Aggressive)**
- After **9:16 AM**
- Heatmap ke top 2 stocks (highest %)
- Buy entries:
  - (a) Breakdown→Breakout entry
  - (b) Lifeline (min 2-3 red candles)
- Sell entries:
  - (c) Breakout→Breakdown entry
  - (d) Lifeline (min 2-3 green candles)

### Entry Type 4 — **INFINITY STRATEGY (Swing-based)**
- **Previous day 2 PM ke baad** check karo
- **Inverted V** (^) → **BUY** above swing high (continuation/lifeline)
- **Normal V** (v) → **SELL** below swing low (continuation/lifeline)

---

## 🛑 STEP 5 — RISK MANAGEMENT (NON-NEGOTIABLE)

### Stop Loss Rules

| Rule | Value |
|---|---|
| Min SL | **0.50%** |
| Max SL | **1.80%** |
| Average SL | **0.60% – 1.50%** |
| ❌ Never place SL at | Breakout candle low / Breakdown candle high |
| ✅ Place SL | Bhog ke level se thoda neeche/upar (logical level) |

### Position Sizing (Capital Protection)

| Capital | Risk per Trade | Max SL Distance | Position Size |
|---|---|---|---|
| ₹1,00,000 | ₹1,000 (1%) | 1% SL | Quantity = ₹1000 / SL points |
| ₹5,00,000 | ₹5,000 (1%) | 1% SL | Quantity accordingly |

> Daily loss limit: **3% of capital**. Hit ho gaya → laptop band, end of day.

### Risk:Reward Filter
- ❌ Agar **1:1 RRR bhi nahi mil raha** → **TRADE NAHI**
- 1:1 ke andar OI resistance/support? → **SKIP**
- Target minimum 1:2, ideal 1:3

### Trailing Stop Logic

```
Entry → SL set
   │
   ▼
3/5-min candle close > 1:1?
   YES → SL ko COST pe le aao (breakeven)
   │
   ▼
3/5-min candle close > 1:2?
   YES → SL ko 1:1 pe le aao (lock 1R profit)
   │
   ▼
EXIT signals (kabhi bhi):
   • High volume reversal candle
   • Heikin Ashi color change
   • Trendline break
```

---

## 🚫 STEP 6 — RULE BREAKING WARNINGS

Yeh situations me **NEVER ENTER** (PDF v1.0 ke "When we break rules" section se):

1. ❌ **Entry ke pehle high volume candle** ban gayi
2. ❌ **1st 5-min high volume candle** thi
3. ❌ **1st 5-min big body / Marubozu candle** thi
4. ❌ **Lifeline me neutral candle** (doji-like)
5. ❌ **Lifeline me big body candle**
6. ❌ Sector ka 1st stock pehle hi 1.80%+ chala gaya (2nd lo)
7. ❌ 1:1 ke andar resistance/support hai (OI/PDH/PDL/swing)
8. ❌ Counter-trend trade (gap up + bearish volume → counter logic apply)

### Counter-Trend Special Cases

| Setup | Action |
|---|---|
| Gap **DOWN** + bullish volume + Declines 70-80% | Go **BEARISH** (trap reversal) |
| Gap **UP** + bearish volume + Advances 70-80% | Go **BULLISH** (trap reversal) |

---

## 📋 ONE-PAGE DECISION CHECKLIST

Print karke screen ke saamne rakho:

```
═══════════════════════════════════════════════════════
  PRE-TRADE CHECKLIST (har trade pe tick karo)
═══════════════════════════════════════════════════════
□ Time 9:20 AM ke baad hai? (1-min: 9:16+)
□ Trend confirmed (2 out of 3 signals)?
□ Stock universe match kar raha hai trend se?
□ Movement < 1.80%?
□ 1st 5-min Marubozu nahi hai?
□ Stock A-Data ya B-Data?
□ Stock A-Tech ya B-Tech?
□ Heikin Ashi BO confirmed?
□ Lifeline / BO/BD setup ban gaya?
□ Wick check (chhota/bada → candle/line)?
□ 1:1 ke andar resistance/support clear hai?
□ Min 1:1 RRR mil raha hai?
□ SL planned (0.5%-1.8%, breakout candle pe nahi)?
□ Position size = (1% capital) / SL%?
□ High volume / big body / neutral candle red flags?

   12+ ✅ → ENTRY
   <12 ✅ → SKIP

═══════════════════════════════════════════════════════
  POST-ENTRY MANAGEMENT
═══════════════════════════════════════════════════════
□ 1:1 hit → SL to COST
□ 1:2 hit → SL to 1:1
□ HV reversal candle / HA flip / trendline break → BOOK
□ 3:00 PM → Square off all
═══════════════════════════════════════════════════════
```

---

## 📊 STEP 7 — DAILY JOURNAL (MANDATORY)

Excel me track karo (`Equity Trading Report.xlsx` me already template hai):

| Field | Note |
|---|---|
| Date | DD-MM-YYYY |
| Stock | Symbol |
| Entry Price | ₹ |
| Entry Reason | 5-min BO / Lifeline 5/15 / Infinity / 1-min |
| View | Bullish / Bearish |
| Source | Nifty 100 / 200 / Sector / Heatmap / FnO |
| Quantity | Calculated from 1% rule |
| Exit Price | ₹ |
| Exit Reason | Target / SL hit / HA trail / Trendline / Time exit |
| P/L | ₹ + % |
| Mistakes | Rule break? Plan deviation? |

**Weekly review (Sunday):**
- Win rate %
- Avg win / Avg loss ratio
- Most profitable setup type
- Most repeated mistake

---

## 🧠 GOLDEN RULES (Iss Strategy ka DNA)

1. **9:20 AM ke pehle koi entry nahi** (1-min: 9:16+)
2. **2-out-of-3 trend confirmation** ke bina entry nahi
3. **A-grade ya B-grade ke alawa** trade nahi
4. **Heikin Ashi BO + Lifeline (N-pattern)** = best combo
5. **SL ko breakout/breakdown candle pe NEVER place** karo
6. **1:1 RRR minimum**, warna trade skip
7. **1.80% se zyada move** ho gaya → wo stock dead, doosra lo
8. **High volume candle** entry se pehle = red flag
9. **1:1 hit = breakeven SL**, **1:2 hit = lock 1R**
10. **3% daily loss = stop trading**, kal phir aayenge

---

## 🎬 EK PURI TRADE — EXAMPLE FLOW

```
8:45 AM  → SGX Nifty +80 (gap up). US closed +0.5%. Bullish bias.
9:15 AM  → Nifty opens +60 (gap up but small body).
9:16 AM  → A/D ratio 75% advance. Banking sector +0.8% leading.
9:20 AM  → Volume analysis: bullish. Trend = BULLISH TREND confirmed.
           → Universe: Nifty 200 + Banking sector
9:25 AM  → Shortlist: HDFCBANK (52w high candidate, OI negative = A-Data),
           ICICIBANK (high value, OI positive = B-Data)
9:30 AM  → HDFCBANK 5-min HA BO above 1620. 3-min me 2 green candles already.
           Movement abhi 0.7% only. No marubozu in 1st 5-min. ✅
           OI data: 1640 strong resistance (~1.2% away = beyond 1:1, OK)
9:32 AM  → ENTRY @ 1622, SL @ 1610 (0.74%), Target1 1634 (1:1), Target2 1646 (1:2)
           Position: 100 shares = ₹1,200 risk on ₹1L capital (1.2%)
9:48 AM  → Hit 1634 (1:1) → SL trail to 1622 (cost)
10:15 AM → Hit 1646 (1:2) → SL trail to 1634 (1:1 lock)
10:32 AM → High volume red candle in HA → BOOK @ 1644
RESULT   → +₹2,200 profit (≈1.85R)
```

---

## ⚠️ DISCLAIMER (Real Trader Talk)

- Ye strategy **rules-based** hai par **guarantee nahi** deti
- Backtest karo paper trading me **minimum 30 trades** before real money
- Brokerage + STT + slippage realistic include karo (~0.05-0.1% per trade)
- Market regimes change hote hain — strategy ko **monthly review** karo
- **No setup is 100% — your edge is consistency, not perfection**

---

**ALL THE BEST!!! 🚀**

*Built from: Vinay Bhelkar's Equity Set Up (v1, v2, v3, 1-min TF, Latest) — compiled by Shahbaz Khan.*
