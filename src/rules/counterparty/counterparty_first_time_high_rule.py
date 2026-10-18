from rules.core.base_rule import BaseRule, RuleResult
from rules.core.decision import TWO_FACTOR_REQUIRED


class CounterpartyFirstTimeHighRule(BaseRule):
    code = "COUNTERPARTY_FIRST_TIME_HIGH"
    family = "counterparty"

    def __init__(self, min_amount_cents: int) -> None:
        self.min_amount_cents = min_amount_cents

    def evaluate(self, pix, context) -> RuleResult | None:
        if pix.is_self_transfer:
            return None
        if context.source_history_size < 1 or context.destination_seen_for_source:
            return None
        if pix.amount <= self.min_amount_cents:
            return None

        return RuleResult(
            self.code,
            TWO_FACTOR_REQUIRED,
            f"Primeiro Pix para este destino, no valor de R$ {pix.amount / 100:.2f}.",
            {"amount_cents": pix.amount, "history_size": context.source_history_size},
        )
