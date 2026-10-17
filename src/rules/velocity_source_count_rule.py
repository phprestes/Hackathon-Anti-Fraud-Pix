from rules.base_rule import BaseRule, RuleResult
from rules.decision import REJECTED, TWO_FACTOR_REQUIRED


class VelocitySourceCountRule(BaseRule):
    code = "VELOCITY_SOURCE_COUNT"
    family = "velocity"

    def __init__(self, window_minutes: int, two_factor_count: int, reject_count: int) -> None:
        self.window_minutes = window_minutes
        self.two_factor_count = two_factor_count
        self.reject_count = reject_count

    def evaluate(self, pix, context) -> RuleResult | None:
        attempts = context.source_attempts_last_velocity_window + 1

        if attempts >= self.reject_count:
            decision = REJECTED
        elif attempts >= self.two_factor_count:
            decision = TWO_FACTOR_REQUIRED
        else:
            return None

        return RuleResult(
            self.code,
            decision,
            f"{attempts} Pix do mesmo pagador em {self.window_minutes} minutos.",
            {"attempts_in_window": attempts, "window_minutes": self.window_minutes},
        )
