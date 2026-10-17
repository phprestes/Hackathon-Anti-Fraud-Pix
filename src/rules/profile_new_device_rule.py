from rules.base_rule import BaseRule, RuleResult
from rules.decision import TWO_FACTOR_REQUIRED


class ProfileNewDeviceRule(BaseRule):
    code = "PROFILE_NEW_DEVICE"
    family = "profile"

    def __init__(self, min_amount_cents: int) -> None:
        self.min_amount_cents = min_amount_cents

    def evaluate(self, pix, context) -> RuleResult | None:
        if context.source_history_size < 1 or context.device_seen_for_source:
            return None
        if pix.amount < self.min_amount_cents:
            return None

        return RuleResult(
            self.code,
            TWO_FACTOR_REQUIRED,
            f"Dispositivo nunca usado por este pagador em Pix de R$ {pix.amount / 100:.2f}.",
            {"history_size": context.source_history_size, "amount_cents": pix.amount},
        )
