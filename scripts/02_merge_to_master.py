"""
Alpha-Q | Task 1b
INNER JOIN financial_metrics + filing_insights → alpha_q_master.db
Also exports a PostgreSQL-compatible alpha_q_master_pg.sql.

Run AFTER 01_fetch_yfinance_and_calc.py:
    python scripts/02_merge_to_master.py
"""

import json
import sqlite3
from pathlib import Path

ROOT         = Path(__file__).resolve().parent.parent
SRC_METRICS  = ROOT / "data" / "financial_metrics.db"
SRC_INSIGHTS = ROOT / "data" / "insights.db"
DST_MASTER   = ROOT / "data" / "alpha_q_master.db"
DST_SQL      = ROOT / "data" / "alpha_q_master_pg.sql"


# ── DDL ───────────────────────────────────────────────────────────────────────

_MASTER_DDL = """
CREATE TABLE IF NOT EXISTS alpha_q_master (
    ticker                   TEXT    NOT NULL,
    fiscal_year              INTEGER NOT NULL,

    -- Piotroski F-Score
    f_score                  INTEGER,
    f1 INTEGER, f2 INTEGER, f3 INTEGER, f4 INTEGER, f5 INTEGER,
    f6 INTEGER, f7 INTEGER, f8 INTEGER, f9 INTEGER,

    -- Altman Z-Score
    z_score                  REAL,
    z_score_type             TEXT,

    -- DuPont ROE
    roe                      REAL,
    net_margin               REAL,
    asset_turnover           REAL,
    equity_multiplier        REAL,
    market_cap               REAL,

    -- NLP / filing insights
    tier                     TEXT,
    filing_type              TEXT,
    ai_investment_focus      TEXT,
    ai_monetization_status   TEXT,
    capex_guidance_tone      TEXT,
    china_exposure_risk      TEXT,
    supply_chain_bottlenecks TEXT,
    restructuring_plans      TEXT,
    efficiency_initiatives   TEXT,
    mda_sentiment_score      INTEGER,
    macro_concern_1          TEXT,
    macro_concern_2          TEXT,
    macro_concern_3          TEXT,
    growing_segments         TEXT,
    shrinking_segments       TEXT,
    mda_char_count           INTEGER,
    risk_char_count          INTEGER,

    PRIMARY KEY (ticker, fiscal_year)
);
"""

_INSERT = """
INSERT OR REPLACE INTO alpha_q_master (
    ticker, fiscal_year,
    f_score, f1, f2, f3, f4, f5, f6, f7, f8, f9,
    z_score, z_score_type,
    roe, net_margin, asset_turnover, equity_multiplier, market_cap,
    tier, filing_type,
    ai_investment_focus, ai_monetization_status, capex_guidance_tone,
    china_exposure_risk, supply_chain_bottlenecks, restructuring_plans,
    efficiency_initiatives, mda_sentiment_score,
    macro_concern_1, macro_concern_2, macro_concern_3,
    growing_segments, shrinking_segments,
    mda_char_count, risk_char_count
) VALUES (
    :ticker, :fiscal_year,
    :f_score, :f1, :f2, :f3, :f4, :f5, :f6, :f7, :f8, :f9,
    :z_score, :z_score_type,
    :roe, :net_margin, :asset_turnover, :equity_multiplier, :market_cap,
    :tier, :filing_type,
    :ai_investment_focus, :ai_monetization_status, :capex_guidance_tone,
    :china_exposure_risk, :supply_chain_bottlenecks, :restructuring_plans,
    :efficiency_initiatives, :mda_sentiment_score,
    :macro_concern_1, :macro_concern_2, :macro_concern_3,
    :growing_segments, :shrinking_segments,
    :mda_char_count, :risk_char_count
)
"""


# ── Loaders ────────────────────────────────────────────────���──────────────────

def _load_metrics(path: Path) -> list[dict]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM financial_metrics").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _load_insights(path: Path) -> dict[tuple[str, int], dict]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT ticker, fiscal_year, tier, filing_type,
               ai_investment_focus, ai_monetization_status, capex_guidance_tone,
               china_exposure_risk, supply_chain_bottlenecks, restructuring_plans,
               efficiency_initiatives, mda_sentiment_score,
               macro_concerns, growing_segments, shrinking_segments,
               mda_char_count, risk_char_count
        FROM filing_insights
    """).fetchall()
    conn.close()

    index: dict[tuple[str, int], dict] = {}
    for r in rows:
        raw = r["macro_concerns"]
        try:
            concerns = json.loads(raw) if isinstance(raw, str) else (raw or [])
            if not isinstance(concerns, list):
                concerns = []
        except (json.JSONDecodeError, TypeError):
            concerns = []
        # Normalise to exactly 3 entries (pad with None)
        concerns = (concerns + [None, None, None])[:3]

        index[(r["ticker"], r["fiscal_year"])] = {
            "tier":                     r["tier"],
            "filing_type":              r["filing_type"],
            "ai_investment_focus":      r["ai_investment_focus"],
            "ai_monetization_status":   r["ai_monetization_status"],
            "capex_guidance_tone":      r["capex_guidance_tone"],
            "china_exposure_risk":      r["china_exposure_risk"],
            "supply_chain_bottlenecks": r["supply_chain_bottlenecks"],
            "restructuring_plans":      r["restructuring_plans"],
            "efficiency_initiatives":   r["efficiency_initiatives"],
            "mda_sentiment_score":      r["mda_sentiment_score"],
            "macro_concern_1":          concerns[0],
            "macro_concern_2":          concerns[1],
            "macro_concern_3":          concerns[2],
            "growing_segments":         r["growing_segments"],
            "shrinking_segments":       r["shrinking_segments"],
            "mda_char_count":           r["mda_char_count"],
            "risk_char_count":          r["risk_char_count"],
        }
    return index


# ── Merge ─────────────────────────────────────────────────────────────────────

def _merge(metrics: list[dict], insights: dict) -> list[dict]:
    merged, skipped = [], 0
    for m in metrics:
        nlp = insights.get((m["ticker"], m["fiscal_year"]))
        if nlp is None:
            skipped += 1
            continue
        merged.append({**m, **nlp})
    print(f"[Merge] matched={len(merged)}  skipped(no NLP)={skipped}")
    return merged


# ── SQLite writer ─────────────────────────────────────────────────────────────

def _write_sqlite(rows: list[dict]) -> None:
    conn = sqlite3.connect(DST_MASTER)
    conn.execute("DROP TABLE IF EXISTS alpha_q_master")
    conn.execute(_MASTER_DDL)
    conn.executemany(_INSERT, rows)
    conn.commit()
    conn.execute("ANALYZE")
    conn.close()
    print(f"[OK] alpha_q_master.db  ({len(rows)} rows)  → {DST_MASTER}")


# ── PostgreSQL export ─────────────────────────────────────────────────────────

_PG_DDL = """-- Alpha-Q master table — PostgreSQL import
-- Generated by 02_merge_to_master.py
-- Usage: psql -U <user> -d <dbname> -f alpha_q_master_pg.sql

CREATE TABLE IF NOT EXISTS alpha_q_master (
    ticker                   VARCHAR(16)   NOT NULL,
    fiscal_year              SMALLINT      NOT NULL,
    f_score                  SMALLINT,
    f1 SMALLINT, f2 SMALLINT, f3 SMALLINT, f4 SMALLINT, f5 SMALLINT,
    f6 SMALLINT, f7 SMALLINT, f8 SMALLINT, f9 SMALLINT,
    z_score                  NUMERIC(10,4),
    z_score_type             VARCHAR(8),
    roe                      NUMERIC(14,6),
    net_margin               NUMERIC(14,6),
    asset_turnover           NUMERIC(14,6),
    equity_multiplier        NUMERIC(14,6),
    market_cap               NUMERIC(22,2),
    tier                     VARCHAR(32),
    filing_type              VARCHAR(8),
    ai_investment_focus      TEXT,
    ai_monetization_status   TEXT,
    capex_guidance_tone      VARCHAR(32),
    china_exposure_risk      TEXT,
    supply_chain_bottlenecks TEXT,
    restructuring_plans      TEXT,
    efficiency_initiatives   TEXT,
    mda_sentiment_score      SMALLINT,
    macro_concern_1          TEXT,
    macro_concern_2          TEXT,
    macro_concern_3          TEXT,
    growing_segments         TEXT,
    shrinking_segments       TEXT,
    mda_char_count           INTEGER,
    risk_char_count          INTEGER,
    CONSTRAINT pk_aqm PRIMARY KEY (ticker, fiscal_year)
);
"""

_COL_ORDER = [
    "ticker", "fiscal_year",
    "f_score", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9",
    "z_score", "z_score_type",
    "roe", "net_margin", "asset_turnover", "equity_multiplier", "market_cap",
    "tier", "filing_type",
    "ai_investment_focus", "ai_monetization_status", "capex_guidance_tone",
    "china_exposure_risk", "supply_chain_bottlenecks", "restructuring_plans",
    "efficiency_initiatives", "mda_sentiment_score",
    "macro_concern_1", "macro_concern_2", "macro_concern_3",
    "growing_segments", "shrinking_segments",
    "mda_char_count", "risk_char_count",
]


def _pg_val(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, float):
        import math
        if not math.isfinite(v):
            return "NULL"
        return format(v, 'f')
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def _write_pg_sql(rows: list[dict]) -> None:
    col_list = ", ".join(_COL_ORDER)
    lines = [_PG_DDL, "BEGIN;"]
    for r in rows:
        vals = ", ".join(_pg_val(r.get(c)) for c in _COL_ORDER)
        lines.append(
            f"INSERT INTO alpha_q_master ({col_list}) VALUES ({vals})"
            f" ON CONFLICT (ticker, fiscal_year) DO NOTHING;"
        )
    lines.append("COMMIT;")
    DST_SQL.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] PostgreSQL export  ({len(rows)} rows)  → {DST_SQL}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    for path in (SRC_METRICS, SRC_INSIGHTS):
        if not path.exists():
            raise FileNotFoundError(
                f"Required database missing: {path}\n"
                "Run 01_fetch_yfinance_and_calc.py first."
            )

    metrics  = _load_metrics(SRC_METRICS)
    insights = _load_insights(SRC_INSIGHTS)
    rows     = _merge(metrics, insights)

    if not rows:
        print("[ERROR] No rows after merge — verify (ticker, fiscal_year) overlap.")
        return

    _write_sqlite(rows)
    _write_pg_sql(rows)


if __name__ == "__main__":
    main()
