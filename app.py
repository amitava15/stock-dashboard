"""
Stock Research Dashboard  —  Layers 1 & 2  (FMP "stable" API)
------------------------------------------------------------
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

# NOTE: FMP retired the old /api/v3/ endpoints. New keys use the /stable/ API.
BASE = "https://financialmodelingprep.com/stable"

# Your FMP API key lives in Streamlit "secrets", never in this file.
API_KEY = st.secrets.get("FMP_API_KEY", "")


# ---------------------------------------------------------------------------
# Plain-English explainers  —  this is the "understand finance" layer.
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
    """Call an FMP /stable/ endpoint and return parsed JSON. Cached 15 min."""
    sep = "&" if "?" in path else "?"
    url = f"{BASE}/{path}{sep}apikey={API_KEY}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


# Stable endpoint names for the movers presets
MOVER_ENDPOINTS = {
    "gainers": "biggest-gainers",
    "losers": "biggest-losers",
    "actives": "most-actives",
}


def get_movers(kind: str):
    data = fmp_get(MOVER_ENDPOINTS[kind])
    return data if isinstance(data, list) else []


def _first(path: str):
    """Most FMP endpoints return a list with one object; grab it safely."""
    data = fmp_get(path)
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return {}


def get_quote(symbol):        return _first(f"quote?symbol={symbol}")
def get_ratios(symbol):       return _first(f"ratios-ttm?symbol={symbol}")
def get_key_metrics(symbol):  return _first(f"key-metrics-ttm?symbol={symbol}")
def get_profile(symbol):      return _first(f"profile?symbol={symbol}")


@st.cache_data(ttl=3600, show_spinner=False)
def search_companies(query: str):
    """Look up tickers by company name (or partial name/ticker)."""
    q = requests.utils.quote(query)
    try:
        data = fmp_get(f"search-name?query={q}")
    except requests.HTTPError:
        return []
    return data if isinstance(data, list) else []


# ---------------------------------------------------------------------------
# Safe field access + formatting helpers
# ---------------------------------------------------------------------------
def pick(d, *keys):
    """Return the first present, non-null value among candidate field names."""
    if not isinstance(d, dict):
        return None
    for k in keys:
        if d.get(k) is not None:
            return d.get(k)
    return None


def to_float(v):
    try:
        s = str(v).replace("%", "").replace("(", "").replace(")", "").replace("+", "").replace(",", "")
        return float(s)
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


def as_pct(v):
    """Format a margin whether FMP returns a fraction (0.25) or a number (25)."""
    v = to_float(v)
    if v is None:
        return "N/A"
    if abs(v) <= 1.5:      # looks like a fraction -> convert to percent
        v *= 100
    return f"{v:,.2f}%"


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

    try:
        rows = get_movers(kind)
    except requests.HTTPError as e:
        st.error(f"Couldn't load movers from the data provider. The API limit may be reached, or it's outside market hours. ({e})")
        return

    if not rows:
        st.warning("No data came back. This can happen outside US market hours, or if the daily API limit was hit.")
        return

    df = pd.DataFrame(rows)
    # Normalize the percent-change column name across API versions
    for cand in ("changePercentage", "changesPercentage", "changesPercent"):
        if cand in df.columns:
            df = df.rename(columns={cand: "changePct"})
            break
    keep = [c for c in ["symbol", "name", "price", "changePct"] if c in df.columns]
    df = df[keep].head(15).copy()
    if "changePct" in df.columns:
        df["changePct"] = df["changePct"].map(to_float)
    df = df.rename(columns={
        "symbol": "Symbol", "name": "Company",
        "price": "Price ($)", "changePct": "Change %",
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

    # These are secondary; if any fail, keep going with what we have.
    try:
        profile = get_profile(symbol)
    except requests.HTTPError:
        profile = {}
    try:
        ratios = get_ratios(symbol)
    except requests.HTTPError:
        ratios = {}
    try:
        metrics = get_key_metrics(symbol)
    except requests.HTTPError:
        metrics = {}

    name = pick(profile, "companyName") or pick(quote, "name") or symbol
    sector = pick(profile, "sector")
    industry = pick(profile, "industry")
    header = name
    if sector:
        header += f"  ·  {sector}" + (f" / {industry}" if industry else "")
    st.markdown(f"**{header}**")

    price = pick(quote, "price")
    change_pct = pick(quote, "changePercentage", "changesPercentage")

    # ---- Snapshot ----
    st.markdown("#### Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Price", money(price),
                  delta=pct(change_pct) if to_float(change_pct) is not None else None)
    metric_tile(c2, "Market Cap",
                big_money(pick(quote, "marketCap") or pick(profile, "marketCap", "mktCap")),
                "market_cap")

    low, high = pick(quote, "yearLow"), pick(quote, "yearHigh")
    range_val = f"{money(low)} – {money(high)}" if to_float(low) and to_float(high) else "N/A"
    range_note = None
    p, lo, hi = to_float(price), to_float(low), to_float(high)
    if None not in (p, lo, hi) and hi > lo:
        position = (p - lo) / (hi - lo) * 100
        range_note = f"Today's price sits about {position:.0f}% of the way up its 52-week range."
    metric_tile(c3, "52-Week Range", range_val, "week_range", note=range_note)

    vol = pick(quote, "volume")
    avg_vol = pick(quote, "avgVolume", "averageVolume") or pick(profile, "averageVolume", "volAvg")
    vol_note = None
    v, av = to_float(vol), to_float(avg_vol)
    if v and av and av > 0:
        vol_note = f"Today's volume is about {v / av:.1f}× the average — {'unusually high' if v / av > 1.5 else 'roughly normal'}."
    metric_tile(c4, "Volume (vs avg)",
                f"{big_count(vol)}  (avg {big_count(avg_vol)})", "volume", note=vol_note)

    # ---- Valuation ----
    st.markdown("#### Valuation")
    c1, c2, c3 = st.columns(3)
    pe = pick(quote, "pe") or pick(ratios, "priceToEarningsRatioTTM", "peRatioTTM")
    peg = pick(ratios, "pegRatioTTM", "priceEarningsToGrowthRatioTTM")
    ev = pick(metrics, "enterpriseValueOverEBITDATTM", "evToEBITDATTM",
              "enterpriseValueMultipleTTM", "evToOperatingCashFlowTTM")
    metric_tile(c1, "P/E (trailing)", num(pe), "pe")
    metric_tile(c2, "PEG", num(peg), "peg")
    metric_tile(c3, "EV / EBITDA", num(ev), "ev_ebitda")

    # ---- Financial health ----
    st.markdown("#### Financial Health")
    c1, c2, c3, c4 = st.columns(4)
    nm = pick(ratios, "netProfitMarginTTM", "netProfitMargin")
    gm = pick(ratios, "grossProfitMarginTTM", "grossProfitMargin")
    de = pick(ratios, "debtToEquityRatioTTM", "debtEquityRatioTTM", "debtToEquityTTM")
    fcf = pick(metrics, "freeCashFlowPerShareTTM", "freeCashFlowPerShare")
    metric_tile(c1, "Net Margin", as_pct(nm), "net_margin")
    metric_tile(c2, "Gross Margin", as_pct(gm), "gross_margin")
    metric_tile(c3, "Debt / Equity", num(de), "debt_equity")
    metric_tile(c4, "FCF / Share", money(fcf), "fcf_per_share")

    # ---- Trend & risk ----
    st.markdown("#### Trend & Risk")
    c1, c2, c3 = st.columns(3)
    ma50 = pick(quote, "priceAvg50")
    ma200 = pick(quote, "priceAvg200")
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
    metric_tile(c3, "Beta", num(pick(profile, "beta")), "beta")

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

search_term = st.sidebar.text_input("🔎 Search company or ticker",
                                     placeholder="e.g. Apple  or  AAPL").strip()

selected_symbol = None
if search_term:
    matches = search_companies(search_term)
    if matches:
        options = {}
        for m in matches[:10]:
            sym = m.get("symbol")
            if not sym:
                continue
            nm = m.get("name") or sym
            exch = m.get("exchangeFullName") or m.get("exchange") or ""
            label = f"{nm} ({sym})" + (f" · {exch}" if exch else "")
            options[label] = sym
        if options:
            choice = st.sidebar.selectbox("Select a match:", list(options.keys()))
            selected_symbol = options[choice]
    if selected_symbol is None:
        # No name matches — fall back to treating the input as a ticker.
        selected_symbol = search_term.upper()
        st.sidebar.caption(f"No name matches — trying **{selected_symbol}** as a ticker.")

st.sidebar.markdown("---")
preset = st.sidebar.radio("Or browse movers:", ["Top Gainers", "Top Losers", "Most Active"])
preset_map = {"Top Gainers": "gainers", "Top Losers": "losers", "Most Active": "actives"}

st.title("Stock Research Dashboard")

if not API_KEY:
    st.error("No FMP API key found.")
    st.markdown(
        "**To get started (free, no credit card):**\n"
        "1. Get a free key at https://site.financialmodelingprep.com/developer/docs/dashboard\n"
        "2. Add it to your Streamlit secrets as `FMP_API_KEY = \"your_key\"`\n"
        "3. Reload this page."
    )
    st.stop()

if selected_symbol:
    show_ticker(selected_symbol)
else:
    show_movers(preset_map[preset])

st.markdown("---")
st.caption(
    "📚 Educational tool, not financial advice. Data is provided by Financial Modeling Prep and may be "
    "delayed. Metrics and 'healthy ranges' are general guidance — always compare within a company's own "
    "industry, and make your own decisions."
)
