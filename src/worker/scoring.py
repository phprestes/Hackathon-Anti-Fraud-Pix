import math

from constants import (
    GRAPH_RISK_AMOUNT_UNIT_CENTS,
    GRAPH_RISK_BIAS,
    GRAPH_RISK_NEW_ACCOUNT_DAYS,
    GRAPH_RISK_W_AMOUNT,
    GRAPH_RISK_W_DISPERSION,
    GRAPH_RISK_W_NEW_ACCOUNT,
    GRAPH_RISK_W_PAYERS,
    GRAPH_RISK_W_TWO_HOP,
)


def contributions(features: dict) -> dict[str, float]:
    """Each feature's share of the logit; log1p damps counts so one huge funnel does not saturate alone."""
    return {
        "in_distinct_payers_24h": GRAPH_RISK_W_PAYERS * math.log1p(features["in_distinct_payers_24h"]),
        "dispersion_out_distinct_6h": GRAPH_RISK_W_DISPERSION * math.log1p(features["dispersion_out_distinct_6h"]),
        "two_hop_flagged": GRAPH_RISK_W_TWO_HOP * math.log1p(features["two_hop_flagged"]),
        "in_amount_24h_cents": GRAPH_RISK_W_AMOUNT * math.log1p(features["in_amount_24h_cents"] / GRAPH_RISK_AMOUNT_UNIT_CENTS),
        "account_age_days": GRAPH_RISK_W_NEW_ACCOUNT if features["account_age_days"] < GRAPH_RISK_NEW_ACCOUNT_DAYS else 0.0,
    }


def score(features: dict) -> tuple[float, dict[str, float]]:
    parts = contributions(features)
    logit = GRAPH_RISK_BIAS + sum(parts.values())
    return round(1.0 / (1.0 + math.exp(-logit)), 5), {name: round(value, 4) for name, value in parts.items()}
