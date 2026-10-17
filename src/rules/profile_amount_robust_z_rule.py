import statistics

from rules.base_rule import BaseRule, RuleResult
from rules.decision import TWO_FACTOR_REQUIRED
from rules.signals import amount_z


class ProfileAmountRobustZRule(BaseRule):
    code = "PROFILE_AMOUNT_ROBUST_Z"
    family = "profile"

    def __init__(self, min_history: int, min_scale: float, z_threshold: float) -> None:
        self.min_history = min_history
        self.min_scale = min_scale
        self.z_threshold = z_threshold

    def evaluate(self, pix, context) -> RuleResult | None:
        z = amount_z(pix, context, self.min_history, self.min_scale)
        if z is None or z <= self.z_threshold:
            return None

        amounts = context.source_amounts_last_30d_cents
        z_text = f"{z:.1f}".replace(".", ",")
        median = round(statistics.median(amounts))
        return RuleResult(
            self.code,
            TWO_FACTOR_REQUIRED,
            f"Valor {z_text} desvios acima do padrão do pagador.",
            {"z": round(z, 2), "median_cents": median, "history_size": len(amounts)},
        )
