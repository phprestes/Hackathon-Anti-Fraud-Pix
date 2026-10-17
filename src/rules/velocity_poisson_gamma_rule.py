from rules.base_rule import BaseRule, RuleResult
from rules.decision import TWO_FACTOR_REQUIRED
from utils.statistics import negative_binomial_tail


class VelocityPoissonGammaRule(BaseRule):
    code = "VELOCITY_POISSON_GAMMA"
    family = "velocity"

    def __init__(
        self,
        window_minutes: int,
        lookback_days: int,
        prior_shape: float,
        prior_rate_hours: float,
        tail_threshold: float,
        min_exposure_hours: float,
    ) -> None:
        self.window_minutes = window_minutes
        self.lookback_days = lookback_days
        self.prior_shape = prior_shape
        self.prior_rate_hours = prior_rate_hours
        self.tail_threshold = tail_threshold
        self.min_exposure_hours = min_exposure_hours

    def evaluate(self, pix, context) -> RuleResult | None:
        first_seen = context.source_first_seen
        if first_seen is None:
            return None

        window_hours = self.window_minutes / 60
        observed_hours = (pix.transaction_date - first_seen).total_seconds() / 3600 - window_hours
        exposure = max(0.0, min(self.lookback_days * 24, observed_hours))
        # New payers stay with VELOCITY_SOURCE_COUNT: a near-empty history makes the prior decide.
        if exposure < self.min_exposure_hours:
            return None

        k = context.source_attempts_poisson_window + 1
        shape = self.prior_shape + context.source_attempts_poisson_lookback
        rate = self.prior_rate_hours + exposure
        tail = negative_binomial_tail(k, shape, rate, window_hours)
        if tail >= self.tail_threshold:
            return None

        tail_text = f"{tail:.4f}".replace(".", ",")
        return RuleResult(
            self.code,
            TWO_FACTOR_REQUIRED,
            f"{k} Pix em {self.window_minutes} min é improvável para este pagador (p = {tail_text}).",
            {"k": k, "tail": float(f"{tail:.3e}"), "exposure_hours": round(exposure, 1)},
        )
