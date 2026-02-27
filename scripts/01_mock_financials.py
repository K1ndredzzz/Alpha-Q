import sqlite3
import json
import random
from pathlib import Path

# Paths
ROOT = Path(__file__).parent.parent
DB_INSIGHTS = ROOT / "data/insights.jsonl"
DB_OUT = ROOT / "data/financial_metrics.db"

# Mock logic
def generate_mock_financials(ticker: str, year: int):
    # Deterministic random based on ticker+year
    seed = sum(ord(c) for c in ticker) + year
    random.seed(seed)

    # Realistic ranges
    f_score = random.choices(range(0, 10), weights=[1, 2, 5, 10, 15, 20, 20, 15, 10, 2])[0]
    z_score = random.uniform(0.5, 5.0)

    # Financial metrics
    roe = random.uniform(-0.1, 0.4)
    net_margin = random.uniform(0.05, 0.3)
    asset_turnover = random.uniform(0.5, 2.0)
    equity_multiplier = roe / (net_margin * asset_turnover) if net_margin * asset_turnover != 0 else 1.5
    market_cap = random.uniform(1e9, 2e12)

    return {
        "ticker": ticker,
        "fiscal_year": year,
        "f_score": f_score,
        "f1": 1 if f_score > 0 else 0, # simplified
        "f2": 1, "f3": 1, "f4": 1, "f5": 0, "f6": 1, "f7": 0, "f8": 1, "f9": 1,
        "z_score": z_score,
        "z_score_type": "prime" if ticker in ["JPM", "BAC"] else "standard",
        "roe": roe,
        "net_margin": net_margin,
        "asset_turnover": asset_turnover,
        "equity_multiplier": equity_multiplier,
        "market_cap": market_cap
    }

DDL = """
CREATE TABLE IF NOT EXISTS financial_metrics (
    ticker TEXT,
    fiscal_year INTEGER,
    f_score INTEGER, f1 INTEGER, f2 INTEGER, f3 INTEGER, f4 INTEGER, f5 INTEGER, f6 INTEGER, f7 INTEGER, f8 INTEGER, f9 INTEGER,
    z_score REAL, z_score_type TEXT,
    roe REAL, net_margin REAL, asset_turnover REAL, equity_multiplier REAL, market_cap REAL,
    PRIMARY KEY (ticker, fiscal_year)
);
"""

INSERT = """
INSERT OR REPLACE INTO financial_metrics
(ticker, fiscal_year, f_score, f1, f2, f3, f4, f5, f6, f7, f8, f9, z_score, z_score_type, roe, net_margin, asset_turnover, equity_multiplier, market_cap)
VALUES
(:ticker, :fiscal_year, :f_score, :f1, :f2, :f3, :f4, :f5, :f6, :f7, :f8, :f9, :z_score, :z_score_type, :roe, :net_margin, :asset_turnover, :equity_multiplier, :market_cap)
"""

def main():
    print(f"Reading tickers from {DB_INSIGHTS}...")
    tickers_years = set()

    # Read unique ticker/year pairs from insights
    if not DB_INSIGHTS.exists():
        print(f"[ERROR] {DB_INSIGHTS} not found.")
        return

    with open(DB_INSIGHTS, "r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
                # Map 'year' to 'fiscal_year'
                y = row.get("fiscal_year") or row.get("year")
                if y:
                    tickers_years.add((row["ticker"], int(y)))
            except:
                pass

    print(f"Found {len(tickers_years)} ticker/year pairs.")

    metrics = []
    for t, y in tickers_years:
        metrics.append(generate_mock_financials(t, y))

    with sqlite3.connect(DB_OUT) as conn:
        conn.execute(DDL)
        conn.executemany(INSERT, metrics)
        conn.commit()

    print(f"[OK] Generated {len(metrics)} mock financial records in {DB_OUT}")

if __name__ == "__main__":
    main()
