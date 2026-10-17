from rules.base_rule import BaseRule, RuleResult
from rules.decision import TWO_FACTOR_REQUIRED


class CounterpartyFlaggedRule(BaseRule):
    code = "COUNTERPARTY_FLAGGED"
    family = "counterparty"

    def __init__(self, window_days: int) -> None:
        self.window_days = window_days

    def evaluate(self, pix, context) -> RuleResult | None:
        rejected = context.destination_rejected_by_others_last_window
        if pix.is_self_transfer or rejected < 1:
            return None

        return RuleResult(
            self.code,
            TWO_FACTOR_REQUIRED,
            f"Destino recebeu Pix reprovado de outro pagador nos últimos {self.window_days} dias.",
            {"rejected_by_others": rejected, "window_days": self.window_days},
        )
