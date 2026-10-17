from rules.base_rule import BaseRule, RuleResult
from rules.decision import TWO_FACTOR_REQUIRED


class AmountSourceDailySumRule(BaseRule):
    code = "AMOUNT_SOURCE_DAILY_SUM"
    family = "amount"

    def __init__(self, limit_cents: int, limit_legal_entity_cents: int) -> None:
        self.limit_cents = limit_cents
        self.limit_legal_entity_cents = limit_legal_entity_cents

    def evaluate(self, pix, context) -> RuleResult | None:
        total = context.source_sum_last_24h_cents + pix.amount
        limit = self.limit_legal_entity_cents if pix.is_legal_entity_source else self.limit_cents

        if total <= limit:
            return None

        return RuleResult(
            self.code,
            TWO_FACTOR_REQUIRED,
            f"Soma de R$ {total / 100:.2f} em 24 horas acima do teto de R$ {limit / 100:.2f}.",
            {"sum_24h_cents": total, "limit_cents": limit},
        )
