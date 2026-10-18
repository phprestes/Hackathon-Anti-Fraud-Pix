from rules.core.base_rule import BaseRule, RuleResult
from rules.core.decision import REJECTED


class CounterpartyFanInRule(BaseRule):
    code = "COUNTERPARTY_FAN_IN"
    family = "counterparty"

    def __init__(self, max_sources: int) -> None:
        self.max_sources = max_sources

    def evaluate(self, pix, context) -> RuleResult | None:
        if pix.is_self_transfer:
            return None

        sources = context.destination_distinct_other_sources_last_1h + 1
        if sources <= self.max_sources:
            return None

        return RuleResult(
            self.code,
            REJECTED,
            f"{sources} pagadores distintos para o mesmo destino em 1 hora.",
            {"distinct_sources_1h": sources, "max_sources": self.max_sources},
        )
