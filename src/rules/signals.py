import math

from rules.pix_snapshot import PixSnapshot
from rules.rule_context import RuleContext
from utils.statistics import haversine_km, robust_z

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
