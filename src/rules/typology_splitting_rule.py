from rules.base_rule import BaseRule, RuleResult
from rules.decision import REJECTED


class TypologySplittingRule(BaseRule):
    code = "TYPOLOGY_SPLITTING"
    family = "typology"

    def __init__(
        self, max_amount_cents: int, min_count: int, min_destinations: int, limit_cents: int, limit_legal_entity_cents: int
    ) -> None:
        self.max_amount_cents = max_amount_cents
        self.min_count = min_count
        self.min_destinations = min_destinations
        self.limit_cents = limit_cents
        self.limit_legal_entity_cents = limit_legal_entity_cents

    def evaluate(self, pix, context) -> RuleResult | None:
        if pix.amount > self.max_amount_cents:
            return None

        count = context.source_small_attempts_last_24h + 1
        # Assumes the current destination is new: whether it repeats a past one is not in the context.
        destinations = context.source_distinct_destinations_last_24h + 1
        total = context.source_sum_last_24h_cents + pix.amount
        limit = self.limit_legal_entity_cents if pix.is_legal_entity_source else self.limit_cents
        if count < self.min_count or destinations < self.min_destinations or total <= limit:
            return None

        money = f"{total / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return RuleResult(
            self.code,
            REJECTED,
            f"Padrão de fracionamento: {count} Pix pequenos para {destinations} destinos "
            f"somando R$ {money} em 24 h.",
            {"small_count_24h": count, "destinations_24h": destinations, "sum_24h_cents": total, "limit_cents": limit},
        )
