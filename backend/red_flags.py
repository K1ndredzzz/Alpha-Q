"""
M3 Red Flag rule engine.
Pure functions: evaluate(rows) -> list[RedFlag]
None values on required fields short-circuit every rule (no false positives).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional
from .schemas import RedFlag

# RF-003: Z-Score distress thresholds per Altman model variant
_Z_THRESHOLD = {"standard": 1.81, "prime": 1.23}
_LIQUIDITY_KW = {"liquidity", "debt", "credit", "default"}


@dataclass(frozen=True, slots=True)
class Row:
    fiscal_year: int
    f_score: Optional[int]
    z_score: Optional[float]
    z_score_type: Optional[str]
    net_margin: Optional[float]
    roe: Optional[float]
    mda_sentiment_score: Optional[int]
    macro_concern_1: Optional[str]
    macro_concern_2: Optional[str]
    macro_concern_3: Optional[str]
    efficiency_initiatives: Optional[str]

    @classmethod
    def from_dict(cls, d: dict) -> "Row":
        return cls(**{f: d.get(f) for f in cls.__dataclass_fields__})

    def macro_concerns(self) -> list[str]:
        return [
            c for c in (self.macro_concern_1, self.macro_concern_2, self.macro_concern_3)
            if c is not None
        ]


# ── Rule functions ────────────────────────────────────────────────────────────

def _rf001(cur: Row, _prior: Optional[Row]) -> Optional[RedFlag]:
    if cur.f_score is None or cur.mda_sentiment_score is None:
        return None
    if cur.f_score <= 3 and cur.mda_sentiment_score <= 4:
        return RedFlag(
            rule_id="RF-001",
            fiscal_year=cur.fiscal_year,
            severity="MEDIUM",
            title="Low F-Score + Negative Management Tone",
            detail=f"F-Score={cur.f_score}, MDA sentiment={cur.mda_sentiment_score}",
        )
    return None


def _rf002(cur: Row, prior: Optional[Row]) -> Optional[RedFlag]:
    if prior is None or cur.f_score is None or prior.f_score is None:
        return None
    drop = prior.f_score - cur.f_score
    if drop >= 3:
        return RedFlag(
            rule_id="RF-002",
            fiscal_year=cur.fiscal_year,
            severity="HIGH",
            title="Sharp F-Score Deterioration",
            detail=(
                f"F-Score dropped {drop} pts: "
                f"{prior.f_score} ({cur.fiscal_year - 1}) → {cur.f_score} ({cur.fiscal_year})"
            ),
        )
    return None


def _rf003(cur: Row, _prior: Optional[Row]) -> Optional[RedFlag]:
    if cur.z_score is None or cur.z_score_type is None:
        return None
    threshold = _Z_THRESHOLD.get(cur.z_score_type, 1.81)
    if cur.z_score >= threshold:
        return None
    matching = next(
        (c for c in cur.macro_concerns() if any(kw in c.lower() for kw in _LIQUIDITY_KW)),
        None,
    )
    if matching is None:
        return None
    return RedFlag(
        rule_id="RF-003",
        fiscal_year=cur.fiscal_year,
        severity="CRITICAL",
        title="Z-Score Distress + Liquidity Concern",
        detail=(
            f"Z-Score={cur.z_score:.4f} ({cur.z_score_type}, threshold={threshold}). "
            f"Matching concern: '{matching}'"
        ),
    )


def _rf004(cur: Row, _prior: Optional[Row]) -> Optional[RedFlag]:
    if cur.net_margin is None or cur.mda_sentiment_score is None:
        return None
    if cur.net_margin < 0 and cur.mda_sentiment_score >= 7:
        return RedFlag(
            rule_id="RF-004",
            fiscal_year=cur.fiscal_year,
            severity="HIGH",
            title="Earnings-Tone Divergence",
            detail=(
                f"Negative net margin ({cur.net_margin:.2%}) "
                f"while management tone is positive (score={cur.mda_sentiment_score})"
            ),
        )
    return None


def _rf005(cur: Row, _prior: Optional[Row]) -> Optional[RedFlag]:
    if cur.roe is None or cur.efficiency_initiatives is None:
        return None
    if cur.roe < -0.1:
        snippet = cur.efficiency_initiatives[:80]
        return RedFlag(
            rule_id="RF-005",
            fiscal_year=cur.fiscal_year,
            severity="MEDIUM",
            title="Operational Emergency Signal",
            detail=f"ROE={cur.roe:.2%}. Efficiency signal: '{snippet}'",
        )
    return None


_RULES: list[Callable[[Row, Optional[Row]], Optional[RedFlag]]] = [
    _rf001, _rf002, _rf003, _rf004, _rf005,
]


# ── Public entry point ────────────────────────────────────────────────────────

def evaluate(rows_dicts: list[dict]) -> list[RedFlag]:
    """
    Run all 5 rules across every year in a ticker's history (sorted ascending).
    Returns all triggered RedFlags in (year, rule) order.
    """
    rows = [Row.from_dict(d) for d in rows_dicts]
    flags: list[RedFlag] = []
    for i, cur in enumerate(rows):
        prior = rows[i - 1] if i > 0 else None
        for rule in _RULES:
            flag = rule(cur, prior)
            if flag is not None:
                flags.append(flag)
    return flags
