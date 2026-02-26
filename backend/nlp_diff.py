"""
NLP semantic diff computation.
All functions are pure — no I/O, no side effects.
"""
from __future__ import annotations
from typing import Optional, Literal
from .schemas import NlpDiffEntry


def _macro_set(row: dict) -> set[str]:
    return {
        row[k]
        for k in ("macro_concern_1", "macro_concern_2", "macro_concern_3")
        if row.get(k) is not None
    }


def _sentiment_trend(
    scores: list[Optional[int]],
) -> Optional[Literal["improving", "stable", "deteriorating"]]:
    """
    Classify trend from the last 3 non-None scores ending at the current index.
    Requires at least 2 data points.
    """
    valid = [s for s in scores if s is not None][-3:]
    if len(valid) < 2:
        return None
    delta = valid[-1] - valid[0]
    if delta >= 1:
        return "improving"
    if delta <= -1:
        return "deteriorating"
    return "stable"


def compute(rows: list[dict]) -> list[NlpDiffEntry]:
    """
    Compute YoY NLP diffs for a ticker's full history.
    `rows` must be pre-sorted ascending by fiscal_year.
    """
    all_scores: list[Optional[int]] = [r.get("mda_sentiment_score") for r in rows]
    result: list[NlpDiffEntry] = []

    for i, row in enumerate(rows):
        prior = rows[i - 1] if i > 0 else None
        cur_score: Optional[int] = row.get("mda_sentiment_score")

        # Sentiment delta
        sentiment_delta: Optional[int] = None
        if prior is not None:
            prior_score = prior.get("mda_sentiment_score")
            if cur_score is not None and prior_score is not None:
                sentiment_delta = cur_score - prior_score

        # Macro concern set diff
        cur_concerns = _macro_set(row)
        prior_concerns = _macro_set(prior) if prior is not None else set()
        new_macro = sorted(cur_concerns - prior_concerns)
        dropped_macro = sorted(prior_concerns - cur_concerns)

        # Capex tone change
        capex_tone_changed: Optional[bool] = None
        if prior is not None:
            capex_tone_changed = (
                row.get("capex_guidance_tone") != prior.get("capex_guidance_tone")
            )

        # Sentiment trend (uses only data up to current year)
        trend = _sentiment_trend(all_scores[: i + 1])

        result.append(NlpDiffEntry(
            fiscal_year=row["fiscal_year"],
            mda_sentiment_score=cur_score,
            sentiment_delta=sentiment_delta,
            sentiment_trend=trend,
            macro_concerns=[
                row.get("macro_concern_1"),
                row.get("macro_concern_2"),
                row.get("macro_concern_3"),
            ],
            new_macro_concerns=new_macro,
            dropped_macro_concerns=dropped_macro,
            capex_guidance_tone=row.get("capex_guidance_tone"),
            capex_tone_changed=capex_tone_changed,
            ai_investment_focus=row.get("ai_investment_focus"),
            ai_monetization_status=row.get("ai_monetization_status"),
            china_exposure_risk=row.get("china_exposure_risk"),
            supply_chain_bottlenecks=row.get("supply_chain_bottlenecks"),
            restructuring_plans=row.get("restructuring_plans"),
            efficiency_initiatives=row.get("efficiency_initiatives"),
            growing_segments=row.get("growing_segments"),
            shrinking_segments=row.get("shrinking_segments"),
            mda_char_count=row.get("mda_char_count"),
            risk_char_count=row.get("risk_char_count"),
        ))

    return result
