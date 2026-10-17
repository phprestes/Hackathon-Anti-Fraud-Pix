from rules.base_rule import BaseRule, RuleResult
from rules.decision import REJECTED


class TypologyMuleRule(BaseRule):
    code = "TYPOLOGY_MULE"
    family = "typology"

    def __init__(self, min_age_days: int, min_sources_1h: int) -> None:
        self.min_age_days = min_age_days
        self.min_sources_1h = min_sources_1h

    def evaluate(self, pix, context) -> RuleResult | None:
        if pix.is_self_transfer:
            return None

        age_days = (pix.transaction_date - pix.destination_opening_date).days
        sources = context.destination_distinct_other_sources_last_1h + 1
        if age_days >= self.min_age_days or sources < self.min_sources_1h:
            return None

        return RuleResult(
            self.code,
            REJECTED,
            f"Padrão de conta laranja: conta de {age_days} dias recebendo de {sources} pagadores em 1 h.",
            {"destination_age_days": age_days, "distinct_sources_1h": sources},
        )
