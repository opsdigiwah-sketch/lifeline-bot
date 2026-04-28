# 🤖 ZERO-TOUCH BOT — SETUP (30 min, ek baar)

Tu ye 4 step kar de, fir bot daily auto chalega. Tu sirf shaam ko Telegram dekhega.

---

## ✅ STEP 1 — Dhan Account (10 min)

1. Open https://dhan.co
2. **"Open Account"** click → mobile/email se signup
3. KYC complete karo (PAN + Aadhar + bank)
4. Approval 24-48 hrs me aata hai
5. **Profile → Trading Preferences → Paper Trading: ENABLE**

---

## ✅ STEP 2 — Dhan API Credentials (5 min)

1. Login → https://api.dhan.co
2. **"Generate Access Token"** click (free)
3. **CLIENT_ID** aur **ACCESS_TOKEN** copy karo

---

## ✅ STEP 3 — Telegram Bot (5 min)

1. Telegram me search → **`@BotFather`**
2. Send: `/newbot`
3. Bot ka naam: `LifelineBot` (kuch bhi)
4. Username: `lifeline_xxx_bot` (unique)
5. **Bot Token** mil jayega — copy karo
6. Tum apne bot ko `hi` bhejo
7. Browser me kholo (apna token daal ke):
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
8. Response me **`"chat":{"id": 123456789}`** dikhega — wo number copy

---

## ✅ STEP 4 — Bot Configure (2 min)

Open `ZERO_TOUCH_BOT.py` and update lines 28-32:

```python
DHAN_CLIENT_ID    = "1100123456"           # Step 2 se
DHAN_ACCESS_TOKEN = "eyJ0eXAiOi..."        # Step 2 se
TELEGRAM_TOKEN    = "7234567890:AAH..."    # Step 3 se
TELEGRAM_CHAT_ID  = "123456789"            # Step 3 se
PAPER_MODE = True                          # IMPORTANT: paper rakhna pehle
```

---

## ✅ STEP 5 — Install Libraries (3 min)

PowerShell me:
```powershell
py -m pip install dhanhq pandas yfinance requests
```

---

## ✅ STEP 6 — Auto-Start Daily (5 min, ek baar)

### Option A: Windows Task Scheduler

1. Win + R → `taskschd.msc`
2. **"Create Basic Task"**
3. Name: `Lifeline Bot`
4. Trigger: **Daily at 9:10 AM**
5. Action: **Start a program**
6. Program: `D:\Window\lifeline\start_bot.bat`
7. Save

### Option B: Manual Start (Daily 9:10 AM ko 1 click)

`start_bot.bat` pe **double click** karo — bus.

---

## 📱 Daily Routine (Tumhari Side)

```
9:00 AM  — PC on rakho (ya laptop)
9:10 AM  — Bot auto-start (Task Scheduler se)
9:25 AM  — Bot scan start kar deta hai
3:15 PM  — Bot khud square off
3:30 PM  — Bot daily summary Telegram pe bhejega:
            "📊 Day Summary
             Trades: 3
             P&L: ₹+1,250"
```

**Bus. Tu kuch nahi karega.**

---

## 🛡️ Safety Features (built-in)

- ✅ **PAPER_MODE = True** by default → real money risk zero
- ✅ **Max 5 trades/day** → over-trading prevent
- ✅ **3% daily loss limit** → bot khud band ho jata hai
- ✅ **State file** (`bot_state.json`) → crash hone pe resume
- ✅ **All actions Telegram pe** → tu poori transparency
- ✅ **OI rejection check** → bad setups skip
- ✅ **Auto SL trail** (1:1 → cost, 1:2 → 1R lock)

---

## ⚠️ Real Money Pe Switch Karne Se Pehle

**Minimum criteria (mera honest advice):**
1. ✅ 30 din paper run → consistently profitable?
2. ✅ Win rate >55%?
3. ✅ Avg R per trade >0.3R?
4. ✅ Max DD <10%?

**Tabhi:** `PAPER_MODE = False` aur start with **₹10,000 capital** (`CAPITAL = 10000`)

---

## 🆘 Troubleshooting

| Issue | Fix |
|---|---|
| `dhanhq not found` | `py -m pip install dhanhq` |
| Telegram nahi aa raha | Token aur chat_id check karo |
| `NSE blocked` errors | Bot apne aap retry karta hai, ignore |
| `Market closed` | 9:15-3:30 IST ke alawa nahi chalega |
| Bot crash hua | `start_bot.bat` se restart, state preserved |

---

## 📂 Files

| File | Purpose |
|---|---|
| `ZERO_TOUCH_BOT.py` | Main bot |
| `start_bot.bat` | Auto-start launcher |
| `bot_state.json` | Live state (auto-created) |
| `live_oi_module.py` | OI helper |
| `LIFELINE_MASTER_STRATEGY.md` | Strategy reference |
| `backtest_v2_complete.py` | Historical proof |
