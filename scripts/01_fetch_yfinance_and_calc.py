"""
Alpha-Q | Task 1a
Fetch annual financial statements via yfinance and compute:
  - Piotroski F-Score (9 binary signals)
  - Altman Z-Score (standard) / Z-Prime (financial firms)
  - DuPont ROE decomposition (3-factor)

Output: data/financial_metrics.db  (SQLite, keyed on ticker + fiscal_year)

Usage:
    python scripts/01_fetch_yfinance_and_calc.py
"""

import sqlite3
import tomllib
from pathlib import Path

import pandas as pd
import yfinance as yf
from tqdm import tqdm

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).resolve().parent.parent
DB_OUT  = ROOT / "data" / "financial_metrics.db"

# ── Financial-sector tickers → use Altman Z-Prime formula ────────────────────
FINANCIAL_TICKERS = {
    "JPM", "BAC", "GS", "V", "MA", "AXP",
    "BLK", "MS", "C", "PYPL", "SQ",
    "WFC", "USB", "PNC", "SCHW",
}

# ── yfinance v0.2+ field names (case-sensitive row index strings) ──────────────
# Balance Sheet
_F_TA   = "Total Assets"
_F_TL   = "Total Liabilities Net Minority Interest"
_F_CA   = "Current Assets"
_F_CL   = "Current Liabilities"
_F_RE   = "Retained Earnings"
_F_LTD  = "Long Term Debt"
_F_EQ   = "Stockholders Equity"
_F_SH   = "Ordinary Shares Number"
# Income Statement
_F_REV  = "Total Revenue"
_F_NI   = "Net Income"
_F_GP   = "Gross Profit"
_F_EBIT = "EBIT"
_F_OPINC= "Operating Income"   # EBIT fallback
# Cash Flow
_F_CFO  = "Operating Cash Flow"


# ── Config loading ────────────────────────────────────────────────────────────

def _load_config() -> tuple[list[int], dict[str, int], list[str]]:
    with open(ROOT / "stocks.toml", "rb") as f:
        cfg = tomllib.load(f)
    years: list[int] = cfg["years"]
    ipo_floors: dict[str, int] = cfg.get("ipo_year_floor", {})
    seen: set[str] = set()
    tickers: list[str] = []
    for tier in cfg.get("companies", {}).values():
        for tk in tier.get("tickers", []):
            if tk not in seen:
                seen.add(tk)
                tickers.append(tk)
    return years, ipo_floors, tickers


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _get(df: pd.DataFrame | None, field: str, col) -> float | None:
    """Return scalar float from a yfinance statement DataFrame, None if missing."""
    if df is None or df.empty or field not in df.index or col not in df.columns:
        return None
    try:
        v = float(df.at[field, col])
        return None if pd.isna(v) else v
    except (TypeError, ValueError):
        return None


def _year_col(df: pd.DataFrame | None, year: int):
    """
    yfinance annual statement columns are Timestamp objects.
    Return the column whose .year matches, or None.
    """
    if df is None or df.empty:
        return None
    for col in df.columns:
        if getattr(col, "year", None) == year:
            return col
    return None


def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or not b:
        return None
    return a / b


# ── Piotroski F-Score ─────────────────────────────────────────────────────────

def _fscore(
    bs: pd.DataFrame,
    inc: pd.DataFrame,
    cf: pd.DataFrame,
    year: int,
) -> dict:
    """
    Compute 9 Piotroski binary signals for a single fiscal year.
    Returns dict with f1..f9 (0/1/None) and f_score (int or None).
    f_score is None when fewer than 5 signals resolve (insufficient data).
    """
    cur  = _year_col(bs, year)
    prev = _year_col(bs, year - 1)

    def b(f): return _get(bs,  f, cur)
    def bp(f): return _get(bs,  f, prev)
    def i(f): return _get(inc, f, _year_col(inc, year))
    def ip(f): return _get(inc, f, _year_col(inc, year - 1))
    def c(f): return _get(cf,  f, _year_col(cf, year))

    ta, ta_p = b(_F_TA), bp(_F_TA)
    ni, ni_p = i(_F_NI), ip(_F_NI)
    cfo      = c(_F_CFO)
    rev, rev_p = i(_F_REV), ip(_F_REV)
    gp,  gp_p  = i(_F_GP),  ip(_F_GP)
    ltd, ltd_p = b(_F_LTD), bp(_F_LTD)
    ca,  ca_p  = b(_F_CA),  bp(_F_CA)
    cl,  cl_p  = b(_F_CL),  bp(_F_CL)
    sh,  sh_p  = b(_F_SH),  bp(_F_SH)

    roa   = _safe_div(ni,   ta)
    roa_p = _safe_div(ni_p, ta_p)
    lev   = _safe_div(ltd,  ta)
    lev_p = _safe_div(ltd_p, ta_p)
    cr    = _safe_div(ca,  cl)
    cr_p  = _safe_div(ca_p, cl_p)
    gm    = _safe_div(gp,  rev)
    gm_p  = _safe_div(gp_p, rev_p)
    at    = _safe_div(rev,  ta)
    at_p  = _safe_div(rev_p, ta_p)

    # Each signal: None = data missing (not penalised), 0/1 = computed
    f1 = None if roa is None else int(roa > 0)
    f2 = None if cfo is None else int(cfo > 0)
    f3 = None if (roa is None or roa_p is None) else int(roa > roa_p)
    f4 = None if (cfo is None or ta is None or roa is None) else int((cfo / ta) > roa)
    f5 = None if (lev is None or lev_p is None) else int(lev < lev_p)
    f6 = None if (cr  is None or cr_p  is None) else int(cr  > cr_p)
    f7 = None if (sh  is None or sh_p  is None) else int(sh  <= sh_p)
    f8 = None if (gm  is None or gm_p  is None) else int(gm  > gm_p)
    f9 = None if (at  is None or at_p  is None) else int(at  > at_p)

    signals = [f1, f2, f3, f4, f5, f6, f7, f8, f9]
    valid   = [s for s in signals if s is not None]
    f_score = sum(valid) if len(valid) >= 5 else None

    return {
        "f1": f1, "f2": f2, "f3": f3, "f4": f4, "f5": f5,
        "f6": f6, "f7": f7, "f8": f8, "f9": f9,
        "f_score": f_score,
    }


# ── Altman Z-Score ────────────────────────────────────────────────────────────

def _zscore(
    ticker: str,
    bs: pd.DataFrame,
    inc: pd.DataFrame,
    year: int,
    market_cap: float | None,
) -> tuple[float | None, str]:
    cur = _year_col(bs, year)
    if cur is None:
        z_type = "prime" if ticker in FINANCIAL_TICKERS else "standard"
        return None, z_type

    def b(f): return _get(bs,  f, cur)
    def i(f): return _get(inc, f, _year_col(inc, year))

    ta   = b(_F_TA)
    if not ta:
        z_type = "prime" if ticker in FINANCIAL_TICKERS else "standard"
        return None, z_type

    ca   = b(_F_CA)
    cl   = b(_F_CL)
    re   = b(_F_RE)
    _ebit_raw = i(_F_EBIT)
    ebit = _ebit_raw if _ebit_raw is not None else i(_F_OPINC)
    rev  = i(_F_REV)
    eq   = b(_F_EQ)
    tl   = b(_F_TL)
    wc   = (ca - cl) if (ca is not None and cl is not None) else None

    x1 = _safe_div(wc,   ta)
    x2 = _safe_div(re,   ta)
    x3 = _safe_div(ebit, ta)

    if ticker in FINANCIAL_TICKERS:
        # Z-Prime: X4 = Book Equity / Total Liabilities (no market price dependency)
        x4 = _safe_div(eq, tl)
        if any(v is None for v in (x1, x2, x3, x4)):
            return None, "prime"
        z = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
        return round(z, 4), "prime"
    else:
        # Standard Z: X4 = Market Cap / Total Liabilities
        x4 = _safe_div(market_cap, tl)
        x5 = _safe_div(rev, ta)
        if any(v is None for v in (x1, x2, x3, x4, x5)):
            return None, "standard"
        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
        return round(z, 4), "standard"


# ── DuPont ROE ────────────────────────────────────────────────────────────────

def _dupont(bs: pd.DataFrame, inc: pd.DataFrame, year: int) -> dict:
    cur = _year_col(bs, year)
    if cur is None:
        return {"roe": None, "net_margin": None, "asset_turnover": None, "equity_multiplier": None}

    ta  = _get(bs,  _F_TA,  cur)
    eq  = _get(bs,  _F_EQ,  cur)
    rev = _get(inc, _F_REV, _year_col(inc, year))
    ni  = _get(inc, _F_NI,  _year_col(inc, year))

    nm  = _safe_div(ni,  rev)
    at  = _safe_div(rev, ta)
    em  = _safe_div(ta,  eq)
    roe = (nm * at * em) if (nm is not None and at is not None and em is not None) else None

    def _r(v): return round(v, 6) if v is not None else None
    return {"roe": _r(roe), "net_margin": _r(nm), "asset_turnover": _r(at), "equity_multiplier": _r(em)}


# ── Per-ticker processor ──────────────────────────────────────────────────────

def _process_ticker(
    ticker: str,
    years: list[int],
    ipo_floors: dict[str, int],
) -> list[dict]:
    ipo_floor = ipo_floors.get(ticker, 0)
    valid_years = [y for y in years if y >= ipo_floor]
    if not valid_years:
        return []

    try:
        t   = yf.Ticker(ticker)
        bs  = t.balance_sheet
        inc = t.income_stmt
        cf  = t.cashflow
    except Exception as e:
        tqdm.write(f"  [WARN] {ticker}: fetch failed — {e}")
        return []

    if bs is None or bs.empty:
        tqdm.write(f"  [WARN] {ticker}: no balance sheet data")
        return []

    # Market cap fetched once per ticker (current snapshot, free API limitation)
    try:
        mc = getattr(t.fast_info, "market_cap", None)
        market_cap = float(mc) if mc else None
    except Exception:
        market_cap = None

    rows = []
    for year in sorted(valid_years):
        if _year_col(bs, year) is None:
            continue
        try:
            fs  = _fscore(bs, inc, cf, year)
            z, z_type = _zscore(ticker, bs, inc, year, market_cap)
            dp  = _dupont(bs, inc, year)
            rows.append({
                "ticker":      ticker,
                "fiscal_year": year,
                "z_score":     z,
                "z_score_type": z_type,
                "market_cap":  market_cap,
                **fs,
                **dp,
            })
        except Exception as e:
            tqdm.write(f"  [WARN] {ticker}/{year}: compute error — {e}")

    return rows


# ── DDL + writer ──────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS financial_metrics (
    ticker            TEXT    NOT NULL,
    fiscal_year       INTEGER NOT NULL,
    f_score           INTEGER,
    f1 INTEGER, f2 INTEGER, f3 INTEGER, f4 INTEGER, f5 INTEGER,
    f6 INTEGER, f7 INTEGER, f8 INTEGER, f9 INTEGER,
    z_score           REAL,
    z_score_type      TEXT,
    roe               REAL,
    net_margin        REAL,
    asset_turnover    REAL,
    equity_multiplier REAL,
    market_cap        REAL,
    PRIMARY KEY (ticker, fiscal_year)
);
"""

_INSERT = """
INSERT OR REPLACE INTO financial_metrics
    (ticker, fiscal_year, f_score, f1, f2, f3, f4, f5, f6, f7, f8, f9,
     z_score, z_score_type, roe, net_margin, asset_turnover, equity_multiplier, market_cap)
VALUES
    (:ticker, :fiscal_year, :f_score, :f1, :f2, :f3, :f4, :f5, :f6, :f7, :f8, :f9,
     :z_score, :z_score_type, :roe, :net_margin, :asset_turnover, :equity_multiplier, :market_cap)
"""


def _write_db(rows: list[dict]) -> None:
    DB_OUT.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_OUT) as conn:
        conn.execute(_DDL)
        conn.executemany(_INSERT, rows)
        conn.commit()
        conn.execute("ANALYZE")
    print(f"\n[OK] {len(rows)} rows → {DB_OUT}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    years, ipo_floors, tickers = _load_config()
    print(f"Tickers: {len(tickers)}  |  Years: {years[-1]}–{years[0]}")

    all_rows: list[dict] = []
    for ticker in tqdm(tickers, desc="Fetching", unit="ticker"):
        all_rows.extend(_process_ticker(ticker, years, ipo_floors))

    if not all_rows:
        print("[ERROR] No data computed. Check network and yfinance version.")
        return
    _write_db(all_rows)


if __name__ == "__main__":
    main()
