from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RuleContext:
    source_attempts_last_velocity_window: int
    source_sum_last_24h_cents: int
    source_history_size: int
    device_seen_for_source: bool
    destination_seen_for_source: bool
    device_distinct_other_sources_last_24h: int
    destination_distinct_other_sources_last_1h: int
    source_amounts_last_30d_cents: tuple[int, ...]
    source_attempts_poisson_window: int
    source_attempts_poisson_lookback: int
    source_first_seen: datetime | None
    source_last_geolocation: tuple[float, float, datetime] | None
    source_new_destinations_last_24h: int
    destination_used_before: bool
    source_small_attempts_last_24h: int
    destination_rejected_by_others_last_window: int
    destination_graph_risk: float | None = None
    destination_graph_risk_age_minutes: float | None = None
    destination_graph_risk_contributions: tuple[tuple[str, float], ...] = ()
