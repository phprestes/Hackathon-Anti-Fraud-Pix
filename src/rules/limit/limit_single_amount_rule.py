from rules.core.base_rule import BaseRule, RuleResult
from rules.core.decision import TWO_FACTOR_REQUIRED


class LimitSingleAmountRule(BaseRule):
    code = "LIMIT_SINGLE_AMOUNT"
    family = "limit"

    def __init__(self, limit_cents: int, limit_legal_entity_cents: int) -> None:
        self.limit_cents = limit_cents
        self.limit_legal_entity_cents = limit_legal_entity_cents

    def evaluate(self, pix, context) -> RuleResult | None:
        limit = self.limit_legal_entity_cents if pix.is_legal_entity_source else self.limit_cents
        if pix.amount <= limit:
            return None

        return RuleResult(
            self.code,
            TWO_FACTOR_REQUIRED,
            f"Pix de R$ {pix.amount / 100:.2f} acima do teto unitário de R$ {limit / 100:.2f}.",
            {"amount_cents": pix.amount, "limit_cents": limit},
        )
