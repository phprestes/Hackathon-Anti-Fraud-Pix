import math

from rules.pix_snapshot import PixSnapshot
from rules.rule_context import RuleContext
from utils.statistics import haversine_km, negative_binomial_tail, robust_z

# Floor avoids dividing by ~0 when two Pix share the same instant.
MIN_ELAPSED_HOURS = 1 / 60


def amount_z(pix: PixSnapshot, context: RuleContext, min_history: int, min_scale: float) -> float | None:
    amounts = context.source_amounts_last_30d_cents
    if len(amounts) < min_history or pix.amount <= 0:
        return None

    # Log scale: amounts are multiplicative, so "2x the usual" weighs the same at any level.
    return robust_z([math.log(a) for a in amounts if a > 0], math.log(pix.amount), min_scale)


def geo_elapsed_hours(pix: PixSnapshot, context: RuleContext) -> float | None:
    if context.source_last_geolocation is None:
        return None
    previous_at = context.source_last_geolocation[2]
    return max((pix.transaction_date - previous_at).total_seconds() / 3600, MIN_ELAPSED_HOURS)


def geo_speed_kmh(pix: PixSnapshot, context: RuleContext) -> tuple[float, float] | None:
    previous = context.source_last_geolocation
    if previous is None or pix.latitude is None or pix.longitude is None:
        return None

    km = haversine_km(previous[0], previous[1], float(pix.latitude), float(pix.longitude))
    return km, km / geo_elapsed_hours(pix, context)


def poisson_tail(
    pix: PixSnapshot,
    context: RuleContext,
    window_minutes: int,
    lookback_days: int,
    prior_shape: float,
    prior_rate_hours: float,
    min_exposure_hours: float,
) -> tuple[int, float, float] | None:
    """Returns (k, tail, exposure_hours), or None when the payer is unknown or too new."""
    first_seen = context.source_first_seen
    if first_seen is None:
        return None

    window_hours = window_minutes / 60
    observed_hours = (pix.transaction_date - first_seen).total_seconds() / 3600 - window_hours
    exposure = max(0.0, min(lookback_days * 24, observed_hours))
    # New payers stay with VELOCITY_SOURCE_COUNT: a near-empty history makes the prior decide.
    if exposure < min_exposure_hours:
        return None

    k = context.source_attempts_poisson_window + 1
    shape = prior_shape + context.source_attempts_poisson_lookback
    rate = prior_rate_hours + exposure
    return k, negative_binomial_tail(k, shape, rate, window_hours), exposure
