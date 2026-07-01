"""
Stock Research Dashboard  —  provider-layered
---------------------------------------------
The app calls a clean interface — get_quote(), get_company_profile(),
get_key_metrics(), search_companies() — and doesn't care which provider
answers. Swapping/adding a provider later means editing one section, not
the whole app.

Providers wired now:
  • FMP (free)      -> movers lists + company name search  (work for all tickers)
  • Finnhub (free)  -> quote, profile, fundamentals        (work for all tickers)
Stubs for later:
  • SEC EDGAR       -> filings          (get_filings, placeholder)
  • Finnhub news    -> news/sentiment   (get_news, placeholder)

This app AGGREGATES and EXPLAINS. It never tells you to buy or sell.
"""

import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Stock Research Dashboard", page_icon="📈", layout="wide")

FMP_BASE = "https://financialmodelingprep.com/stable"
FINNHUB_BASE = "https://finnhub.io/api/v1"

FMP_KEY = st.secrets.get("FMP_API_KEY", "")
FINNHUB_KEY = st.secrets.get("FINNHUB_API_KEY", "")


# ===========================================================================
# PLAIN-ENGLISH EXPLAINERS  (the "understand finance" layer)
# ===========================================================================
EXPLAINERS = {
    "market_cap": (
        "**Market capitalization** = share price × number of shares. The total value "
        "the market places on the whole company.\n\n"
        "Rough buckets: mega (>$200B), large ($10B–$200B), mid ($2B–$10B), "
        "small ($300M–$2B), micro (<$300M). Bigger tends to be steadier; smaller can "
        "move faster, both ways."
    ),
    "pe": (
        "**Price-to-Earnings (P/E)** = share price ÷ earnings per share. Dollars paid per "
        "dollar of annual profit.\n\n"
        "**High** can mean growth expectations *or* an expensive stock; **low** can mean a "
        "bargain *or* expected trouble. Compare within the same industry — normal P/E "
        "varies a lot by sector. No P/E usually means no current profit."
    ),
    "peg": (
        "**PEG** = P/E ÷ earnings growth rate. Puts the P/E in context of growth.\n\n"
        "Rule of thumb: ~**1** fair, **<1** possibly undervalued for its growth, **>2** "
        "possibly pricey. Only meaningful with real, positive earnings growth."
    ),
    "ev_ebitda": (
        "**EV/EBITDA** = enterprise value ÷ EBITDA. A valuation measure that *includes "
        "debt* (unlike P/E), so it's fairer across companies with different borrowing.\n\n"
        "**Lower** generally = cheaper. Compare against industry peers."
    ),
    "net_margin": (
        "**Net profit margin** = net profit ÷ revenue. Of every sales dollar, how much "
        "becomes profit.\n\n"
        "**Higher** is generally healthier. Varies hugely by industry (software high, "
        "grocery thin) — compare within a sector."
    ),
    "gross_margin": (
        "**Gross margin** = (revenue − cost of goods sold) ÷ revenue. Profit after the "
        "direct cost of making the product, before overhead.\n\n"
        "High, stable gross margins often signal a strong product or brand."
    ),
    "debt_equity": (
        "**Debt-to-Equity** = total debt ÷ shareholder equity. How much the company leans "
        "on borrowing vs. owners' money.\n\n"
        "**Higher** = more leverage: potentially higher returns, more risk if earnings "
        "wobble or rates rise. 'Safe' depends on industry — utilities/telecom carry more.\n\n"
        "*(Shown here as a percentage: 150 means 1.5× equity.)*"
    ),
    "roe": (
        "**Return on Equity (ROE)** = net income ÷ shareholder equity. How much profit the "
        "company squeezes from shareholders' money.\n\n"
        "**Higher** generally means efficient use of capital — but very high ROE can be "
        "inflated by heavy debt, so read it next to Debt-to-Equity. Compare within an industry."
    ),
    "beta": (
        "**Beta** = how much the stock moves relative to the overall market.\n\n"
        "≈1 moves with the market · **>1** more volatile · **<1** steadier · **negative** "
        "moves opposite. Higher beta = more risk *and* more potential reward."
    ),
    "week_range": (
        "The **52-week range** is the lowest and highest price over the past year. Where "
        "today's price sits is a quick read on momentum:\n\n"
        "Near the **high** → strength (or overextended). Near the **low** → weakness (or a "
        "bargain, *if* the business is sound)."
    ),
    "volume": (
        "**Average daily volume** is how many shares typically trade per day. It's about "
        "liquidity and conviction — heavily traded stocks are easier to buy/sell, and big "
        "price moves on high volume carry more weight than moves on thin volume."
    ),
}


# ===========================================================================
# PROVIDER: FMP  (movers lists + name search — both work for all tickers, free)
# ===========================================================================
@st.cache_data(ttl=900, show_spinner=False)
def _fmp_get(path: str):
    sep = "&" if "?" in path else "?"
    url = f"{FMP_BASE}/{path}{sep}apikey={FMP_KEY}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


MOVER_ENDPOINTS = {"gainers": "biggest-gainers", "losers": "biggest-losers", "actives": "most-actives"}


def get_movers(kind: str):
    data = _fmp_get(MOVER_ENDPOINTS[kind])
    return data if isinstance(data, list) else []


@st.cache_data(ttl=3600, show_spinner=False)
def search_companies(query: str):
    """Name -> ticker lookup, major US exchanges sorted first."""
    q = requests.utils.quote(query)
    try:
        data = _fmp_get(f"search-name?query={q}")
    except requests.HTTPError:
        return []
    if not isinstance(data, list):
        return []
    major = {"NASDAQ", "NYSE", "AMEX", "NYSEARCA", "BATS"}

    def rank(m):
        exch = (m.get("exchangeShortName") or m.get("exchange") or "").upper()
        return 0 if exch in major else 1

    return sorted(data, key=rank)


# ===========================================================================
# PROVIDER: Finnhub  (quote, profile, fundamentals — work for all tickers, free)
# ===========================================================================
@st.cache_data(ttl=900, show_spinner=False)
def _finnhub_get(path: str):
    sep = "&" if "?" in path else "?"
    url = f"{FINNHUB_BASE}/{path}{sep}token={FINNHUB_KEY}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _fh_quote(symbol):    return _finnhub_get(f"quote?symbol={symbol}")
def _fh_profile(symbol):  return _finnhub_get(f"stock/profile2?symbol={symbol}")
def _fh_metric(symbol):
    data = _finnhub_get(f"stock/metric?symbol={symbol}&metric=all")
    return data.get("metric", {}) if isinstance(data, dict) else {}


# ===========================================================================
# PROVIDER: SEC / news  (LATER — placeholders so the seams exist)
# ===========================================================================
def get_filings(symbol):
    """TODO: pull 10-K/10-Q/8-K from SEC EDGAR. Not built yet."""
    return None


def get_news(symbol):
    """TODO: pull recent news via Finnhub /company-news. Not built yet."""
    return []


# ===========================================================================
# NORMALIZED INTERFACE  (what the rest of the app calls — provider-agnostic)
# Units are normalized here so the display layer never has to guess.
# ===========================================================================
def get_quote(symbol):
    q = _fh_quote(symbol)
    if not isinstance(q, dict) or not q.get("c"):   # c==0 -> unknown symbol
        return {}
    return {
        "price": q.get("c"),
        "change_pct": q.get("dp"),
        "day_high": q.get("h"),
        "day_low": q.get("l"),
        "prev_close": q.get("pc"),
    }


def get_company_profile(symbol):
    p = _fh_profile(symbol)
    if not isinstance(p, dict) or not p:
        return {}
    mcap = p.get("marketCapitalization")  # Finnhub gives this in millions
    return {
        "name": p.get("name"),
        "exchange": p.get("exchange"),
        "industry": p.get("finnhubIndustry"),
        "market_cap": mcap * 1e6 if isinstance(mcap, (int, float)) else None,
    }


def get_key_metrics(symbol):
    m = _fh_metric(symbol)

    def g(*keys):
        return pick(m, *keys)

    avg_vol_m = g("10DayAverageTradingVolume", "3MonthAverageTradingVolume")  # in millions of shares
    return {
        "pe": g("peTTM", "peBasicExclExtraTTM", "peInclExtraTTM", "peNormalizedAnnual"),
        "peg": g("pegTTM", "pegRatioTTM"),
        "ev_ebitda": g("evEbitdaTTM", "currentEv/ebitdaTTM", "enterpriseValueEbitdaTTM"),
        "net_margin_pct": g("netProfitMarginTTM", "netProfitMarginAnnual"),
        "gross_margin_pct": g("grossMarginTTM", "grossMarginAnnual"),
        "debt_to_equity": g("totalDebt/totalEquityQuarterly", "totalDebt/totalEquityAnnual",
                            "longTermDebt/equityQuarterly", "longTermDebt/equityAnnual"),
        "roe_pct": g("roeTTM", "roeRfy"),
        "beta": g("beta"),
        "week_high": g("52WeekHigh"),
        "week_low": g("52WeekLow"),
        "avg_volume": avg_vol_m * 1e6 if isinstance(avg_vol_m, (int, float)) else None,
    }


# ===========================================================================
# Safe field access + formatting helpers
# ===========================================================================
def pick(d, *keys):
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


def big_count(v):
    v = to_float(v)
    if v is None:
        return "N/A"
    for unit, size in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= size:
            return f"{v / size:,.2f}{unit}"
    return f"{v:,.0f}"


def metric_tile(col, label, value, explainer_key, note=None):
    with col:
        st.metric(label, value)
        with st.expander("ℹ️ What does this mean?"):
            st.markdown(EXPLAINERS.get(explainer_key, "_No explainer yet._"))
            if note:
                st.info(note)


# ===========================================================================
# Views
# ===========================================================================
def show_movers(kind):
    titles = {"gainers": "📈 Top Gainers", "losers": "📉 Top Losers", "actives": "🔥 Most Active"}
    st.subheader(titles.get(kind, "Movers"))
    st.caption("Today's biggest moves. See one you want to understand? Search it in the sidebar to drill in.")

    try:
        rows = get_movers(kind)
    except requests.HTTPError as e:
        st.error(f"Couldn't load movers. The API limit may be reached, or it's outside market hours. ({e})")
        return
    if not rows:
        st.warning("No data came back — common outside US market hours, or if the daily API limit was hit.")
        return

    df = pd.DataFrame(rows)
    for cand in ("changePercentage", "changesPercentage", "changesPercent"):
        if cand in df.columns:
            df = df.rename(columns={cand: "changePct"})
            break
    keep = [c for c in ["symbol", "name", "price", "changePct"] if c in df.columns]
    df = df[keep].head(15).copy()
    if "changePct" in df.columns:
        df["changePct"] = df["changePct"].map(to_float)
    df = df.rename(columns={"symbol": "Symbol", "name": "Company",
                            "price": "Price ($)", "changePct": "Change %"})
    st.dataframe(df, hide_index=True, use_container_width=True, column_config={
        "Price ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Change %": st.column_config.NumberColumn(format="%.2f%%"),
    })


def show_ticker(symbol):
    symbol = symbol.upper().strip()
    st.subheader(f"🔎 {symbol}")

    if not FINNHUB_KEY:
        st.info(
            "**One quick setup step to unlock stock details (free):**\n"
            "1. Get a free key at https://finnhub.io/register\n"
            "2. Add it to your Streamlit secrets as `FINNHUB_API_KEY = \"your_key\"`\n"
            "   (App → Settings → Secrets — same place as your FMP key)\n"
            "3. Reload. The movers lists already work without it."
        )
        return

    try:
        quote = get_quote(symbol)
    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        if status == 401:
            st.error("Finnhub rejected the API key. Double-check `FINNHUB_API_KEY` in your Streamlit secrets.")
        elif status == 429:
            st.warning("Hit Finnhub's rate limit (60/min on free). Wait a minute and try again.")
        else:
            st.error(f"Couldn't fetch data for {symbol}. ({e})")
        return

    if not quote:
        st.warning(f"No data found for '{symbol}'. Double-check the ticker symbol.")
        return

    try:
        profile = get_company_profile(symbol)
    except requests.HTTPError:
        profile = {}
    try:
        metrics = get_key_metrics(symbol)
    except requests.HTTPError:
        metrics = {}

    name = profile.get("name") or symbol
    industry = profile.get("industry")
    header = name + (f"  ·  {industry}" if industry else "")
    if profile.get("exchange"):
        header += f"  ·  {profile['exchange']}"
    st.markdown(f"**{header}**")

    price = quote.get("price")
    change_pct = quote.get("change_pct")

    # ---- Snapshot ----
    st.markdown("#### Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Price", money(price),
                  delta=pct(change_pct) if to_float(change_pct) is not None else None)
    metric_tile(c2, "Market Cap", big_money(profile.get("market_cap")), "market_cap")

    low, high = metrics.get("week_low"), metrics.get("week_high")
    range_val = f"{money(low)} – {money(high)}" if to_float(low) and to_float(high) else "N/A"
    range_note = None
    p, lo, hi = to_float(price), to_float(low), to_float(high)
    if None not in (p, lo, hi) and hi > lo:
        pos = (p - lo) / (hi - lo) * 100
        range_note = f"Today's price sits about {pos:.0f}% of the way up its 52-week range."
    metric_tile(c3, "52-Week Range", range_val, "week_range", note=range_note)

    metric_tile(c4, "Avg Daily Volume", big_count(metrics.get("avg_volume")), "volume")

    # ---- Valuation ----
    st.markdown("#### Valuation")
    c1, c2, c3 = st.columns(3)
    metric_tile(c1, "P/E (trailing)", num(metrics.get("pe")), "pe")
    metric_tile(c2, "PEG", num(metrics.get("peg")), "peg")
    metric_tile(c3, "EV / EBITDA", num(metrics.get("ev_ebitda")), "ev_ebitda")

    # ---- Financial health ----
    st.markdown("#### Financial Health")
    c1, c2, c3, c4 = st.columns(4)
    metric_tile(c1, "Net Margin", pct(metrics.get("net_margin_pct")), "net_margin")
    metric_tile(c2, "Gross Margin", pct(metrics.get("gross_margin_pct")), "gross_margin")
    metric_tile(c3, "Debt / Equity", num(metrics.get("debt_to_equity")), "debt_equity")
    metric_tile(c4, "Return on Equity", pct(metrics.get("roe_pct")), "roe")

    # ---- Risk ----
    st.markdown("#### Risk")
    c1, c2, c3 = st.columns(3)
    metric_tile(c1, "Beta", num(metrics.get("beta")), "beta")
    with c2:
        st.metric("Day Range", f"{money(quote.get('day_low'))} – {money(quote.get('day_high'))}")
    with c3:
        st.metric("Prev Close", money(quote.get("prev_close")))

    # ---- Your notes ----
    st.markdown("#### Your Notes")
    st.caption("Write your own reasoning. (Session-only for now — permanent saving is a later feature.)")
    st.text_area("What's your read on this one?", key=f"notes_{symbol}", height=120,
                 placeholder="e.g. Strong margins but debt looks high for the sector — check latest earnings before deciding.")

    st.caption("ℹ️ Some metrics (PEG, EV/EBITDA) may show N/A on the free data tier — the app stays fully usable without them.")


# ===========================================================================
# Sidebar + routing
# ===========================================================================
st.sidebar.title("📈 Stock Research")
st.sidebar.caption("Aggregate the data. Understand the metrics. **You** decide.")

search_term = st.sidebar.text_input("🔎 Search company or ticker",
                                     placeholder="e.g. Micron  or  MU").strip()

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
            exch = m.get("exchangeShortName") or m.get("exchange") or ""
            label = f"{nm} ({sym})" + (f" · {exch}" if exch else "")
            options[label] = sym
        if options:
            choice = st.sidebar.selectbox("Select a match:", list(options.keys()))
            selected_symbol = options[choice]
    if selected_symbol is None:
        selected_symbol = search_term.upper()
        st.sidebar.caption(f"No name matches — trying **{selected_symbol}** as a ticker.")

st.sidebar.markdown("---")
preset = st.sidebar.radio("Or browse movers:", ["Top Gainers", "Top Losers", "Most Active"])
preset_map = {"Top Gainers": "gainers", "Top Losers": "losers", "Most Active": "actives"}

st.title("Stock Research Dashboard")

if not FMP_KEY:
    st.error("No FMP API key found.")
    st.markdown(
        "**To get started (free):**\n"
        "1. FMP key: https://site.financialmodelingprep.com/developer/docs/dashboard\n"
        "2. Add to Streamlit secrets as `FMP_API_KEY = \"your_key\"`\n"
        "3. (For stock details) also add a free Finnhub key as `FINNHUB_API_KEY = \"your_key\"` from https://finnhub.io/register\n"
        "4. Reload."
    )
    st.stop()

if selected_symbol:
    show_ticker(selected_symbol)
else:
    show_movers(preset_map[preset])

st.markdown("---")
st.caption(
    "📚 Educational tool, not financial advice. Data from FMP (movers) and Finnhub (stock details), "
    "and may be delayed. Metrics and 'healthy ranges' are general guidance — compare within a "
    "company's own industry, and make your own decisions."
)
