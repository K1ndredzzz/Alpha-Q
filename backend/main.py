import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Connection

from .db import get_db, probe
from .queries import (
    fetch_quant_rows,
    fetch_nlp_rows,
    fetch_red_flag_rows,
    fetch_all_tickers,
)
from .schemas import (
    QuantScoresResponse, QuantEntry,
    NlpDiffResponse,
    RedFlagsResponse, RedFlag,
    TickerListResponse, TickerMeta,
)
from . import nlp_diff as _nlp
from .red_flags import evaluate as _eval_flags


@asynccontextmanager
async def lifespan(_app: FastAPI):
    probe()
    print(f"[alpha-q] DB connected: {os.environ.get('DATABASE_URL', '/data/alpha_q_master.db')}")
    yield


app = FastAPI(title="Alpha-Q Quant API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── GET /api/v1/tickers ───────────────────────────────────────────────────────

@app.get("/api/v1/tickers", response_model=TickerListResponse)
def list_tickers(conn: Connection = Depends(get_db)):
    rows = fetch_all_tickers(conn)
    return TickerListResponse(
        tickers=[TickerMeta(**r) for r in rows],
        total=len(rows),
    )


# ── GET /api/v1/ticker/{symbol}/quant_scores ─────────────────────────────────

@app.get("/api/v1/ticker/{symbol}/quant_scores", response_model=QuantScoresResponse)
def quant_scores(symbol: str, conn: Connection = Depends(get_db)):
    rows = fetch_quant_rows(conn, symbol)
    return QuantScoresResponse(
        ticker=symbol.upper(),
        series=[QuantEntry(**r) for r in rows],
    )


# ── GET /api/v1/ticker/{symbol}/nlp_diff ─────────────────────────────────────

@app.get("/api/v1/ticker/{symbol}/nlp_diff", response_model=NlpDiffResponse)
def nlp_diff(symbol: str, conn: Connection = Depends(get_db)):
    rows = fetch_nlp_rows(conn, symbol)
    return NlpDiffResponse(
        ticker=symbol.upper(),
        series=_nlp.compute(rows),
    )


# ── GET /api/v1/ticker/{symbol}/red_flags ────────────────────────────────────

@app.get("/api/v1/ticker/{symbol}/red_flags", response_model=RedFlagsResponse)
def red_flags(symbol: str, conn: Connection = Depends(get_db)):
    rows = fetch_red_flag_rows(conn, symbol)
    flags = _eval_flags(rows)
    return RedFlagsResponse(
        ticker=symbol.upper(),
        flags=flags,
        total=len(flags),
    )
