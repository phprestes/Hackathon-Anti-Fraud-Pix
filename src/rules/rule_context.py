from dataclasses import dataclass


@dataclass(frozen=True)
class RuleContext:
    source_attempts_last_velocity_window: int
    source_sum_last_24h_cents: int
