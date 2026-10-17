import math
import statistics

from constants import (
    RULE_POISSON_LOOKBACK_DAYS,
    RULE_POISSON_MIN_EXPOSURE_HOURS,
    RULE_POISSON_PRIOR_RATE_HOURS,
    RULE_POISSON_PRIOR_SHAPE,
    RULE_POISSON_WINDOW_MINUTES,
    RULE_PROFILE_MIN_HISTORY,
    RULE_PROFILE_MIN_SCALE_PERCENT,
)
from rules.pix_snapshot import PixSnapshot
from rules.rule_context import RuleContext
from rules.signals import amount_z, geo_speed_kmh, poisson_tail

FEATURE_NAMES = [
    "amount",
    "log_amount",
    "local_hour",
    "weekday",
    "source_age_days",
    "destination_age_days",
    "is_self_transfer",
    "is_legal_entity_source",
    "has_geolocation",
    "source_attempts_last_velocity_window",
    "source_sum_last_24h_cents",
    "source_history_size",
    "device_seen_for_source",
    "destination_seen_for_source",
    "device_distinct_other_sources_last_24h",
    "destination_distinct_other_sources_last_1h",
    "source_attempts_poisson_window",
    "source_attempts_poisson_lookback",
    "source_new_destinations_last_24h",
    "destination_used_before",
    "source_small_attempts_last_24h",
    "destination_rejected_by_others_last_window",
    "history_30d_size",
    "history_30d_median_cents",
    "amount_robust_z",
    "hours_since_first_seen",
    "km_since_last_geolocation",
    "speed_kmh_since_last_geolocation",
    "poisson_tail_log10",
]

# Floor so a zero tail does not become -inf.
MIN_TAIL = 1e-300


def build_features(pix: PixSnapshot, context: RuleContext) -> dict[str, float]:
    amounts = context.source_amounts_last_30d_cents
    z = amount_z(pix, context, RULE_PROFILE_MIN_HISTORY, RULE_PROFILE_MIN_SCALE_PERCENT / 100)
    travel = geo_speed_kmh(pix, context)
    poisson = poisson_tail(
        pix,
        context,
        RULE_POISSON_WINDOW_MINUTES,
        RULE_POISSON_LOOKBACK_DAYS,
        RULE_POISSON_PRIOR_SHAPE,
        RULE_POISSON_PRIOR_RATE_HOURS,
        RULE_POISSON_MIN_EXPOSURE_HOURS,
    )
    first_seen = context.source_first_seen

    values = {
        "amount": pix.amount,
        "log_amount": math.log(pix.amount) if pix.amount > 0 else 0.0,
        "local_hour": pix.transaction_date.hour,
        "weekday": pix.transaction_date.weekday(),
        "source_age_days": (pix.transaction_date - pix.source_opening_date).days,
        "destination_age_days": (pix.transaction_date - pix.destination_opening_date).days,
        "is_self_transfer": pix.is_self_transfer,
        "is_legal_entity_source": pix.is_legal_entity_source,
        "has_geolocation": pix.latitude is not None and pix.longitude is not None,
        "source_attempts_last_velocity_window": context.source_attempts_last_velocity_window,
        "source_sum_last_24h_cents": context.source_sum_last_24h_cents,
        "source_history_size": context.source_history_size,
        "device_seen_for_source": context.device_seen_for_source,
        "destination_seen_for_source": context.destination_seen_for_source,
        "device_distinct_other_sources_last_24h": context.device_distinct_other_sources_last_24h,
        "destination_distinct_other_sources_last_1h": context.destination_distinct_other_sources_last_1h,
        "source_attempts_poisson_window": context.source_attempts_poisson_window,
        "source_attempts_poisson_lookback": context.source_attempts_poisson_lookback,
        "source_new_destinations_last_24h": context.source_new_destinations_last_24h,
        "destination_used_before": context.destination_used_before,
        "source_small_attempts_last_24h": context.source_small_attempts_last_24h,
        "destination_rejected_by_others_last_window": context.destination_rejected_by_others_last_window,
        "history_30d_size": len(amounts),
        "history_30d_median_cents": statistics.median(amounts) if amounts else 0,
        "amount_robust_z": z if z is not None else 0.0,
        "hours_since_first_seen": (
            (pix.transaction_date - first_seen).total_seconds() / 3600 if first_seen is not None else -1
        ),
        "km_since_last_geolocation": travel[0] if travel is not None else -1,
        "speed_kmh_since_last_geolocation": travel[1] if travel is not None else -1,
        "poisson_tail_log10": math.log10(max(poisson[1], MIN_TAIL)) if poisson is not None else 0.0,
    }
    return {name: _number(values[name]) for name in FEATURE_NAMES}


def _number(value) -> float:
    if isinstance(value, bool):
        return int(value)
    return round(value, 6) if isinstance(value, float) else value
