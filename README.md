# 📈 Stock Research Dashboard

A personal tool to **see top-moving stocks**, **drill into any ticker**, and understand
**what every metric means** — so *you* decide whether to invest. It aggregates and explains;
it never tells you to buy or sell.

This is **Layer 1 + Layer 2** of the plan:
- **Layer 1** — a screen of top movers (gainers / losers / most active)
- **Layer 2** — drill into any ticker, with a plain-English explainer on every metric

---

## Step 1 — Get a free API key (no credit card)

1. Go to **https://site.financialmodelingprep.com/developer/docs/dashboard**
2. Sign up with your email.
3. Copy your **API key**. The free plan gives you **250 requests/day** — plenty here,
   because the app caches results for 15 minutes.

---

## Step 2 — Try it on your computer first (optional but recommended)

1. Make sure you have Python installed.
2. In a terminal, from this folder:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a file called `.streamlit/secrets.toml` (note the leading dot) containing:
   ```toml
   FMP_API_KEY = "paste_your_key_here"
   ```
4. Run it:
   ```bash
   streamlit run app.py
   ```
   Your browser opens the app. Type a ticker (e.g. `AAPL`) in the sidebar to drill in.

---

## Step 3 — Put it online so you can open it from your phone

1. Create a **free GitHub account** if you don't have one.
2. Make a **new repository** and upload these three files: `app.py`, `requirements.txt`, `README.md`.
   - ⚠️ **Do NOT upload your `secrets.toml`** — your key stays private.
3. Go to **https://share.streamlit.io**, sign in with GitHub.
4. Click **New app**, pick your repo, and set the main file to `app.py`.
5. Open **Advanced settings → Secrets** and paste:
   ```toml
   FMP_API_KEY = "paste_your_key_here"
   ```
6. Click **Deploy**. In a minute or two you'll get a URL like `yourapp.streamlit.app`.
7. On your phone, open that URL and **add it to your home screen** — now it behaves like an app.

---

## What's next (the later layers we planned)

3. **Pundits & confidence signals** — analyst buy/hold/sell, price targets, signal agreement
4. **Earnings & filings** — next earnings date, last beat/miss, link to latest SEC filing
5. **News & context** — recent news for the ticker and its sector
6. **AI summary layer** — summarize filings/news into "what changed"
7. **Notifications** — a Telegram bot that pings you on slow, meaningful triggers

Also planned as an upgrade to Layer 1: a **screener with custom filters** (P/E, market cap,
volume, sector, etc.) that shows *why* each stock passed.

---

*Educational tool, not financial advice. Data may be delayed. Compare metrics within a
company's own industry, and make your own decisions.*
