"""
Stock Research Dashboard  —  Layers 1 & 2
------------------------------------------
Layer 1: A screen of top movers (gainers / losers / most active).
Layer 2: Drill into any ticker and see its key metrics, each with a
         plain-English explainer so you learn what the number means.

This app AGGREGATES and EXPLAINS. It never tells you to buy or sell.
You look at the data and you decide.

Data source: Financial Modeling Prep (FMP) free tier (250 calls/day).
Results are cached for 15 minutes so you don't burn through that limit.
"""

import streamlit as st
import requests
import pandas as pd

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Stock Research Dashboard", page_icon="📈", layout="wide")

BASE = "https://financialmodelingprep.com/api/v3"

# Your FMP API key lives in Streamlit "secrets", never in this file.
# Locally: create .streamlit/secrets.toml  with   FMP_API_KEY = "your_key"
# On Streamlit Cloud: paste it under App settings -> Secrets.
API_KEY = st.secrets.get("FMP_API_KEY", "")


# ---------------------------------------------------------------------------
# Plain-English explainers  —  this is the "understand finance" layer.
# Each entry explains: what it measures, what's healthy, what high/low signals.
# ---------------------------------------------------------------------------
EXPLAINERS = {
    "market_cap": (
        "**Market capitalization** = share price × number of shares. It's the total "
        "value the market places on the whole company.\n\n"
        "Rough buckets: mega-cap (>$200B), large ($10B–$200B), mid ($2B–$10B), "
        "small ($300M–$2B), micro (<$300M).\n\n"
        "Bigger companies tend to be more stable and easier to trade; smaller ones "
        "can move faster — in both directions."
    ),
    "pe": (
        "**Price-to-Earnings (P/E)** = share price ÷ earnings per share. How many "
        "dollars you pay for each dollar of annual profit.\n\n"
        "A **high** P/E can mean investors expect strong growth — *or* that the stock "
        "is expensive. A **low** P/E can mean it's cheap — *or* that the market expects "
        "trouble.\n\n"
        "Always compare within the same industry; a 'normal' P/E varies a lot by sector. "
        "No P/E usually means the company isn't currently profitable."
    ),
    "peg": (
        "**PEG ratio** = P/E ÷ earnings growth rate. It puts the P/E in context of how "
        "fast profits are actually growing.\n\n"
        "Rule of thumb: around **1** is often seen as fair, **below 1** may be "
        "undervalued relative to growth, **above 2** may be pricey.\n\n"
        "Only meaningful when the company has real, positive earnings growth."
    ),
    "ev_ebitda": (
        "**EV/EBITDA** = enterprise value ÷ EBITDA. A valuation measure that *includes "
        "debt* (unlike P/E), so it's useful for comparing companies that carry different "
        "amounts of borrowing.\n\n"
        "**Lower** generally means cheaper. Like P/E, what's normal varies by industry, "
        "so compare against peers."
    ),
    "net_margin": (
        "**Net profit margin** = net profit ÷ revenue. Of every dollar of sales, how "
        "much ends up as actual profit.\n\n"
        "**Higher** is generally healthier — it signals pricing power or efficiency. "
        "Margins vary hugely by industry (software is often high, grocery retail is thin), "
        "so compare within a sector."
    ),
    "gross_margin": (
        "**Gross margin** = (revenue − cost of goods sold) ÷ revenue. The profit left "
        "after the direct cost of making the product, before overhead.\n\n"
        "High, stable gross margins often point to a strong product or brand."
    ),
    "debt_equity": (
        "**Debt-to-Equity** = total debt ÷ shareholder equity. How much the company "
        "leans on borrowing vs. owners' money.\n\n"
        "**Higher** = more leverage — potentially higher returns but more risk, "
        "especially if earnings wobble or interest rates rise. What's 'safe' depends on "
        "the industry; capital-heavy businesses (utilities, telecom) normally carry more."
    ),
    "fcf_per_share": (
        "**Free cash flow per share** = cash left over after running the business *and* "
        "paying for capital spending, divided by shares.\n\n"
        "Unlike reported earnings, cash flow is harder to massage with accounting. "
        "**Positive and growing** is a strong health sign; **persistently negative** "
        "means the company is burning cash."
    ),
    "beta": (
        "**Beta** measures how much the stock tends to move relative to the overall market.\n\n"
        "≈1 → moves with the market · **>1** → more volatile (bigger swings) · "
        "**<1** → steadier · **negative** → tends to move opposite the market.\n\n"
        "Higher beta = more risk *and* more potential reward."
    ),
    "moving_avg": (
        "The **50-day** and **200-day moving averages** are the average closing price over "
        "the last 50 and 200 trading days. They smooth out daily noise to reveal the trend.\n\n"
        "Common convention: price **above both** is read as an uptrend, **below both** as a "
        "downtrend. When the 50-day crosses *above* the 200-day it's a 'golden cross' "
        "(bullish); the reverse is a 'death cross' (bearish).\n\n"
        "These are trend *signals*, not guarantees."
    ),
    "week_range": (
        "The **52-week range** is the lowest and highest price over the past year. Where "
        "today's price sits in that range is a quick read on momentum:\n\n"
        "Near the **high** → strength (or possibly overextended). Near the **low** → "
        "weakness (or possibly a bargain, *if* the business is sound)."
    ),
    "volume": (
        "**Volume** is how many shares traded. It matters as *confirmation*: a big price "
        "move on **high** volume has conviction behind it; the same move on **low** volume "
        "is easier to reverse and can be a 'trap.'\n\n"
        "Comparing today's volume to the average tells you if interest is unusually high."
    ),
}


# ---------------------------------------------------------------------------
# Data helpers  (cached so repeated views don't waste API calls)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def fmp_get(path: str):
    """Call an FMP endpoint and return parsed JSON. Cached for 15 minutes."""
    sep = "&" if "?" in path else "?"
    url = f"{BASE}/{path}{sep}apikey={API_KEY}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_movers(kind: str):
    """kind is 'gainers', 'losers', or 'actives'."""
    data = fmp_get(f"stock_market/{kind}")
    return data if isinstance(data, list) else []


def _first(path: str):
    """Many FMP endpoints return a list with one object; grab it safely."""
    data = fmp_get(path)
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return {}


def get_quote(symbol):        return _first(f"quote/{symbol}")
def get_ratios(symbol):       return _first(f"ratios-ttm/{symbol}")
def get_key_metrics(symbol):  return _first(f"key-metrics-ttm/{symbol}")
def get_profile(symbol):      return _first(f"profile/{symbol}")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def to_float(v):
    try:
        return float(str(v).replace("%", "").replace("(", "").replace(")", "").replace("+", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def money(v):
    v = to_float(v)
    return f"${v:,.2f}" if v is not None else "N/A"


def big_money(v):
    v = to_float(v)
    if v is None:
        return "N/A"
    for unit, size in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if abs(v) >= size:
            return f"${v / size:,.2f}{unit}"
    return f"${v:,.0f}"


def num(v, decimals=2, suffix=""):
    v = to_float(v)
    return f"{v:,.{decimals}f}{suffix}" if v is not None else "N/A"


def pct(v):
    v = to_float(v)
    return f"{v:,.2f}%" if v is not None else "N/A"


def big_count(v):
    v = to_float(v)
    if v is None:
        return "N/A"
    for unit, size in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= size:
            return f"{v / size:,.2f}{unit}"
    return f"{v:,.0f}"


# ---------------------------------------------------------------------------
# A metric tile with a tap-to-expand explainer  (the teaching moment)
# ---------------------------------------------------------------------------
def metric_tile(col, label, value, explainer_key, note=None):
    with col:
        st.metric(label, value)
        with st.expander("ℹ️ What does this mean?"):
            st.markdown(EXPLAINERS.get(explainer_key, "_No explainer yet._"))
            if note:
                st.info(note)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
def show_movers(kind):
    titles = {"gainers": "📈 Top Gainers", "losers": "📉 Top Losers", "actives": "🔥 Most Active"}
    st.subheader(titles.get(kind, "Movers"))
    st.caption("Today's biggest moves. See one you want to understand? Type its ticker in the sidebar to drill in.")

    rows = get_movers(kind)
    if not rows:
        st.warning("No data came back. This can happen outside US market hours, or if the daily API limit was hit.")
        return

    df = pd.DataFrame(rows)
    keep = [c for c in ["symbol", "name", "price", "changesPercentage"] if c in df.columns]
    df = df[keep].head(15).copy()
    if "changesPercentage" in df.columns:
        df["changesPercentage"] = df["changesPercentage"].map(to_float)
    df = df.rename(columns={
        "symbol": "Symbol", "name": "Company",
        "price": "Price ($)", "changesPercentage": "Change %",
    })

    st.dataframe(
        df, hide_index=True, use_container_width=True,
        column_config={
            "Price ($)": st.column_config.NumberColumn(format="$%.2f"),
            "Change %": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )


def show_ticker(symbol):
    symbol = symbol.upper().strip()
    st.subheader(f"🔎 {symbol}")

    try:
        quote = get_quote(symbol)
    except requests.HTTPError as e:
        st.error(f"Couldn't fetch data for {symbol}. Check the ticker, or the API limit may be reached. ({e})")
        return

    if not quote:
        st.warning(f"No data found for '{symbol}'. Double-check the ticker symbol.")
        return

    profile = get_profile(symbol)
    ratios = get_ratios(symbol)
    metrics = get_key_metrics(symbol)

    name = profile.get("companyName") or quote.get("name") or symbol
    sector = profile.get("sector")
    industry = profile.get("industry")
    header = name
    if sector:
        header += f"  ·  {sector}" + (f" / {industry}" if industry else "")
    st.markdown(f"**{header}**")

    # ---- Snapshot ----
    st.markdown("#### Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    price = quote.get("price")
    change_pct = quote.get("changesPercentage")
    with c1:
        st.metric("Price", money(price), delta=pct(change_pct) if to_float(change_pct) is not None else None)
    metric_tile(c2, "Market Cap", big_money(quote.get("marketCap")), "market_cap")

    low, high = quote.get("yearLow"), quote.get("yearHigh")
    range_val = f"{money(low)} – {money(high)}" if to_float(low) and to_float(high) else "N/A"
    range_note = None
    p, lo, hi = to_float(price), to_float(low), to_float(high)
    if None not in (p, lo, hi) and hi > lo:
        position = (p - lo) / (hi - lo) * 100
        range_note = f"Today's price sits about {position:.0f}% of the way up its 52-week range."
    metric_tile(c3, "52-Week Range", range_val, "week_range", note=range_note)

    vol, avg_vol = quote.get("volume"), quote.get("avgVolume")
    vol_note = None
    v, av = to_float(vol), to_float(avg_vol)
    if v and av and av > 0:
        vol_note = f"Today's volume is about {v / av:.1f}× the average — {'unusually high' if v / av > 1.5 else 'roughly normal'}."
    metric_tile(c4, "Volume (vs avg)", f"{big_count(vol)}  (avg {big_count(avg_vol)})", "volume", note=vol_note)

    # ---- Valuation ----
    st.markdown("#### Valuation")
    c1, c2, c3 = st.columns(3)
    metric_tile(c1, "P/E (trailing)", num(quote.get("pe")), "pe")
    metric_tile(c2, "PEG", num(ratios.get("pegRatioTTM")), "peg")
    metric_tile(c3, "EV / EBITDA", num(metrics.get("enterpriseValueOverEBITDATTM")), "ev_ebitda")

    # ---- Financial health ----
    st.markdown("#### Financial Health")
    c1, c2, c3, c4 = st.columns(4)
    nm = ratios.get("netProfitMarginTTM")
    gm = ratios.get("grossProfitMarginTTM")
    metric_tile(c1, "Net Margin", pct(to_float(nm) * 100) if to_float(nm) is not None else "N/A", "net_margin")
    metric_tile(c2, "Gross Margin", pct(to_float(gm) * 100) if to_float(gm) is not None else "N/A", "gross_margin")
    metric_tile(c3, "Debt / Equity", num(ratios.get("debtEquityRatioTTM")), "debt_equity")
    metric_tile(c4, "FCF / Share", money(metrics.get("freeCashFlowPerShareTTM")), "fcf_per_share")

    # ---- Trend & risk ----
    st.markdown("#### Trend & Risk")
    c1, c2, c3 = st.columns(3)
    ma50, ma200 = quote.get("priceAvg50"), quote.get("priceAvg200")
    trend_note = None
    m50, m200 = to_float(ma50), to_float(ma200)
    if None not in (p, m50, m200):
        if p > m50 and p > m200:
            trend_note = "Price is above both moving averages — conventionally read as an uptrend."
        elif p < m50 and p < m200:
            trend_note = "Price is below both moving averages — conventionally read as a downtrend."
        else:
            trend_note = "Price is between its moving averages — a mixed/transitional trend."
    metric_tile(c1, "50-Day Avg", money(ma50), "moving_avg", note=trend_note)
    metric_tile(c2, "200-Day Avg", money(ma200), "moving_avg")
    metric_tile(c3, "Beta", num(profile.get("beta")), "beta")

    # ---- Your own notes (this decision is yours) ----
    st.markdown("#### Your Notes")
    st.caption("Write down your own reasoning. (Note: notes are session-only for now — saving them permanently is a later feature.)")
    st.text_area("What's your read on this one?", key=f"notes_{symbol}", height=120,
                 placeholder="e.g. Strong margins but debt looks high for the sector — want to check the latest earnings before deciding.")


# ---------------------------------------------------------------------------
# Sidebar + routing
# ---------------------------------------------------------------------------
st.sidebar.title("📈 Stock Research")
st.sidebar.caption("Aggregate the data. Understand the metrics. **You** decide.")

ticker = st.sidebar.text_input("🔎 Analyze a ticker", placeholder="e.g. AAPL").strip()

st.sidebar.markdown("---")
preset = st.sidebar.radio("Or browse movers:", ["Top Gainers", "Top Losers", "Most Active"])
preset_map = {"Top Gainers": "gainers", "Top Losers": "losers", "Most Active": "actives"}

# Main area
st.title("Stock Research Dashboard")

if not API_KEY:
    st.error("No FMP API key found.")
    st.markdown(
        "**To get started (free, no credit card):**\n"
        "1. Get a free key at https://site.financialmodelingprep.com/developer/docs/dashboard\n"
        "2. Add it to your Streamlit secrets as `FMP_API_KEY = \"your_key\"`\n"
        "   - Locally: put that line in `.streamlit/secrets.toml`\n"
        "   - On Streamlit Cloud: App → Settings → Secrets\n"
        "3. Reload this page."
    )
    st.stop()

if ticker:
    show_ticker(ticker)
else:
    show_movers(preset_map[preset])

st.markdown("---")
st.caption(
    "📚 Educational tool, not financial advice. Data is provided by Financial Modeling Prep and may be "
    "delayed. Metrics and 'healthy ranges' are general guidance — always compare within a company's own "
    "industry, and make your own decisions."
)
