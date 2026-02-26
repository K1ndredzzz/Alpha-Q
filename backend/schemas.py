from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict


# ── Quant Scores ──────────────────────────────────────────────────────────────

class QuantEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fiscal_year: int
    f_score: Optional[int] = None
    f1: Optional[int] = None
    f2: Optional[int] = None
    f3: Optional[int] = None
    f4: Optional[int] = None
    f5: Optional[int] = None
    f6: Optional[int] = None
    f7: Optional[int] = None
    f8: Optional[int] = None
    f9: Optional[int] = None
    z_score: Optional[float] = None
    z_score_type: Optional[Literal["standard", "prime"]] = None
    roe: Optional[float] = None
    net_margin: Optional[float] = None
    asset_turnover: Optional[float] = None
    equity_multiplier: Optional[float] = None
    market_cap: Optional[float] = None


class QuantScoresResponse(BaseModel):
    ticker: str
    series: list[QuantEntry]


# ── NLP Diff ──────────────────────────────────────────────────────────────────

class NlpDiffEntry(BaseModel):
    fiscal_year: int
    mda_sentiment_score: Optional[int] = None
    sentiment_delta: Optional[int] = None
    sentiment_trend: Optional[Literal["improving", "stable", "deteriorating"]] = None
    macro_concerns: list[Optional[str]]
    new_macro_concerns: list[str]
    dropped_macro_concerns: list[str]
    capex_guidance_tone: Optional[str] = None
    capex_tone_changed: Optional[bool] = None
    ai_investment_focus: Optional[str] = None
    ai_monetization_status: Optional[str] = None
    china_exposure_risk: Optional[str] = None
    supply_chain_bottlenecks: Optional[str] = None
    restructuring_plans: Optional[str] = None
    efficiency_initiatives: Optional[str] = None
    growing_segments: Optional[str] = None
    shrinking_segments: Optional[str] = None
    mda_char_count: Optional[int] = None
    risk_char_count: Optional[int] = None


class NlpDiffResponse(BaseModel):
    ticker: str
    series: list[NlpDiffEntry]


# ── Red Flags ─────────────────────────────────────────────────────────────────

class RedFlag(BaseModel):
    rule_id: str
    fiscal_year: int
    severity: Literal["MEDIUM", "HIGH", "CRITICAL"]
    title: str
    detail: str


class RedFlagsResponse(BaseModel):
    ticker: str
    flags: list[RedFlag]
    total: int


# ── Ticker List ───────────────────────────────────────────────────────────────

class TickerMeta(BaseModel):
    ticker: str
    tier: Optional[str] = None
    years_available: int


class TickerListResponse(BaseModel):
    tickers: list[TickerMeta]
    total: int
