from rules.core.base_rule import BaseRule, RuleResult
from rules.core.decision import TWO_FACTOR_REQUIRED
from rules.core.signals import poisson_tail


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
        evaluated = poisson_tail(
            pix,
            context,
            self.window_minutes,
            self.lookback_days,
            self.prior_shape,
            self.prior_rate_hours,
            self.min_exposure_hours,
        )
        if evaluated is None:
            return None

        k, tail, exposure = evaluated
        if tail >= self.tail_threshold:
            return None

        tail_text = f"{tail:.4f}".replace(".", ",")
        return RuleResult(
            self.code,
            TWO_FACTOR_REQUIRED,
            f"{k} Pix em {self.window_minutes} min é improvável para este pagador (p = {tail_text}).",
            {"k": k, "tail": float(f"{tail:.3e}"), "exposure_hours": round(exposure, 1)},
        )
