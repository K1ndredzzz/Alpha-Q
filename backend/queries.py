from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Connection

_QUANT_COLS = """
    ticker, fiscal_year,
    f_score, f1, f2, f3, f4, f5, f6, f7, f8, f9,
    z_score, z_score_type,
    roe, net_margin, asset_turnover, equity_multiplier, market_cap
"""

_NLP_COLS = """
    ticker, fiscal_year,
    mda_sentiment_score,
    macro_concern_1, macro_concern_2, macro_concern_3,
    capex_guidance_tone, ai_investment_focus, ai_monetization_status,
    china_exposure_risk, supply_chain_bottlenecks, restructuring_plans,
    efficiency_initiatives, growing_segments, shrinking_segments,
    mda_char_count, risk_char_count
"""

_RED_FLAG_COLS = """
    ticker, fiscal_year,
    f_score, mda_sentiment_score,
    z_score, z_score_type,
    macro_concern_1, macro_concern_2, macro_concern_3,
    net_margin, roe, efficiency_initiatives
"""


def _fetch(conn: Connection, cols: str, ticker: str) -> list[dict]:
    sql = text(
        f"SELECT {cols} FROM alpha_q_master "
        "WHERE UPPER(ticker) = UPPER(:ticker) "
        "ORDER BY fiscal_year ASC"
    )
    rows = conn.execute(sql, {"ticker": ticker}).mappings().all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker.upper()}' not found")
    return [dict(r) for r in rows]


def fetch_quant_rows(conn: Connection, ticker: str) -> list[dict]:
    return _fetch(conn, _QUANT_COLS, ticker)


def fetch_nlp_rows(conn: Connection, ticker: str) -> list[dict]:
    return _fetch(conn, _NLP_COLS, ticker)


def fetch_red_flag_rows(conn: Connection, ticker: str) -> list[dict]:
    return _fetch(conn, _RED_FLAG_COLS, ticker)


def fetch_all_tickers(conn: Connection) -> list[dict]:
    sql = text(
        "SELECT ticker, MAX(tier) AS tier, COUNT(*) AS years_available "
        "FROM alpha_q_master "
        "GROUP BY ticker "
        "ORDER BY ticker ASC"
    )
    return [dict(r) for r in conn.execute(sql).mappings().all()]
