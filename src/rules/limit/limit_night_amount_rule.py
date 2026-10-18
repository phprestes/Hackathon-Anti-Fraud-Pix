from rules.core.base_rule import BaseRule, RuleResult
from rules.core.decision import TWO_FACTOR_REQUIRED


class LimitNightAmountRule(BaseRule):
    code = "LIMIT_NIGHT_AMOUNT"
    family = "limit"

    def __init__(self, start_hour: int, end_hour: int, limit_cents: int) -> None:
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.limit_cents = limit_cents

    def evaluate(self, pix, context) -> RuleResult | None:
        # The night limit is a retail (individual) rule.
        if pix.is_legal_entity_source:
            return None

        # Local hour: transaction_date keeps the offset it arrived with.
        hour = pix.transaction_date.hour
        is_night = hour >= self.start_hour or hour < self.end_hour
        if not is_night or pix.amount <= self.limit_cents:
            return None

        return RuleResult(
            self.code,
            TWO_FACTOR_REQUIRED,
            f"Pix de R$ {pix.amount / 100:.2f} às {hour}h acima do limite noturno de R$ {self.limit_cents / 100:.2f}.",
            {"local_hour": hour, "amount_cents": pix.amount, "limit_cents": self.limit_cents},
        )
