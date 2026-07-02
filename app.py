"""
Stock Research Dashboard  —  provider-layered
---------------------------------------------
The app calls a clean interface — get_quote(), get_company_profile(),
get_key_metrics(), search_companies() — and doesn't care which provider
answers. Adding a provider later means editing one section, not the whole app.

Providers wired now:
  • FMP Starter     -> movers, search, real-time quote, profile, TTM ratios/metrics,
                       and historical prices  (all US tickers, one provider)
Stubs for later:
  • SEC EDGAR       -> filings          (get_filings, placeholder)
  • News            -> FMP /news/stock  (get_news, placeholder)

This app AGGREGATES and EXPLAINS. It never tells you to buy or sell.
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Stock Research Dashboard", page_icon="📈", layout="wide")

# ---------------------------------------------------------------------------
# Styling: quiet editorial "tasting card" — serif values like menu prices,
# letter-spaced labels like menu sections, hairline rules between courses.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root{
  --ink:#23231E; --paper:#FCFBF8; --muted:#7A7970; --line:#E8E6DE;
  --pos:#2F6B4F; --neg:#A24A38;
}

.stApp, [data-testid="stAppViewContainer"]{ background:var(--paper); }
[data-testid="stHeader"]{ background:transparent; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"]{
  font-family:'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif; color:var(--ink);
}
.block-container{ max-width:1080px; padding-top:2.6rem; padding-bottom:4.5rem; }

/* Page title — masthead */
h1{ font-family:'Fraunces', Georgia, serif !important; font-weight:600 !important;
    letter-spacing:-0.015em; font-size:2.4rem !important; color:var(--ink); }
h3, h4{ font-family:'Fraunces', Georgia, serif !important; font-weight:500 !important;
    letter-spacing:-0.01em; }

/* Ticker symbol + company line */
.rt-symbol{ font-family:'Fraunces', Georgia, serif; font-weight:600; font-size:2.15rem;
    letter-spacing:-0.015em; line-height:1.1; margin:.2rem 0 .1rem; }
.rt-company{ font-family:'Fraunces', Georgia, serif; font-style:italic; font-size:1.02rem;
    color:var(--muted); margin:0 0 .2rem; }

/* Section header — a "course" with a hairline rule and a plain-English kicker */
.rt-section{ margin:2.1rem 0 1.1rem; padding-top:1.1rem; border-top:1px solid var(--line); }
.rt-section .kicker{ font-size:.68rem; letter-spacing:.2em; text-transform:uppercase;
    color:var(--muted); }
.rt-section h2{ font-family:'Fraunces', Georgia, serif; font-weight:500; font-size:1.3rem;
    margin:.15rem 0 0; color:var(--ink); }

/* Metric labels — small, letter-spaced, quiet (menu section labels) */
[data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"] div{
    font-family:'IBM Plex Sans', sans-serif !important; font-size:.7rem !important;
    letter-spacing:.11em; text-transform:uppercase; color:var(--muted) !important; font-weight:500; }

/* Metric values — clean sans, uniform size (match the label font) */
[data-testid="stMetricValue"]{
    font-family:'IBM Plex Sans', sans-serif !important; font-weight:500 !important;
    font-variant-numeric:tabular-nums; letter-spacing:0; color:var(--ink);
    font-size:1.35rem !important; line-height:1.25 !important; }
/* Kill Streamlit's auto green/red tint on values inside the range strings */
[data-testid="stMetricValue"] *{
    color:var(--ink) !important; font-size:inherit !important; font-family:inherit !important; }

[data-testid="stMetricDelta"]{ font-family:'IBM Plex Sans', sans-serif !important; font-weight:500; }
[data-testid="stMetricLabel"] svg{ opacity:.55; }

/* Sidebar — soft, set apart with a hairline */
[data-testid="stSidebar"]{ background:#F5F3EC; border-right:1px solid var(--line); }
[data-testid="stSidebar"] h1{ font-family:'Fraunces', Georgia, serif !important;
    font-size:1.2rem !important; font-weight:600 !important; }

hr{ border-color:var(--line); }
[data-testid="stCaptionContainer"]{ color:var(--muted); }
</style>
""", unsafe_allow_html=True)

FMP_BASE = "https://financialmodelingprep.com/stable"
FMP_KEY = st.secrets.get("FMP_API_KEY", "")


# ===========================================================================
# PLAIN-ENGLISH EXPLAINERS  (shown as a small "?" tooltip on each metric)
# Each: what it is in simple terms + what it says about the business.
# ===========================================================================
EXPLAINERS = {
    "market_cap": (
        "How much the whole company is worth on the market (share price × number of shares).\n\n"
        "**For the business:** it's the market's overall price tag. Bigger companies are usually "
        "more established and steady; smaller ones can grow — or fall — faster."
    ),
    "pe": (
        "How many dollars you pay for each $1 of the company's yearly profit.\n\n"
        "**For the business:** a high number means investors expect strong future growth (or the "
        "stock is simply expensive); a low number can mean it's cheap, or that people worry about "
        "its future. Only meaningful compared with similar companies."
    ),
    "peg": (
        "The P/E adjusted for how fast profits are growing.\n\n"
        "**For the business:** it answers 'is the price fair for the growth you're getting?' Around "
        "1 is reasonable, well below 1 can be a bargain, well above 2 can be pricey."
    ),
    "ev_ebitda": (
        "A price tag that also counts the company's debt, not just its stock.\n\n"
        "**For the business:** useful for comparing companies that borrow different amounts. Lower "
        "generally means better value for what you get."
    ),
    "net_margin": (
        "Out of every $1 in sales, how many cents end up as actual profit.\n\n"
        "**For the business:** higher means the company keeps more of what it earns — a sign of "
        "efficiency or strong pricing power. Thin margins leave little room for error."
    ),
    "gross_margin": (
        "Profit left after the direct cost of making the product, before other expenses.\n\n"
        "**For the business:** high, steady gross margins usually point to a strong product or "
        "brand that customers will pay up for."
    ),
    "debt_equity": (
        "How much the company relies on borrowed money versus its owners' money.\n\n"
        "**For the business:** more debt can boost returns but adds risk — if sales dip or interest "
        "rates rise, heavy debt bites. What's 'safe' depends on the industry. "
        "(Shown as a ratio: 0.5 means debt is half of equity; 1.0 means they're equal.)"
    ),
    "roe": (
        "How much profit the company makes from the money shareholders have put in.\n\n"
        "**For the business:** higher means it's using investors' money efficiently — but a very "
        "high figure can be propped up by heavy borrowing, so read it next to Debt/Equity."
    ),
    "beta": (
        "How jumpy the stock is compared to the overall market.\n\n"
        "**For your risk:** above 1 = bigger swings up and down; below 1 = steadier; 1 = moves with "
        "the market. Higher beta means more risk and more potential reward."
    ),
    "week_range": (
        "The lowest and highest price over the past year.\n\n"
        "**For the business:** where today's price sits shows momentum — near the high suggests "
        "strength (or that it's run up a lot); near the low suggests weakness (or a possible bargain "
        "if the business is solid)."
    ),
    "volume": (
        "How many shares typically change hands each day.\n\n"
        "**For tradability:** high volume means the stock is easy to buy and sell, and big price "
        "moves on high volume carry more conviction than moves on light trading."
    ),
}


# ===========================================================================
# PROVIDER: FMP  (movers lists + search — both work for all tickers, free)
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


US_STOCK_EXCHANGES = {"NASDAQ", "NYSE", "AMEX"}


def _search_raw(endpoint: str, query: str):
    q = requests.utils.quote(query)
    try:
        data = _fmp_get(f"{endpoint}?query={q}")
    except requests.HTTPError:
        return []
    return data if isinstance(data, list) else []


@st.cache_data(ttl=3600, show_spinner=False)
def search_companies(query: str):
    """Find real US-listed stocks by ticker OR company name.

    Searches both the symbol and name endpoints, keeps only major US stock
    exchanges, drops mutual funds / forex / crypto, and puts an exact ticker
    match first — so typing 'MU' surfaces Micron, not a mutual fund.
    """
    qup = query.upper().strip()
    combined = {}
    for endpoint in ("search-symbol", "search-name"):
        for m in _search_raw(endpoint, query):
            sym = (m.get("symbol") or "").upper()
            if not sym:
                continue
            exch = (m.get("exchangeShortName") or m.get("exchange") or "").upper()
            if exch not in US_STOCK_EXCHANGES:        # drop forex/crypto/foreign/etc.
                continue
            if len(sym) == 5 and sym.endswith("X"):   # drop obvious mutual funds
                continue
            combined.setdefault(sym, m)

    results = list(combined.values())
    results.sort(key=lambda m: 0 if (m.get("symbol") or "").upper() == qup else 1)
    return results


@st.cache_data(ttl=900, show_spinner=False)
def get_price_history(symbol: str):
    """Daily price history from FMP (arrives newest-first).

    Returns a DataFrame sorted oldest -> newest with a 'date' column and
    'close'. On the free tier this 402s for real tickers; it works once
    FMP Starter is active. Any error yields an empty frame (handled upstream).
    """
    try:
        data = _fmp_get(f"historical-price-eod/full?symbol={symbol.upper()}")
    except requests.HTTPError:
        return pd.DataFrame()
    if not isinstance(data, list) or not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if "date" not in df.columns or "close" not in df.columns:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
    return df


# ===========================================================================
# PROVIDER: FMP detail endpoints  (quote, profile, TTM ratios/metrics — Starter)
# One provider for everything: real-time quote, company profile, and *trailing-
# twelve-month* ratios so figures like P/E stay current (not frozen at last FY).
# ===========================================================================
def _fmp_first(path: str):
    """FMP detail endpoints return a one-item list; grab [0] safely ({} on error)."""
    try:
        data = _fmp_get(path)
    except requests.HTTPError:
        return {}
    if isinstance(data, list):
        return data[0] if data else {}
    return data if isinstance(data, dict) else {}


def _fmp_quote(symbol):          return _fmp_first(f"quote?symbol={symbol}")
def _fmp_profile(symbol):        return _fmp_first(f"profile?symbol={symbol}")
def _fmp_ratios_ttm(symbol):     return _fmp_first(f"ratios-ttm?symbol={symbol}")
def _fmp_keymetrics_ttm(symbol): return _fmp_first(f"key-metrics-ttm?symbol={symbol}")


# ===========================================================================
# PROVIDER: SEC / news  (LATER — placeholders so the seams exist)
# ===========================================================================
def get_filings(symbol):
    """TODO: pull 10-K/10-Q/8-K from SEC EDGAR. Not built yet."""
    return None


def get_news(symbol):
    """TODO: pull recent news via FMP /news/stock. Not built yet."""
    return []


# ===========================================================================
# NORMALIZED INTERFACE  (provider-agnostic; units normalized here)
# ===========================================================================
def _avg_volume_from_history(symbol):
    """Fallback average daily volume: mean of the last 30 sessions' volume."""
    df = get_price_history(symbol)
    if df.empty or "volume" not in df.columns:
        return None
    tail = pd.to_numeric(df.tail(30)["volume"], errors="coerce").dropna()
    return float(tail.mean()) if len(tail) else None


def get_quote(symbol):
    q = _fmp_quote(symbol)
    if not isinstance(q, dict) or q.get("price") is None:   # unknown/uncovered symbol
        return {}
    return {
        "price": q.get("price"),
        "change_pct": q.get("changePercentage"),   # already a percent (e.g. -10.57)
        "day_high": q.get("dayHigh"),
        "day_low": q.get("dayLow"),
        "prev_close": q.get("previousClose"),
        "market_cap": q.get("marketCap"),           # absolute dollars (not millions)
        "week_high": q.get("yearHigh"),             # 52-week range lives on the quote
        "week_low": q.get("yearLow"),
        "name": q.get("name"),
        "exchange": q.get("exchange"),
        "ma_50": q.get("priceAvg50"),
        "ma_200": q.get("priceAvg200"),
    }


def get_company_profile(symbol):
    p = _fmp_profile(symbol)
    if not isinstance(p, dict) or not p:
        return {}
    return {
        "name": pick(p, "companyName", "name"),
        "exchange": pick(p, "exchangeShortName", "exchange"),
        "industry": pick(p, "industry"),
        "sector": pick(p, "sector"),
        "market_cap": pick(p, "marketCap", "mktCap"),
        "beta": pick(p, "beta"),
        "avg_volume": pick(p, "averageVolume", "avgVolume", "volAvg"),
    }


def get_key_metrics(symbol):
    r = _fmp_ratios_ttm(symbol)       # margins, P/E, PEG, debt/equity
    k = _fmp_keymetrics_ttm(symbol)   # EV/EBITDA, ROE
    p = _fmp_profile(symbol)          # beta, avg volume (cached; shared with profile)

    def as_pct(x):                    # FMP gives margins/ROE as fractions (0.55 -> 55%)
        f = to_float(x)
        return f * 100 if f is not None else None

    avg_vol = pick(p, "averageVolume", "avgVolume", "volAvg")
    if avg_vol is None:
        avg_vol = _avg_volume_from_history(symbol)

    return {
        "pe": pick(r, "priceToEarningsRatioTTM"),
        "peg": pick(r, "priceToEarningsGrowthRatioTTM"),
        "ev_ebitda": pick(k, "evToEBITDATTM", "enterpriseValueMultipleTTM")
                     or pick(r, "enterpriseValueMultipleTTM"),
        "net_margin_pct": as_pct(pick(r, "netProfitMarginTTM", "bottomLineProfitMarginTTM")),
        "gross_margin_pct": as_pct(pick(r, "grossProfitMarginTTM")),
        "debt_to_equity": pick(r, "debtToEquityRatioTTM"),
        "roe_pct": as_pct(pick(k, "returnOnEquityTTM")),
        "beta": pick(p, "beta"),
        "avg_volume": avg_vol,
    }


def _fmp_statement(path):
    """Fetch a statement list (income / balance-sheet / cash-flow / key-metrics).
    Returns [] on any error so an unavailable endpoint degrades gracefully."""
    try:
        data = _fmp_get(path)
    except requests.HTTPError:
        return []
    return data if isinstance(data, list) else []


def get_trajectory_annual(symbol, years=6):
    """Assemble multi-year annual series for the Business Trajectory charts.

    Each metric is a list aligned to `years` (oldest -> newest); a value is None
    where a field/endpoint isn't available, and a whole metric reads as
    'unavailable' upstream when every value is None. Income statement is the
    anchor; if it's empty the section shows a single unavailable note.
    """
    sym = symbol.upper()
    inc = _fmp_statement(f"income-statement?symbol={sym}&period=annual&limit={years}")
    km = _fmp_statement(f"key-metrics?symbol={sym}&period=annual&limit={years}")
    cf = _fmp_statement(f"cash-flow-statement?symbol={sym}&period=annual&limit={years}")
    bs = _fmp_statement(f"balance-sheet-statement?symbol={sym}&period=annual&limit={years}")

    def by_year(rows):
        out = {}
        for r in rows or []:
            y = str(r.get("fiscalYear") or r.get("calendarYear") or "")
            if not y and r.get("date"):
                y = str(r["date"])[:4]
            if y:
                out.setdefault(y, r)
        return out

    inc_y, km_y, cf_y, bs_y = by_year(inc), by_year(km), by_year(cf), by_year(bs)
    if not inc_y:
        return {"years": [], "metrics": {}}

    order = sorted(inc_y.keys())[-years:]                 # oldest -> newest

    def margin(y, field):                                 # % of revenue
        row = inc_y.get(y, {})
        rev = to_float(row.get("revenue"))
        val = to_float(row.get(field))
        return (val / rev * 100) if (rev not in (None, 0) and val is not None) else None

    def revenue(y):
        return to_float(inc_y.get(y, {}).get("revenue"))

    def eps(y):
        return to_float(pick(inc_y.get(y, {}), "epsDiluted", "eps"))

    def roe(y):
        v = to_float(pick(km_y.get(y, {}), "returnOnEquity"))
        return v * 100 if v is not None else None

    def fcf(y):
        row = cf_y.get(y, {})
        v = to_float(pick(row, "freeCashFlow"))
        if v is not None:
            return v
        ocf = to_float(pick(row, "operatingCashFlow", "netCashProvidedByOperatingActivities"))
        capex = to_float(pick(row, "capitalExpenditure"))
        if ocf is None or capex is None:
            return None
        return ocf - abs(capex)                           # capex is a cash outflow

    def debt(y):
        row = bs_y.get(y, {})
        v = to_float(pick(row, "totalDebt"))
        if v is not None:
            return v
        st_d = to_float(pick(row, "shortTermDebt"))
        lt_d = to_float(pick(row, "longTermDebt"))
        if st_d is None and lt_d is None:
            return None
        return (st_d or 0) + (lt_d or 0)

    metrics = {
        "revenue": [revenue(y) for y in order],
        "eps": [eps(y) for y in order],
        "gross_margin": [margin(y, "grossProfit") for y in order],
        "op_margin": [margin(y, "operatingIncome") for y in order],
        "net_margin": [margin(y, "netIncome") for y in order],
        "roe": [roe(y) for y in order],
        "fcf": [fcf(y) for y in order],
        "debt": [debt(y) for y in order],
    }
    return {"years": order, "metrics": metrics}


def get_cash_annual(symbol, years=6):
    """Assemble annual cash-generation series: FCF, FCF margin, FCF/share, FCF
    yield (all from the same annual statements, so the section is internally
    consistent). Values are None where a field/endpoint is unavailable.
    """
    sym = symbol.upper()
    inc = _fmp_statement(f"income-statement?symbol={sym}&period=annual&limit={years}")
    cf = _fmp_statement(f"cash-flow-statement?symbol={sym}&period=annual&limit={years}")
    km = _fmp_statement(f"key-metrics?symbol={sym}&period=annual&limit={years}")

    def by_year(rows):
        out = {}
        for r in rows or []:
            y = str(r.get("fiscalYear") or r.get("calendarYear") or "")
            if not y and r.get("date"):
                y = str(r["date"])[:4]
            if y:
                out.setdefault(y, r)
        return out

    inc_y, cf_y, km_y = by_year(inc), by_year(cf), by_year(km)
    if not cf_y and not inc_y:
        return {"years": [], "metrics": {}, "latest": {}}
    order = sorted(set(list(cf_y.keys()) + list(inc_y.keys())))[-years:]

    def fcf(y):
        row = cf_y.get(y, {})
        v = to_float(pick(row, "freeCashFlow"))
        if v is not None:
            return v
        ocf = to_float(pick(row, "operatingCashFlow", "netCashProvidedByOperatingActivities"))
        capex = to_float(pick(row, "capitalExpenditure"))
        if ocf is None or capex is None:
            return None
        return ocf - abs(capex)

    def fcf_margin(y):
        f, rev = fcf(y), to_float(inc_y.get(y, {}).get("revenue"))
        return (f / rev * 100) if (f is not None and rev not in (None, 0)) else None

    def fcf_ps(y):
        f = fcf(y)
        sh = to_float(pick(inc_y.get(y, {}), "weightedAverageShsOutDil", "weightedAverageShsOut"))
        return (f / sh) if (f is not None and sh not in (None, 0)) else None

    def fcf_yield(y):
        f = fcf(y)
        mc = to_float(pick(km_y.get(y, {}), "marketCap"))
        return (f / mc * 100) if (f is not None and mc not in (None, 0)) else None

    metrics = {
        "fcf": [fcf(y) for y in order],
        "fcf_margin": [fcf_margin(y) for y in order],
        "fcf_ps": [fcf_ps(y) for y in order],
        "fcf_yield": [fcf_yield(y) for y in order],
    }

    fcf_pairs = [(y, fcf(y)) for y in order if fcf(y) is not None]
    growth = None
    if len(fcf_pairs) >= 2 and fcf_pairs[-2][1] not in (None, 0):
        growth = (fcf_pairs[-1][1] - fcf_pairs[-2][1]) / abs(fcf_pairs[-2][1]) * 100
    latest = {
        "year": order[-1] if order else None,
        "fcf": metrics["fcf"][-1] if metrics["fcf"] else None,
        "fcf_growth": growth,
    }
    return {"years": order, "metrics": metrics, "latest": latest}


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


def money_range(a, b):
    """A 'low – high' price range. Escapes '$' so st.metric doesn't read a
    '$...$' pair as LaTeX math (which garbles the display)."""
    if to_float(a) is None or to_float(b) is None:
        return "N/A"
    return f"{money(a)} – {money(b)}".replace("$", r"\$")


def metric_tile(col, label, value, explainer_key, note=None):
    """A metric with a small '?' tooltip (hover on desktop, tap on mobile)."""
    help_text = EXPLAINERS.get(explainer_key, "")
    if note:
        help_text = (help_text + "\n\n**This one:** " + note).strip()
    with col:
        st.metric(label, value, help=help_text or None)


def section(title, kicker=""):
    """Render an editorial section header: hairline rule + kicker + serif title."""
    kick = f'<div class="kicker">{kicker}</div>' if kicker else ""
    st.markdown(f'<div class="rt-section">{kick}<h2>{title}</h2></div>', unsafe_allow_html=True)


# Editorial palette (kept in sync with the CSS block up top)
INK, PAPER, MUTED, LINE = "#23231E", "#FCFBF8", "#7A7970", "#E8E6DE"
POS, NEG = "#2F6B4F", "#A24A38"
RANGE_DAYS = {"1W": 7, "1M": 30, "6M": 182, "1Y": 365, "5Y": 365 * 5}
RANGE_WORDS = {"1W": "over the past week", "1M": "over the past month",
               "6M": "over the past 6 months", "1Y": "over the past year",
               "5Y": "over the past 5 years"}


def render_price_chart(symbol):
    """A quiet, editorial price line — styled to match the tasting-card look."""
    df = get_price_history(symbol)
    if df.empty:
        st.caption("Price history isn't available for this ticker on the current data plan.")
        return

    options = list(RANGE_DAYS.keys())
    picker = getattr(st, "segmented_control", None)
    if picker:
        choice = picker("Range", options, default="1Y",
                        key=f"range_{symbol}", label_visibility="collapsed")
    else:
        choice = st.radio("Range", options, index=3, horizontal=True,
                          key=f"range_{symbol}", label_visibility="collapsed")
    choice = choice or "1Y"

    cutoff = df["date"].max() - pd.Timedelta(days=RANGE_DAYS[choice])
    d = df[df["date"] >= cutoff]
    if len(d) < 2:
        d = df

    first, last = d["close"].iloc[0], d["close"].iloc[-1]
    up = last >= first
    line_color = POS if up else NEG
    fill_color = "rgba(47,107,79,0.08)" if up else "rgba(162,74,56,0.08)"

    change = (last - first) / first * 100 if first else 0
    st.caption(f"{'Up' if up else 'Down'} {abs(change):.1f}% {RANGE_WORDS[choice]}.")

    ymin, ymax = d["close"].min(), d["close"].max()
    pad = (ymax - ymin) * 0.08 or (ymax * 0.05)

    fig = go.Figure(go.Scatter(
        x=d["date"], y=d["close"], mode="lines",
        line=dict(color=line_color, width=2),
        fill="tozeroy", fillcolor=fill_color,
        hovertemplate="%{x|%b %-d, %Y}   $%{y:.2f}<extra></extra>",
    ))
    fig.update_layout(
        height=340,
        margin=dict(l=6, r=6, t=6, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", color=MUTED, size=12),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=PAPER, bordercolor=LINE,
                        font=dict(family="IBM Plex Sans, sans-serif", color=INK, size=12)),
        showlegend=False,
        xaxis=dict(showgrid=False, showline=False, zeroline=False, ticks="",
                   tickfont=dict(color=MUTED, size=11), fixedrange=True),
        yaxis=dict(showgrid=True, gridcolor=LINE, griddash="dot",
                   showline=False, zeroline=False, ticks="", tickprefix="$",
                   tickfont=dict(color=MUTED, size=11),
                   range=[ymin - pad, ymax + pad], fixedrange=True),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ===========================================================================
# BUSINESS TRAJECTORY  (multi-year annual trend charts — full set, grouped)
# ===========================================================================
def _money_scale(vals):
    m = max((abs(v) for v in vals if v is not None), default=0)
    for size, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if m >= size:
            return size, unit
    return 1, ""


def _trend_chart(years, values, fmt):
    """A small, quiet trend line for one metric. None if <2 real points."""
    pts = [(y, v) for y, v in zip(years, values) if v is not None]
    if len(pts) < 2:
        return None
    xs = [f"FY{y[2:]}" if len(y) == 4 else y for y, _ in pts]
    ys = [v for _, v in pts]

    tickprefix, ticksuffix, tickformat = "", "", ",.2f"
    if fmt == "money":
        scale, unit = _money_scale(ys)
        ys = [v / scale for v in ys]
        tickprefix, ticksuffix, tickformat = "$", unit, ",.1f"
        hov = f"%{{x}}   $%{{y:,.1f}}{unit}<extra></extra>"
    elif fmt == "pct":
        ticksuffix, tickformat = "%", ",.0f"
        hov = "%{x}   %{y:,.1f}%<extra></extra>"
    elif fmt == "eps":
        tickprefix, tickformat = "$", ",.2f"
        hov = "%{x}   $%{y:,.2f}<extra></extra>"
    else:
        hov = "%{x}   %{y:,.2f}<extra></extra>"

    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="lines+markers",
        line=dict(color=INK, width=2),
        marker=dict(color=INK, size=6),
        hovertemplate=hov,
    ))
    fig.update_layout(
        height=200, margin=dict(l=6, r=6, t=6, b=6),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", color=MUTED, size=11),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=PAPER, bordercolor=LINE,
                        font=dict(family="IBM Plex Sans, sans-serif", color=INK, size=12)),
        showlegend=False,
        xaxis=dict(showgrid=False, showline=False, zeroline=False, ticks="",
                   tickfont=dict(color=MUTED, size=10), fixedrange=True, type="category"),
        yaxis=dict(showgrid=True, gridcolor=LINE, griddash="dot", showline=False,
                   zeroline=False, ticks="", tickprefix=tickprefix, ticksuffix=ticksuffix,
                   tickformat=tickformat, tickfont=dict(color=MUTED, size=10), fixedrange=True),
    )
    if min(ys) < 0:
        fig.add_hline(y=0, line=dict(color=LINE, width=1))
    return fig


def _trend_bar(years, values, fmt):
    """A small bar chart with the actual value labeled on each bar.
    None if there are no real points. Same formats as _trend_chart."""
    pts = [(y, v) for y, v in zip(years, values) if v is not None]
    if len(pts) < 1:
        return None
    xs = [f"FY{y[2:]}" if len(y) == 4 else y for y, _ in pts]
    ys = [v for _, v in pts]

    if fmt == "money":
        scale, unit = _money_scale(ys)
        ys = [v / scale for v in ys]
        labels = [f"${v:,.1f}{unit}" for v in ys]
        tickprefix, ticksuffix, tickformat = "$", unit, ",.1f"
    elif fmt == "pct":
        labels = [f"{v:,.1f}%" for v in ys]
        tickprefix, ticksuffix, tickformat = "", "%", ",.0f"
    elif fmt in ("eps", "pershare"):
        labels = [f"${v:,.2f}" for v in ys]
        tickprefix, ticksuffix, tickformat = "$", "", ",.2f"
    else:
        labels = [f"{v:,.2f}" for v in ys]
        tickprefix, ticksuffix, tickformat = "", "", ",.2f"

    fig = go.Figure(go.Bar(
        x=xs, y=ys, text=labels, textposition="outside", cliponaxis=False,
        textfont=dict(family="IBM Plex Sans, sans-serif", color=INK, size=11),
        marker=dict(color=INK),
        hovertemplate="%{x}   %{text}<extra></extra>",
    ))
    lo, hi = min(ys), max(ys)
    span = (hi - lo) or abs(hi) or 1
    pad = span * 0.22
    ymin = (lo - pad) if lo < 0 else 0
    ymax = (hi + pad) if hi > 0 else pad
    fig.update_layout(
        height=210, margin=dict(l=6, r=6, t=14, b=6),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", color=MUTED, size=11),
        showlegend=False, bargap=0.35,
        xaxis=dict(showgrid=False, showline=False, zeroline=False, ticks="",
                   tickfont=dict(color=MUTED, size=10), fixedrange=True, type="category"),
        yaxis=dict(showgrid=True, gridcolor=LINE, griddash="dot", showline=False,
                   zeroline=False, ticks="", tickprefix=tickprefix, ticksuffix=ticksuffix,
                   tickformat=tickformat, tickfont=dict(color=MUTED, size=10),
                   range=[ymin, ymax], fixedrange=True),
    )
    if lo < 0:
        fig.add_hline(y=0, line=dict(color=LINE, width=1))
    return fig


def _direction(vals):
    pts = [v for v in (vals or []) if v is not None]
    if len(pts) < 2 or pts[0] == 0:
        return None
    chg = (pts[-1] - pts[0]) / abs(pts[0])
    return "up" if chg > 0.05 else "down" if chg < -0.05 else "flat"


def _trajectory_summary(years, m):
    rev, nm = _direction(m.get("revenue")), _direction(m.get("net_margin"))
    if not rev and not nm:
        return "Not enough history to summarize the trajectory."
    span = f"FY{years[0][2:]}–FY{years[-1][2:]}" if years and len(years[0]) == 4 else "the period"
    read = "mixed"
    if rev == "up" and nm in ("up", "flat"):
        read = "improving"
    elif rev == "down" and nm in ("down", "flat"):
        read = "weakening"
    words = {"up": "rising", "down": "declining", "flat": "roughly flat"}
    mwords = {"up": "expanding", "down": "compressing", "flat": "steady"}
    bits = []
    if rev:
        bits.append(f"revenue {words[rev]}")
    if nm:
        bits.append(f"net margin {mwords[nm]}")
    return (f"**Business trajectory: {read}** over {span} — {' and '.join(bits)}. "
            "This describes the numbers only — it isn't a recommendation.")


def _subgroup(label):
    st.markdown(
        f'<div style="font:600 .72rem/1 \'IBM Plex Sans\',sans-serif;letter-spacing:.14em;'
        f'text-transform:uppercase;color:var(--muted,#7A7970);margin:1.3rem 0 .2rem;">{label}</div>',
        unsafe_allow_html=True,
    )


def render_trajectory(symbol):
    data = get_trajectory_annual(symbol)
    years, m = data["years"], data["metrics"]
    if not years:
        st.caption("Unavailable from current data source.")
        return

    def cell(col, label, key, fmt):
        with col:
            st.markdown(f"**{label}**")
            fig = _trend_bar(years, m.get(key), fmt)
            if fig is None:
                st.caption("Unavailable from current data source.")
            else:
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False}, key=f"traj_{symbol}_{key}")

    _subgroup("Growth")
    c1, c2 = st.columns(2)
    cell(c1, "Revenue", "revenue", "money")
    cell(c2, "EPS (diluted)", "eps", "eps")

    _subgroup("Profitability")
    c1, c2 = st.columns(2)
    cell(c1, "Gross Margin", "gross_margin", "pct")
    cell(c2, "Operating Margin", "op_margin", "pct")
    c1, c2 = st.columns(2)
    cell(c1, "Net Margin", "net_margin", "pct")
    cell(c2, "Return on Equity", "roe", "pct")

    _subgroup("Cash & Balance Sheet")
    c1, c2 = st.columns(2)
    cell(c1, "Free Cash Flow", "fcf", "money")
    cell(c2, "Total Debt", "debt", "money")

    st.caption(_trajectory_summary(years, m))


def _cash_summary(data):
    m, latest, years = data["metrics"], data["latest"], data["years"]
    fdir = _direction(m.get("fcf"))
    if not fdir and latest.get("fcf_growth") is None:
        return "Not enough history to summarize cash generation."
    span = f"FY{years[0][2:]}–FY{years[-1][2:]}" if years and len(years[0]) == 4 else "the period"
    words = {"up": "rising", "down": "declining", "flat": "roughly flat"}
    bits = []
    if fdir:
        bits.append(f"free cash flow {words[fdir]}")
    g = latest.get("fcf_growth")
    if g is not None:
        bits.append(f"latest-year FCF {'up' if g >= 0 else 'down'} {abs(g):,.0f}%")
    return (f"**Cash generation** over {span} — {', '.join(bits)}. "
            "Describes the numbers only — it isn't a recommendation.")


def render_cash_generation(symbol):
    data = get_cash_annual(symbol)
    years, m = data["years"], data["metrics"]
    if not years:
        st.caption("Unavailable from current data source.")
        return

    def cell(col, label, key, fmt):
        with col:
            st.markdown(f"**{label}**")
            fig = _trend_bar(years, m.get(key), fmt)
            if fig is None:
                st.caption("Unavailable from current data source.")
            else:
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False}, key=f"cash_{symbol}_{key}")

    c1, c2 = st.columns(2)
    cell(c1, "Free Cash Flow", "fcf", "money")
    cell(c2, "FCF Margin", "fcf_margin", "pct")
    c1, c2 = st.columns(2)
    cell(c1, "FCF per Share", "fcf_ps", "pershare")
    cell(c2, "FCF Yield", "fcf_yield", "pct")

    st.caption(_cash_summary(data))
    st.caption("Free cash flow is the cash a business generates after reinvesting to keep "
               "running and growing. For long-term investors, strong and growing free cash flow "
               "is often more durable than accounting earnings alone.")


# ===========================================================================
# Views
# ===========================================================================
def show_movers(kind):
    titles = {"gainers": "Top Gainers", "losers": "Top Losers", "actives": "Most Active"}
    section(titles.get(kind, "Movers"), "today's biggest moves")
    st.caption("See one you want to understand? Search it in the sidebar to drill in.")

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
    st.markdown(f'<div class="rt-symbol">{symbol}</div>', unsafe_allow_html=True)

    quote = get_quote(symbol)
    if not quote:
        st.warning(
            f"No data found for **{symbol}** on the current plan. Check the ticker — it may be a "
            "fund, index, or non-US listing. Try a US-listed stock (e.g. **MU** for Micron)."
        )
        return

    profile = get_company_profile(symbol)
    metrics = get_key_metrics(symbol)
    st.session_state.last_symbol = symbol   # seed the Compare view

    name = profile.get("name") or quote.get("name") or symbol
    industry = profile.get("industry")
    exchange = profile.get("exchange") or quote.get("exchange")
    header = name + (f"  ·  {industry}" if industry else "")
    if exchange:
        header += f"  ·  {exchange}"
    st.markdown(f'<div class="rt-company">{header}</div>', unsafe_allow_html=True)

    price = quote.get("price")
    change_pct = quote.get("change_pct")

    # ---- Snapshot ----
    section("Snapshot", "the essentials")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Price", money(price),
                  delta=pct(change_pct) if to_float(change_pct) is not None else None)
    metric_tile(c2, "Market Cap", big_money(profile.get("market_cap") or quote.get("market_cap")), "market_cap")

    low, high = quote.get("week_low"), quote.get("week_high")
    range_val = money_range(low, high)
    range_note = None
    p, lo, hi = to_float(price), to_float(low), to_float(high)
    if None not in (p, lo, hi) and hi > lo:
        pos = (p - lo) / (hi - lo) * 100
        range_note = f"Price sits about {pos:.0f}% of the way up its 52-week range."
    metric_tile(c3, "52-Week Range", range_val, "week_range", note=range_note)

    metric_tile(c4, "Avg Daily Volume", big_count(metrics.get("avg_volume")), "volume")

    # ---- Price ----
    section("Price", "the trend over time")
    render_price_chart(symbol)

    # ---- Business Trajectory ----
    section("Business Trajectory", "the shape of the business")
    st.caption("How the fundamentals have moved over recent fiscal years (annual). "
               "A quarterly view is planned.")
    render_trajectory(symbol)

    # ---- Cash Generation ----
    section("Cash Generation", "does it make real money?")
    render_cash_generation(symbol)

    # ---- Valuation ----
    section("Valuation", "what it costs")
    c1, c2, c3 = st.columns(3)
    metric_tile(c1, "P/E (trailing)", num(metrics.get("pe")), "pe")
    metric_tile(c2, "PEG", num(metrics.get("peg")), "peg")
    metric_tile(c3, "EV / EBITDA", num(metrics.get("ev_ebitda")), "ev_ebitda")

    # ---- Financial health ----
    section("Financial Health", "how it's doing")
    c1, c2, c3, c4 = st.columns(4)
    metric_tile(c1, "Net Margin", pct(metrics.get("net_margin_pct")), "net_margin")
    metric_tile(c2, "Gross Margin", pct(metrics.get("gross_margin_pct")), "gross_margin")
    metric_tile(c3, "Debt / Equity", num(metrics.get("debt_to_equity")), "debt_equity")
    metric_tile(c4, "Return on Equity", pct(metrics.get("roe_pct")), "roe")

    # ---- Risk ----
    section("Risk", "what could move it")
    c1, c2, c3 = st.columns(3)
    metric_tile(c1, "Beta", num(metrics.get("beta")), "beta")
    with c2:
        st.metric("Day Range", money_range(quote.get("day_low"), quote.get("day_high")))
    with c3:
        st.metric("Prev Close", money(quote.get("prev_close")))

    # ---- Your notes ----
    section("Your Notes", "your call")
    st.caption("Write your own reasoning. (Session-only for now — permanent saving is a later feature.)")
    st.text_area("What's your read on this one?", key=f"notes_{symbol}", height=120,
                 placeholder="e.g. Strong margins but debt looks high for the sector — check latest earnings before deciding.")

    st.caption("ℹ️ Hover the **?** on any metric for a plain-English explanation. Some metrics (PEG, EV/EBITDA) may show N/A on the free data tier — the app stays fully usable without them.")


# ===========================================================================
# COMPARISON VIEW  (normalized price chart + side-by-side metrics table)
# ===========================================================================
# Editorial categorical palette for multiple series (readable on warm paper).
SERIES_COLORS = ["#23231E", "#2F6B4F", "#A24A38", "#3A5A78", "#8A6D3B", "#6B4E71"]


def _resolve_symbol(query):
    """Resolve a typed name or ticker to (SYMBOL, name). Exact ticker wins;
    otherwise take the best search match; otherwise treat the input as a ticker."""
    q = query.strip()
    qU = q.upper()
    matches = search_companies(q) or []
    for m in matches:                                   # exact ticker match first
        if (m.get("symbol") or "").upper() == qU:
            return qU, m.get("name")
    if matches:                                         # else best-ranked match
        m0 = matches[0]
        return (m0.get("symbol") or qU).upper(), m0.get("name")
    return qU, None                                     # else assume it's a ticker


def _cmp_add():
    """Add-button / Enter callback: resolve the box and append a chip (max 5)."""
    q = st.session_state.get("cmp_add_box", "").strip()
    st.session_state.cmp_add_box = ""                   # clear the box
    if not q:
        return
    lst = st.session_state.setdefault("cmp_list", [])
    if len(lst) >= 5:
        return
    sym, name = _resolve_symbol(q)
    if sym and all(item["sym"] != sym for item in lst):
        lst.append({"sym": sym, "name": name})
        st.session_state.cmp_last_added = f"{sym} — {name}" if name else sym


def _cmp_remove(sym):
    """Chip-click callback: drop that ticker from the comparison set."""
    st.session_state.cmp_list = [
        i for i in st.session_state.get("cmp_list", []) if i["sym"] != sym
    ]


def _rebased_series(symbol, days):
    """Price history rebased so the window starts at 0% -> DataFrame[date, pct]."""
    df = get_price_history(symbol)
    if df.empty:
        return None
    cutoff = df["date"].max() - pd.Timedelta(days=days)
    d = df[df["date"] >= cutoff]
    if len(d) < 2:
        d = df
    base = d["close"].iloc[0]
    if not base:
        return None
    out = d[["date"]].copy()
    out["pct"] = (d["close"] / base - 1.0) * 100.0
    return out


def _comparison_chart(symbols, days, include_spy):
    """Overlay each ticker's % change on one axis. Returns (figure, missing[])."""
    fig = go.Figure()
    plotted, missing = [], []

    for i, sym in enumerate(symbols):
        s = _rebased_series(sym, days)
        if s is None or s.empty:
            missing.append(sym)
            continue
        fig.add_trace(go.Scatter(
            x=s["date"], y=s["pct"], mode="lines", name=sym,
            line=dict(color=SERIES_COLORS[i % len(SERIES_COLORS)], width=2),
            hovertemplate=f"<b>{sym}</b>  %{{x|%b %-d, %Y}}   %{{y:+.1f}}%<extra></extra>",
        ))
        plotted.append(sym)

    spy_plotted = False
    if include_spy:
        s = _rebased_series("SPY", days)
        if s is not None and not s.empty:
            fig.add_trace(go.Scatter(
                x=s["date"], y=s["pct"], mode="lines", name="S&P 500",
                line=dict(color=MUTED, width=1.5, dash="dash"),
                hovertemplate="<b>S&P 500</b>  %{x|%b %-d, %Y}   %{y:+.1f}%<extra></extra>",
            ))
            spy_plotted = True
        else:
            missing.append("SPY")

    if not plotted and not spy_plotted:
        return None, missing

    fig.add_hline(y=0, line=dict(color=LINE, width=1))
    fig.update_layout(
        height=380,
        margin=dict(l=6, r=6, t=6, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", color=MUTED, size=12),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=PAPER, bordercolor=LINE,
                        font=dict(family="IBM Plex Sans, sans-serif", color=INK, size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                    font=dict(family="IBM Plex Sans, sans-serif", color=INK, size=12),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=False, showline=False, zeroline=False, ticks="",
                   tickfont=dict(color=MUTED, size=11), fixedrange=True),
        yaxis=dict(showgrid=True, gridcolor=LINE, griddash="dot",
                   showline=False, zeroline=False, ticks="", ticksuffix="%",
                   tickfont=dict(color=MUTED, size=11), fixedrange=True),
    )
    return fig, missing


def _metrics_column(symbol):
    """Formatted TTM metric values for one ticker (a table column), or None."""
    q = get_quote(symbol)
    if not q:
        return None
    m = get_key_metrics(symbol)
    p = get_company_profile(symbol)
    return {
        "Price": money(q.get("price")),
        "Market Cap": big_money(q.get("market_cap") or p.get("market_cap")),
        "P/E (TTM)": num(m.get("pe")),
        "PEG": num(m.get("peg")),
        "EV / EBITDA": num(m.get("ev_ebitda")),
        "Net Margin": pct(m.get("net_margin_pct")),
        "Gross Margin": pct(m.get("gross_margin_pct")),
        "Debt / Equity": num(m.get("debt_to_equity")),
        "ROE": pct(m.get("roe_pct")),
        "Beta": num(m.get("beta")),
    }


def show_comparison():
    section("Compare", "side by side")
    st.caption("Build a set of 2–5 companies to see relative performance and fundamentals "
               "side by side. **You** decide what the differences mean.")

    # Seed once from the last stock you viewed (if any).
    if not st.session_state.get("cmp_init"):
        seed = st.session_state.get("last_symbol")
        if seed:
            s_sym, s_name = _resolve_symbol(seed)
            st.session_state.cmp_list = [{"sym": s_sym, "name": s_name}]
        st.session_state.cmp_init = True

    lst = st.session_state.setdefault("cmp_list", [])
    at_cap = len(lst) >= 5

    # --- Add a company or ticker (one at a time) ---
    st.markdown("**Add a company or ticker**")
    c_in, c_btn = st.columns([5, 1])
    with c_in:
        st.text_input("Add", key="cmp_add_box", label_visibility="collapsed",
                      placeholder="e.g.  Amazon   or   AMZN",
                      on_change=_cmp_add, disabled=at_cap)
    with c_btn:
        st.button("Add", use_container_width=True, on_click=_cmp_add, disabled=at_cap)

    added = st.session_state.pop("cmp_last_added", None)
    if added:
        st.caption(f"Added **{added}**.")
    if at_cap:
        st.caption("That's the maximum of 5 — remove one to add another.")

    # --- Selected companies as removable chips ---
    if lst:
        st.caption("Comparing (tap to remove):")
        cols = st.columns(6)
        for i, item in enumerate(lst):
            with cols[i]:
                st.button(f"{item['sym']}  ✕", key=f"chip_{item['sym']}",
                          help=f"Remove {item.get('name') or item['sym']}",
                          on_click=_cmp_remove, args=(item["sym"],))

    include_spy = st.checkbox("Compare price to the S&P 500 (SPY)", value=True, key="cmp_spy")

    tickers = [item["sym"] for item in lst]
    if not tickers:
        st.info("Add at least one company above to get started — e.g. **Amazon** or **AMZN**.")
        return

    # ---- Relative performance chart ----
    section("Relative Performance", "rebased to % change")
    options = list(RANGE_DAYS.keys())
    picker = getattr(st, "segmented_control", None)
    if picker:
        choice = picker("Range", options, default="1Y",
                        key="cmp_range", label_visibility="collapsed")
    else:
        choice = st.radio("Range", options, index=3, horizontal=True,
                          key="cmp_range", label_visibility="collapsed")
    choice = choice or "1Y"

    st.caption("Every line starts at 0%, so you're comparing growth over the period — not share "
               "prices. A $30 stock and a $1,000 stock sit on the same footing here.")

    with st.spinner("Loading price history…"):
        fig, missing = _comparison_chart(tickers, RANGE_DAYS[choice], include_spy)
    if fig is None:
        st.warning("Couldn't load price history for those tickers on the current plan. "
                   "Check the symbols — try US-listed stocks like **NVDA, AMD**.")
        return
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    if missing:
        st.caption("Couldn't chart: " + ", ".join(f"**{m}**" for m in missing) +
                   " — likely not covered on the current plan (funds, indices, or non-US listings).")

    # ---- Metrics table ----
    section("The Numbers", "fundamentals side by side")
    st.caption("Trailing-twelve-month figures. The S&P 500 is a benchmark on the chart only — "
               "the fundamentals below are for the companies you entered.")
    with st.spinner("Loading fundamentals…"):
        data, no_data = {}, []
        for t in tickers:
            col = _metrics_column(t)
            if col:
                data[t] = col
            else:
                no_data.append(t)
    if data:
        st.dataframe(pd.DataFrame(data), use_container_width=True)
        st.caption("ℹ️ Some cells may show N/A on the current tier. Compare within the same "
                   "industry — a 'good' P/E or margin in one sector can be poor in another.")
    else:
        st.warning("No fundamental data came back for those tickers.")
    if no_data:
        st.caption("No fundamentals for: " + ", ".join(f"**{m}**" for m in no_data) + ".")


# ===========================================================================
# Sidebar + routing
# ===========================================================================
st.sidebar.title("Stock Research")
st.sidebar.caption("Aggregate the data. Understand the metrics. **You** decide.")


def _view_stock(sym):
    st.session_state.view = {"kind": "stock", "symbol": sym}


def _view_movers(mover):
    st.session_state.view = {"kind": "movers", "mover": mover}


def _view_compare():
    st.session_state.view = {"kind": "compare"}


# on_click callbacks (below) run at the start of the rerun, before this body,
# so `view` already reflects the button the person just clicked — no stale state.
view = st.session_state.get("view", {"kind": "movers", "mover": "gainers"})
active_mover = view.get("mover") if view.get("kind") == "movers" else None
on_compare = view.get("kind") == "compare"

# --- Search ---
search_term = st.sidebar.text_input("🔎 Search company or ticker",
                                     placeholder="e.g. Micron  or  MU",
                                     key="search_box").strip()
candidate = None
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
            options[f"{nm} ({sym})" + (f" · {exch}" if exch else "")] = sym
        if options:
            choice = st.sidebar.selectbox("Select a match:", list(options.keys()),
                                          key="match_select")
            candidate = options[choice]
    if candidate is None:
        candidate = search_term.upper()
        st.sidebar.caption(f"No stock matches — trying **{candidate}** as a ticker.")
    if candidate:
        on_stock = view.get("kind") == "stock" and view.get("symbol") == candidate
        st.sidebar.button(f"View {candidate} details  →", use_container_width=True,
                          type="primary" if on_stock else "secondary",
                          on_click=_view_stock, args=(candidate,))

# --- Browse movers ---
st.sidebar.markdown("---")
st.sidebar.caption("Browse movers")
for _label, _key in [("Top Gainers", "gainers"), ("Top Losers", "losers"), ("Most Active", "actives")]:
    st.sidebar.button(_label, use_container_width=True,
                      type="primary" if active_mover == _key else "secondary",
                      on_click=_view_movers, args=(_key,))

# --- Compare ---
st.sidebar.markdown("---")
st.sidebar.caption("Compare")
st.sidebar.button("Compare stocks  →", use_container_width=True,
                  type="primary" if on_compare else "secondary",
                  on_click=_view_compare)

st.title("Stock Research Dashboard")

if not FMP_KEY:
    st.error("No FMP API key found.")
    st.markdown(
        "**To get started (free):**\n"
        "1. FMP key: https://site.financialmodelingprep.com/developer/docs/dashboard\n"
        "2. Add to Streamlit secrets as `FMP_API_KEY = \"your_key\"`\n"
        "3. Reload."
    )
    st.stop()

if view.get("kind") == "stock":
    show_ticker(view["symbol"])
elif view.get("kind") == "compare":
    show_comparison()
else:
    show_movers(view.get("mover", "gainers"))

st.markdown("---")
st.caption(
    "📚 Educational tool, not financial advice. Data from Financial Modeling Prep, "
    "and may be delayed. Metrics and 'healthy ranges' are general guidance — compare within a "
    "company's own industry, and make your own decisions."
)
