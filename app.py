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

# App version — bump this on every change so you can confirm what's actually
# deployed. It shows in the sidebar footer and the page footer.
APP_VERSION = "0.15.0"
APP_BUILD = "2026-07-02"

# ---------------------------------------------------------------------------
# Styling: quiet editorial "tasting card" — serif values like menu prices,
# letter-spaced labels like menu sections, hairline rules between courses.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root{
  --ink:#23231E; --paper:#FCFBF8; --muted:#7A7970; --line:#E8E6DE;
  --pos:#2F6B4F; --neg:#A24A38; --warn:#B07A2E; --info:#3A5A78;
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



/* Subtle signal chips used under metrics. These are interpretation aids, not buy/sell signals. */
.rt-chip{display:inline-block;margin:.18rem 0 .1rem;padding:.13rem .48rem;border-radius:999px;
  font-family:'IBM Plex Sans',sans-serif;font-size:.66rem;font-weight:600;letter-spacing:.07em;
  text-transform:uppercase;border:1px solid transparent;line-height:1.35}
.rt-chip-good{color:var(--pos,#2F6B4F);background:rgba(47,107,79,.08);border-color:rgba(47,107,79,.22)}
.rt-chip-risk{color:var(--neg,#A24A38);background:rgba(162,74,56,.08);border-color:rgba(162,74,56,.22)}
.rt-chip-caution{color:var(--warn,#B07A2E);background:rgba(176,122,46,.10);border-color:rgba(176,122,46,.25)}
.rt-chip-neutral{color:var(--muted,#7A7970);background:rgba(122,121,112,.08);border-color:rgba(122,121,112,.18)}
.rt-chip-info{color:var(--info,#3A5A78);background:rgba(58,90,120,.08);border-color:rgba(58,90,120,.20)}

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

# For the optional AI-analysis feature. Model is overridable via secrets so a
# name change doesn't require a code edit.
ANTHROPIC_MODEL = st.secrets.get("ANTHROPIC_MODEL", "claude-sonnet-5")


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
    "forward_pe": (
        "Like P/E, but using analysts' estimate of next year's profit instead of last year's.\n\n"
        "**For the business:** if forward P/E is lower than trailing P/E, the market expects profits "
        "to grow. Relies on analyst estimates, which can be wrong."
    ),
    "price_sales": (
        "How many dollars you pay for each $1 of the company's yearly sales.\n\n"
        "**For the business:** useful when profits are thin or negative. High P/S means a lot of "
        "growth is priced in; compare within the same industry."
    ),
    "fcf_yield": (
        "The free cash flow the company throws off, as a percentage of its market value.\n\n"
        "**For the business:** think of it like an interest rate on the stock — higher means more "
        "cash generated for the price. Low FCF yield means you're paying up for future growth."
    ),
    "revenue_growth": (
        "How fast yearly sales grew versus the year before.\n\n"
        "**For the business:** the top-line engine. Steady growth is the clearest sign demand is "
        "expanding; a single year can be lumpy, so read it alongside the multi-year trend above."
    ),
    "eps_growth": (
        "How fast earnings per share grew versus the year before.\n\n"
        "**For the business:** growth in per-share profit is what compounds shareholder value. Watch "
        "for growth coming from real profit, not just fewer shares. Very small bases make % look wild."
    ),
    "fcf_growth": (
        "How fast free cash flow grew versus the year before.\n\n"
        "**For the business:** growing cash generation is hard to fake and tends to be durable. Note "
        "that when the prior year was near zero, the percentage can look extreme."
    ),
    "pe_vs_median": (
        "Today's P/E next to the middle of its own last-5-years range.\n\n"
        "**For the business:** answers 'is the stock expensive versus its own history?' Above its "
        "median means pricier than usual — justified only if growth or quality has improved."
    ),
    "ev_vs_median": (
        "Today's EV/EBITDA next to the middle of its own last-5-years range.\n\n"
        "**For the business:** a debt-aware version of the same 'expensive vs its own history?' "
        "check. Well above the median means the market is paying a premium to the past."
    ),
    "ps_vs_median": (
        "Today's Price/Sales next to the middle of its own last-5-years range.\n\n"
        "**For the business:** shows whether the market is paying more per dollar of sales than it "
        "usually has. A big jump often signals rich expectations."
    ),
    "analyst_consensus": (
        "The overall buy / hold / sell recommendation across analysts covering the stock.\n\n"
        "**For context:** it reflects professional sentiment, but analysts often lag events and tend "
        "to cluster together. Treat it as one input, not an answer."
    ),
    "implied_upside": (
        "How far the average analyst price target sits above (or below) today's price.\n\n"
        "**For context:** targets are estimates and get revised often. A large implied upside can "
        "mean a bargain — or that analysts are too optimistic."
    ),
    "ma_50": (
        "The average closing price over the last 50 trading days (about 2½ months).\n\n"
        "**For context:** price above the 50-day line generally signals near-term strength; below it, "
        "near-term weakness. It's a trend gauge, not a value gauge."
    ),
    "ma_200": (
        "The average closing price over the last 200 trading days (about 10 months).\n\n"
        "**For context:** the classic long-term trend line. Above it is often read as a healthy "
        "up-trend; below it as a longer-term down-trend."
    ),
    "rsi": (
        "A 0–100 momentum gauge of how fast the price has risen or fallen lately (14-day).\n\n"
        "**For context:** above ~70 is often called 'overbought' (may be stretched), below ~30 "
        "'oversold' (may be beaten down). It's a short-term signal, not a verdict."
    ),
    "dist_high": (
        "How far today's price sits below its highest point of the past year.\n\n"
        "**For context:** near 0% means it's close to a 52-week high (momentum, or run up a lot); a "
        "big negative number means it's well off its highs."
    ),
    "dist_low": (
        "How far today's price sits above its lowest point of the past year.\n\n"
        "**For context:** a large positive number means it has recovered well from its 52-week low; "
        "near 0% means it's close to its lows."
    ),
    "vol_ratio": (
        "Today's trading volume compared with its typical daily volume.\n\n"
        "**For context:** above 1× means unusually heavy trading (news or conviction); below 1× is "
        "quieter than usual. Big moves on high volume carry more weight."
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


def _fmp_probe(path: str):
    """Diagnostic fetch (uncached) — returns (rows, http_status, error) WITHOUT
    swallowing, so the UI can surface exactly why an endpoint came back empty."""
    sep = "&" if "?" in path else "?"
    url = f"{FMP_BASE}/{path}{sep}apikey={FMP_KEY}"
    try:
        resp = requests.get(url, timeout=15)
        status = resp.status_code
        if status != 200:
            try:
                detail = str(resp.json())[:180]
            except Exception:
                detail = resp.text[:180]
            return [], status, detail
        data = resp.json()
        if not isinstance(data, list):
            return [], status, f"non-list: {str(data)[:180]}"
        return data, status, ""
    except Exception as e:  # noqa: BLE001
        return [], None, str(e)[:180]


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
def get_price_history(symbol: str, start_days: int = None):
    """Daily price history from FMP (arrives newest-first).

    Returns a DataFrame sorted oldest -> newest with a 'date' column and
    'close' (the raw 'volume' column is preserved too). On the free tier this
    402s for real tickers; it works once FMP Starter is active. Any error
    yields an empty frame (handled upstream).

    start_days: if given, only fetch roughly the last N calendar days (via the
    endpoint's `from` filter). Default None fetches full history, so existing
    callers are unchanged; the daily scan passes a small window to stay light.
    """
    path = f"historical-price-eod/full?symbol={symbol.upper()}"
    if start_days:
        import datetime as _dt
        frm = (_dt.date.today() - _dt.timedelta(days=int(start_days))).isoformat()
        path += f"&from={frm}"
    try:
        data = _fmp_get(path)
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


def _median(vals, positive_only=False):
    xs = [v for v in vals if v is not None]
    if positive_only:
        xs = [v for v in xs if v > 0]
    if not xs:
        return None
    xs.sort()
    n, mid = len(xs), len(xs) // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2


def _yoy(series):
    pts = [v for v in series if v is not None]
    if len(pts) < 2 or pts[-2] == 0:
        return None
    return (pts[-1] - pts[-2]) / abs(pts[-2]) * 100


def _nearest_future_estimate(rows):
    """From analyst-estimate rows, the one whose fiscal-year-end is soonest but
    still on/after today (the nearest forward year). None if none qualify."""
    import datetime as _dt
    today = _dt.date.today()
    best = None
    for r in rows or []:
        ds = str(r.get("date") or r.get("fiscalYear") or "")[:10]
        try:
            dd = _dt.date.fromisoformat(ds) if len(ds) == 10 else _dt.date(int(ds[:4]), 1, 1)
        except (ValueError, TypeError):
            continue
        if dd >= today and (best is None or dd < best[0]):
            best = (dd, r)
    return best[1] if best else None


def _parse_quarterly(inc, cf, n=6):
    """Merge quarterly income + cash-flow rows (FMP arrives newest-first) into
    chronological trend series. Margins are computed from the statement fields."""
    def key(r):
        return (str(r.get("fiscalYear") or ""), str(r.get("period") or ""))
    fcf_by = {key(r): to_float(pick(r, "freeCashFlow")) for r in (cf or [])}
    rows = list(reversed(list(inc or [])))[-n:]
    labels, rev, eps, gm, om, nm, fcf = [], [], [], [], [], [], []
    for r in rows:
        fy, per = str(r.get("fiscalYear") or ""), str(r.get("period") or "")
        lab = f"{per} '{fy[2:]}" if len(fy) == 4 else (per or fy or str(r.get("date"))[:10])
        revenue = to_float(pick(r, "revenue"))
        gp = to_float(pick(r, "grossProfit"))
        oi = to_float(pick(r, "operatingIncome"))
        ni = to_float(pick(r, "netIncome", "bottomLineNetIncome"))
        labels.append(lab)
        rev.append(revenue)
        eps.append(to_float(pick(r, "epsDiluted", "eps")))
        gm.append((gp / revenue * 100) if (gp is not None and revenue) else None)
        om.append((oi / revenue * 100) if (oi is not None and revenue) else None)
        nm.append((ni / revenue * 100) if (ni is not None and revenue) else None)
        fcf.append(fcf_by.get(key(r)))
    return {"labels": labels, "metrics": {"revenue": rev, "eps": eps,
            "gross_margin": gm, "op_margin": om, "net_margin": nm, "fcf": fcf}}


def get_quarterly_trend(symbol, n=6):
    """Last n quarters of revenue, diluted EPS, margins, and free cash flow
    (chronological, oldest->newest). Confirmed on FMP Starter via period=quarter."""
    sym = symbol.upper()
    inc = _fmp_statement(f"income-statement?symbol={sym}&period=quarter&limit={n}")
    cf = _fmp_statement(f"cash-flow-statement?symbol={sym}&period=quarter&limit={n}")
    return _parse_quarterly(inc, cf, n)


def get_forward_estimates(symbol, n=3):
    """Next n fiscal years of consensus revenue + EPS estimates (nearest future
    first), each with a forward P/E (current price / estimated EPS). Source is
    analyst-estimates (annual); empty list if the endpoint returns nothing."""
    import datetime as _dt
    sym = symbol.upper()
    rows = _fmp_statement(f"analyst-estimates?symbol={sym}&period=annual&limit=10") or []
    price = to_float(pick(_fmp_quote(sym), "price"))
    today = _dt.date.today()
    fut = []
    for r in rows:
        ds = str(r.get("date") or "")[:10]
        try:
            dd = _dt.date.fromisoformat(ds) if len(ds) == 10 else _dt.date(int(ds[:4]), 1, 1)
        except (ValueError, TypeError):
            continue
        if dd >= today:
            fut.append((dd, r))
    fut.sort(key=lambda x: x[0])
    out = []
    for dd, r in fut[:n]:
        eps = to_float(pick(r, "epsAvg"))
        rev = to_float(pick(r, "revenueAvg"))
        out.append({"fiscal_year": dd.year, "revenue": rev, "eps": eps,
                    "forward_pe": (price / eps) if (price and eps and eps > 0) else None,
                    "n_eps": to_float(pick(r, "numAnalystsEps")),
                    "n_rev": to_float(pick(r, "numAnalystsRevenue"))})
    return {"price": price, "years": out}


def get_valuation_growth(symbol, years=6):
    """Current valuation (TTM), growth context (YoY), and each multiple vs its
    own 5-year median. Forward P/E needs analyst estimates and degrades to None
    if that endpoint isn't on the current plan."""
    sym = symbol.upper()
    rt = _fmp_ratios_ttm(sym)
    kt = _fmp_keymetrics_ttm(sym)
    q = _fmp_quote(sym)
    inc = _fmp_statement(f"income-statement?symbol={sym}&period=annual&limit={years}")
    cf = _fmp_statement(f"cash-flow-statement?symbol={sym}&period=annual&limit={years}")
    km = _fmp_statement(f"key-metrics?symbol={sym}&period=annual&limit={years}")
    ra = _fmp_statement(f"ratios?symbol={sym}&period=annual&limit={years}")

    def by_year(rows):
        out = {}
        for r in rows or []:
            y = str(r.get("fiscalYear") or r.get("calendarYear") or "")
            if not y and r.get("date"):
                y = str(r["date"])[:4]
            if y:
                out.setdefault(y, r)
        return out

    inc_y, cf_y, km_y, ra_y = by_year(inc), by_year(cf), by_year(km), by_year(ra)
    order = sorted(inc_y.keys())[-years:]

    revenue = [to_float(inc_y.get(y, {}).get("revenue")) for y in order]
    eps = [to_float(pick(inc_y.get(y, {}), "epsDiluted", "eps")) for y in order]

    def fcf_of(y):
        row = cf_y.get(y, {})
        v = to_float(pick(row, "freeCashFlow"))
        if v is not None:
            return v
        o = to_float(pick(row, "operatingCashFlow", "netCashProvidedByOperatingActivities"))
        c = to_float(pick(row, "capitalExpenditure"))
        return None if (o is None or c is None) else o - abs(c)

    fcf = [fcf_of(y) for y in order]
    pe_hist = [to_float(pick(ra_y.get(y, {}), "priceToEarningsRatio")) for y in order]
    ev_hist = [to_float(pick(km_y.get(y, {}), "evToEBITDA")) for y in order]
    ps_hist = [to_float(pick(ra_y.get(y, {}), "priceToSalesRatio")) for y in order]

    pe = to_float(pick(rt, "priceToEarningsRatioTTM"))
    peg = to_float(pick(rt, "priceToEarningsGrowthRatioTTM"))
    ev = (to_float(pick(kt, "evToEBITDATTM", "enterpriseValueMultipleTTM"))
          or to_float(pick(rt, "enterpriseValueMultipleTTM")))
    ps = to_float(pick(rt, "priceToSalesRatioTTM"))
    fy = to_float(pick(kt, "freeCashFlowYieldTTM"))
    fcf_yield = fy * 100 if fy is not None else None

    # Forward P/E from analyst estimates (may be gated -> stays None).
    fwd_pe = None
    price = to_float(pick(q, "price"))
    est = _fmp_statement(f"analyst-estimates?symbol={sym}&period=annual&limit=10")
    row = _nearest_future_estimate(est)
    if row and price is not None:
        eps_est = to_float(pick(row, "epsAvg", "estimatedEpsAvg", "estimatedEps", "epsEstimated"))
        if eps_est and eps_est > 0:
            fwd_pe = price / eps_est

    return {
        "current": {"pe": pe, "forward_pe": fwd_pe, "peg": peg,
                    "ev_ebitda": ev, "ps": ps, "fcf_yield": fcf_yield},
        "growth": {"revenue": _yoy(revenue), "eps": _yoy(eps), "fcf": _yoy(fcf)},
        "history": {
            "pe": {"now": pe, "median": _median(pe_hist, positive_only=True)},
            "ev": {"now": ev, "median": _median(ev_hist, positive_only=True)},
            "ps": {"now": ps, "median": _median(ps_hist, positive_only=True)},
        },
        "years": order,
    }


def get_analyst(symbol):
    """Consensus, price targets, and nearest-year forward estimates."""
    sym = symbol.upper()
    gr = _fmp_first(f"grades-consensus?symbol={sym}")
    pt = _fmp_first(f"price-target-consensus?symbol={sym}")
    est = _fmp_statement(f"analyst-estimates?symbol={sym}&period=annual&limit=10")
    price = to_float(pick(_fmp_quote(sym), "price"))
    fwd = _nearest_future_estimate(est) or {}
    target = to_float(pick(pt, "targetConsensus"))
    upside = ((target / price - 1) * 100) if (target and price) else None
    return {
        "consensus": pick(gr, "consensus"),
        "grades": {k: to_float(pick(gr, k)) for k in
                   ("strongBuy", "buy", "hold", "sell", "strongSell")},
        "target": {"low": to_float(pick(pt, "targetLow")), "avg": target,
                   "median": to_float(pick(pt, "targetMedian")),
                   "high": to_float(pick(pt, "targetHigh")), "upside": upside},
        "price": price,
        "forward": {"year": str(pick(fwd, "date") or "")[:4],
                    "revenue": to_float(pick(fwd, "revenueAvg")),
                    "eps": to_float(pick(fwd, "epsAvg")),
                    "n_rev": to_float(pick(fwd, "numAnalystsRevenue")),
                    "n_eps": to_float(pick(fwd, "numAnalystsEps"))},
    }


def get_earnings_context(symbol):
    """Next earnings date, last actual-vs-estimate, and CIK for EDGAR links."""
    import datetime as _dt
    sym = symbol.upper()
    rows = _fmp_statement(f"earnings?symbol={sym}&limit=10")
    today = _dt.date.today()

    def parse(r):
        try:
            return _dt.date.fromisoformat(str(r.get("date"))[:10])
        except (ValueError, TypeError):
            return None

    nxt = last = None
    for r in rows or []:
        d = parse(r)
        if d is None:
            continue
        has_actual = pick(r, "epsActual") is not None
        if (d >= today or not has_actual) and (nxt is None or d < parse(nxt)):
            nxt = r
        if has_actual and (last is None or d > parse(last)):
            last = r

    cik = None
    inc = _fmp_statement(f"income-statement?symbol={sym}&period=annual&limit=1")
    if inc:
        cik = pick(inc[0], "cik")

    def surprise(a, e):
        a, e = to_float(a), to_float(e)
        return ((a - e) / abs(e) * 100) if (a is not None and e not in (None, 0)) else None

    out = {"cik": cik}
    if nxt:
        d = parse(nxt)
        out["next"] = {"date": d.isoformat() if d else None,
                       "days": (d - today).days if d else None,
                       "eps_est": to_float(pick(nxt, "epsEstimated")),
                       "rev_est": to_float(pick(nxt, "revenueEstimated"))}
    if last:
        out["last"] = {"date": parse(last).isoformat(),
                       "eps_actual": to_float(pick(last, "epsActual")),
                       "eps_est": to_float(pick(last, "epsEstimated")),
                       "eps_surprise": surprise(pick(last, "epsActual"), pick(last, "epsEstimated")),
                       "rev_actual": to_float(pick(last, "revenueActual")),
                       "rev_est": to_float(pick(last, "revenueEstimated")),
                       "rev_surprise": surprise(pick(last, "revenueActual"), pick(last, "revenueEstimated"))}
    return out


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


def _tone_color(tone):
    return {"good": POS, "risk": NEG, "caution": WARN, "neutral": MUTED,
            "info": INFO}.get(tone or "neutral", MUTED)


def _chip(text, tone="neutral"):
    """Small, quiet status label under a metric. Tone is an interpretation aid,
    not a recommendation."""
    if not text:
        return
    tone = tone if tone in {"good", "risk", "caution", "neutral", "info"} else "neutral"
    st.markdown(f"<span class='rt-chip rt-chip-{tone}'>{text}</span>", unsafe_allow_html=True)


def _colored(text, tone="neutral", weight=600):
    return f"<span style='color:{_tone_color(tone)};font-weight:{weight}'>{text}</span>"


def metric_tile(col, label, value, explainer_key, note=None, status=None, status_tone="neutral"):
    """A metric with a small '?' tooltip and an optional color-coded status chip."""
    help_text = EXPLAINERS.get(explainer_key, "")
    if note:
        help_text = (help_text + "\n\n**This one:** " + note).strip()
    with col:
        st.metric(label, value, help=help_text or None)
        if status:
            _chip(status, status_tone)


# ---------------------------------------------------------------------------
# Signal helpers for restrained color-coding. These intentionally avoid turning
# the app into a buy/sell terminal: green/red/amber only describe the metric's
# condition in plain English.
# ---------------------------------------------------------------------------
def _sign_signal(v, pos="positive", neg="negative", flat="flat", extreme_warn=True):
    v = to_float(v)
    if v is None:
        return None, "neutral"
    if extreme_warn and abs(v) >= 300:
        return "Extreme / verify", "caution"
    if v > 5:
        return pos, "good"
    if v < -5:
        return neg, "risk"
    return flat, "neutral"


def _margin_signal(v, gross=False):
    v = to_float(v)
    if v is None:
        return None, "neutral"
    if v < 0:
        return "Negative", "risk"
    if gross:
        if v >= 40:
            return "Strong margin", "good"
        if v < 20:
            return "Thin margin", "caution"
    else:
        if v >= 15:
            return "Strong margin", "good"
        if v < 5:
            return "Thin margin", "caution"
    return "Normal range", "neutral"


def _roe_signal(v):
    v = to_float(v)
    if v is None:
        return None, "neutral"
    if v < 0:
        return "Negative ROE", "risk"
    if v >= 20:
        return "High ROE", "good"
    if v >= 10:
        return "Healthy ROE", "good"
    return "Low ROE", "caution"


def _debt_signal(v):
    v = to_float(v)
    if v is None:
        return None, "neutral"
    if v < 0:
        return "Net cash / unusual", "info"
    if v <= 0.5:
        return "Low leverage", "good"
    if v <= 1.5:
        return "Moderate leverage", "neutral"
    if v <= 2.5:
        return "Elevated leverage", "caution"
    return "High leverage", "risk"


def _beta_signal(v):
    v = to_float(v)
    if v is None:
        return None, "neutral"
    if v < 0.8:
        return "Lower volatility", "good"
    if v <= 1.3:
        return "Market-like risk", "neutral"
    if v <= 2.0:
        return "High volatility", "caution"
    return "Very high volatility", "risk"


def _valuation_signal(v, kind):
    v = to_float(v)
    if v is None:
        return None, "neutral"
    if kind in {"pe", "forward_pe"}:
        if v <= 0:
            return "Loss / distorted", "risk"
        if v < 15:
            return "Lower multiple", "good"
        if v <= 30:
            return "Moderate multiple", "neutral"
        if v <= 50:
            return "Premium multiple", "caution"
        return "Very high multiple", "risk"
    if kind == "peg":
        if v <= 0:
            return "Distorted / verify", "caution"
        if v < 1:
            return "Growth-adjusted low", "good"
        if v <= 2:
            return "Reasonable range", "neutral"
        return "Growth-adjusted high", "caution"
    if kind == "ev":
        if v <= 0:
            return "Distorted / verify", "caution"
        if v < 10:
            return "Lower multiple", "good"
        if v <= 15:
            return "Moderate multiple", "neutral"
        if v <= 25:
            return "Premium multiple", "caution"
        return "Very high multiple", "risk"
    if kind == "ps":
        if v < 3:
            return "Lower sales multiple", "good"
        if v <= 7:
            return "Moderate sales multiple", "neutral"
        if v <= 12:
            return "High sales multiple", "caution"
        return "Very high sales multiple", "risk"
    if kind == "fcf_yield":
        if v < 0:
            return "Negative cash yield", "risk"
        if v < 2:
            return "Low cash yield", "caution"
        if v >= 5:
            return "Strong cash yield", "good"
        return "Moderate cash yield", "neutral"
    return None, "neutral"


def _ma_signal(is_above):
    if is_above is None:
        return None, "neutral"
    return ("Above trend", "good") if is_above else ("Below trend", "risk")


def _rsi_signal(v):
    v = to_float(v)
    if v is None:
        return None, "neutral"
    if v >= 70:
        return "Overbought / stretched", "caution"
    if v <= 30:
        return "Oversold / weak", "caution"
    if 45 <= v <= 55:
        return "Neutral", "neutral"
    return ("Positive momentum", "good") if v > 55 else ("Soft momentum", "caution")


def _volume_signal(v):
    v = to_float(v)
    if v is None:
        return None, "neutral"
    if v >= 1.5:
        return "High attention", "caution"
    if v >= 1.2:
        return "Elevated volume", "info"
    if v < 0.8:
        return "Light volume", "neutral"
    return "Normal volume", "neutral"


def _history_tone(word):
    # For valuation multiples, lower than history is not automatically "good",
    # but it is favorable relative to the company's own past; above is caution.
    return {"above": "caution", "below": "good", "near": "neutral"}.get(word, "neutral")


def section(title, kicker=""):
    """Render an editorial section header: hairline rule + kicker + serif title."""
    kick = f'<div class="kicker">{kicker}</div>' if kicker else ""
    st.markdown(f'<div class="rt-section">{kick}<h2>{title}</h2></div>', unsafe_allow_html=True)


# Editorial palette (kept in sync with the CSS block up top)
INK, PAPER, MUTED, LINE = "#23231E", "#FCFBF8", "#7A7970", "#E8E6DE"
POS, NEG = "#2F6B4F", "#A24A38"
WARN, INFO = "#B07A2E", "#3A5A78"
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
    """A small line-with-points trend for one metric (the value is labeled at
    each point). A dark baseline marks zero *only when values actually go
    negative*, so a negative year reads differently from a mere dip.
    None if fewer than 2 real points."""
    pts = [(y, v) for y, v in zip(years, values) if v is not None]
    if len(pts) < 2:
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

    # value labels sit above positive points and below negative ones
    positions = ["top center" if v >= 0 else "bottom center" for v in ys]

    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="lines+markers+text",
        line=dict(color=INK, width=2),
        marker=dict(color=PAPER, size=7, line=dict(color=INK, width=2)),  # hollow points
        text=labels, textposition=positions, cliponaxis=False,
        textfont=dict(family="IBM Plex Sans, sans-serif", color=INK, size=11),
        hovertemplate="%{x}   %{text}<extra></extra>",
    ))

    lo, hi = min(ys), max(ys)
    span = (hi - lo) or abs(hi) or 1
    pad = span * 0.22
    ymin, ymax = lo - pad, hi + pad
    if lo < 0:
        ymax = max(ymax, span * 0.06)   # keep the zero baseline on-chart

    fig.update_layout(
        height=210, margin=dict(l=10, r=10, t=16, b=6),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", color=MUTED, size=11),
        hoverlabel=dict(bgcolor=PAPER, bordercolor=LINE,
                        font=dict(family="IBM Plex Sans, sans-serif", color=INK, size=12)),
        showlegend=False,
        xaxis=dict(showgrid=False, showline=False, zeroline=False, ticks="",
                   tickfont=dict(color=MUTED, size=10), fixedrange=True, type="category"),
        yaxis=dict(showgrid=True, gridcolor=LINE, griddash="dot", showline=False,
                   zeroline=False, ticks="", tickprefix=tickprefix, ticksuffix=ticksuffix,
                   tickformat=tickformat, tickfont=dict(color=MUTED, size=10),
                   range=[ymin, ymax], fixedrange=True),
    )
    # dark zero baseline — the cue that distinguishes a negative from a dip.
    # Solid near-black against the dotted light gridlines; only drawn when a
    # value actually crosses zero, so its mere presence signals "went negative".
    if lo < 0:
        fig.add_hline(y=0, line=dict(color=INK, width=1.25))
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
            fig = _trend_chart(years, m.get(key), fmt)
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
            fig = _trend_chart(years, m.get(key), fmt)
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


def render_quarterly(symbol):
    q = get_quarterly_trend(symbol)
    labels, m = q["labels"], q["metrics"]
    if len(labels) < 2:
        st.caption("Quarterly data isn't available for this stock on the current plan.")
        return

    def cell(col, label, key, fmt):
        with col:
            st.markdown(f"**{label}**")
            fig = _trend_chart(labels, m.get(key), fmt)
            if fig is None:
                st.caption("Unavailable.")
            else:
                st.plotly_chart(fig, use_container_width=True,
                                config={"displayModeBar": False}, key=f"q_{symbol}_{key}")

    c1, c2 = st.columns(2)
    cell(c1, "Revenue", "revenue", "money")
    cell(c2, "EPS (diluted)", "eps", "eps")
    c1, c2 = st.columns(2)
    cell(c1, "Gross Margin", "gross_margin", "pct")
    cell(c2, "Operating Margin", "op_margin", "pct")
    c1, c2 = st.columns(2)
    cell(c1, "Net Margin", "net_margin", "pct")
    cell(c2, "Free Cash Flow", "fcf", "money")

    st.caption("The last several fiscal quarters (most recent on the right). Quarterly data shows "
               "inflections annual figures can hide — accelerating or slowing revenue, margin "
               "turns, and whether cash generation is keeping pace with reported profit.")


def _cmp_word(now, med):
    if now is None or med is None or med == 0:
        return None
    r = now / med
    return "above" if r >= 1.15 else "below" if r <= 0.85 else "near"


def _valuation_read(d):
    hist, gro = d["history"], d["growth"]
    words = [w for w in (_cmp_word(hist[k]["now"], hist[k]["median"]) for k in ("pe", "ev", "ps")) if w]
    if words:
        if words.count("above") >= 2:
            val = "above"
        elif words.count("below") >= 2:
            val = "below"
        else:
            val = "near"
        val_sentence = f"The stock trades **{val}** its own 5-year valuation range"
    else:
        val_sentence = "Historical valuation context is limited on the current data"
    rg = gro.get("revenue")
    grow = ""
    if rg is not None:
        gw = "growing" if rg > 5 else "shrinking" if rg < -5 else "roughly flat"
        grow = f", and revenue is **{gw}** ({rg:+,.0f}% year over year)"
    return (f"**Valuation read:** {val_sentence}{grow}. "
            "This describes the numbers only — it isn't a recommendation.")


def render_valuation_growth(symbol):
    d = get_valuation_growth(symbol)
    cur, gro, hist = d["current"], d["growth"], d["history"]

    _subgroup("Current Valuation")
    c = st.columns(3)
    _s, _t = _valuation_signal(cur.get("pe"), "pe")
    metric_tile(c[0], "P/E (TTM)", num(cur.get("pe")), "pe", status=_s, status_tone=_t)
    _s, _t = _valuation_signal(cur.get("forward_pe"), "forward_pe")
    metric_tile(c[1], "Forward P/E", num(cur.get("forward_pe")), "forward_pe", status=_s, status_tone=_t)
    _s, _t = _valuation_signal(cur.get("peg"), "peg")
    metric_tile(c[2], "PEG", num(cur.get("peg")), "peg", status=_s, status_tone=_t)
    c = st.columns(3)
    _s, _t = _valuation_signal(cur.get("ev_ebitda"), "ev")
    metric_tile(c[0], "EV / EBITDA", num(cur.get("ev_ebitda")), "ev_ebitda", status=_s, status_tone=_t)
    _s, _t = _valuation_signal(cur.get("ps"), "ps")
    metric_tile(c[1], "Price / Sales", num(cur.get("ps")), "price_sales", status=_s, status_tone=_t)
    _s, _t = _valuation_signal(cur.get("fcf_yield"), "fcf_yield")
    metric_tile(c[2], "FCF Yield", pct(cur.get("fcf_yield")), "fcf_yield", status=_s, status_tone=_t)

    fe = get_forward_estimates(symbol, n=2)
    if fe["years"]:
        _subgroup("Forward Valuation")
        cols = st.columns(len(fe["years"]))
        for col, y in zip(cols, fe["years"]):
            with col:
                st.metric(f"FY{y['fiscal_year']} est. EPS",
                          f"${y['eps']:,.2f}" if to_float(y.get("eps")) is not None else "N/A",
                          help="Consensus analyst EPS estimate for this fiscal year.")
                bits = []
                if to_float(y.get("forward_pe")) is not None:
                    bits.append(f"**{y['forward_pe']:.1f}×** fwd P/E")
                if to_float(y.get("revenue")) is not None:
                    bits.append(f"${y['revenue'] / 1e9:,.0f}B rev")
                if bits:
                    st.caption(" · ".join(bits))
                if to_float(y.get("n_eps")) is not None:
                    st.caption(f"{int(y['n_eps'])} analysts")
        pe_ttm = to_float(cur.get("pe"))
        fpe1 = to_float(fe["years"][0].get("forward_pe"))
        if pe_ttm and fpe1 and fpe1 < pe_ttm * 0.85:
            st.caption(f"Trailing P/E is **{pe_ttm:.0f}×** but forward P/E is **{fpe1:.0f}×** — the "
                       "market expects earnings to rise sharply, so the stock looks cheaper against "
                       "*future* profits than past ones. That read only holds if the estimates do.")
        elif pe_ttm and fpe1 and fpe1 > pe_ttm * 1.15:
            st.caption(f"Trailing P/E is **{pe_ttm:.0f}×** but forward P/E is **{fpe1:.0f}×** — "
                       "earnings are expected to fall, so the stock is more expensive against future "
                       "profits than trailing ones suggest.")
    else:
        st.caption("Forward estimates aren't available for this stock right now.")

    _subgroup("Growth Context")
    c = st.columns(3)
    _s, _t = _sign_signal(gro.get("revenue"), pos="Growing", neg="Shrinking", flat="Flat")
    metric_tile(c[0], "Revenue Growth (YoY)", pct(gro.get("revenue")), "revenue_growth", status=_s, status_tone=_t)
    _s, _t = _sign_signal(gro.get("eps"), pos="EPS growing", neg="EPS shrinking", flat="Flat", extreme_warn=True)
    metric_tile(c[1], "EPS Growth (YoY)", pct(gro.get("eps")), "eps_growth", status=_s, status_tone=_t)
    _s, _t = _sign_signal(gro.get("fcf"), pos="FCF growing", neg="FCF shrinking", flat="Flat", extreme_warn=True)
    metric_tile(c[2], "FCF Growth (YoY)", pct(gro.get("fcf")), "fcf_growth", status=_s, status_tone=_t)

    _subgroup("Historical Context")
    c = st.columns(3)

    def hist_tile(col, label, item, help_key):
        """Historical context should center the stock's own 5-year median.

        The current value is already shown in Current Valuation, so this tile
        uses the historical median as the main number and puts today's value in
        the caption only as context.
        """
        now, med = item.get("now"), item.get("median")
        word = _cmp_word(now, med)
        with col:
            st.metric(f"{label} 5-yr median", num(med), help=EXPLAINERS.get(help_key))
            if now is not None:
                if word:
                    st.markdown(
                        f"<div style='color:{MUTED};font-size:.79rem;margin-top:-.55rem;line-height:1.5'>"
                        f"Now <b>{num(now)}</b> · trading {_colored(word, _history_tone(word))}</div>",
                        unsafe_allow_html=True)
                else:
                    st.caption(f"Now **{num(now)}**")
            else:
                st.caption("Current value unavailable")

    hist_tile(c[0], "P/E", hist["pe"], "pe_vs_median")
    hist_tile(c[1], "EV/EBITDA", hist["ev"], "ev_vs_median")
    hist_tile(c[2], "P/S", hist["ps"], "ps_vs_median")

    st.caption(_valuation_read(d))
    render_industry_benchmark(symbol)


def _consensus_bar(grades):
    cats = [("Strong Buy", "strongBuy", "#2F6B4F"), ("Buy", "buy", "#4E8B6B"),
            ("Hold", "hold", MUTED), ("Sell", "sell", "#C06B58"),
            ("Strong Sell", "strongSell", NEG)]
    total = sum((grades.get(k) or 0) for _, k, _ in cats)
    if total <= 0:
        return None
    fig = go.Figure()
    for label, key, color in cats:
        v = grades.get(key) or 0
        if v <= 0:
            continue
        fig.add_trace(go.Bar(
            x=[v], y=["r"], orientation="h", marker=dict(color=color),
            text=f"{label.replace('Strong ', 'S. ')} {int(v)}", textposition="inside",
            insidetextanchor="middle", textfont=dict(color="#FCFBF8", size=11),
            hovertemplate=f"{label}: {int(v)}<extra></extra>"))
    fig.update_layout(barmode="stack", height=64, margin=dict(l=6, r=6, t=4, b=4),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      showlegend=False,
                      xaxis=dict(visible=False, fixedrange=True),
                      yaxis=dict(visible=False, fixedrange=True))
    return fig


def _analyst_read(a):
    bits = []
    if a.get("consensus"):
        bits.append(f"analysts lean **{a['consensus']}**")
    up = a["target"].get("upside")
    if up is not None:
        bits.append(f"the average target implies **{up:+,.0f}%** {'upside' if up >= 0 else 'downside'}")
    if not bits:
        return "Analyst data is limited on the current plan."
    return ("**Expectation read:** " + ", and ".join(bits) +
            ". Strong expectations can already be priced in — this isn't a recommendation.")


def render_analyst(symbol):
    a = get_analyst(symbol)
    gr, tg, fw = a["grades"], a["target"], a["forward"]
    total = sum(v or 0 for v in gr.values())
    if not total and not tg.get("avg") and not fw.get("eps"):
        st.caption("Unavailable from current data source.")
        return

    if total:
        _subgroup("Analyst Consensus")
        fig = _consensus_bar(gr)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False}, key=f"consensus_{symbol}")
        c = st.columns(4)
        metric_tile(c[0], "Consensus", a.get("consensus") or "N/A", "analyst_consensus")
        with c[1]:
            st.metric("Buy", f"{int((gr.get('strongBuy') or 0) + (gr.get('buy') or 0))}")
        with c[2]:
            st.metric("Hold", f"{int(gr.get('hold') or 0)}")
        with c[3]:
            st.metric("Sell", f"{int((gr.get('sell') or 0) + (gr.get('strongSell') or 0))}")

    if tg.get("avg") is not None:
        _subgroup("Price Target")
        c = st.columns(4)
        with c[0]:
            st.metric("Low", money(tg.get("low")))
        with c[1]:
            st.metric("Average", money(tg.get("avg")))
        with c[2]:
            st.metric("High", money(tg.get("high")))
        _s, _t = _sign_signal(tg.get("upside"), pos="Upside to target", neg="Below target", flat="Near target", extreme_warn=False)
        metric_tile(c[3], "Implied Upside", pct(tg.get("upside")), "implied_upside", status=_s, status_tone=_t)

    if fw.get("eps") is not None or fw.get("revenue") is not None:
        _subgroup("Forward Estimates")
        yr = fw.get("year") or ""
        tag = f"FY{yr[2:]}" if len(yr) == 4 else "next yr"
        c = st.columns(3)
        with c[0]:
            st.metric(f"Est. Revenue ({tag})", big_money(fw.get("revenue")))
        with c[1]:
            st.metric(f"Est. EPS ({tag})", money(fw.get("eps")))
        with c[2]:
            st.metric("Covering Analysts", f"{int(fw.get('n_eps') or 0)} EPS · {int(fw.get('n_rev') or 0)} rev")

    st.caption(_analyst_read(a))
    st.caption("Estimate revisions (whether these forecasts are drifting up or down over time) need "
               "saved history — they'll arrive with the Thesis Tracker. Recent upgrades / downgrades "
               "are planned too.")


def _beat_str(surprise_pct):
    if surprise_pct is None:
        return None
    return f"{'beat' if surprise_pct >= 0 else 'missed'} by {abs(surprise_pct):,.0f}%"


def render_earnings(symbol):
    e = get_earnings_context(symbol)
    nxt, last, cik = e.get("next"), e.get("last"), e.get("cik")
    if not nxt and not last:
        st.caption("Unavailable from current data source.")
        return

    if nxt:
        _subgroup("Next Earnings")
        c = st.columns(3)
        with c[0]:
            st.metric("Date", nxt.get("date") or "N/A")
        days = nxt.get("days")
        with c[1]:
            st.metric("Days Away", f"{days}" if days is not None else "N/A")
        with c[2]:
            st.metric("EPS Estimate", money(nxt.get("eps_est")))
        if days is not None and 0 <= days <= 7:
            st.warning(f"⚠️ Earnings are ~{days} day(s) away — the stock may move materially on the release.")

    if last:
        _subgroup("Last Earnings — Actual vs Estimate")
        c = st.columns(2)
        with c[0]:
            st.metric("EPS", money(last.get("eps_actual")))
            beat = _beat_str(last.get("eps_surprise"))
            if beat:
                tone = "good" if to_float(last.get("eps_surprise")) >= 0 else "risk"
                st.markdown(f"<div style='color:{MUTED};font-size:.79rem'>est. {money(last.get('eps_est'))} · {_colored(beat, tone)}</div>", unsafe_allow_html=True)
            else:
                st.caption(f"est. {money(last.get('eps_est'))}")
        with c[1]:
            st.metric("Revenue", big_money(last.get("rev_actual")))
            beat = _beat_str(last.get("rev_surprise"))
            if beat:
                tone = "good" if to_float(last.get("rev_surprise")) >= 0 else "risk"
                st.markdown(f"<div style='color:{MUTED};font-size:.79rem'>est. {big_money(last.get('rev_est'))} · {_colored(beat, tone)}</div>", unsafe_allow_html=True)
            else:
                st.caption(f"est. {big_money(last.get('rev_est'))}")

    _subgroup("SEC Filings")
    if cik:
        base = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&owner=include&count=40"
        st.markdown(f"[10-K (annual)]({base}&type=10-K) &nbsp;·&nbsp; [10-Q (quarterly)]({base}&type=10-Q) "
                    f"&nbsp;·&nbsp; [8-K (events)]({base}&type=8-K) &nbsp;·&nbsp; [All filings]({base}&type=)")
    else:
        st.caption("Filing links unavailable.")
    st.caption("Earnings press releases and transcripts are planned.")


def _rsi(closes, period=14):
    """14-day Wilder RSI from a list of closing prices (oldest -> newest)."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def get_technicals(symbol):
    """Light technicals computed locally: MAs (from quote), RSI (from history),
    distance from 52-week high/low, and volume vs average."""
    q = get_quote(symbol)
    raw = _fmp_quote(symbol)
    price = to_float(q.get("price"))
    ma50, ma200 = to_float(q.get("ma_50")), to_float(q.get("ma_200"))
    hi, lo = to_float(q.get("week_high")), to_float(q.get("week_low"))
    cur_vol = to_float(pick(raw, "volume"))
    avg_vol = to_float(get_key_metrics(symbol).get("avg_volume"))

    rsi = None
    df = get_price_history(symbol)
    if not df.empty:
        closes = pd.to_numeric(df["close"], errors="coerce").dropna().tolist()
        if len(closes) > 15:
            rsi = _rsi(closes[-260:], 14)

    return {
        "price": price, "ma50": ma50, "ma200": ma200,
        "above_50": (price > ma50) if (price and ma50) else None,
        "above_200": (price > ma200) if (price and ma200) else None,
        "rsi": rsi,
        "dist_high": ((price / hi - 1) * 100) if (price and hi) else None,
        "dist_low": ((price / lo - 1) * 100) if (price and lo) else None,
        "vol_ratio": (cur_vol / avg_vol) if (cur_vol and avg_vol) else None,
    }


def _technicals_read(t):
    bits = []
    a50, a200 = t.get("above_50"), t.get("above_200")
    if a50 is not None and a200 is not None:
        if a50 and a200:
            bits.append("trading above both major moving averages (price strength)")
        elif not a50 and not a200:
            bits.append("below both major moving averages (price weakness)")
        else:
            bits.append("between its 50- and 200-day averages (mixed trend)")
    rsi = t.get("rsi")
    if rsi is not None:
        if rsi >= 70:
            bits.append(f"RSI {rsi:.0f} is elevated (possibly stretched near-term)")
        elif rsi <= 30:
            bits.append(f"RSI {rsi:.0f} is low (possibly oversold)")
        else:
            bits.append(f"RSI {rsi:.0f} is neutral")
    if not bits:
        return "Price-context data is limited on the current plan."
    return ("**Price context:** " + ", and ".join(bits) +
            ". Technicals describe price behavior, not business quality — not a recommendation.")


def render_technicals(symbol):
    t = get_technicals(symbol)
    if t.get("price") is None:
        st.caption("Unavailable from current data source.")
        return

    c = st.columns(3)
    with c[0]:
        a = t.get("above_50")
        st.metric("vs 50-day MA", ("Above" if a else "Below") if a is not None else "N/A",
                  help=EXPLAINERS.get("ma_50"))
        _s, _t = _ma_signal(a)
        _chip(_s, _t)
        if t.get("ma50") is not None:
            st.caption(f"50-day avg {money(t['ma50'])}")
    with c[1]:
        a = t.get("above_200")
        st.metric("vs 200-day MA", ("Above" if a else "Below") if a is not None else "N/A",
                  help=EXPLAINERS.get("ma_200"))
        _s, _t = _ma_signal(a)
        _chip(_s, _t)
        if t.get("ma200") is not None:
            st.caption(f"200-day avg {money(t['ma200'])}")
    with c[2]:
        rsi = t.get("rsi")
        st.metric("RSI (14-day)", num(rsi, 0) if rsi is not None else "N/A",
                  help=EXPLAINERS.get("rsi"))
        _s, _t = _rsi_signal(rsi)
        _chip(_s, _t)

    c = st.columns(3)
    metric_tile(c[0], "From 52-wk High", pct(t.get("dist_high")), "dist_high")
    metric_tile(c[1], "From 52-wk Low", pct(t.get("dist_low")), "dist_low")
    with c[2]:
        vr = t.get("vol_ratio")
        st.metric("Volume vs Avg", f"{vr:,.2f}×" if vr is not None else "N/A",
                  help=EXPLAINERS.get("vol_ratio"))
        _s, _t = _volume_signal(vr)
        _chip(_s, _t)

    st.caption(_technicals_read(t))


# ===========================================================================
# AI ANALYSIS  (optional — calls Claude to explain the whole page in plain English)
# ===========================================================================
ANALYSIS_SYSTEM = (
    "You are an equity research assistant for a personal stock-research dashboard.\n\n"
    "Your job is to analyze the provided company and stock data and generate a plain-English "
    "investment research summary for a non-expert investor.\n\n"
    "Important rules:\n"
    "- Do NOT give personalized financial advice.\n"
    "- Do NOT say \"you should buy\" or \"you should sell.\"\n"
    "- You may give a research view such as: \"Buyable on pullback,\" \"Hold / watch,\" "
    "\"Avoid for now,\" \"High-risk growth candidate,\" or \"Strong business but valuation stretched.\"\n"
    "- Explain every major metric in simple language.\n"
    "- Tie the metrics together into a clear, insightful recommendation framework.\n"
    "- Be honest about missing, stale, contradictory, or suspicious data.\n"
    "- If data looks wrong or extreme, flag it clearly before drawing conclusions.\n"
    "- Distinguish between company quality and stock buyability. A great company can still be a "
    "poor buy if the price is too high."
)

# The user-message template. {STOCK_DATA} and {TICKER} are filled in at call time
# (via str.replace, so the literal braces elsewhere are safe).
ANALYSIS_TEMPLATE = """Input data:
{STOCK_DATA}

Generate the analysis in the following structure:

# {TICKER} — Plain-English Investment Research Summary

## 1. Bottom-line research view

Start with a short conclusion in plain English.

Use one of these styles:
- "Strong business, but valuation looks stretched."
- "Improving turnaround, but still risky."
- "High-quality compounder, buyable only at a fair price."
- "Momentum is strong, but the stock may already price in a lot of good news."
- "Weak fundamentals; not attractive unless the turnaround becomes clearer."

Include:
- Research stance: Buyable / Hold / Watchlist / Avoid for now / Trim if overexposed
- Time horizon: short-term setup vs long-term thesis
- Confidence level: Low / Medium / High
- Main reason for the stance

## 2. What business are we buying?

Explain what the company actually does: business model, main products/services, industry, and
whether the business is cyclical, stable, high-growth, commodity-like, subscription-like, or
capital-intensive — and why that matters for interpreting the numbers. Explain it as if the reader
has never analyzed the company before.

## 3. Business trajectory: is the company getting better or worse?

Analyze multi-year trends in revenue, EPS, gross margin, operating margin, net margin, return on
equity, and debt. For each important metric: (1) explain what it means, (2) state what the data
shows, (3) translate it into an insight. Answer: is revenue growing consistently or cyclically? Are
profits improving or deteriorating? Are margins expanding or shrinking? Is the company becoming more
efficient? Is debt rising faster than the business?

## 4. Cash generation: does profit turn into real cash?

Analyze operating cash flow, free cash flow, FCF margin, FCF per share, FCF yield, and capex if
available. Explain that free cash flow is the cash left after running the business and investing to
keep growing; strong earnings with weak FCF can mean heavy investment, working-capital pressure, or
lower earnings quality. Answer: is FCF positive and improving? Does it support the earnings story?
Is the company spending heavily to grow? Is the FCF yield attractive relative to market cap?

## 5. Valuation: is the stock cheap, fair, or expensive?

Analyze P/E, forward P/E, PEG, EV/EBITDA, price/sales, FCF yield, current valuation vs 5-year
median, and valuation relative to growth. Explain each simply. Do NOT call a stock cheap just
because PEG is low. If growth is temporarily inflated by a rebound from losses, explain that.
Compare current multiples to historical medians and say whether the market is already pricing in a
lot of good news. End with a valuation read: Cheap / Reasonable / Premium but justified / Stretched /
Very expensive (expectation-heavy).

## 6. Analyst expectations: what do professionals think?

Analyze buy/hold/sell counts, average price target, low and high targets, implied upside/downside,
and earnings/revenue estimates. Note that consensus is expert sentiment, price targets are not
guarantees, and analysts can be late, overly optimistic, or clustered. Answer: are analysts broadly
bullish, mixed, or cautious? Is the average target meaningfully above the current price? Is the low
target below it? Are expectations already very high?

## 7. Earnings and upcoming catalysts

Analyze the next earnings date, days until it, EPS estimate, last EPS actual vs estimate, last
revenue actual vs estimate, and any guidance/filings if available. Note that a company can beat and
still fall if expectations were higher. Answer: did it beat or miss last quarter? Was the beat
meaningful? Are next-quarter expectations high? What could move the stock next?

## 8. Price context and timing

Analyze current price, distance from 52-week high and low, 50-day and 200-day moving averages, RSI,
volume vs average, and beta. Explain the 50-day (medium-term trend), 200-day (long-term trend), RSI
(short-term overbought/oversold; ~50 is neutral), and beta (volatility vs the market). Answer: is
the stock extended or beaten down? Is momentum strong or weakening? Is it near a high after a big
run? Is this a calm entry or a chase? How volatile is it likely to be?

## 9. Financial health and risk

Analyze gross margin, net margin, ROE, debt/equity, cash and debt if available, beta, and any
industry-specific risks. Explain that strong margins show pricing power or efficiency, high ROE
means strong profit on shareholder capital, low debt/equity means less balance-sheet stress, and
high beta means larger swings. Identify the biggest risks (valuation, cyclical, demand slowdown,
margin compression, debt/capex, customer concentration, regulatory/geopolitical, execution,
expectations).

## 10. Bull case, bear case, and what would change the view

Bull case: what has to go right for the stock to work? Bear case: what could cause it to fall? What
would change the view: what data would make it more attractive, and what would make it less
attractive? Be specific and use metrics.

## 11. Final tied-together recommendation framework

Give a clear research stance in this format:

Research stance:
- For existing holders:
- For new buyers:
- For risk-averse investors:
- For aggressive growth investors:

Then a final one-sentence summary.

Before writing the final summary, check the data for anomalies:
- Is the price or market cap unusually different from recent known values?
- Are growth rates distorted by a prior negative year?
- Are valuation ratios missing, stale, or mathematically inconsistent?
- Are analyst targets split-adjusted consistently with the current price?
- Are any fields marked N/A?
If there are anomalies, include a short "Data quality notes" section before the recommendation."""


# A short, cheap variant — a fraction of the output tokens of the full report.
ANALYSIS_TEMPLATE_QUICK = """Input data:
{STOCK_DATA}

Write a CONCISE plain-English research summary for {TICKER} — aim for roughly 400-600 words total,
tight and skimmable. Use exactly this structure:

# {TICKER} — Quick Research Take

## Bottom line
2-3 sentences: research stance (Buyable / Hold / Watchlist / Avoid for now), confidence
(Low / Medium / High), and the single main reason.

## The business
1-2 sentences on what it does and whether it's cyclical, stable, or high-growth.

## Trajectory & cash
2-3 sentences: are revenue, margins, and free cash flow improving or deteriorating? Flag any loss
years or unusually heavy capex (earnings much larger than free cash flow).

## Valuation
2-3 sentences: cheap / reasonable / stretched versus its own 5-year history and its growth. If PEG
looks tiny, explain whether it's distorted by a low or negative prior-year base — do NOT call the
stock cheap just because PEG is low.

## Analysts & catalysts
1-2 sentences: consensus lean, upside to the average price target, and the next earnings date.

## Price & risk
1-2 sentences: extended or beaten down (moving averages, RSI, distance from highs), how volatile
(beta), and the single biggest risk.

## Bull vs bear
One line each.

## Final read
One sentence tying it together into a research view.

Before the final read, if any data looks wrong, stale, or extreme (e.g. a P/E that doesn't match the
reported EPS, or a growth rate inflated by a negative prior year), flag it in one short line. Rules:
no personalized advice, no "you should buy/sell"; explain jargon briefly; be honest about missing or
suspicious data."""


def _fmt_series(years, vals, fmt):
    out = []
    for y, v in zip(years or [], vals or []):
        if v is None:
            continue
        tag = f"FY{y[2:]}" if len(y) == 4 else y
        if fmt == "money":
            out.append(f"{tag} {big_money(v)}")
        elif fmt == "pct":
            out.append(f"{tag} {v:,.1f}%")
        elif fmt == "eps":
            out.append(f"{tag} ${v:,.2f}")
        else:
            out.append(f"{tag} {v:,.2f}")
    return ", ".join(out) if out else "unavailable"


def compute_quality_flags(symbol):
    """Cheap, in-code data sanity checks — fed to the AI and shown in the UI so
    the analysis leads with caveats instead of trusting broken numbers. All
    fetches here are cached, so this is nearly free."""
    sym = symbol.upper()
    q = _fmp_quote(sym)
    tr = get_trajectory_annual(sym)
    val = get_valuation_growth(sym)
    ea = get_earnings_context(sym)
    tm = tr["metrics"]
    cur = val["current"]
    last = ea.get("last") or {}
    notes, missing = [], []

    # 1) missing valuation fields
    for label, k in (("forward P/E", "forward_pe"), ("PEG", "peg"),
                     ("EV/EBITDA", "ev_ebitda"), ("P/S", "ps")):
        if to_float(cur.get(k)) is None:
            missing.append(label)

    # 2) growth distorted by a prior loss year
    eps_hist = [to_float(x) for x in (tm.get("eps") or [])]
    prior_losses = [x for x in eps_hist[:-1] if x is not None and x < 0]
    ge = to_float(val["growth"].get("eps"))
    if prior_losses and ge is not None and ge > 100:
        notes.append(f"EPS growth of about {ge:.0f}% year-over-year is inflated by a prior loss "
                     "year, so PEG and EPS-growth figures overstate how fast the business is "
                     "durably growing.")

    # 3) suspiciously low PEG
    peg = to_float(cur.get("peg"))
    if peg is not None and 0 < peg < 0.2:
        notes.append(f"PEG of {peg:.2f} is artificially low (a growth spike off a low or negative "
                     "base), not evidence the stock is cheap.")

    # 4) quarterly-vs-annual EPS basis mismatch
    last_q_eps = to_float(last.get("eps_actual"))
    latest_annual = next((x for x in reversed(eps_hist) if x is not None), None)
    if (last_q_eps is not None and latest_annual is not None
            and abs(latest_annual) > 0 and last_q_eps > 1.5 * abs(latest_annual)):
        notes.append(f"The last-earnings EPS ({last_q_eps:.2f}) is a single quarter, while the "
                     "trajectory EPS is a full fiscal year — the two are not directly comparable.")

    # 5) implausible margins
    for label, k in (("gross", "gross_margin"), ("operating", "op_margin"), ("net", "net_margin")):
        vals = [to_float(x) for x in (tm.get(k) or [])]
        if any(x is not None and (x > 100 or x < -120) for x in vals):
            notes.append(f"A {label} margin outside a plausible range appears in the history — "
                         "treat that year as a possible data glitch.")

    # 6) market cap vs price x shares
    inc_q = _fmp_statement(f"income-statement?symbol={sym}&period=quarter&limit=1") or [{}]
    price, mc = to_float(pick(q, "price")), to_float(pick(q, "marketCap"))
    sh = to_float(pick(inc_q[0], "weightedAverageShsOutDil", "weightedAverageShsOut"))
    if price and mc and sh:
        implied = price * sh
        if abs(implied - mc) / mc > 0.15:
            notes.append(f"Market cap (~${mc/1e9:.0f}B) doesn't reconcile with price x shares "
                         f"(~${implied/1e9:.0f}B) — possibly a stale share count or split issue.")

    # 7) EBITDA below EBIT (impossible) in the latest quarter
    row = inc_q[0]
    eb, ei = to_float(pick(row, "ebitda")), to_float(pick(row, "ebit"))
    if eb is not None and ei is not None and eb < ei:
        per = row.get("period") or "the latest quarter"
        notes.append(f"Reported EBITDA is below EBIT in {per}, which is mathematically impossible "
                     "(a data glitch); that quarter's EBITDA and D&A are unreliable.")

    return {"missing_fields": missing, "notes": notes}


def _analysis_json(symbol):
    """Assemble everything the dashboard knows into the structured JSON the
    research prompt consumes. Keeps the requested field names, and adds the
    margin/ROE/debt and cash-generation history + valuation-vs-median context
    the prompt's sections need. Revenues/FCF/debt in billions; percent fields
    stay percent-scaled; None where unavailable."""
    import json as _json
    q, prof, m = get_quote(symbol), get_company_profile(symbol), get_key_metrics(symbol)
    tr, cash = get_trajectory_annual(symbol), get_cash_annual(symbol)
    val, an, ea, tech = (get_valuation_growth(symbol), get_analyst(symbol),
                         get_earnings_context(symbol), get_technicals(symbol))
    ty, tm = tr["years"], tr["metrics"]
    cy, cm = cash["years"], cash["metrics"]
    cur, gro, hist = val["current"], val["growth"], val["history"]
    g, tgt = an["grades"], an["target"]
    nxt, last = ea.get("next") or {}, ea.get("last") or {}
    ql = get_quarterly_trend(symbol)
    qm = ql["metrics"]
    fe = get_forward_estimates(symbol, n=3)
    dq = compute_quality_flags(symbol)

    def rnd(v, nd=2):
        f = to_float(v)
        if f is None:
            return None
        return int(round(f)) if nd == 0 else round(f, nd)

    def bil(v):
        f = to_float(v)
        return round(f / 1e9, 2) if f is not None else None

    def fy_map(years, vals, scale=1.0, nd=2):
        out = {}
        for y, v in zip(years or [], vals or []):
            f = to_float(v)
            if f is None:
                continue
            key = f"FY{str(y)[2:]}" if len(str(y)) == 4 else str(y)
            out[key] = round(f / scale, nd)
        return out

    def med(d):
        return {"now": rnd(d.get("now")), "median": rnd(d.get("median"))}

    mc = to_float(q.get("market_cap"))
    mc_str = None
    if mc is not None:
        for size, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
            if abs(mc) >= size:
                mc_str = f"{mc / size:.2f}{unit}"
                break
        else:
            mc_str = f"{mc:.0f}"

    data = {
        "ticker": symbol,
        "company": prof.get("name") or q.get("name") or symbol,
        "sector": prof.get("sector") or prof.get("industry"),
        "price": rnd(q.get("price")),
        "daily_change_pct": rnd(q.get("change_pct")),
        "market_cap": mc_str,
        "revenue_history": fy_map(ty, tm.get("revenue"), scale=1e9, nd=1),
        "eps_history": fy_map(ty, tm.get("eps"), scale=1.0, nd=2),
        "gross_margin_pct_history": fy_map(ty, tm.get("gross_margin"), scale=1.0, nd=1),
        "operating_margin_pct_history": fy_map(ty, tm.get("op_margin"), scale=1.0, nd=1),
        "net_margin_pct_history": fy_map(ty, tm.get("net_margin"), scale=1.0, nd=1),
        "roe_pct_history": fy_map(ty, tm.get("roe"), scale=1.0, nd=1),
        "total_debt_history_billions": fy_map(ty, tm.get("debt"), scale=1e9, nd=2),
        "cash_generation_history": {
            "fcf_billions": fy_map(cy, cm.get("fcf"), scale=1e9, nd=2),
            "fcf_margin_pct": fy_map(cy, cm.get("fcf_margin"), scale=1.0, nd=1),
            "fcf_per_share": fy_map(cy, cm.get("fcf_ps"), scale=1.0, nd=2),
            "fcf_yield_pct": fy_map(cy, cm.get("fcf_yield"), scale=1.0, nd=2),
        },
        "recent_quarters": {
            "labels": ql["labels"],
            "revenue_billions": [round(v / 1e9, 2) if to_float(v) is not None else None for v in qm["revenue"]],
            "eps_diluted": qm["eps"],
            "gross_margin_pct": [round(v, 1) if v is not None else None for v in qm["gross_margin"]],
            "operating_margin_pct": [round(v, 1) if v is not None else None for v in qm["op_margin"]],
            "net_margin_pct": [round(v, 1) if v is not None else None for v in qm["net_margin"]],
            "fcf_billions": [round(v / 1e9, 2) if to_float(v) is not None else None for v in qm["fcf"]],
        },
        "valuation": {
            "pe": rnd(cur.get("pe")),
            "forward_pe": rnd(cur.get("forward_pe")),
            "peg": rnd(cur.get("peg")),
            "ev_ebitda": rnd(cur.get("ev_ebitda")),
            "price_sales": rnd(cur.get("ps")),
            "fcf_yield": rnd(cur.get("fcf_yield")),
            "vs_5yr_median": {
                "pe": med(hist.get("pe", {})),
                "ev_ebitda": med(hist.get("ev", {})),
                "price_sales": med(hist.get("ps", {})),
            },
        },
        "growth_yoy_pct": {
            "revenue": rnd(gro.get("revenue")),
            "eps": rnd(gro.get("eps")),
            "fcf": rnd(gro.get("fcf")),
        },
        "forward_estimates": {
            "note": "consensus analyst estimates for upcoming fiscal years; forward_pe = current price / estimated EPS",
            "years": [
                {"fiscal_year": y["fiscal_year"],
                 "revenue_billions": round(y["revenue"] / 1e9, 1) if to_float(y["revenue"]) is not None else None,
                 "eps": round(y["eps"], 2) if to_float(y["eps"]) is not None else None,
                 "forward_pe": round(y["forward_pe"], 1) if to_float(y["forward_pe"]) is not None else None,
                 "analysts_eps": int(y["n_eps"]) if to_float(y["n_eps"]) is not None else None}
                for y in fe["years"]
            ],
        },
        "analyst_view": {
            "buy": int((to_float(g.get("strongBuy")) or 0) + (to_float(g.get("buy")) or 0)),
            "hold": int(to_float(g.get("hold")) or 0),
            "sell": int((to_float(g.get("sell")) or 0) + (to_float(g.get("strongSell")) or 0)),
            "average_price_target": rnd(tgt.get("avg")),
            "low_price_target": rnd(tgt.get("low")),
            "high_price_target": rnd(tgt.get("high")),
            "implied_upside_pct": rnd(tgt.get("upside")),
        },
        "earnings": {
            "next_earnings_date": nxt.get("date"),
            "days_until_earnings": rnd(nxt.get("days"), 0),
            "eps_estimate": rnd(nxt.get("eps_est")),
            "last_eps_actual": rnd(last.get("eps_actual")),
            "last_eps_estimate": rnd(last.get("eps_est")),
            "last_revenue_actual": bil(last.get("rev_actual")),
            "last_revenue_estimate": bil(last.get("rev_est")),
        },
        "technicals": {
            "fifty_day_ma": rnd(tech.get("ma50")),
            "two_hundred_day_ma": rnd(tech.get("ma200")),
            "rsi_14": rnd(tech.get("rsi"), 0),
            "from_52_week_high_pct": rnd(tech.get("dist_high")),
            "from_52_week_low_pct": rnd(tech.get("dist_low")),
            "volume_vs_avg": rnd(tech.get("vol_ratio")),
            "beta": rnd(m.get("beta") or prof.get("beta")),
        },
        "data_quality": dq,
    }
    return _json.dumps(data, indent=2)


def generate_ai_analysis(symbol, stock_json, full=False):
    """Call Claude's Messages API. Returns (text, error). Uses raw HTTP so no extra
    dependency is needed. Reads the key from Streamlit secrets. `full` selects the
    long detailed report; otherwise a short, much cheaper quick take."""
    key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not key:
        return None, "no_key"
    template = ANALYSIS_TEMPLATE if full else ANALYSIS_TEMPLATE_QUICK
    max_out = 16000 if full else 2000
    user_msg = template.replace("{STOCK_DATA}", stock_json).replace("{TICKER}", symbol)
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": ANTHROPIC_MODEL, "max_tokens": max_out,
                  "system": ANALYSIS_SYSTEM,
                  "messages": [{"role": "user", "content": user_msg}]},
            timeout=150,
        )
        resp.raise_for_status()
        data = resp.json()
        parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        text = "\n".join(p for p in parts if p).strip()
        return (text or None), (None if text else "empty response")
    except requests.HTTPError as e:
        code = getattr(e.response, "status_code", "?")
        detail = ""
        try:
            detail = e.response.json().get("error", {}).get("message", "")
        except Exception:
            pass
        return None, f"HTTP {code} {detail}".strip()
    except Exception as e:  # noqa: BLE001
        return None, str(e)


AI_REPORT_CSS = """<style>
/* AI analysis: simple document look — 14pt headers, 12pt body, sans, no italics */
.st-key-ai_report h1, .st-key-ai_report h2, .st-key-ai_report h3, .st-key-ai_report h4 {
  font-family:'IBM Plex Sans', system-ui, sans-serif !important;
  font-weight:600 !important; font-style:normal !important;
  font-size:14pt !important; line-height:1.25 !important;
  letter-spacing:0 !important; text-transform:none !important;
  margin:1rem 0 .4rem !important; color:var(--ink,#23231E) !important; }
.st-key-ai_report p, .st-key-ai_report li {
  font-family:'IBM Plex Sans', system-ui, sans-serif !important;
  font-size:12pt !important; font-style:normal !important;
  line-height:1.5 !important; color:var(--ink,#23231E) !important; }
.st-key-ai_report em, .st-key-ai_report i, .st-key-ai_report code { font-style:normal !important; }
.st-key-ai_report strong, .st-key-ai_report b { font-weight:600 !important; }
</style>"""


def render_ai_analysis(symbol):
    if not st.secrets.get("ANTHROPIC_API_KEY", ""):
        st.info(
            "**AI analysis needs an Anthropic API key** — this is separate from your Claude.ai "
            "subscription and is billed per use (a few cents per analysis).\n\n"
            "1. Get a key at https://console.anthropic.com\n"
            "2. Add it to your Streamlit app's secrets as `ANTHROPIC_API_KEY = \"sk-ant-...\"`\n"
            "3. Reload. Then a **Generate AI analysis** button appears here."
        )
        return

    st.caption("Claude reads all the data on this stock and writes a plain-English research "
               "summary — what each metric means, whether the business is improving, whether the "
               "valuation is demanding, and a bull/bear framework. It gives a research view "
               "(e.g. Buyable / Hold / Watchlist / Avoid), not personalized advice. Educational only.")
    depth = st.radio(
        "Report depth", ["Quick take", "Full report"], horizontal=True, key=f"ai_depth_{symbol}",
        captions=["Short & skimmable — roughly 1–3¢ per run",
                  "All 11 sections in depth — roughly 10–15¢ per run"],
    )
    full = depth == "Full report"
    st.caption("Want it cheaper still? Set `ANTHROPIC_MODEL = \"claude-haiku-4-5-20251001\"` in your "
               "secrets — Haiku is about 3× cheaper than the default. You can also set a monthly "
               "spend cap in the Anthropic Console.")
    cache = st.session_state.setdefault("ai_analysis", {})
    if st.button("✨ Generate AI analysis", key=f"ai_btn_{symbol}"):
        with st.spinner("Claude is writing the full report…" if full else "Claude is reading the data…"):
            text, err = generate_ai_analysis(symbol, _analysis_json(symbol), full=full)
        if err:
            st.error(f"Analysis failed ({err}). Check the API key, and if it mentions the model, "
                     "set `ANTHROPIC_MODEL` in your secrets to a current model name.")
        else:
            cache[symbol] = text

    if cache.get(symbol):
        st.markdown(AI_REPORT_CSS, unsafe_allow_html=True)
        # Escape "$" so Streamlit doesn't read "$...$" as LaTeX math — that was
        # italicising and garbling the dollar figures.
        clean = cache[symbol].replace("$", "\\$")
        with st.container(key="ai_report"):
            st.markdown(clean)
        st.caption("⚠️ AI-generated research view for education — not personalized financial "
                   "advice, and it may contain errors. Any stance (Buyable / Hold / Avoid, etc.) is "
                   "a research framing, not a recommendation to act. Verify against primary sources "
                   "and make your own decision.")


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
    df = df[keep].copy()

    # --- sector filter (independent per movers tab) ---
    umap = get_universe_map()
    if "symbol" in df.columns and umap:
        df["Sector"] = df["symbol"].map(
            lambda s: umap.get(str(s).upper(), {}).get("sector") or "")
        opts = ["All sectors"] + sorted(x for x in df["Sector"].unique() if x)
        if len(opts) > 1:
            sel = st.selectbox("Sector", opts, key=f"sector_{kind}", label_visibility="collapsed")
            if sel != "All sectors":
                df = df[df["Sector"] == sel]

    df = df.head(15).copy()
    if "changePct" in df.columns:
        df["changePct"] = df["changePct"].map(to_float)
    df = df.rename(columns={"symbol": "Symbol", "name": "Company",
                            "price": "Price ($)", "changePct": "Change %"})
    if df.empty:
        st.caption("No names in that sector among today's movers.")
        return
    st.dataframe(df, hide_index=True, use_container_width=True, column_config={
        "Price ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Change %": st.column_config.NumberColumn(format="%.2f%%"),
    })


# --- sticky compact header + editorial tab styling for the stock page ---
_STOCK_PAGE_CSS = """
<style>
.stock-hdr{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;
  padding:2px 0 10px;border-bottom:1px solid var(--line,#E8E6DE);margin:0 0 2px}
.stock-hdr .sh-tkr{font-family:'Fraunces',Georgia,serif;font-weight:700;font-size:1.85rem;
  line-height:1;letter-spacing:-.01em;color:var(--ink,#23231E)}
.stock-hdr .sh-co{font-size:.72rem;color:var(--muted,#7A7970);margin-top:5px;letter-spacing:.01em}
.stock-hdr .sh-px{font-family:'IBM Plex Sans',sans-serif;font-weight:600;font-size:1.45rem;
  line-height:1;color:var(--ink,#23231E);font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
.stock-hdr .sh-chg{font-size:.8rem;font-weight:500;margin-top:5px;text-align:right;
  font-variant-numeric:tabular-nums}
.stock-hdr .sh-chg.up{color:var(--pos,#2F6B4F)} .stock-hdr .sh-chg.dn{color:var(--neg,#A24A38)}

/* tabs: editorial look, and sticky so navigation stays reachable while scrolling */
div[data-testid="stTabs"] div[data-baseweb="tab-list"]{
  position:sticky;top:0;z-index:50;background:var(--paper,#FCFBF8);
  border-bottom:1px solid var(--line,#E8E6DE);gap:1.7rem;padding-top:.35rem;margin-bottom:.5rem}
div[data-testid="stTabs"] button[data-baseweb="tab"]{
  background:transparent;padding:.55rem .15rem;font-family:'IBM Plex Sans',sans-serif;
  font-size:.72rem;font-weight:600;letter-spacing:.13em;text-transform:uppercase;
  color:var(--muted,#7A7970)}
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"]{color:var(--ink,#23231E)}
div[data-testid="stTabs"] div[data-baseweb="tab-highlight"]{background-color:var(--ink,#23231E)}
div[data-testid="stTabs"] div[data-baseweb="tab-border"]{background-color:transparent}

/* Floating PDF button(s) — reachable from any tab. Bottom-RIGHT but raised so
   it clears BOTH the sidebar (left strip) and Streamlit Cloud's bottom-right
   "Manage app" badge. */
.st-key-pdf_fab_gen,.st-key-pdf_fab_dl{position:fixed;right:20px;z-index:9999;width:auto}
.st-key-pdf_fab_gen{bottom:80px}
.st-key-pdf_fab_dl{bottom:126px}
.st-key-pdf_fab_gen button,.st-key-pdf_fab_dl button{
  width:auto;border-radius:999px;padding:.5rem 1rem;font-family:'IBM Plex Sans',sans-serif;
  font-weight:600;font-size:.78rem;letter-spacing:.02em;box-shadow:0 3px 12px rgba(35,35,30,.20)}
.st-key-pdf_fab_gen button{background:var(--ink,#23231E);color:var(--paper,#FCFBF8);
  border:1px solid var(--ink,#23231E)}
.st-key-pdf_fab_dl button{background:var(--paper,#FCFBF8);color:var(--ink,#23231E);
  border:1px solid var(--ink,#23231E)}
</style>
"""


def _render_stock_header(symbol, name, industry, exchange, quote):
    sub = "  ·  ".join(x for x in (industry, exchange) if x)
    chg = to_float(quote.get("change_pct"))
    if chg is None:
        chg_html = ""
    else:
        cls = "up" if chg >= 0 else "dn"
        arrow = "▲" if chg >= 0 else "▼"
        chg_html = f'<div class="sh-chg {cls}">{arrow} {abs(chg):.2f}%</div>'
    st.markdown(
        '<div class="stock-hdr">'
        f'<div><div class="sh-tkr">{symbol}</div>'
        f'<div class="sh-co">{name}{("  ·  " + sub) if sub else ""}</div></div>'
        f'<div><div class="sh-px">{money(quote.get("price"))}</div>{chg_html}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ===========================================================================
# PDF EXPORT  — server-side report of the whole stock page (all tabs).
# Built with reportlab + matplotlib (no browser/Chrome needed). Guarded so the
# rest of the app keeps running if those packages aren't installed yet.
# ===========================================================================
try:
    import io as _io
    import os as _os
    import datetime as _dt
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from reportlab.lib.pagesizes import letter as _LETTER
    from reportlab.lib.units import inch as _INCH
    from reportlab.lib.colors import HexColor
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                    Image as RLImage, HRFlowable)
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.utils import ImageReader
    _PDF_OK = True
except Exception:
    _PDF_OK = False

_FONTS_READY = False


def _pdf_fonts():
    """Embed DejaVu (ships with matplotlib) so arrows/dashes/minus signs render
    as glyphs, not boxes. Falls back to built-ins if the files aren't found."""
    global _FONTS_READY
    if _FONTS_READY or not _PDF_OK:
        return
    base = _os.path.join(_os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
    try:
        pdfmetrics.registerFont(TTFont("Body", _os.path.join(base, "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("Body-Bold", _os.path.join(base, "DejaVuSans-Bold.ttf")))
        pdfmetrics.registerFont(TTFont("Head", _os.path.join(base, "DejaVuSerif.ttf")))
        pdfmetrics.registerFont(TTFont("Head-Bold", _os.path.join(base, "DejaVuSerif-Bold.ttf")))
        pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold")
        pdfmetrics.registerFontFamily("Head", normal="Head", bold="Head-Bold")
        _FONTS_READY = True
    except Exception:
        _FONTS_READY = False


def _hf(bold=False):
    return ("Head-Bold" if bold else "Head") if _FONTS_READY else ("Times-Bold" if bold else "Times-Roman")


def _bf(bold=False):
    return ("Body-Bold" if bold else "Body") if _FONTS_READY else ("Helvetica-Bold" if bold else "Helvetica")


def _fig_png(fig, dpi=200):
    buf = _io.BytesIO()
    FigureCanvasAgg(fig)
    fig.savefig(buf, format="png", dpi=dpi, facecolor=fig.get_facecolor())
    buf.seek(0)
    return buf


def _pdf_trend(ax, years, values, fmt):
    """Option-A line + points with value labels and the dark zero baseline for
    negatives — the same reading as the on-screen charts."""
    pts = [(y, v) for y, v in zip(years, values or []) if v is not None]
    if len(pts) < 2:
        ax.axis("off")
        ax.text(0.5, 0.5, "n/a", ha="center", va="center", color=MUTED, fontsize=8)
        return
    xs = [f"FY{str(y)[2:]}" if len(str(y)) == 4 else str(y) for y, _ in pts]
    ys = [v for _, v in pts]
    if fmt == "money":
        sc, u = _money_scale(ys); ys = [v / sc for v in ys]; lab = lambda v: f"${v:,.1f}{u}"
    elif fmt == "pct":
        lab = lambda v: f"{v:,.0f}%"
    elif fmt in ("eps", "pershare"):
        lab = lambda v: f"${v:,.2f}"
    else:
        lab = lambda v: f"{v:,.1f}"
    x = list(range(len(ys)))
    lo, hi = min(ys), max(ys)
    span = (hi - lo) or abs(hi) or 1
    pad = span * 0.32
    ymin, ymax = lo - pad, hi + pad
    if lo < 0:
        ymax = max(ymax, span * 0.06)
    ax.set_ylim(ymin, ymax)
    ax.set_xlim(-0.45, len(ys) - 0.55)
    ax.grid(axis="y", color=LINE, lw=0.6, linestyle=(0, (1, 3)))
    ax.set_axisbelow(True)
    ax.plot(x, ys, color=INK, lw=1.4, zorder=3)
    ax.scatter(x, ys, facecolor=PAPER, edgecolor=INK, s=22, lw=1.4, zorder=4)
    for xi, v in zip(x, ys):
        ax.annotate(lab(v), (xi, v), textcoords="offset points",
                    xytext=(0, 5 if v >= 0 else -11), ha="center", fontsize=6.5, color=INK)
    if lo < 0:
        ax.axhline(0, color=INK, lw=0.9, zorder=2)
    ax.set_xticks(x)
    ax.set_xticklabels(xs, fontsize=6.5, color=MUTED)
    ax.set_yticks([])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)


def _pdf_grid(specs, ncols, cell_w=2.6, cell_h=1.5):
    nrows = (len(specs) + ncols - 1) // ncols
    fig = Figure(figsize=(cell_w * ncols, cell_h * nrows), facecolor=PAPER)
    for i, (title, years, values, fmt) in enumerate(specs):
        ax = fig.add_subplot(nrows, ncols, i + 1)
        ax.set_facecolor(PAPER)
        _pdf_trend(ax, years, values, fmt)
        ax.set_title(title, fontsize=8, color=INK, loc="left", pad=6, fontfamily="DejaVu Serif")
    fig.subplots_adjust(left=0.03, right=0.99, top=0.93, bottom=0.07, hspace=0.55, wspace=0.12)
    return _fig_png(fig)


def _pdf_price(closes):
    fig = Figure(figsize=(6.6, 2.1), facecolor=PAPER)
    ax = fig.add_subplot(111)
    ax.set_facecolor(PAPER)
    xs = list(range(len(closes)))
    ax.plot(xs, closes, color=INK, lw=1.4)
    ax.fill_between(xs, closes, min(closes), color=POS, alpha=0.06)
    ax.grid(axis="y", color=LINE, lw=0.6, linestyle=(0, (1, 3)))
    ax.set_axisbelow(True)
    ax.set_xticks([])
    ax.tick_params(length=0, labelsize=7, colors=MUTED)
    for s in ["top", "right", "bottom"]:
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(LINE)
    fig.subplots_adjust(left=0.08, right=0.99, top=0.96, bottom=0.05)
    return _fig_png(fig)


def _pdf_consensus(g):
    order = [("Strong Buy", g.get("strongBuy", 0), "#3D6B52"), ("Buy", g.get("buy", 0), "#4E8B6B"),
             ("Hold", g.get("hold", 0), MUTED), ("Sell", g.get("sell", 0), "#C06A56"),
             ("Strong Sell", g.get("strongSell", 0), NEG)]
    order = [(l, to_float(v) or 0, c) for l, v, c in order if to_float(v)]
    total = sum(v for _, v, _ in order) or 1
    fig = Figure(figsize=(6.6, 0.7), facecolor=PAPER)
    ax = fig.add_subplot(111)
    ax.set_facecolor(PAPER)
    left = 0
    for l, v, c in order:
        w = v / total
        ax.barh(0, w, left=left, color=c, height=0.6)
        if w > 0.06:
            ax.text(left + w / 2, 0, f"{l} {int(v)}", ha="center", va="center", color="white", fontsize=7.5)
        left += w
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, 0.5)
    ax.axis("off")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.1)
    return _fig_png(fig)


def _pdf_styles():
    return {
        "kicker": ParagraphStyle("k", fontName=_bf(), fontSize=7.5, textColor=HexColor(MUTED), leading=10, spaceAfter=2),
        "h2": ParagraphStyle("h2", fontName=_hf(True), fontSize=14, textColor=HexColor(INK), leading=17, spaceAfter=6),
        "body": ParagraphStyle("b", fontName=_bf(), fontSize=8.5, textColor=HexColor(INK), leading=12.5),
        "note": ParagraphStyle("n", fontName=_bf(), fontSize=7.5, textColor=HexColor(MUTED), leading=11, spaceBefore=4),
        "subg": ParagraphStyle("sg", fontName=_bf(True), fontSize=7.5, textColor=HexColor(MUTED), leading=11, spaceBefore=8, spaceAfter=3),
        "lab": ParagraphStyle("l", fontName=_bf(), fontSize=7, textColor=HexColor(MUTED), leading=9),
        "val": ParagraphStyle("v", fontName=_bf(), fontSize=10, textColor=HexColor(INK), leading=13),
        "ai_h": ParagraphStyle("aih", fontName=_bf(True), fontSize=14, textColor=HexColor(INK),
                               leading=17, spaceBefore=10, spaceAfter=4),
        "ai_body": ParagraphStyle("aib", fontName=_bf(), fontSize=12, textColor=HexColor(INK),
                                  leading=16, spaceAfter=4),
    }


def _pdf_section(title, kicker, S):
    return [Spacer(1, 10), Paragraph(kicker.upper(), S["kicker"]),
            HRFlowable(width="100%", thickness=0.6, color=HexColor(LINE), spaceBefore=1, spaceAfter=4),
            Paragraph(title, S["h2"])]


def _pdf_tiles(items, S, cols=3):
    cells = []
    for it in items:
        inner = [Paragraph(it[0].upper(), S["lab"]), Paragraph(it[1], S["val"])]
        if len(it) > 2 and it[2]:
            inner.append(Paragraph(it[2], S["note"]))
        cells.append(inner)
    rows = []
    for i in range(0, len(cells), cols):
        row = cells[i:i + cols]
        while len(row) < cols:
            row.append("")
        rows.append(row)
    usable = 6.5 * _INCH
    t = Table(rows, colWidths=[usable / cols] * cols)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("LINEBELOW", (0, 0), (-1, -1), 0.5, HexColor(LINE))]))
    return t


def _pdf_img(buf, width_in):
    ir = ImageReader(buf)
    iw, ih = ir.getSize()
    w = width_in * _INCH
    buf.seek(0)
    return RLImage(buf, width=w, height=w * ih / iw)


def _pdf_range(a, b):
    """Price range for the PDF. Like money_range but WITHOUT the '$'->'\\$'
    escaping — that escape exists only for Streamlit's LaTeX; in a PDF it would
    print a literal backslash."""
    a, b = to_float(a), to_float(b)
    if a is None or b is None:
        return "N/A"
    return f"${a:,.0f} \u2013 ${b:,.0f}"


def _pdf_escape(text):
    """Escape text used inside ReportLab Paragraphs."""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _pdf_render(symbol, quote, profile, metrics, traj, cash, val, analyst, earn, tech, closes, ai_text, notes,
                quarterly=None, forward=None, benchmark=None, quality=None):
    _pdf_fonts()
    S = _pdf_styles()
    W, H = _LETTER
    margin = 0.75 * _INCH

    def _decor(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(HexColor(PAPER))
        canvas.rect(0, 0, W, H, fill=1, stroke=0)
        canvas.setFont(_bf(), 7)
        canvas.setFillColor(HexColor(MUTED))
        canvas.drawString(margin, 0.5 * _INCH, "Aggregated for personal research \u2014 not investment advice.")
        canvas.drawRightString(W - margin, 0.5 * _INCH, f"{symbol}  \u00b7  page {doc.page}")
        canvas.restoreState()

    story = []
    name = profile.get("name") or quote.get("name") or symbol
    if len(name) > 40:
        name = name[:38] + "\u2026"
    sub = " \u00b7 ".join([x for x in [profile.get("industry"), profile.get("exchange") or quote.get("exchange")] if x])
    chg = to_float(quote.get("change_pct"))
    chg_str = f"{chg:+.2f}%" if chg is not None else ""
    price_color = NEG if (chg is not None and chg < 0) else POS if chg is not None else INK
    left = [Paragraph("STOCK RESEARCH SNAPSHOT", S["kicker"]),
            Paragraph(f"{symbol} \u2014 {name}", ParagraphStyle("tk", fontName=_hf(True), fontSize=18, textColor=HexColor(INK), leading=21)),
            Paragraph(sub, S["note"])]
    right = [Paragraph(money(quote.get("price")), ParagraphStyle("px", fontName=_bf(True), fontSize=16, alignment=TA_RIGHT, textColor=HexColor(INK), leading=19)),
             Paragraph(chg_str, ParagraphStyle("cx", fontName=_bf(), fontSize=9, alignment=TA_RIGHT, textColor=HexColor(price_color), leading=13)),
             Paragraph(f"{big_money(profile.get('market_cap') or quote.get('market_cap'))} mkt cap", ParagraphStyle("mc", fontName=_bf(), fontSize=8, alignment=TA_RIGHT, textColor=HexColor(MUTED), leading=12))]
    htab = Table([[left, right]], colWidths=[4.7 * _INCH, 1.8 * _INCH])
    htab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [htab, Paragraph(f"Generated {_dt.datetime.now():%B %d, %Y}", S["note"]),
              HRFlowable(width="100%", thickness=1.1, color=HexColor(INK), spaceBefore=6, spaceAfter=2)]

    story += _pdf_section("Snapshot", "the essentials", S)
    story.append(_pdf_tiles([("Price", money(quote.get("price")), chg_str),
                             ("Market Cap", big_money(profile.get("market_cap") or quote.get("market_cap"))),
                             ("52-Week Range", _pdf_range(quote.get("week_low"), quote.get("week_high"))),
                             ("Avg Daily Volume", big_count(metrics.get("avg_volume")))], S, cols=4))

    if closes:
        story += _pdf_section("Price", "the trend over time", S)
        story.append(_pdf_img(_pdf_price(closes), 6.5))

    ty, tm = traj["years"], traj["metrics"]
    story += _pdf_section("Business Trajectory", "the shape of the business", S)
    story.append(_pdf_img(_pdf_grid([("Revenue", ty, tm.get("revenue"), "money"),
                                     ("EPS (diluted)", ty, tm.get("eps"), "eps"),
                                     ("Gross Margin", ty, tm.get("gross_margin"), "pct"),
                                     ("Operating Margin", ty, tm.get("op_margin"), "pct"),
                                     ("Net Margin", ty, tm.get("net_margin"), "pct"),
                                     ("Return on Equity", ty, tm.get("roe"), "pct"),
                                     ("Free Cash Flow", ty, tm.get("fcf"), "money"),
                                     ("Total Debt", ty, tm.get("debt"), "money")], ncols=2), 6.5))

    quarterly = quarterly or {"labels": [], "metrics": {}}
    qy, qm = quarterly.get("labels") or [], quarterly.get("metrics") or {}
    if qy and any((qm.get(k) or []) for k in ("revenue", "eps", "gross_margin", "op_margin", "net_margin", "fcf")):
        story += _pdf_section("Recent Quarters", "the latest few quarters up close", S)
        story.append(_pdf_img(_pdf_grid([("Revenue", qy, qm.get("revenue"), "money"),
                                         ("EPS (diluted)", qy, qm.get("eps"), "eps"),
                                         ("Gross Margin", qy, qm.get("gross_margin"), "pct"),
                                         ("Operating Margin", qy, qm.get("op_margin"), "pct"),
                                         ("Net Margin", qy, qm.get("net_margin"), "pct"),
                                         ("Free Cash Flow", qy, qm.get("fcf"), "money")],
                                        ncols=2, cell_h=1.35), 6.5))
        story.append(Paragraph("Quarterly data highlights inflections that annual charts can hide, especially for cyclical companies.", S["note"]))

    cy, cm = cash["years"], cash["metrics"]
    story += _pdf_section("Cash Generation", "does it make real money?", S)
    story.append(_pdf_img(_pdf_grid([("Free Cash Flow", cy, cm.get("fcf"), "money"),
                                     ("FCF Margin", cy, cm.get("fcf_margin"), "pct"),
                                     ("FCF per Share", cy, cm.get("fcf_ps"), "pershare"),
                                     ("FCF Yield", cy, cm.get("fcf_yield"), "pct")], ncols=2, cell_h=1.4), 6.5))

    cur, gro, his = val["current"], val["growth"], val["history"]
    story += _pdf_section("Valuation vs Growth", "is it worth the price?", S)
    story.append(Paragraph("CURRENT VALUATION", S["subg"]))
    story.append(_pdf_tiles([("P/E", num(cur.get("pe"))), ("Forward P/E", num(cur.get("forward_pe"))),
                             ("PEG", num(cur.get("peg"))), ("EV/EBITDA", num(cur.get("ev_ebitda"))),
                             ("P/S", num(cur.get("ps"))), ("FCF Yield", pct(cur.get("fcf_yield")))], S, cols=3))

    forward = forward or {"years": []}
    fy_rows = forward.get("years") or []
    if fy_rows:
        story.append(Paragraph("FORWARD VALUATION", S["subg"]))
        ftiles = []
        for y in fy_rows[:3]:
            fy = y.get("fiscal_year") or "?"
            eps_v, fpe_v, rev_v = to_float(y.get("eps")), to_float(y.get("forward_pe")), to_float(y.get("revenue"))
            note_bits = []
            if fpe_v is not None:
                note_bits.append(f"{fpe_v:,.1f}x fwd P/E")
            if rev_v is not None:
                note_bits.append(f"{big_money(rev_v)} revenue")
            n = to_float(y.get("n_eps")) or to_float(y.get("n_rev"))
            if n is not None:
                note_bits.append(f"{int(n)} analysts")
            ftiles.append((f"FY{fy} est. EPS", money(eps_v), " · ".join(note_bits)))
        story.append(_pdf_tiles(ftiles, S, cols=3))

    story.append(Paragraph("GROWTH CONTEXT (YoY)", S["subg"]))
    story.append(_pdf_tiles([("Revenue", pct(gro.get("revenue"))), ("EPS", pct(gro.get("eps"))),
                             ("Free Cash Flow", pct(gro.get("fcf")))], S, cols=3))
    story.append(Paragraph("HISTORICAL CONTEXT", S["subg"]))

    def _hrow(k, lbl):
        d = his.get(k, {})
        now, med = to_float(d.get("now")), to_float(d.get("median"))
        if med is not None:
            if now is not None and med != 0:
                ratio = now / med
                tag = "trading above" if ratio >= 1.15 else "trading below" if ratio <= 0.85 else "trading near"
                return (f"{lbl} 5-yr median", num(med), f"Now {num(now)} · {tag}")
            return (f"{lbl} 5-yr median", num(med), "Current value unavailable")
        return (f"{lbl} 5-yr median", "N/A", f"Now {num(now)}")

    story.append(_pdf_tiles([_hrow("pe", "P/E"), _hrow("ev", "EV/EBITDA"), _hrow("ps", "P/S")], S, cols=3))

    benchmark = benchmark or None
    if benchmark and benchmark.get("rows"):
        story.append(Paragraph("VERSUS INDUSTRY PEERS", S["subg"]))
        grp = benchmark.get("industry") if benchmark.get("grouping") != "sector" and benchmark.get("industry") else benchmark.get("sector")
        peers = benchmark.get("peers") or []
        if peers:
            peer_bits = " · ".join(f"{p.get('symbol')} {p.get('name')}" for p in peers[:10])
            story.append(Paragraph(_pdf_escape(f"Peer set: {peer_bits}"), S["note"]))
        peer_tiles = []
        for row in benchmark.get("rows", [])[:6]:
            unit = row.get("unit")
            tgt, p25, p75 = row.get("target"), row.get("p25"), row.get("p75")
            if tgt is not None and p25 is not None and p75 is not None:
                if tgt > p75:
                    pos = "above peer range"
                elif tgt < p25:
                    pos = "below peer range"
                else:
                    pos = "within peer range"
            else:
                pos = "company value unavailable"
            peer_range = f"{_fmt_bench(p25, unit)} – {_fmt_bench(p75, unit)}"
            note = f"Median: {_fmt_bench(row.get('median'), unit)} · {int(row.get('n') or 0)} peers · {symbol.upper()} is {pos}"
            peer_tiles.append((row.get("label", "Peer metric"), peer_range, note))
        story.append(_pdf_tiles(peer_tiles, S, cols=3))
        story.append(Paragraph("Peer ranges use the 25th–75th percentile. Median is the middle value, so extreme outliers do not dominate the comparison.", S["note"]))

    quality = quality or {"missing_fields": [], "notes": []}
    qnotes = list(quality.get("notes") or [])
    missing = list(quality.get("missing_fields") or [])
    if qnotes or missing:
        story.append(Paragraph("DATA QUALITY NOTES", S["subg"]))
        if missing:
            story.append(Paragraph(_pdf_escape("Missing fields: " + ", ".join(missing)), S["note"]))
        for n in qnotes[:6]:
            story.append(Paragraph("• " + _pdf_escape(n), S["note"]))

    story += _pdf_section("Analyst Expectations", "what the market already expects", S)
    story.append(Paragraph("CONSENSUS", S["subg"]))
    story.append(_pdf_img(_pdf_consensus(analyst["grades"]), 6.5))
    tg = analyst["target"]
    story.append(Paragraph("PRICE TARGET", S["subg"]))
    story.append(_pdf_tiles([("Low", money(tg.get("low"))), ("Average", money(tg.get("avg"))),
                             ("High", money(tg.get("high"))), ("Implied Upside", pct(tg.get("upside")))], S, cols=4))
    fw = analyst["forward"]
    fy2 = str(fw.get("year"))[2:] if fw.get("year") else "?"
    story.append(_pdf_tiles([(f"Est. Revenue (FY{fy2})", big_money(fw.get("revenue"))),
                             (f"Est. EPS (FY{fy2})", money(fw.get("eps")))], S, cols=4))

    story += _pdf_section("Earnings & Filings", "what's coming, what just happened", S)
    nxt, last = earn.get("next") or {}, earn.get("last") or {}
    story.append(_pdf_tiles([("Next Earnings", str(nxt.get("date") or "N/A")),
                             ("Days Away", num(nxt.get("days"), 0)), ("EPS Estimate", money(nxt.get("eps_est")))], S, cols=3))
    if last:
        def _surp(x):
            x = to_float(x)
            return "" if x is None else (f"beat {x:.0f}%" if x >= 0 else f"miss {abs(x):.0f}%")
        story.append(Paragraph("LAST EARNINGS \u2014 ACTUAL VS ESTIMATE", S["subg"]))
        story.append(_pdf_tiles([("EPS", money(last.get("eps_actual")), f"est. {money(last.get('eps_est'))} \u00b7 {_surp(last.get('eps_surprise'))}"),
                                 ("Revenue", big_money(last.get("rev_actual")), f"est. {big_money(last.get('rev_est'))} \u00b7 {_surp(last.get('rev_surprise'))}")], S, cols=2))
    cik = earn.get("cik")
    if cik:
        b = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&owner=include&count=40&type="
        story.append(Paragraph(f'SEC filings (EDGAR): <a href="{b}10-K">10-K</a> \u00b7 <a href="{b}10-Q">10-Q</a> \u00b7 <a href="{b}8-K">8-K</a>', S["body"]))

    story += _pdf_section("Price Context", "is the price stretched or reasonable?", S)

    def _ab(x):
        return "Above" if x else "Below" if x is not None else "N/A"

    vr = to_float(tech.get("vol_ratio"))
    story.append(_pdf_tiles([("vs 50-day MA", _ab(tech.get("above_50")), money(tech.get("ma50"))),
                             ("vs 200-day MA", _ab(tech.get("above_200")), money(tech.get("ma200"))),
                             ("RSI (14)", num(tech.get("rsi"), 0)),
                             ("From 52-wk High", pct(tech.get("dist_high"))),
                             ("From 52-wk Low", pct(tech.get("dist_low"))),
                             ("Volume vs Avg", f"{vr:,.2f}x" if vr is not None else "N/A")], S, cols=3))

    story += _pdf_section("Financial Health & Risk", "how it's doing \u00b7 what could move it", S)
    story.append(_pdf_tiles([("Net Margin", pct(metrics.get("net_margin_pct"))),
                             ("Gross Margin", pct(metrics.get("gross_margin_pct"))),
                             ("Return on Equity", pct(metrics.get("roe_pct"))),
                             ("Debt / Equity", num(metrics.get("debt_to_equity"))),
                             ("Beta", num(metrics.get("beta") or profile.get("beta"))),
                             ("Prev Close", money(quote.get("prev_close")))], S, cols=3))

    if ai_text:
        story += _pdf_section("AI Analysis", "the whole picture, in plain English", S)
        import re as _re

        def _mdclean(s):
            s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            s = _re.sub(r"\*\*(.+?)\*\*", r"\1", s)   # bold markers
            s = _re.sub(r"__(.+?)__", r"\1", s)
            s = _re.sub(r"\*(.+?)\*", r"\1", s)        # italic markers (no italics)
            return s.strip()

        for para in str(ai_text).split("\n"):
            p = para.strip()
            if not p:
                continue
            if p.startswith("#"):
                story.append(Paragraph(_mdclean(p.lstrip("# ").strip()), S["ai_h"]))
            else:
                story.append(Paragraph(_mdclean(p), S["ai_body"]))
                story.append(Spacer(1, 3))
        story.append(Paragraph("AI-generated and may contain errors; verify against primary sources. Not a recommendation.", S["note"]))

    if notes and notes.strip():
        story += _pdf_section("Your Notes", "your call", S)
        for para in notes.split("\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), S["body"]))
                story.append(Spacer(1, 3))

    buf = _io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=_LETTER, leftMargin=margin, rightMargin=margin,
                            topMargin=margin, bottomMargin=0.75 * _INCH, title=f"{symbol} research snapshot")
    doc.build(story, onFirstPage=_decor, onLaterPages=_decor)
    buf.seek(0)
    return buf.getvalue()


def build_pdf_report(symbol):
    quote = get_quote(symbol)
    profile = get_company_profile(symbol)
    metrics = get_key_metrics(symbol)
    traj = get_trajectory_annual(symbol)
    cash = get_cash_annual(symbol)
    val = get_valuation_growth(symbol)
    analyst = get_analyst(symbol)
    earn = get_earnings_context(symbol)
    tech = get_technicals(symbol)
    quarterly = get_quarterly_trend(symbol)
    forward = get_forward_estimates(symbol, n=3)
    benchmark = get_industry_benchmark(symbol)
    quality = compute_quality_flags(symbol)
    closes = None
    try:
        df = get_price_history(symbol)
        if df is not None and not df.empty and "close" in df:
            c = pd.to_numeric(df["close"], errors="coerce").dropna().tolist()
            if len(c) >= 2:
                closes = c
    except Exception:
        closes = None
    ai_text = st.session_state.get("ai_analysis", {}).get(symbol)
    notes = st.session_state.get(f"notes_{symbol}", "")
    return _pdf_render(symbol, quote, profile, metrics, traj, cash, val, analyst, earn, tech, closes, ai_text, notes,
                       quarterly=quarterly, forward=forward, benchmark=benchmark, quality=quality)


def render_pdf_fab(symbol):
    """Floating 'Generate / Download PDF' control, pinned on-screen so it's
    reachable from any tab (positioned via CSS in _STOCK_PAGE_CSS). Sits
    bottom-left to steer clear of Streamlit Cloud's bottom-right 'Manage app'
    badge. If reportlab/matplotlib aren't installed yet, nothing floats — the
    Notes tab explains why."""
    if not _PDF_OK:
        return
    cache = st.session_state.setdefault("pdf_cache", {})
    if st.button("\U0001F4C4 PDF", key="pdf_fab_gen",
                 help="Build a PDF of this stock — every tab, charts included. Generate the AI "
                      "analysis and write your notes first if you want them in the report."):
        with st.spinner("Building your report…"):
            try:
                cache[symbol] = build_pdf_report(symbol)
            except Exception as e:  # noqa: BLE001
                cache.pop(symbol, None)
                st.error(f"Couldn't build the PDF: {e}")
    if cache.get(symbol):
        st.download_button("\u2B07 Save", data=cache[symbol],
                           file_name=f"{symbol}_research_{_dt.date.today():%Y%m%d}.pdf",
                           mime="application/pdf", key="pdf_fab_dl")



# ===========================================================================
# TOP STOCKS TO EXPLORE — a daily "what should I look into" board.
# Scans a hardcoded quality universe (S&P 500) using ONLY get_price_history,
# confirms movement across multiple days + volume (so one-day spikes and
# penny-stock pops don't dominate), scores a Focus Priority, and shows the
# top 20. Cached once per day; the first load of the day takes ~1-2 minutes
# while it scans ~500 names, then it's instant for the rest of the day.
# ===========================================================================

# S&P 500 constituents — snapshot as of 2026-07-02. Index membership drifts a
# few times a year, so refresh this list periodically. Unknown/delisted tickers
# simply return no history and are skipped, so a slightly stale list degrades
# quietly rather than breaking the scan.
SP500 = (
    "MMM", "AOS", "ABT", "ABBV", "ACN", "ADBE", "AMD", "AES", "AFL", "A", "APD", "ABNB", "AKAM",
    "ALB", "ARE", "ALGN", "ALLE", "LNT", "ALL", "GOOGL", "GOOG", "MO", "AMZN", "AMCR", "AEE", "AEP",
    "AXP", "AIG", "AMT", "AWK", "AMP", "AME", "AMGN", "APH", "ADI", "ANSS", "AON", "APA", "AAPL",
    "AMAT", "APTV", "ACGL", "ADM", "ANET", "AJG", "AIZ", "T", "ATO", "ADSK", "ADP", "AZO", "AVB",
    "AVY", "AXON", "BKR", "BALL", "BAC", "BAX", "BDX", "BRK.B", "BBY", "BIO", "TECH", "BIIB", "BLK",
    "BX", "BK", "BA", "BKNG", "BWA", "BSX", "BMY", "AVGO", "BR", "BRO", "BF.B", "BLDR", "BG", "CDNS",
    "CZR", "CPT", "CPB", "COF", "CAH", "KMX", "CCL", "CARR", "CTLT", "CAT", "CBOE", "CBRE", "CDW",
    "CE", "COR", "CNC", "CNP", "CF", "CHRW", "CRL", "SCHW", "CHTR", "CVX", "CMG", "CB", "CHD", "CI",
    "CINF", "CTAS", "CSCO", "C", "CFG", "CLX", "CME", "CMS", "KO", "CTSH", "CL", "CMCSA", "CMA",
    "CAG", "COP", "ED", "STZ", "CEG", "COO", "CPRT", "GLW", "CPAY", "CTVA", "CSGP", "COST", "CTRA",
    "CCI", "CSX", "CMI", "CVS", "DHR", "DRI", "DVA", "DAY", "DECK", "DE", "DAL", "DVN", "DXCM", "FANG",
    "DLR", "DFS", "DG", "DLTR", "D", "DPZ", "DOV", "DOW", "DHI", "DTE", "DUK", "DD", "EMN", "ETN",
    "EBAY", "ECL", "EIX", "EW", "EA", "ELV", "EMR", "ENPH", "ETR", "EOG", "EPAM", "EQT", "EFX", "EQIX",
    "EQR", "ESS", "EL", "EG", "EVRG", "ES", "EXC", "EXPE", "EXPD", "EXR", "XOM", "FFIV", "FDS", "FICO",
    "FAST", "FRT", "FDX", "FIS", "FITB", "FSLR", "FE", "FI", "FMC", "F", "FTNT", "FTV", "FOXA", "FOX",
    "BEN", "FCX", "GRMN", "IT", "GEHC", "GEV", "GEN", "GNRC", "GD", "GE", "GIS", "GM", "GPC", "GILD",
    "GPN", "GL", "GDDY", "GS", "HAL", "HIG", "HAS", "HCA", "DOC", "HSIC", "HSY", "HES", "HPE", "HLT",
    "HOLX", "HD", "HON", "HRL", "HST", "HWM", "HPQ", "HUBB", "HUM", "HBAN", "HII", "IBM", "IEX", "IDXX",
    "ITW", "ILMN", "INCY", "IR", "PODD", "INTC", "ICE", "IFF", "IP", "IPG", "INTU", "ISRG", "IVZ",
    "INVH", "IQV", "IRM", "JBHT", "JBL", "JKHY", "J", "JNJ", "JCI", "JPM", "JNPR", "K", "KVUE", "KDP",
    "KEY", "KEYS", "KMB", "KIM", "KMI", "KLAC", "KHC", "KR", "LHX", "LH", "LRCX", "LW", "LVS", "LDOS",
    "LEN", "LII", "LLY", "LIN", "LYV", "LKQ", "LMT", "L", "LOW", "LULU", "LYB", "MTB", "MPC", "MKTX",
    "MAR", "MMC", "MLM", "MAS", "MA", "MTCH", "MKC", "MCD", "MCK", "MDT", "MRK", "META", "MET", "MTD",
    "MGM", "MCHP", "MU", "MSFT", "MAA", "MRNA", "MHK", "MOH", "TAP", "MDLZ", "MPWR", "MNST", "MCO",
    "MS", "MOS", "MSI", "MSCI", "NDAQ", "NTAP", "NFLX", "NEM", "NWSA", "NWS", "NEE", "NKE", "NI", "NDSN",
    "NSC", "NTRS", "NOC", "NCLH", "NRG", "NUE", "NVDA", "NVR", "NXPI", "ORLY", "OXY", "ODFL", "OMC",
    "ON", "OKE", "ORCL", "OTIS", "PCAR", "PKG", "PLTR", "PANW", "PARA", "PH", "PAYX", "PAYC", "PYPL",
    "PNR", "PEP", "PFE", "PCG", "PM", "PSX", "PNW", "PNC", "POOL", "PPG", "PPL", "PFG", "PG", "PGR",
    "PLD", "PRU", "PEG", "PTC", "PSA", "PHM", "QRVO", "PWR", "QCOM", "DGX", "RL", "RJF", "RTX", "O",
    "REG", "REGN", "RF", "RSG", "RMD", "RVTY", "ROK", "ROL", "ROP", "ROST", "RCL", "SPGI", "CRM", "SBAC",
    "SLB", "STX", "SRE", "NOW", "SHW", "SPG", "SWKS", "SJM", "SW", "SNA", "SOLV", "SO", "LUV", "SWK",
    "SBUX", "STT", "STLD", "STE", "SYK", "SMCI", "SYF", "SNPS", "SYY", "TMUS", "TROW", "TTWO", "TPR",
    "TRGP", "TGT", "TEL", "TDY", "TFX", "TER", "TSLA", "TXN", "TPL", "TXT", "TMO", "TJX", "TSCO", "TT",
    "TDG", "TRV", "TRMB", "TFC", "TYL", "TSN", "USB", "UBER", "UDR", "ULTA", "UNP", "UAL", "UPS", "URI",
    "UNH", "UHS", "VLO", "VTR", "VLTO", "VRSN", "VRSK", "VZ", "VRTX", "VTRS", "VICI", "V", "VST", "VMC",
    "WRB", "GWW", "WAB", "WBA", "WMT", "DIS", "WBD", "WM", "WAT", "WEC", "WFC", "WELL", "WST", "WDC",
    "WY", "WMB", "WTW", "WYNN", "XEL", "XYL", "YUM", "ZBRA", "ZBH", "ZTS",
)

# A small watchlist that earns a Focus Priority bonus — names you want surfaced
# even on a quieter day. Tune freely (these are just examples).
WATCHLIST = {"NVDA", "MU", "AMD", "AVGO", "TSM", "ASML", "SMCI", "PLTR", "META", "AMZN", "MSFT"}

_TREND_LABEL = {
    "Confirmed multi-day trend": ("CONFIRMED TREND", "#2F6B4F"),
    "Quiet steady trend": ("QUIET TREND", "#3D6B52"),
    "Possible reversal": ("POSSIBLE REVERSAL", "#B07A2E"),
    "Fresh move — needs confirmation": ("FRESH MOVE", "#7A7970"),
    "Noise / low priority": ("NOISE", "#A0A099"),
}


def _pctret(a, b):
    return ((a - b) / b * 100.0) if (a is not None and b not in (None, 0)) else None


def _scan_metrics(df):
    """From a price/volume history frame, compute the movement metrics used to
    classify and score. Returns None if there isn't enough history."""
    if df is None or df.empty or "close" not in df.columns:
        return None
    closes = pd.to_numeric(df["close"], errors="coerce").dropna().tolist()
    if len(closes) < 21:
        return None
    last = closes[-1]

    def ret(n):
        return _pctret(last, closes[-1 - n]) if len(closes) > n else None

    r1, r3, r5, r20 = ret(1), ret(3), ret(5), ret(20)
    # Move over the 4 days ending YESTERDAY — i.e. the trend that was in place
    # before today. This is what separates a sustained move (prior move already
    # underway) from a one-day spike (flat before, jumped today).
    r_prior = _pctret(closes[-2], closes[-6]) if len(closes) >= 6 else None
    ma50 = sum(closes[-50:]) / min(50, len(closes))
    vs_ma50 = _pctret(last, ma50)
    win = closes[-60:]
    hi, lo = max(win), min(win)
    dist_high = _pctret(last, hi)   # <= 0: how far below the recent high
    dist_low = _pctret(last, lo)    # >= 0: how far above the recent low
    vol_ratio = None
    if "volume" in df.columns:
        vols = [x for x in pd.to_numeric(df["volume"], errors="coerce").tolist() if x is not None]
        if len(vols) >= 21:
            avg20 = sum(vols[-21:-1]) / 20
            vol_ratio = (vols[-1] / avg20) if avg20 else None
    return dict(price=last, r1=r1, r3=r3, r5=r5, r20=r20, r_prior=r_prior, vs_ma50=vs_ma50,
                dist_high=dist_high, dist_low=dist_low, vol_ratio=vol_ratio)


def _sgn(x):
    return 0 if not x else (1 if x > 0 else -1)


def _classify(m):
    r3, r5, r20 = m["r3"], m["r5"], m["r20"]
    r1, rp = m["r1"], m["r_prior"]
    vr = m["vol_ratio"] or 1.0
    vs = m["vs_ma50"] or 0.0
    a1, a3, a20, ap = abs(r1 or 0), abs(r3 or 0), abs(r20 or 0), abs(rp or 0)
    up = (r20 or 0) > 0
    # Fresh move: a real move TODAY that the prior days don't back up — either
    # there was no prior trend (ap small) or today dominates the whole 20-day
    # move. This is what catches one-day spikes.
    if a1 >= 4 and (ap < 2 or a1 >= 0.6 * a20):
        return "Fresh move — needs confirmation"
    # Confirmed multi-day trend: a strong 20-day move that is SPREAD across days
    # (today is only a fraction of it), with the week agreeing on direction and
    # price on the right side of its 50-day average.
    if a20 >= 6 and a1 < 0.6 * a20 and _sgn(r5) == _sgn(r20) and (
            (up and vs > 0) or ((not up) and vs < 0)):
        return "Confirmed multi-day trend"
    # Possible reversal: an established 20-day trend with the last few days turning.
    if a20 >= 5 and a3 >= 3 and _sgn(r3) != _sgn(r20):
        return "Possible reversal"
    # Quiet steady trend: a milder, calm, consistent drift on normal volume.
    if a20 >= 3 and a1 < 2 and vr < 1.5 and _sgn(r5) == _sgn(r20):
        return "Quiet steady trend"
    return "Noise / low priority"


def _clampf(x, lo, hi):
    return max(lo, min(hi, x))


def _focus_score(m, trend, symbol):
    r1, r20 = m["r1"] or 0, m["r20"] or 0
    rp = m["r_prior"] or 0
    vr = m["vol_ratio"] or 1.0
    a1, ap, a20 = abs(r1), abs(rp), abs(r20)
    score = 0.0
    # confirmation rewards movement ALREADY underway before today (a sustained
    # trend), not today's pop alone.
    score += _clampf(ap, 0, 12) * 2.0     # multi-day confirmation (core) -> up to 24
    score += _clampf(a20, 0, 30) * 1.0    # 20-day trend context          -> up to 30
    score += _clampf(a1, 0, 8) * 1.0      # 1-day move (modest)           -> up to 8
    if vr >= 2.0:                         # volume confirmation
        score += 12
    elif vr >= 1.5:
        score += 8
    elif vr >= 1.2:
        score += 4
    score += {"Confirmed multi-day trend": 15, "Quiet steady trend": 10,   # trend quality
              "Possible reversal": 6, "Fresh move — needs confirmation": 4,
              "Noise / low priority": 0}[trend]
    if symbol in WATCHLIST:               # watchlist bonus
        score += 8
    if a1 >= 5 and ap < 2:                # one-day-spike penalty (no prior trend)
        score -= 15
    return max(0, round(score))


def _why_explore(m, trend):
    r1, r3, r5, r20, vr = m["r1"], m["r3"], m["r5"], m["r20"], m["vol_ratio"]
    vtxt = f" on {vr:.1f}\u00d7 its usual volume" if (vr and vr >= 1.3) else ""

    def s(x):
        return f"{x:+.1f}%" if x is not None else "n/a"

    if trend == "Confirmed multi-day trend":
        return (f"{s(r20)} over 20 days and still moving ({s(r5)} this week){vtxt} — a sustained "
                "trend, not a one-day pop.")
    if trend == "Possible reversal":
        return (f"{s(r20)} over 20 days but turning lately ({s(r3)} over 3 days) — a possible turn "
                "worth a closer look.")
    if trend == "Fresh move — needs confirmation":
        return (f"Moved {s(r1)} today{vtxt}, but the week ({s(r5)}) hasn't confirmed it yet — watch "
                "whether it holds.")
    if trend == "Quiet steady trend":
        return (f"Grinding {s(r20)} over 20 days in small, steady steps — the kind of trend that "
                "rarely shows up on a top-gainers list.")
    return f"{s(r1)} today, {s(r5)} this week — mixed signals, lower priority."


@st.cache_data(ttl=21600, show_spinner=False)   # ~6h; keyed on the date -> recomputes daily
def _run_daily_scan(date_str, universe):
    import time as _t
    rows = []
    for sym in universe:
        try:
            df = get_price_history(sym, start_days=130)
        except Exception:  # noqa: BLE001
            df = None
        m = _scan_metrics(df)
        if not m:
            continue
        trend = _classify(m)
        rows.append({"symbol": sym, "trend": trend,
                     "score": _focus_score(m, trend, sym), "m": m})
        _t.sleep(0.03)   # gentle throttle to stay under the 300/min Starter cap
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows, len(rows)


def _delta_html(v, label):
    if v is None:
        return (f"<div style='font-size:.62rem;letter-spacing:.09em;color:{MUTED};"
                f"text-transform:uppercase'>{label}</div><div style='color:{MUTED}'>\u2014</div>")
    color = POS if v >= 0 else NEG
    return (f"<div style='font-size:.62rem;letter-spacing:.09em;color:{MUTED};"
            f"text-transform:uppercase'>{label}</div>"
            f"<div style='color:{color};font-weight:600;font-size:1.02rem'>{v:+.1f}%</div>")


def render_top_stocks():
    import datetime as _dt
    section("Top Stocks to Explore", "your morning starting point")
    st.caption("A daily scan of the S&P 500 for stocks with **confirmed multi-day movement** — not "
               "one-day spikes or penny-stock noise. Ranked by a Focus Priority score that rewards "
               "moves that hold up across days and come with real volume. The first load each day "
               "scans ~500 names and takes a minute or two; after that it's cached and instant.")
    today = _dt.date.today()
    with st.spinner("Scanning the S&P 500 for today's trends\u2026  (first load of the day only)"):
        ranked, scanned = _run_daily_scan(today.isoformat(), SP500)

    if not ranked:
        st.info("Nothing to show yet. If this is the very first load it may still be warming up, or "
                "price history is briefly unavailable — try again in a moment.")
        return

    umap = get_universe_map()
    for r in ranked:
        r["sector"] = umap.get(r["symbol"], {}).get("sector") or "Other"
    secs = ["All sectors"] + sorted({r["sector"] for r in ranked
                                     if r["sector"] and r["sector"] != "Other"})
    fcol = st.columns([1.35, 1.0])
    with fcol[0]:
        direction = st.radio("Direction", ["Rising", "Falling", "Both"], horizontal=True,
                             index=0, label_visibility="collapsed", key="top_direction")
    with fcol[1]:
        sel_sector = st.selectbox("Sector", secs, key="top_sector", label_visibility="collapsed")
    if direction == "Rising":
        pool = [r for r in ranked if (r["m"].get("r20") or 0) > 0]
    elif direction == "Falling":
        pool = [r for r in ranked if (r["m"].get("r20") or 0) < 0]
    else:
        pool = ranked
    if sel_sector != "All sectors":
        pool = [r for r in pool if r["sector"] == sel_sector]
    top = pool[:20]
    for r in top:      # company name + reason only for the 20 actually shown (cheap, cached)
        if "name" not in r:
            r["name"] = (get_company_profile(r["symbol"]).get("name") or r["symbol"])
            r["why"] = _why_explore(r["m"], r["trend"])

    if not top:
        st.caption(f"As of {today:%B %-d, %Y} \u00b7 scanned {scanned} names \u00b7 nothing matched "
                   "those filters today.")
        return

    dtxt = {"Rising": "rising", "Falling": "falling", "Both": "moving"}[direction]
    sfx = "" if sel_sector == "All sectors" else f" in {sel_sector}"
    st.caption(f"As of {today:%B %-d, %Y} \u00b7 scanned {scanned} names \u00b7 showing the top "
               f"{len(top)} {dtxt}{sfx} by Focus Priority.")
    st.markdown(f"<hr style='border:none;border-top:1px solid {LINE};margin:.4rem 0 .8rem'>",
                unsafe_allow_html=True)

    for i, r in enumerate(top, 1):
        m = r["m"]
        c = st.columns([3.4, 1.15, 1.15, 1.15, 1.0, 0.95])
        with c[0]:
            _px = r["m"].get("price")
            _pxs = (f" <span style='color:{MUTED};font-weight:400;font-size:.88rem'>"
                    f"${_px:,.2f}</span>") if _px is not None else ""
            st.markdown(f"<div style='font-weight:600;font-size:1.02rem'>{i}. {r['symbol']}{_pxs}</div>"
                        f"<div style='color:{MUTED};font-size:.8rem'>{r['name']}</div>",
                        unsafe_allow_html=True)
        with c[1]:
            st.markdown(_delta_html(m["r1"], "Today"), unsafe_allow_html=True)
        with c[2]:
            st.markdown(_delta_html(m["r5"], "5D"), unsafe_allow_html=True)
        with c[3]:
            st.markdown(_delta_html(m["r20"], "20D"), unsafe_allow_html=True)
        with c[4]:
            vr = m["vol_ratio"]
            vtxt = f"{vr:.1f}\u00d7" if vr else "\u2014"
            vcol = POS if (vr and vr >= 1.3) else MUTED
            st.markdown(f"<div style='font-size:.62rem;letter-spacing:.09em;color:{MUTED};"
                        f"text-transform:uppercase'>Vol</div>"
                        f"<div style='color:{vcol};font-weight:600'>{vtxt}</div>",
                        unsafe_allow_html=True)
        with c[5]:
            st.button("View \u2192", key=f"top_{r['symbol']}", use_container_width=True,
                      on_click=_view_stock, args=(r["symbol"],))

        label, lcolor = _TREND_LABEL.get(r["trend"], (r["trend"].upper(), MUTED))
        b = st.columns([5.0, 1.0])
        with b[0]:
            st.markdown(
                f"<span style='font-size:.64rem;letter-spacing:.1em;font-weight:600;color:{lcolor};"
                f"text-transform:uppercase'>{label}</span>"
                f"<span style='color:{MUTED};font-size:.86rem'> \u00b7 {r['why']}</span>",
                unsafe_allow_html=True)
        with b[1]:
            st.markdown(
                f"<div style='text-align:right'><span style='font-size:.6rem;letter-spacing:.09em;"
                f"color:{MUTED};text-transform:uppercase'>Focus</span><br>"
                f"<span style='font-weight:700;font-size:1.1rem;color:{INK}'>{r['score']}</span></div>",
                unsafe_allow_html=True)
        st.markdown(f"<hr style='border:none;border-top:1px solid {LINE};margin:.55rem 0'>",
                    unsafe_allow_html=True)

    st.caption("Focus Priority weighs multi-day confirmation, 20-day trend, volume, and trend "
               "quality, with a penalty for one-day spikes. It's a starting point for research, not "
               "a signal to trade \u2014 open any name to dig into the fundamentals and decide for "
               "yourself.")



# ===========================================================================
# SECTOR MAP + INDUSTRY BENCHMARKS
# One company-screener call (cached ~half a day) yields sector, industry, and
# market cap for the whole US large/mid-cap universe. That single map powers two
# things: the per-tab SECTOR filters, and the peer groups behind the industry
# benchmark on each stock page (automated comparable-company analysis — peers
# picked by industry + similar size, compared on the median with a 25th-75th
# percentile range).
# ===========================================================================

@st.cache_data(ttl=43200, show_spinner=False)   # ~12h
def get_universe_map():
    """{SYMBOL: {sector, industry, market_cap, name}} for US names above ~$2B,
    from one screener call. Empty dict on failure, so dependent features quietly
    no-op rather than break."""
    rows = _fmp_statement("company-screener?country=US&isEtf=false&isFund=false"
                          "&isActivelyTrading=true&marketCapMoreThan=2000000000&limit=3000")
    out = {}
    for r in rows or []:
        sym = (r.get("symbol") or "").upper()
        if not sym:
            continue
        out[sym] = {"sector": (r.get("sector") or "").strip(),
                    "industry": (r.get("industry") or "").strip(),
                    "market_cap": to_float(r.get("marketCap")),
                    "name": r.get("companyName") or sym}
    return out


def sector_options(symbols):
    """Sorted list of sectors present among the given symbols, for a filter."""
    umap = get_universe_map()
    secs = {umap.get(s.upper(), {}).get("sector", "") for s in symbols}
    return sorted(x for x in secs if x)


def _peer_snapshot(sym):
    """One ratios-ttm call -> the comparison metrics for a peer, on the same
    scale the rest of the app uses (margins/ROE as percentages)."""
    rt = _fmp_first(f"ratios-ttm?symbol={sym.upper()}")

    def as_pct(x):
        f = to_float(x)
        return f * 100 if f is not None else None

    return {
        "pe": to_float(pick(rt, "priceToEarningsRatioTTM")),
        "ev_ebitda": to_float(pick(rt, "enterpriseValueMultipleTTM", "evToEBITDATTM")),
        "ps": to_float(pick(rt, "priceToSalesRatioTTM")),
        "net_margin": as_pct(pick(rt, "netProfitMarginTTM", "bottomLineProfitMarginTTM")),
        "gross_margin": as_pct(pick(rt, "grossProfitMarginTTM")),
        "roe": as_pct(pick(rt, "returnOnEquityTTM")),
    }


def _pctile(xs_sorted, q):
    if not xs_sorted:
        return None
    if len(xs_sorted) == 1:
        return xs_sorted[0]
    pos = (q / 100.0) * (len(xs_sorted) - 1)
    lo = int(pos)
    frac = pos - lo
    if lo + 1 < len(xs_sorted):
        return xs_sorted[lo] + frac * (xs_sorted[lo + 1] - xs_sorted[lo])
    return xs_sorted[lo]


# (key, label, unit, higher_is_stronger). Valuation multiples use "x"; margins/ROE "%".
BENCH_METRICS = [
    ("pe", "P/E (TTM)", "x", False),
    ("ev_ebitda", "EV / EBITDA", "x", False),
    ("ps", "P / Sales", "x", False),
    ("net_margin", "Net margin", "%", True),
    ("gross_margin", "Gross margin", "%", True),
    ("roe", "ROE", "%", True),
]


@st.cache_data(ttl=43200, show_spinner=False)   # ~12h per stock
def get_industry_benchmark(symbol, max_peers=10):
    """Automated comps: peers = same-industry names of similar market cap (fall
    back to sector if an industry is too thin), compared on the median + 25th-75th
    percentile range. Returns None if we can't assemble a usable peer set."""
    umap = get_universe_map()
    sym = symbol.upper()
    me = umap.get(sym) or {}
    industry, sector, cap = me.get("industry", ""), me.get("sector", ""), me.get("market_cap")
    if not (industry or sector):          # not in the screener map -> try the profile
        prof = get_company_profile(sym)
        sector = sector or (prof.get("sector") or "")
        industry = industry or (prof.get("industry") or "")
        cap = cap or prof.get("market_cap")

    def band(cands):
        if not cap:
            return cands
        lo, hi = cap * 0.2, cap * 5.0
        b = [s for s in cands
             if umap[s].get("market_cap") and lo <= umap[s]["market_cap"] <= hi]
        return b if len(b) >= 5 else cands   # keep the size band only if it leaves enough

    grouping = "industry"
    peers = band([s for s, d in umap.items()
                  if s != sym and industry and d.get("industry") == industry])
    if len(peers) < 5 and sector:
        grouping = "sector" if len(peers) < 2 else "industry+sector"
        speers = band([s for s, d in umap.items()
                       if s != sym and d.get("sector") == sector])
        peers = list(dict.fromkeys(peers + speers))
    if not peers:
        return None
    if cap:                               # nearest in size first, then cap the count
        peers.sort(key=lambda s: abs((umap[s].get("market_cap") or cap) - cap))
    peers = peers[:max_peers]

    tgt = _peer_snapshot(sym)
    snaps = [_peer_snapshot(p) for p in peers]
    rows = []
    for key, label, unit, higher in BENCH_METRICS:
        pos_only = (unit == "x")          # drop negative/zero multiples (loss-makers)
        xs = sorted(v for v in (s.get(key) for s in snaps)
                    if v is not None and (v > 0 if pos_only else True))
        med = _median(xs, positive_only=False)
        if med is None or len(xs) < 5:    # need enough real data points for a reliable peer range
            continue
        rows.append({"key": key, "label": label, "unit": unit, "higher": higher,
                     "target": tgt.get(key), "median": med,
                     "p25": _pctile(xs, 25), "p75": _pctile(xs, 75), "n": len(xs)})
    if not rows:
        return None
    return {"industry": industry, "sector": sector, "grouping": grouping,
            "n_peers": len(peers),
            "peers": [{"symbol": p, "name": (umap.get(p, {}).get("name") or p)} for p in peers],
            "rows": rows}


def _fmt_bench(v, unit):
    if v is None:
        return "\u2014"
    return f"{v:,.1f}\u00d7" if unit == "x" else f"{v:,.1f}%"


def _short_name(n):
    for suf in (", Incorporated", " Incorporated", ", Inc.", " Inc.", " Corporation",
                " Corp.", ", Ltd.", " Ltd.", " Company", " plc", " N.V.", " S.A.", " Co."):
        if n.endswith(suf):
            return n[:-len(suf)]
    return n


def render_industry_benchmark(symbol):
    b = get_industry_benchmark(symbol)
    if not b:
        st.caption("Not enough same-industry peers of similar size to build a benchmark for this one.")
        return
    grp = b["industry"] if (b["grouping"] != "sector" and b["industry"]) else b["sector"]
    _subgroup("Versus Industry Peers")
    st.caption(f"Where {symbol.upper()} sits against **{b['n_peers']} {grp or 'sector'} peers** of "
               "similar size — the peer median and 25th\u201375th percentile range sit beneath each "
               "metric. Context for research, not a verdict: peers share an industry but not always a "
               "business model, and a whole sector can run rich or cheap at once.")

    # the peer set — name & ticker
    peer_bits = " \u00b7 ".join(
        f"<b>{p['symbol']}</b> <span style='color:{MUTED}'>{_short_name(p['name'])}</span>"
        for p in b["peers"])
    st.markdown(
        f"<div style='font-size:.83rem;margin:.15rem 0 .8rem;line-height:1.7'>"
        f"<span style='letter-spacing:.09em;text-transform:uppercase;font-size:.6rem;"
        f"color:{MUTED}'>Peer set</span>&nbsp;&nbsp;{peer_bits}</div>",
        unsafe_allow_html=True)

    rows = b["rows"]
    for i in range(0, len(rows), 3):
        cols = st.columns(3)
        for col, row in zip(cols, rows[i:i + 3]):
            unit = row["unit"]
            tgt, p25, p75 = row["target"], row["p25"], row["p75"]

            if tgt is not None and p25 is not None and p75 is not None:
                if tgt > p75:
                    pos, pcol = "above peer range", (POS if row["higher"] else WARN)
                elif tgt < p25:
                    pos, pcol = "below peer range", (WARN if row["higher"] else POS)
                else:
                    pos, pcol = "within peer range", MUTED
            else:
                pos, pcol = "company value unavailable", MUTED

            peer_range = f"{_fmt_bench(p25, unit)} – {_fmt_bench(p75, unit)}"
            postxt = f"<span style='color:{pcol};font-weight:600'>{pos}</span>"

            with col:
                # Main value = peer 25th–75th percentile range. We don't repeat the
                # company's own value here because it is shown in Current Valuation.
                st.metric(row["label"], peer_range)
                st.markdown(
                    f"<div style='color:{MUTED};font-size:.79rem;margin-top:-.7rem;line-height:1.5'>"
                    f"Median: <b>{_fmt_bench(row['median'], unit)}</b> · {row['n']} peers<br>"
                    f"{symbol.upper()} is {postxt}</div>",
                    unsafe_allow_html=True)
        st.markdown(f"<hr style='border:none;border-top:1px solid {LINE};margin:.5rem 0 .7rem'>",
                    unsafe_allow_html=True)



# ===========================================================================
# GUIDE ME  —  a guided research journey (toggle alternative to the metric tabs)
# Walks the stock in the order a teacher would: what changed -> is the business
# improving -> does it make cash -> is the price fair -> what the market expects
# -> risk & timing. Every step shows the number, then explains it in plain
# English: the facts, what the pattern usually means (both ways), and what to
# verify next. It never issues a buy/sell verdict. An opt-in checkbox swaps in
# an AI-written version; a copy-prompt button exports all the numbers so you can
# run your own AI report for free.
# ===========================================================================

def _build_research_prompt(symbol):
    company = symbol.upper()
    raw = _analysis_json(symbol)
    return (
        f"You are helping me research {company} for my own investment decision. Below is a JSON "
        "snapshot of the company's current data, pulled from my research dashboard.\n\n"
        "Write a detailed, plain-English research report a thoughtful beginner could follow. Walk "
        "these areas in order: (1) what recently changed, (2) business quality, (3) cash "
        "generation, (4) valuation, (5) what the market already expects, (6) risk & timing. For "
        "EACH area:\n"
        "  a. State the facts from the data.\n"
        "  b. Explain what that pattern usually means \u2014 give BOTH the bullish and the bearish "
        "reading.\n"
        "  c. Say what I should verify next, and why it matters.\n\n"
        "Then give a clear Bull Case and Bear Case, and finish with the 3\u20135 open questions that "
        "would settle the debate between them.\n\n"
        "Do NOT tell me to buy, sell, or hold. Explain the numbers so I can decide for myself. Point "
        "out anything in the data that looks extreme, cyclical, or internally inconsistent so I don't "
        "take it at face value.\n\n"
        f"DATA (JSON):\n{raw}\n"
    )


def _prompt_dialog(symbol):
    st.caption("Copy this into Claude.ai, ChatGPT, or any AI chat to get a full written report with "
               "**no API cost**. It already contains every number from this page.")
    st.code(_build_research_prompt(symbol), language="markdown")
    st.caption("Use the copy button at the top-right of the box, then paste it into your AI of choice.")


# Present as a modal where Streamlit supports it; otherwise it renders inline (still works).
if hasattr(st, "dialog"):
    try:
        _prompt_dialog = st.dialog("Research prompt \u2014 paste into any AI", width="large")(_prompt_dialog)
    except TypeError:
        _prompt_dialog = st.dialog("Research prompt \u2014 paste into any AI")(_prompt_dialog)


def _guide_para(text):
    st.markdown(
        f"<div style='font-size:1rem;line-height:1.65;color:{INK};margin:.3rem 0 .2rem;"
        f"max-width:52rem'>{text}</div>", unsafe_allow_html=True)


def _verify_line(text):
    st.markdown(
        f"<div style='font-size:.92rem;line-height:1.6;color:{INK};margin:.15rem 0 .2rem;"
        f"max-width:52rem;border-left:2px solid {LINE};padding-left:.7rem'>"
        f"<b>Worth checking before you decide:</b> {text}</div>", unsafe_allow_html=True)


def _handoff(text):
    st.markdown(
        f"<div style='font-size:.9rem;color:{MUTED};margin:.5rem 0 .1rem;font-style:italic'>"
        f"{text}</div>", unsafe_allow_html=True)


def _trend_block(title, reads):
    reads = [r for r in reads if r]
    if not reads:
        return
    body = "".join(f"<div style='margin:.12rem 0'>\u2022 {r}</div>" for r in reads)
    st.markdown(
        f"<div style='background:rgba(122,121,112,.06);border:1px solid {LINE};border-radius:10px;"
        f"padding:.75rem 1rem;margin:.4rem 0 .3rem;max-width:52rem'>"
        f"<div style='letter-spacing:.08em;text-transform:uppercase;font-size:.6rem;color:{MUTED};"
        f"margin-bottom:.35rem'>{title}</div>"
        f"<div style='font-size:.92rem;line-height:1.5;color:{INK}'>{body}</div></div>",
        unsafe_allow_html=True)


def _join_clauses(items):
    items = [x for x in items if x]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _fmt_v(v, kind):
    if v is None:
        return "n/a"
    if kind == "money_b":
        return f"${v / 1e9:.1f}B"
    if kind == "money":
        return f"${v:,.2f}"
    if kind == "pct":
        return f"{v:.0f}%"
    return f"{v:,.1f}"


def _series_read(values, labels, kind, name):
    """Turn a fundamentals time-series into one plain-English insight sentence
    (trough-to-recovery, steady climb, decline, peak-and-fade, or choppy)."""
    pairs = [(labels[i] if labels and i < len(labels) else str(i), to_float(v))
             for i, v in enumerate(values)]
    pairs = [(l, v) for l, v in pairs if v is not None]
    if len(pairs) < 3:
        return None
    vals = [v for _, v in pairs]
    n = len(vals)
    first_l, first = pairs[0]
    last_l, last = pairs[-1]
    lo_l, lo = min(pairs, key=lambda t: t[1])
    hi_l, hi = max(pairs, key=lambda t: t[1])
    labs = [l for l, _ in pairs]
    lo_i, hi_i = labs.index(lo_l), labs.index(hi_l)
    ups = sum(1 for a, b in zip(vals, vals[1:]) if b > a)
    steps = n - 1
    rng = hi - lo
    unit = "years" if str(first_l).startswith(("FY", "20")) else "quarters"

    def f(v):
        return _fmt_v(v, kind)

    if 0 < lo_i < n - 1 and lo < first and lo < last and (last - lo) > rng * 0.5:
        record = " \u2014 a record high" if last >= hi else ""
        return (f"{name} dropped to a low of {f(lo)} in {lo_l}, then recovered to {f(last)} in "
                f"{last_l}{record}.")
    if 0 < hi_i < n - 1 and hi > first and hi > last and (hi - last) > rng * 0.5:
        return f"{name} peaked at {f(hi)} in {hi_l} and has since faded to {f(last)} in {last_l}."
    if ups >= steps - 1 and last > first:
        return (f"{name} has climbed almost every period, from {f(first)} in {first_l} to {f(last)} in "
                f"{last_l} (up in {ups} of {steps}).")
    if ups <= 1 and last < first:
        return (f"{name} has fallen from {f(first)} in {first_l} to {f(last)} in {last_l} "
                f"(down in {steps - ups} of {steps} {unit}).")
    return (f"{name} has been choppy \u2014 between {f(lo)} and {f(hi)} \u2014 ending at {f(last)} in "
            f"{last_l} (up in {ups} of {steps} {unit}).")


def _sector_lens(profile):
    """Tailor the business framing to the company's industry, so a biotech reads
    as a pipeline story and a chipmaker as a cycle story \u2014 instead of one
    generic 'cyclical' line for everything."""
    sec = (profile.get("sector") or "").lower()
    ind = (profile.get("industry") or "").lower()
    if "semiconductor" in ind or "semiconductor" in sec:
        return {
            "durability": ("Semiconductors are deeply cyclical, so today's strong margins can be a "
                           "<i>cycle peak</i> rather than the new normal \u2014 the question is whether "
                           "the current up-cycle (AI-memory demand, in Micron's case) is durable or "
                           "near its top."),
            "turnaround": ("For a chipmaker, red ink usually marks a <i>cycle trough</i> rather than a "
                           "broken business \u2014 the question is whether the next up-cycle arrives "
                           "before cash gets tight."),
            "verify_extra": " Because it's cyclical, judge margins across a full cycle, not off the "
                            "latest quarter.",
        }
    if ("biotech" in ind or "drug" in ind or "pharmaceutical" in ind
            or ("healthcare" in sec and ("bio" in ind or "pharma" in ind))):
        return {
            "durability": ("For a drug maker, margins ride on a handful of key products \u2014 watch "
                           "for a patent cliff or loss of exclusivity, which can reset revenue quickly."),
            "turnaround": ("For a biotech or pharma name, this usually reads as a <b>pipeline or "
                           "post-product reset</b> \u2014 the real question is whether the drug pipeline "
                           "can rebuild durable revenue before cash runs low."),
            "verify_extra": " For a pipeline story, weigh clinical/approval milestones and cash runway, "
                            "not margins.",
        }
    return {
        "durability": ("<i>If</i> this is a cyclical business or an unusually strong stretch, today's "
                       "margins can be a peak rather than the norm \u2014 which flatters every "
                       "profitability number at once."),
        "turnaround": None,
        "verify_extra": "",
    }


def _lens_kind(profile):
    sec = (profile.get("sector") or "").lower()
    ind = (profile.get("industry") or "").lower()
    if "semiconductor" in ind or "semiconductor" in sec:
        return "semi"
    if ("biotech" in ind or "drug" in ind or "pharmaceutical" in ind
            or ("healthcare" in sec and ("bio" in ind or "pharma" in ind))):
        return "biotech"
    return "generic"


def _research_read_text(name, F):
    rev_g, nm, fcf_y = F["rev_g"], F["nm"], F["fcf_y"]
    pe, pe_med, peer_pe = F["pe"], F["pe_med"], F["peer_pe"]
    upside, stretched = F["upside"], F["stretched"]
    loss, shrink, lens, recovered = F["loss"], F["shrink"], F["lens"], F["recovered"]
    momentum, beat_str = F["momentum"], F["beat_str"]

    if loss and shrink:
        situation = {
            "biotech": f"{name} reads as a pipeline or post-product reset \u2014 a high-risk turnaround, "
                       "not a steady quality-growth business right now.",
            "semi": f"{name} reads as a chipmaker in a cyclical trough \u2014 a bet on the next up-cycle, "
                    "not a steady grower.",
        }.get(lens, f"{name} reads as a turnaround or reset story right now, not a steady "
                    "quality-growth business.")
    elif loss:
        situation = f"{name} is an early, still-unprofitable growth story."
    elif lens == "semi" and recovered:
        situation = f"{name} is a cyclical business riding a strong up-cycle after a recent trough."
    elif rev_g is not None and rev_g >= 15:
        situation = f"{name} is a fast-growing, profitable business."
    else:
        situation = f"{name} is a profitable business growing at a steadier pace."

    pos, neg = [], []
    if momentum:
        pos.append("the stock has strong price momentum")
    if beat_str:
        pos.append(beat_str)
    if rev_g is not None:
        if rev_g >= 10:
            pos.append(f"revenue is growing about {abs(rev_g):.0f}%")
        elif rev_g < 0:
            neg.append(f"revenue is still shrinking (about {abs(rev_g):.0f}%)")
    if nm is not None:
        if nm < 0:
            neg.append(f"margins are deeply negative ({nm:.0f}%)")
        elif nm >= 20:
            pos.append(f"margins are strong ({nm:.0f}%)")
    if fcf_y is not None:
        (neg if fcf_y < 0 else pos).append("free cash flow " + ("remains negative" if fcf_y < 0
                                                                 else "is positive"))
    if recovered:
        pos.append("the multi-year trajectory has recovered off its lows")
    if pe is not None and pe_med is not None and pe > 0:
        if pe > pe_med * 1.1:
            neg.append("it trades above its own 5-year valuation range")
        elif pe < pe_med * 0.9:
            pos.append("it trades below its own 5-year valuation range")
    if peer_pe is not None and pe is not None and 0 < pe < peer_pe:
        pos.append("it's cheaper than its peers")
    if upside is not None:
        if upside < 0:
            neg.append("analyst targets sit below the current price")
        elif upside >= 15:
            pos.append(f"analysts see roughly {upside:.0f}% upside to their average target")
    if stretched:
        neg.append("the stock looks stretched after a strong run")
    pos, neg = pos[:3], neg[:3]
    if pos and neg:
        syn = _join_clauses(pos) + ", but " + _join_clauses(neg)
    else:
        syn = _join_clauses(pos or neg)
    syn = (syn[0].upper() + syn[1:] + ".") if syn else ""

    if loss and lens == "biotech":
        q = "whether the pipeline can rebuild durable revenue before cash burn becomes a bigger concern"
    elif loss and lens == "semi":
        q = "whether the next up-cycle arrives before cash gets tight"
    elif loss:
        q = "whether the business can reach profitability before its cash runs low"
    elif lens == "semi":
        q = ("whether this up-cycle is durable or near its peak \u2014 which comes down to whether "
             "FY26/FY27 estimates keep rising")
    elif pe is not None and pe_med is not None and pe > pe_med * 1.1:
        q = "whether growth stays strong enough to justify a price above its own valuation history"
    else:
        q = "whether the momentum in the business and estimates holds from here"
    return situation, syn, q


def _render_research_read(name, F):
    situation, syn, q = _research_read_text(name, F)
    st.markdown(
        f"<div style='border:1px solid {LINE};border-left:3px solid {INK};background:#F7F5EE;"
        f"border-radius:12px;padding:1rem 1.2rem;margin:.3rem 0 1rem;max-width:52rem'>"
        f"<div style='letter-spacing:.1em;text-transform:uppercase;font-size:.62rem;color:{MUTED};"
        f"margin-bottom:.45rem'>Research Read</div>"
        f"<div style='font-size:1.06rem;line-height:1.5;color:{INK};font-weight:600;"
        f"margin-bottom:.4rem'>{situation}</div>"
        + (f"<div style='font-size:.97rem;line-height:1.6;color:{INK};margin-bottom:.55rem'>{syn}</div>"
           if syn else "")
        + f"<div style='font-size:.95rem;line-height:1.55;color:{INK};border-top:1px solid {LINE};"
        f"padding-top:.55rem'><b>The question to resolve:</b> {q}.</div>"
        f"<div style='font-size:.77rem;color:{MUTED};margin-top:.5rem'>A synthesis of the data below "
        "\u2014 not a recommendation. It frames what to research; the call is yours.</div></div>",
        unsafe_allow_html=True)


# ===========================================================================
# CONTEXT  —  news + filing highlights (the "what changed, and does it matter?"
# layer). Opt-in. Deterministic filing discovery from SEC direct; synthesis +
# citations from a pluggable provider (Perplexity or Gemini). Claude stays for
# the deeper analysis tab. Cached per ticker per day; a free copy-prompt route
# needs no API key. Verdict-free by construction.
# ===========================================================================

CONTEXT_DOMAINS = ["sec.gov", "businesswire.com", "globenewswire.com",
                   "prnewswire.com", "reuters.com", "apnews.com"]
CONTEXT_DAILY_SOFT_LIMIT = 40   # per-session guard against runaway spend


def _sec_ua():
    # SEC requires a descriptive User-Agent with contact info or it returns 403.
    return st.secrets.get("SEC_USER_AGENT", "tava-stock-dashboard research contact@example.com")


def _context_provider():
    forced = (st.secrets.get("CONTEXT_PROVIDER") or "").lower().strip()
    if forced in ("perplexity", "gemini"):
        return forced
    if st.secrets.get("PERPLEXITY_API_KEY"):
        return "perplexity"
    if st.secrets.get("GEMINI_API_KEY"):
        return "gemini"
    return None


@st.cache_data(ttl=21600, show_spinner=False)   # SEC guidance: cache submissions 6-12h
def get_recent_filings(cik):
    """Latest 8-K / 10-Q / 10-K from SEC direct (no key; needs a User-Agent)."""
    if not cik:
        return []
    try:
        cik_int = str(int(cik))
    except (TypeError, ValueError):
        return []
    try:
        r = requests.get(f"https://data.sec.gov/submissions/CIK{cik_int.zfill(10)}.json",
                         headers={"User-Agent": _sec_ua()}, timeout=15)
        r.raise_for_status()
        recent = ((r.json().get("filings") or {}).get("recent") or {})
    except Exception:  # noqa: BLE001
        return []
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    accs = recent.get("accessionNumber") or []
    docs = recent.get("primaryDocument") or []
    descs = recent.get("primaryDocDescription") or []
    out, seen = [], set()
    for i, form in enumerate(forms):                 # arrays are newest-first
        if form in ("10-K", "10-Q", "8-K") and form not in seen:
            acc = (accs[i] if i < len(accs) else "").replace("-", "")
            doc = docs[i] if i < len(docs) else ""
            url = (f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc}/{doc}"
                   if acc and doc else
                   f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_int}&type={form}")
            out.append({"form": form, "date": dates[i] if i < len(dates) else "",
                        "url": url, "desc": descs[i] if i < len(descs) else ""})
            seen.add(form)
        if len(seen) >= 3:
            break
    return out


def _build_context_prompt(symbol, name, filings):
    filing_lines = "\n".join(f"- {f['form']} filed {f['date']}: {f['url']}" for f in filings) \
        or "None retrieved."
    return (
        f"You are writing the \"Context\" section for a personal stock research dashboard. Use web "
        f"search to identify recent, MATERIAL developments for {symbol} ({name}). Cite sources. Do "
        "NOT give buy/sell advice.\n\n"
        f"Most recent SEC filings (summarize the newest 8-K / 10-Q / 10-K only if material):\n"
        f"{filing_lines}\n\n"
        "Priority order: (1) official company announcements / investor-relations, (2) SEC filings "
        "(8-K, 10-Q, 10-K), (3) earnings releases & guidance, (4) reputable news, (5) sector/policy "
        "news only if directly relevant.\n\n"
        "Return ONLY a JSON object, no markdown fences, with exactly this shape:\n"
        '{"latest_catalyst":"one-sentence summary of what changed",'
        '"most_important_event":{"title":"...","source":"...","date":"...","url":"..."},'
        '"materiality":"High|Medium|Low","why_it_matters":"plain-English",'
        '"what_to_verify_next":"a specific next check","confidence":"High|Medium|Low",'
        '"warning":"any caveat, or empty string"}\n\n'
        "Rules: say \"may explain\"/\"appears related to\", not \"caused\", unless a source says so. "
        "Distinguish official filings/press releases from media commentary. If no clear catalyst, say "
        "so in latest_catalyst. If the move looks sector- or policy-driven, label it. Never say buy, "
        "sell, or hold.")


def _context_via_perplexity(prompt):
    key = st.secrets.get("PERPLEXITY_API_KEY")
    body = {"model": st.secrets.get("PERPLEXITY_MODEL", "sonar"),
            "messages": [{"role": "user", "content": prompt}],
            "search_recency_filter": "month", "temperature": 0.2,
            "search_domain_filter": CONTEXT_DOMAINS[:10]}
    r = requests.post("https://api.perplexity.ai/chat/completions",
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                      json=body, timeout=60)
    r.raise_for_status()
    d = r.json()
    text = (((d.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
    cites = d.get("citations") or []
    if not cites and d.get("search_results"):
        cites = [s.get("url") for s in d["search_results"] if s.get("url")]
    return text, cites


def _context_via_gemini(prompt):
    key = st.secrets.get("GEMINI_API_KEY")
    model = st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {"contents": [{"parts": [{"text": prompt}]}], "tools": [{"google_search": {}}]}
    r = requests.post(url, headers={"Content-Type": "application/json"}, json=body, timeout=60)
    r.raise_for_status()
    cand = (r.json().get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in ((cand.get("content") or {}).get("parts") or []))
    cites = [(c.get("web") or {}).get("uri")
             for c in ((cand.get("groundingMetadata") or {}).get("groundingChunks") or [])
             if (c.get("web") or {}).get("uri")]
    return text, cites


def _parse_context_json(text):
    import json as _json
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[4:] if t[:4].lower() == "json" else t
    a, b = t.find("{"), t.rfind("}")
    if a >= 0 and b > a:
        try:
            return _json.loads(t[a:b + 1])
        except Exception:  # noqa: BLE001
            pass
    return {"latest_catalyst": (text or "")[:600].strip(), "_unparsed": True}


@st.cache_data(ttl=43200, show_spinner=False)   # cached per (symbol, provider, day)
def generate_context(symbol, name, provider, day):
    filings = []
    try:
        filings = get_recent_filings(get_earnings_context(symbol).get("cik"))
    except Exception:  # noqa: BLE001
        filings = []
    prompt = _build_context_prompt(symbol, name, filings)
    try:
        if provider == "perplexity":
            text, cites = _context_via_perplexity(prompt)
        elif provider == "gemini":
            text, cites = _context_via_gemini(prompt)
        else:
            return {"error": "No context provider configured.", "filings": filings}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:200], "filings": filings}
    res = _parse_context_json(text)
    res["citations"] = [c for c in (cites or []) if c][:8]
    res["filings"] = filings
    return res


def _ctx_tone(level):
    return {"high": "risk", "medium": "caution", "low": "neutral"}.get((level or "").lower(), "neutral")


def _render_context_card(res, symbol):
    if res.get("error"):
        st.warning(f"Couldn't fetch live context ({res['error']}). The copy-prompt route still works, "
                   "and any filings found are linked below.")
    else:
        cat = res.get("latest_catalyst") or "No clear recent catalyst was found."
        st.markdown(
            f"<div style='border:1px solid {LINE};border-left:3px solid {INK};background:#F7F5EE;"
            f"border-radius:10px;padding:.9rem 1.1rem;margin:.3rem 0 .5rem;max-width:52rem'>"
            f"<div style='letter-spacing:.09em;text-transform:uppercase;font-size:.6rem;color:{MUTED};"
            f"margin-bottom:.35rem'>What changed</div>"
            f"<div style='font-size:1.02rem;line-height:1.5;color:{INK};font-weight:600'>{cat}</div>",
            unsafe_allow_html=True)
        ev = res.get("most_important_event") or {}
        if ev.get("title"):
            link = (f" \u2014 <a href='{ev.get('url')}' target='_blank'>{ev.get('source') or 'source'}</a>"
                    if ev.get("url") else "")
            st.markdown(
                f"<div style='font-size:.9rem;color:{MUTED};margin-top:.4rem'>Most important: "
                f"{ev.get('title')}{(' \u00b7 ' + ev.get('date')) if ev.get('date') else ''}{link}</div>"
                "</div>", unsafe_allow_html=True)
        else:
            st.markdown("</div>", unsafe_allow_html=True)

        c = st.columns(2)
        metric_tile(c[0], "Materiality", res.get("materiality") or "\u2014", "materiality",
                    status=res.get("materiality"), status_tone=_ctx_tone(res.get("materiality")))
        with c[1]:
            st.metric("Confidence", res.get("confidence") or "\u2014")
        if res.get("why_it_matters"):
            _guide_para("<b>Why it matters:</b> " + res["why_it_matters"])
        if res.get("what_to_verify_next"):
            _verify_line(res["what_to_verify_next"])
        if res.get("warning"):
            st.caption("Note: " + res["warning"])

    cites = res.get("citations") or []
    if cites:
        links = " \u00b7 ".join(f"<a href='{u}' target='_blank'>{_short_url(u)}</a>" for u in cites)
        st.markdown(f"<div style='font-size:.8rem;color:{MUTED};margin:.3rem 0'>"
                    f"<b>Sources:</b> {links}</div>", unsafe_allow_html=True)
    filings = res.get("filings") or []
    if filings:
        fl = " \u00b7 ".join(f"<a href='{f['url']}' target='_blank'>{f['form']} ({f['date']})</a>"
                             for f in filings)
        st.markdown(f"<div style='font-size:.8rem;color:{MUTED};margin:.1rem 0 .3rem'>"
                    f"<b>Latest filings:</b> {fl}</div>", unsafe_allow_html=True)
    st.caption("Context is aggregated from cited sources \u2014 not a recommendation.")


def _short_url(u):
    try:
        return u.split("/")[2].replace("www.", "")
    except Exception:  # noqa: BLE001
        return "source"


def _context_prompt_body(symbol, name):
    try:
        filings = get_recent_filings(get_earnings_context(symbol).get("cik"))
    except Exception:  # noqa: BLE001
        filings = []
    st.caption("Paste this into Perplexity, Gemini, ChatGPT, or Claude to get the cited briefing for "
               "free \u2014 it already includes the latest SEC filing links.")
    st.code(_build_context_prompt(symbol, name, filings), language="markdown")


if hasattr(st, "dialog"):
    try:
        _context_prompt_dialog = st.dialog("Context prompt \u2014 paste into any AI",
                                           width="large")(_context_prompt_body)
    except TypeError:
        _context_prompt_dialog = st.dialog("Context prompt")(_context_prompt_body)
else:
    _context_prompt_dialog = _context_prompt_body


def render_context(symbol, name):
    import datetime as _dt
    provider = _context_provider()
    _subgroup("Context \u2014 recent news & filings")
    cc = st.columns([1.7, 1.7, 2.6])
    with cc[0]:
        gen = st.button("Generate latest context", key=f"ctx_{symbol}", use_container_width=True,
                        disabled=(provider is None))
    with cc[1]:
        if st.button("Copy research prompt", key=f"ctxp_{symbol}", use_container_width=True):
            _context_prompt_dialog(symbol, name)
    if provider is None:
        st.caption("Add a `PERPLEXITY_API_KEY` or `GEMINI_API_KEY` in Streamlit secrets to enable the "
                   "in-app briefing \u2014 or use **Copy research prompt** (free, works in any AI).")
        return
    if not gen:
        cap = ("console.perplexity.ai" if provider == "perplexity"
               else "your Google Cloud billing budget")
        st.caption(f"On demand, **{provider}** pulls recent news + the latest SEC filings with "
                   f"citations. Cached per stock per day; set a monthly spend cap in {cap}.")
        return
    if st.session_state.get("_ctx_calls", 0) >= CONTEXT_DAILY_SOFT_LIMIT:
        st.warning("That's a lot of context this session \u2014 pausing to protect your budget. "
                   "Reload to reset, or use the free copy-prompt route.")
        return
    st.session_state["_ctx_calls"] = st.session_state.get("_ctx_calls", 0) + 1
    with st.spinner("Reading recent news and filings\u2026"):
        res = generate_context(symbol, name, provider, _dt.date.today().isoformat())
    _render_context_card(res, symbol)



def render_guided(symbol, quote, profile, metrics):
    sym = symbol.upper()
    name = profile.get("name") or sym

    # ---- top controls: AI toggle + free copy-prompt ----
    cc = st.columns([1.5, 1.7, 2.8])
    with cc[0]:
        ai_on = st.checkbox("AI-powered", key=f"guide_ai_{sym}",
                            help="Let Claude write the analysis instead of the built-in guide. "
                                 "Uses your Anthropic API key (a few cents per run).")
    with cc[1]:
        if st.button("Research prompt", key=f"guide_prompt_{sym}",
                     use_container_width=True,
                     help="Copy a ready-made prompt containing all the numbers, to paste into any "
                          "AI chat \u2014 no API cost."):
            _prompt_dialog(sym)

    if ai_on:
        st.caption("AI mode: Claude reads every number and writes the report. It gives a research "
                   "*view* (with disclaimers); the built-in guide below stays verdict-free \u2014 "
                   "untick to return to it.")
        render_ai_analysis(sym)
        return

    # ---- data (reuses the same functions the metric tabs use) ----
    val = get_valuation_growth(sym)
    an = get_analyst(sym)
    ea = get_earnings_context(sym)
    tech = get_technicals(sym)
    traj = get_trajectory_annual(sym)
    cashn = get_cash_annual(sym)
    quar = get_quarterly_trend(sym)
    cur, gro, hist = val["current"], val["growth"], val["history"]

    # Company-condition flags that make the guidance adaptive (the fix the MRNA
    # review called for): loss-making and shrinking businesses read differently.
    _nm0 = to_float(metrics.get("net_margin_pct"))
    _pe0 = to_float(cur.get("pe"))
    _rev0 = to_float(gro.get("revenue"))
    loss_making = (_nm0 is not None and _nm0 < 0) or (_pe0 is not None and _pe0 < 0)
    shrinking = _rev0 is not None and _rev0 < 0
    lens = _sector_lens(profile)

    # ---- Research Read: the top-of-page synthesis (Slice 2) ----
    _bench = get_industry_benchmark(sym)
    _peer_pe = None
    if _bench:
        for _r in _bench["rows"]:
            if _r["key"] == "pe":
                _peer_pe = to_float(_r.get("median"))
    _rsi = to_float(tech.get("rsi"))
    _dlow = to_float(tech.get("dist_low")) or 0
    _rev_s = [to_float(x) for x in (traj.get("metrics") or {}).get("revenue", [])
              if to_float(x) is not None]
    _recovered = (len(_rev_s) >= 3 and min(_rev_s) < _rev_s[0]
                  and _rev_s[-1] > min(_rev_s) * 1.3
                  and 0 < _rev_s.index(min(_rev_s)) < len(_rev_s) - 1)
    _la = ea.get("last") or {}
    _eaa, _eae = to_float(_la.get("eps_actual")), to_float(_la.get("eps_est"))
    _beat_str = ""
    if _eaa is not None and _eae is not None and _eaa > _eae:
        _beat_str = "recently reported a smaller-than-expected loss" if _eaa < 0 else "recently beat earnings"
    _render_research_read(name, {
        "rev_g": to_float(gro.get("revenue")), "nm": to_float(metrics.get("net_margin_pct")),
        "fcf_y": to_float(cur.get("fcf_yield")), "pe": to_float(cur.get("pe")),
        "pe_med": to_float((hist.get("pe") or {}).get("median")), "peer_pe": _peer_pe,
        "upside": to_float((an.get("target") or {}).get("upside")),
        "stretched": (_rsi is not None and _rsi >= 70)
                     or bool(tech.get("above_50") and tech.get("above_200") and _dlow > 100),
        "momentum": (_rsi is not None and _rsi >= 60)
                    or bool(tech.get("above_200") and _dlow > 50),
        "loss": loss_making, "shrink": shrinking, "lens": _lens_kind(profile),
        "recovered": _recovered, "beat_str": _beat_str,
    })

    # ---- how to read this stock ----
    st.markdown(
        f"<div style='background:rgba(122,121,112,.06);border:1px solid {LINE};border-radius:10px;"
        f"padding:.9rem 1.1rem;margin:.5rem 0 .3rem;max-width:52rem'>"
        f"<div style='letter-spacing:.09em;text-transform:uppercase;font-size:.62rem;color:{MUTED};"
        f"margin-bottom:.35rem'>How to read this stock</div>"
        f"<div style='font-size:.95rem;line-height:1.6;color:{INK}'>Good research follows an order. "
        "First check <b>what just changed</b>, then whether the <b>business is improving</b>, then "
        "whether profits turn into <b>real cash</b>, then whether the <b>price already reflects</b> "
        "the good news, and finally the <b>risk and timing</b>. Each step below shows the number, "
        "then explains it \u2014 and points you to the next thing to check.</div></div>",
        unsafe_allow_html=True)

    # ======================= 1 · WHAT JUST CHANGED =======================
    section("What just changed?", "step 1 \u00b7 the catalyst")
    last, nxt = ea.get("last") or {}, ea.get("next") or {}
    c = st.columns(3)
    ea_a, ea_e = to_float(last.get("eps_actual")), to_float(last.get("eps_est"))
    # Surprise as a share of the ABSOLUTE estimate, so the sign stays correct when
    # EPS is negative: a smaller-than-expected loss is a BEAT, not a miss.
    surprise = ((ea_a - ea_e) / abs(ea_e) * 100) if (ea_a is not None and ea_e not in (None, 0)) else None
    is_beat = (ea_a > ea_e) if (ea_a is not None and ea_e is not None) else None
    loss_q = ea_a is not None and ea_a < 0
    beat_txt = "\u2014"
    if ea_a is not None:
        beat_txt = f"{money(ea_a)} vs {money(ea_e)} est"
        if surprise is not None:
            beat_txt += f" \u00b7 {'beat' if is_beat else 'missed'} by {abs(surprise):.0f}%"
    with c[0]:
        st.metric("Last EPS (actual vs est.)", beat_txt)
    with c[1]:
        st.metric("Next earnings", str(nxt.get("date") or "\u2014"))
    with c[2]:
        st.metric("Days away", str(nxt.get("days")) if nxt.get("days") is not None else "\u2014")
    if ea_a is not None and surprise is not None and loss_q:
        _guide_para(
            f"In its most recent quarter, {name} reported a loss of {money(abs(ea_a))} a share against "
            f"an expected {money(abs(ea_e))} loss \u2014 a {'smaller' if is_beat else 'bigger'} loss "
            f"than analysts modeled, about {abs(surprise):.0f}% {'better' if is_beat else 'worse'}. For "
            "a company still losing money, a 'beat' means the loss was less bad than feared \u2014 a "
            "genuine positive surprise, but not the same as turning profitable. What matters is the "
            "<i>direction</i>: is the loss shrinking quarter over quarter?")
    elif ea_a is not None and surprise is not None:
        _guide_para(
            f"In its most recent quarter, {name} reported earnings of {money(ea_a)} a share against the "
            f"{money(ea_e)} analysts expected \u2014 it {'beat' if is_beat else 'came in under'} the "
            f"estimate by about {abs(surprise):.0f}%. Earnings are where a story is confirmed or broken, "
            "so a beat says the business is running ahead of what the market had modeled; a miss says "
            "the opposite. One quarter isn't a trend, though \u2014 a single beat can come from a one-off.")
    else:
        _guide_para(
            f"There isn't clean actual-vs-estimate data for {name}'s last quarter on the current data "
            "tier, so treat the 'what changed' picture as incomplete and lean on the business and "
            "cash sections below.")
    if nxt.get("date"):
        _verify_line(
            f"whether that last surprise came from durable demand or a one-off \u2014 and whether "
            f"estimates for the next report ({nxt.get('date')}) are drifting up or down heading in. "
            "Rising estimates into a print is a stronger signal than the beat itself.")
    render_context(sym, name)
    _handoff("A good quarter only matters if the business behind it is actually getting stronger \u2014 "
             "so next, the trajectory.")

    # ======================= 2 · IS THE BUSINESS IMPROVING =======================
    section("Is the business improving?", "step 2 \u00b7 quality & trend")
    rev_g = to_float(gro.get("revenue"))
    nm, gm = to_float(metrics.get("net_margin_pct")), to_float(metrics.get("gross_margin_pct"))
    roe = to_float(metrics.get("roe_pct"))
    tyr, tm = traj.get("years") or [], traj.get("metrics") or {}
    c = st.columns(4)
    _s, _t = _sign_signal(rev_g)
    metric_tile(c[0], "Revenue Growth (YoY)", pct(rev_g), "revenue_growth", status=_s, status_tone=_t)
    _s, _t = _margin_signal(gm, gross=True)
    metric_tile(c[1], "Gross Margin", pct(gm), "gross_margin", status=_s, status_tone=_t)
    _s, _t = _margin_signal(nm, gross=False)
    metric_tile(c[2], "Net Margin", pct(nm), "net_margin", status=_s, status_tone=_t)
    _s, _t = _roe_signal(roe)
    metric_tile(c[3], "Return on Equity", pct(roe), "roe", status=_s, status_tone=_t)

    # read the multi-year trajectory aloud (this is the data Guide Me used to only point at)
    reads = []
    for key, lbl, kind in [("revenue", "Revenue", "money_b"), ("net_margin", "Net margin", "pct"),
                           ("gross_margin", "Gross margin", "pct"), ("roe", "ROE", "pct"),
                           ("debt", "Total debt", "money_b")]:
        reads.append(_series_read(tm.get(key, []), tyr, kind, lbl))
    _trend_block("The five-year trajectory", reads)

    bits = []
    if loss_making or shrinking:
        sent = []
        if rev_g is not None:
            sent.append(f"revenue is {'shrinking' if rev_g < 0 else 'growing'} about {abs(rev_g):.0f}% "
                        "year over year")
        if nm is not None and nm < 0:
            sent.append(f"the company is losing roughly ${abs(nm) / 100:.2f} for every $1 of sales "
                        f"(net margin {nm:.0f}%) \u2014 a clear profitability warning")
        elif nm is not None:
            sent.append(f"net margin sits around {nm:.0f}%")
        lead = _join_clauses(sent)
        lead = (lead[0].upper() + lead[1:] + ". ") if lead else ""
        turn = (" " + lens["turnaround"]) if lens.get("turnaround") else ""
        _guide_para(
            lead
            + f"Read alongside the trajectory above, {name} is better understood as a <b>turnaround or "
            "reset story</b> than a steady quality-growth business right now." + turn + " Either way, "
            "the question isn't 'how good are the margins' \u2014 it's 'is the business rebuilding': is "
            "revenue stabilizing, and is the loss getting smaller?")
        _verify_line(
            "whether the loss is <i>shrinking</i> and revenue is <i>stabilizing</i> over the last few "
            "quarters \u2014 the quarterly read below is where you see that first."
            + lens.get("verify_extra", ""))
    else:
        if rev_g is not None:
            bits.append(f"growing revenue about {abs(rev_g):.0f}% a year")
        if nm is not None:
            bits.append(f"keeping about {nm:.0f}\u00a2 of every sales dollar as profit")
        if roe is not None:
            bits.append(f"earning roughly {roe:.0f}% on shareholders' equity")
        _guide_para(
            (f"Today {name} is " + _join_clauses(bits) + ". " if bits else "")
            + "High, rising margins with strong returns usually point to real pricing power and a "
            "business getting more efficient \u2014 and the trajectory above tells you whether that's a "
            "steady build or a sharp bounce. The main caveat is durability: " + lens["durability"])
        _verify_line(
            "whether the trajectory is still bending upward or starting to roll over. Steadily climbing "
            "margins are a quality sign; a sharp spike after a slump often doesn't hold."
            + lens.get("verify_extra", ""))

    # quarterly momentum — the freshest signal
    ql, qm = quar.get("labels") or [], quar.get("metrics") or {}
    qreads = [_series_read(qm.get("revenue", []), ql, "money_b", "Revenue"),
              _series_read(qm.get("net_margin", []), ql, "pct", "Net margin")]
    _trend_block(f"The last {len(ql)} quarters", qreads)
    _handoff("Profit on paper isn't the same as money in the bank \u2014 so next, does it turn into "
             "cash?")

    # ======================= 3 · DOES IT MAKE REAL CASH =======================
    section("Does it make real cash?", "step 3 \u00b7 cash generation")
    fcf_y = to_float(cur.get("fcf_yield"))
    fcf_g = to_float(gro.get("fcf"))
    c = st.columns(2)
    if fcf_y is not None and fcf_y < 0:
        _s, _t = "Negative \u00b7 cash burn", "risk"
    elif fcf_y is not None and fcf_y >= 3:
        _s, _t = "Healthy", "good"
    else:
        _s, _t = _sign_signal(fcf_y, pos="healthy", neg="cash burn")
    metric_tile(c[0], "FCF Yield", pct(fcf_y), "fcf_yield", status=_s, status_tone=_t)
    _s, _t = _sign_signal(fcf_g)
    metric_tile(c[1], "FCF Growth (YoY)", pct(fcf_g), "fcf_growth", status=_s, status_tone=_t)
    cyr, cm = cashn.get("years") or [], cashn.get("metrics") or {}
    _trend_block("Free cash flow over time", [
        _series_read(cm.get("fcf", []), cyr, "money_b", "Free cash flow"),
        _series_read(cm.get("fcf_margin", []), cyr, "pct", "FCF margin"),
    ])
    if fcf_y is not None and fcf_y < 0:
        _guide_para(
            "Free cash flow is what's left after a company funds its operations and investments \u2014 "
            "harder to fake than accounting profit. Here it's <b>negative</b>: a free-cash-flow yield "
            f"of about {fcf_y:.1f}% means the business is <b>burning cash</b> relative to its value. "
            + (f"Cash flow did improve about {abs(fcf_g):.0f}% year over year, so the burn may be "
               "easing \u2014 but it's <i>still negative</i>, so the company isn't yet funding itself. "
               if (fcf_g is not None and fcf_g > 0) else "")
            + "For a cash-burning business the key question isn't yield, it's <b>runway</b>: how much "
            "cash is on hand, and how long does it last at this burn rate?")
        _verify_line(
            "how much cash and short-term investments the company holds, and how many quarters that "
            "funds at the current burn rate. A shrinking loss is only reassuring if the runway is long "
            "enough to reach profitability.")
    elif fcf_y is not None or fcf_g is not None:
        _guide_para(
            "Free cash flow is what's left after the company pays to keep the lights on and invest in "
            "growth \u2014 it's harder to fake than accounting profit. "
            + (f"Here the free-cash-flow yield is about {fcf_y:.1f}%, what the business throws off in "
               "cash relative to its price. " if fcf_y is not None else "")
            + (f"Cash flow is {'up' if (fcf_g or 0) > 0 else 'down'} about {abs(fcf_g):.0f}% year over "
               "year. " if fcf_g is not None else "")
            + "Profit that doesn't become cash is a yellow flag; cash that grows alongside profit is "
            "the real thing. In capital-heavy businesses, watch how much gets eaten by capital "
            "spending before it ever reaches free cash flow.")
        _verify_line(
            "whether free cash flow tracks reported profit over the last few years. If profit rises but "
            "cash doesn't, ask where the money is going \u2014 usually capital spending or working "
            "capital \u2014 and whether that's temporary or the nature of the business.")
    else:
        _guide_para("Cash-flow figures aren't available on the current tier for this one \u2014 the "
                    "Business tab's Cash Generation charts show the multi-year shape.")
    _handoff("A strong, cash-generating business can still be a poor investment if you overpay \u2014 "
             "so next, the price.")

    # ======================= 4 · IS THE PRICE FAIR =======================
    section("Is the price fair?", "step 4 \u00b7 valuation")
    pe = to_float(cur.get("pe"))
    fwd = to_float(cur.get("forward_pe"))
    ps = to_float(cur.get("ps"))
    pe_med = to_float((hist.get("pe") or {}).get("median"))
    unprofitable = loss_making or (pe is not None and pe <= 0)
    bench = get_industry_benchmark(sym)
    peer_pe = None
    if bench:
        for row in bench["rows"]:
            if row["key"] == "pe":
                peer_pe = row
                break

    if unprofitable:
        c = st.columns(3)
        with c[0]:
            st.metric("P/E (TTM)", "Loss-making")
        metric_tile(c[1], "Price / Sales", num(ps), "price_sales")
        with c[2]:
            st.metric("Forward P/E", num(fwd) if fwd is not None else "N/A")
        _guide_para(
            f"P/E isn't a useful gauge for {name} right now, because it's <b>losing money</b>. A "
            "negative or missing P/E doesn't mean 'cheap' \u2014 it just means there are no positive "
            "earnings to price against, so comparing it to a history or a peer median would mislead "
            "you. For a company like this, valuation leans on other anchors: price-to-sales"
            + (f" (about {num(ps)}\u00d7 here)" if ps is not None else "")
            + ", how much cash it holds to fund itself, the revenue trend, and above all <i>when</i> "
            "analysts expect it to return to profit.")
        _verify_line(
            "when analysts expect the company to be profitable again, how much cash it has to bridge "
            "the gap until then, and whether revenue estimates are stabilizing or still falling. Those "
            "decide the value here far more than any earnings multiple does today.")
    else:
        c = st.columns(3)
        _s, _t = _valuation_signal(pe, "pe")
        metric_tile(c[0], "P/E (TTM)", num(pe), "pe", status=_s, status_tone=_t)
        metric_tile(c[1], "Forward P/E", num(fwd), "forward_pe")
        with c[2]:
            st.metric("Own 5-yr median P/E", num(pe_med) if pe_med is not None else "\u2014")
        facts = []
        if pe is not None and pe_med is not None:
            facts.append(f"{sym}'s P/E of {num(pe)} sits {'above' if pe > pe_med else 'below'} its own "
                         f"5-year median of {num(pe_med)}")
        if peer_pe and peer_pe.get("median") is not None and pe is not None:
            facts.append(f"and {'below' if pe < peer_pe['median'] else 'above'} its peer median of "
                         f"{num(peer_pe['median'])}\u00d7")
        cheap_vs_peers = (peer_pe and pe is not None and pe_med is not None
                          and pe < (peer_pe.get('median') or 0) and pe > pe_med)
        if facts:
            _guide_para(
                " ".join(facts) + ". "
                + ("A stock above its own history but below its peers usually means one of two things: "
                   "either the market expects its earnings to keep climbing (so today's price is cheap "
                   "against <i>tomorrow's</i> profit), or the whole peer group is simply expensive "
                   "right now. " if cheap_vs_peers
                   else "The gap between what a stock trades at, its own history, and its peers is the "
                        "heart of the valuation question \u2014 a high multiple is only justified if "
                        "growth is real and durable. ")
                + (f"The forward P/E of {num(fwd)} \u2014 lower than the trailing {num(pe)} \u2014 tells "
                   "you analysts expect earnings to rise, which is exactly the bet embedded in the "
                   "price. " if (fwd is not None and pe is not None and fwd < pe) else ""))
        else:
            _guide_para("Valuation multiples are incomplete for this one on the current tier \u2014 the "
                        "Valuation tab shows whatever is available plus the peer benchmark.")
        if fwd is not None:
            _verify_line(
                "whether earnings estimates are still <i>rising</i>. If FY26/FY27 forecasts are climbing, "
                "a below-peer multiple on growing profit is one story; if they're being cut, the 'cheap "
                "on forward earnings' case quietly falls apart.")
        else:
            _verify_line(
                "what the price assumes about future profit. With no forward P/E available here, lean on "
                "the revenue trend and analyst estimates \u2014 is the market paying for growth that the "
                "forecasts actually support?")
    hist_reads = []
    for _k, _lbl in [("pe", "P/E"), ("ev", "EV/EBITDA"), ("ps", "P/S")]:
        _hd = hist.get(_k) or {}
        _now, _med = to_float(_hd.get("now")), to_float(_hd.get("median"))
        if _now is not None and _med is not None and _now > 0:
            hist_reads.append(f"{_lbl} of {num(_now)}\u00d7 sits {'above' if _now > _med else 'below'} "
                              f"its 5-year median of {num(_med)}\u00d7")
    _trend_block("Versus its own 5-year history", hist_reads)
    _handoff("Price only makes sense against expectations \u2014 so next, what is the market already "
             "counting on?")

    # ======================= 5 · WHAT THE MARKET EXPECTS =======================
    section("What does the market expect?", "step 5 \u00b7 expectations")
    tgt = an.get("target") or {}
    grades = an.get("grades") or {}
    upside = to_float(tgt.get("upside"))
    n_buy = sum(to_float(grades.get(k)) or 0 for k in ("strongBuy", "buy"))
    n_hold = to_float(grades.get("hold")) or 0
    n_sell = sum(to_float(grades.get(k)) or 0 for k in ("sell", "strongSell"))
    c = st.columns(3)
    with c[0]:
        st.metric("Analyst consensus", str(an.get("consensus") or "\u2014"))
    metric_tile(c[1], "Avg price target", money(tgt.get("avg")), "price_target")
    _s, _t = _sign_signal(upside, pos="upside", neg="downside")
    metric_tile(c[2], "Implied upside", pct(upside), "implied_upside", status=_s, status_tone=_t)
    fwd_e = an.get("forward") or {}
    c2 = st.columns(3)
    with c2[0]:
        st.metric("Target range", money_range(tgt.get("low"), tgt.get("high")))
    with c2[1]:
        st.metric(f"Est. revenue FY{str(fwd_e.get('year') or '')[-2:]}",
                  big_money(fwd_e.get("revenue")) if fwd_e.get("revenue") else "\u2014")
    with c2[2]:
        st.metric(f"Est. EPS FY{str(fwd_e.get('year') or '')[-2:]}",
                  money(fwd_e.get("eps")) if fwd_e.get("eps") is not None else "\u2014")
    _guide_para(
        (f"Analysts lean {'bullish' if n_buy > (n_hold + n_sell) else 'mixed'} here \u2014 roughly "
         f"{int(n_buy)} buy, {int(n_hold)} hold, {int(n_sell)} sell. " if (n_buy or n_hold or n_sell) else "")
        + (f"Their average target implies about {upside:.0f}% "
           f"{'upside' if upside >= 0 else 'downside'} from here. " if upside is not None else "")
        + "Consensus tells you what's already <i>priced in</i> \u2014 which cuts both ways. When "
        "everyone is bullish, a lot of good news is already in the stock, so it takes an even bigger "
        "surprise to push it higher, and a stumble can hurt more. Targets also cluster and get "
        "revised after the fact, so treat them as a mood reading, not a forecast.")
    _verify_line(
        "the <i>direction</i> of estimate revisions, not the level. Are analysts raising or cutting "
        "revenue and EPS forecasts over the last few months? Rising revisions into a bullish "
        "consensus is a genuine tailwind; falling revisions behind a bullish consensus is a warning.")
    _handoff("Finally, even a fair price on a great business can be a rough entry if the setup is "
             "stretched \u2014 so last, risk and timing.")

    # ======================= 6 · RISK & TIMING =======================
    section("Is the timing calm or stretched?", "step 6 \u00b7 risk & timing")
    rsi = to_float(tech.get("rsi"))
    dist_high = to_float(tech.get("dist_high"))
    beta = to_float(metrics.get("beta"))
    c = st.columns(3)
    _s, _t = _rsi_signal(rsi)
    metric_tile(c[0], "RSI (14)", num(rsi), "rsi", status=_s, status_tone=_t)
    with c[1]:
        st.metric("From 52-wk high", pct(dist_high) if dist_high is not None else "\u2014")
    _s, _t = _beta_signal(beta)
    metric_tile(c[2], "Beta", num(beta), "beta", status=_s, status_tone=_t)
    dist_low = to_float(tech.get("dist_low"))
    vol_ratio = to_float(tech.get("vol_ratio"))
    c2 = st.columns(3)
    with c2[0]:
        _a50 = tech.get("above_50")
        st.metric("Vs 50-day avg", "Above" if _a50 else ("Below" if _a50 is False else "\u2014"))
    with c2[1]:
        _a200 = tech.get("above_200")
        st.metric("Vs 200-day avg", "Above" if _a200 else ("Below" if _a200 is False else "\u2014"))
    _s, _t = _debt_signal(metrics.get("debt_to_equity"))
    metric_tile(c2[2], "Debt / Equity", num(metrics.get("debt_to_equity")), "debt_equity",
                status=_s, status_tone=_t)
    _guide_para(
        (f"Momentum (RSI) sits at {rsi:.0f}"
         + (" \u2014 in the stretched zone above 70, meaning the stock has run hard and fast" if (rsi or 0) >= 70
            else " \u2014 in the washed-out zone below 30, meaning it's been sold off hard" if (0 < (rsi or 0) <= 30)
            else " \u2014 in a neutral range") + ". " if rsi is not None else "")
        + (f"It's about {abs(dist_high):.0f}% {'below' if (dist_high or 0) < 0 else 'above'} its "
           "52-week high. " if dist_high is not None else "")
        + (f"A beta near {beta:.1f} means it tends to move {'more' if (beta or 0) > 1.2 else 'about as much' if 0.8 <= (beta or 0) <= 1.2 else 'less'} "
           "than the market. " if beta is not None else "")
        + "None of this is a buy or sell trigger \u2014 it describes the <i>entry conditions</i>. A "
        "stretched, high-beta name can keep running or snap back hard; a calm one gives you more "
        "room. Timing is about position size and patience, not about whether the business is good.")
    _verify_line(
        "whether a stretched reading is backed by fundamentals or just enthusiasm. If the run-up came "
        "with rising earnings and estimates, it's momentum with a reason; if the price moved but the "
        "fundamentals didn't, the timing risk is real.")

    # ---- close ----
    st.markdown(f"<hr style='border:none;border-top:1px solid {LINE};margin:1.2rem 0 .6rem'>",
                unsafe_allow_html=True)
    _guide_para(
        "That's the whole story, in order: what changed, whether the business and its cash are "
        "improving, whether the price already reflects it, what the market expects, and how stretched "
        "the setup is. The dashboard's job ends here \u2014 it lays out the evidence and the open "
        f"questions. The decision on {sym} is yours to make.")
    st.caption("Want a second read? Tick **AI-powered** above, or use **Research prompt** to run a "
               "full report in your own AI for free. Switch to **Metrics** (top) for every number and "
               "chart behind this walkthrough.")



def show_ticker(symbol):
    symbol = symbol.upper().strip()

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

    st.markdown(_STOCK_PAGE_CSS, unsafe_allow_html=True)
    _render_stock_header(symbol, name, industry, exchange, quote)
    render_pdf_fab(symbol)   # floating PDF button, reachable from any tab

    mode = st.radio("View mode", ["Guide Me", "Metrics"],
                    horizontal=True, key="detail_mode", label_visibility="collapsed")
    st.markdown(f"<hr style='border:none;border-top:1px solid {LINE};margin:.1rem 0 .6rem'>",
                unsafe_allow_html=True)
    if mode == "Guide Me":
        render_guided(symbol, quote, profile, metrics)
        return

    tab_overview, tab_business, tab_valuation, tab_market, tab_notes, tab_ai = st.tabs(
        ["Overview", "Business", "Valuation", "Market", "Notes", "AI"]
    )

    # ---------------- OVERVIEW: the essentials + price + AI summary ----------------
    with tab_overview:
        section("Snapshot", "the essentials")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Price", money(quote.get("price")),
                      delta=pct(quote.get("change_pct")) if to_float(quote.get("change_pct")) is not None else None)
        metric_tile(c2, "Market Cap", big_money(profile.get("market_cap") or quote.get("market_cap")), "market_cap")

        low, high = quote.get("week_low"), quote.get("week_high")
        range_note = None
        p, lo, hi = to_float(quote.get("price")), to_float(low), to_float(high)
        if None not in (p, lo, hi) and hi > lo:
            pos = (p - lo) / (hi - lo) * 100
            range_note = f"Price sits about {pos:.0f}% of the way up its 52-week range."
        metric_tile(c3, "52-Week Range", money_range(low, high), "week_range", note=range_note)
        metric_tile(c4, "Avg Daily Volume", big_count(metrics.get("avg_volume")), "volume")

        section("Price", "the trend over time")
        render_price_chart(symbol)

    # ---------------- BUSINESS: fundamentals over time ----------------
    with tab_business:
        section("Business Trajectory", "the shape of the business")
        st.caption("How the fundamentals have moved over recent fiscal years (annual).")
        render_trajectory(symbol)

        section("Recent Quarters", "the last few quarters up close")
        render_quarterly(symbol)

        section("Cash Generation", "does it make real money?")
        render_cash_generation(symbol)

        section("Financial Health", "how it's doing")
        c1, c2, c3, c4 = st.columns(4)
        _s, _t = _margin_signal(metrics.get("net_margin_pct"), gross=False)
        metric_tile(c1, "Net Margin", pct(metrics.get("net_margin_pct")), "net_margin", status=_s, status_tone=_t)
        _s, _t = _margin_signal(metrics.get("gross_margin_pct"), gross=True)
        metric_tile(c2, "Gross Margin", pct(metrics.get("gross_margin_pct")), "gross_margin", status=_s, status_tone=_t)
        _s, _t = _debt_signal(metrics.get("debt_to_equity"))
        metric_tile(c3, "Debt / Equity", num(metrics.get("debt_to_equity")), "debt_equity", status=_s, status_tone=_t)
        _s, _t = _roe_signal(metrics.get("roe_pct"))
        metric_tile(c4, "Return on Equity", pct(metrics.get("roe_pct")), "roe", status=_s, status_tone=_t)

    # ---------------- VALUATION ----------------
    with tab_valuation:
        section("Valuation vs Growth", "is it worth the price?")
        render_valuation_growth(symbol)

    # ---------------- MARKET: expectations, earnings, price setup ----------------
    with tab_market:
        section("Analyst Expectations", "what the market already expects")
        render_analyst(symbol)

        section("Earnings & Filings", "what's coming, what just happened")
        render_earnings(symbol)

        section("Price Context", "is the price stretched or reasonable?")
        render_technicals(symbol)

        section("Risk", "what could move it")
        c1, c2, c3 = st.columns(3)
        _s, _t = _beta_signal(metrics.get("beta"))
        metric_tile(c1, "Beta", num(metrics.get("beta")), "beta", status=_s, status_tone=_t)
        with c2:
            st.metric("Day Range", money_range(quote.get("day_low"), quote.get("day_high")))
        with c3:
            st.metric("Prev Close", money(quote.get("prev_close")))

    # ---------------- NOTES ----------------
    with tab_notes:
        section("Your Notes", "your call")
        st.caption("Write your own reasoning. (Session-only for now — permanent saving is a later feature.)")
        st.text_area("What's your read on this one?", key=f"notes_{symbol}", height=140,
                     placeholder="e.g. Business is compounding fast, but it trades above its own 5-yr "
                                 "multiples — is the growth already priced in? Check next earnings before deciding.")
        st.caption("ℹ️ Hover the **?** on any metric for a plain-English explanation. Some metrics "
                   "(PEG, EV/EBITDA) may show N/A on the current data tier — the app stays fully usable without them.")
        if not _PDF_OK:
            st.caption("📄 PDF export needs the **reportlab** and **matplotlib** packages — add them to "
                       "`requirements.txt` and redeploy, and a floating **PDF** button appears bottom-left.")

    # ---------------- AI ANALYSIS (its own tab, last) ----------------
    with tab_ai:
        section("AI Analysis", "the whole picture, in plain English")
        _dq = compute_quality_flags(symbol)
        _n = len(_dq["notes"]) + (1 if _dq["missing_fields"] else 0)
        if _n:
            with st.expander(f"⚠️ Data quality notes ({_n})"):
                for _note in _dq["notes"]:
                    st.markdown(f"- {_note}")
                if _dq["missing_fields"]:
                    st.markdown(f"- Unavailable on the current data tier: "
                                f"{', '.join(_dq['missing_fields'])}.")
                st.caption("Automatic checks on the raw data. The AI is handed these same flags so "
                           "it can account for them before drawing conclusions.")
        render_ai_analysis(symbol)


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


def _view_top():
    st.session_state.view = {"kind": "top"}


# on_click callbacks (below) run at the start of the rerun, before this body,
# so `view` already reflects the button the person just clicked — no stale state.
view = st.session_state.get("view", {"kind": "movers", "mover": "gainers"})
active_mover = view.get("mover") if view.get("kind") == "movers" else None
on_compare = view.get("kind") == "compare"

# --- Daily starting point ---
st.sidebar.button("\u2600\ufe0f  Top Stocks to Explore", use_container_width=True,
                  type="primary" if view.get("kind") == "top" else "secondary",
                  on_click=_view_top)
st.sidebar.markdown("---")

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

st.sidebar.markdown("---")
st.sidebar.caption(f"📦 Version {APP_VERSION} · {APP_BUILD}")

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
elif view.get("kind") == "top":
    render_top_stocks()
else:
    show_movers(view.get("mover", "gainers"))

st.markdown("---")
st.caption("Signal colors: green = favorable/improving, amber = caution/stretched, red = risk/deteriorating, blue = informational, gray = neutral. Colors explain the metric; they are not buy/sell signals.")
st.caption(
    "📚 Educational tool, not financial advice. Data from Financial Modeling Prep, "
    "and may be delayed. Metrics and 'healthy ranges' are general guidance — compare within a "
    "company's own industry, and make your own decisions."
)
st.caption(f"📦 Version {APP_VERSION} · built {APP_BUILD}")
