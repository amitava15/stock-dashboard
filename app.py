"""
Stock Research Dashboard  —  provider-layered
---------------------------------------------
The app calls a clean interface — get_quote(), get_company_profile(),
get_key_metrics(), search_companies() — and doesn't care which provider
answers. Adding a provider later means editing one section, not the whole app.

Providers wired now:
  • FMP (free)      -> movers lists + company/ticker search  (work for all tickers)
  • Finnhub (free)  -> quote, profile, fundamentals          (work for all tickers)
Stubs for later:
  • SEC EDGAR       -> filings          (get_filings, placeholder)
  • Finnhub news    -> news/sentiment   (get_news, placeholder)

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
FINNHUB_BASE = "https://finnhub.io/api/v1"

FMP_KEY = st.secrets.get("FMP_API_KEY", "")
FINNHUB_KEY = st.secrets.get("FINNHUB_API_KEY", "")


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
        "(Shown as a %: 150 means 1.5× equity.)"
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
# NORMALIZED INTERFACE  (provider-agnostic; units normalized here)
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

    avg_vol_m = g("10DayAverageTradingVolume", "3MonthAverageTradingVolume")  # millions of shares
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

    if not FINNHUB_KEY:
        st.info(
            "**One quick setup step to unlock stock details (free):**\n"
            "1. Get a free key at https://finnhub.io/register\n"
            "2. Add it to your Streamlit secrets as `FINNHUB_API_KEY = \"your_key\"`\n"
            "3. Reload. The movers lists already work without it."
        )
        return

    try:
        quote = get_quote(symbol)
    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        if status == 401:
            st.error("Finnhub rejected the API key. Double-check `FINNHUB_API_KEY` in your Streamlit secrets.")
        elif status == 403:
            st.warning(
                f"**{symbol}** isn't covered by the free stock data — it's likely a fund, forex pair, "
                "index, or non-US listing. Try a common US-listed stock (e.g. **MU** for Micron)."
            )
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
    st.markdown(f'<div class="rt-company">{header}</div>', unsafe_allow_html=True)

    price = quote.get("price")
    change_pct = quote.get("change_pct")

    # ---- Snapshot ----
    section("Snapshot", "the essentials")
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
        range_note = f"Price sits about {pos:.0f}% of the way up its 52-week range."
    metric_tile(c3, "52-Week Range", range_val, "week_range", note=range_note)

    metric_tile(c4, "Avg Daily Volume", big_count(metrics.get("avg_volume")), "volume")

    # ---- Price ----
    section("Price", "the trend over time")
    render_price_chart(symbol)

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
        st.metric("Day Range", f"{money(quote.get('day_low'))} – {money(quote.get('day_high'))}")
    with c3:
        st.metric("Prev Close", money(quote.get("prev_close")))

    # ---- Your notes ----
    section("Your Notes", "your call")
    st.caption("Write your own reasoning. (Session-only for now — permanent saving is a later feature.)")
    st.text_area("What's your read on this one?", key=f"notes_{symbol}", height=120,
                 placeholder="e.g. Strong margins but debt looks high for the sector — check latest earnings before deciding.")

    st.caption("ℹ️ Hover the **?** on any metric for a plain-English explanation. Some metrics (PEG, EV/EBITDA) may show N/A on the free data tier — the app stays fully usable without them.")


# ===========================================================================
# Sidebar + routing
# ===========================================================================
st.sidebar.title("Stock Research")
st.sidebar.caption("Aggregate the data. Understand the metrics. **You** decide.")


def _set_mode(mode):
    # Remember whether the person last used Search or Browse, so a click on one
    # doesn't get ignored because the other still holds a value.
    st.session_state.nav_mode = mode


search_term = st.sidebar.text_input("🔎 Search company or ticker",
                                     placeholder="e.g. Micron  or  MU",
                                     key="search_box",
                                     on_change=_set_mode, args=("search",)).strip()

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
            choice = st.sidebar.selectbox("Select a match:", list(options.keys()),
                                          key="match_select",
                                          on_change=_set_mode, args=("search",))
            selected_symbol = options[choice]
    if selected_symbol is None:
        selected_symbol = search_term.upper()
        st.sidebar.caption(f"No stock matches — trying **{selected_symbol}** as a ticker.")

st.sidebar.markdown("---")
preset = st.sidebar.radio("Or browse movers:", ["Top Gainers", "Top Losers", "Most Active"],
                          key="movers_radio", on_change=_set_mode, args=("movers",))
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

nav_mode = st.session_state.get("nav_mode", "movers")
show_detail = (nav_mode == "search") and bool(selected_symbol)

if show_detail:
    show_ticker(selected_symbol)
else:
    show_movers(preset_map[preset])

st.markdown("---")
st.caption(
    "📚 Educational tool, not financial advice. Data from FMP (movers) and Finnhub (stock details), "
    "and may be delayed. Metrics and 'healthy ranges' are general guidance — compare within a "
    "company's own industry, and make your own decisions."
)
