from rules.core.base_rule import BaseRule, RuleResult
from rules.core.decision import REJECTED, TWO_FACTOR_REQUIRED


class CounterpartyNewAccountRule(BaseRule):
    code = "COUNTERPARTY_NEW_ACCOUNT"
    family = "counterparty"

    def __init__(self, min_age_days: int, critical_age_days: int, new_max_amount_cents: int) -> None:
        self.min_age_days = min_age_days
        self.critical_age_days = critical_age_days
        self.new_max_amount_cents = new_max_amount_cents

    def evaluate(self, pix, context) -> RuleResult | None:
        if pix.is_self_transfer:
            return None

        age_days = (pix.transaction_date - pix.destination_opening_date).days
        if age_days >= self.min_age_days:
            return None

        decision = TWO_FACTOR_REQUIRED
        if age_days < self.critical_age_days and pix.amount > self.new_max_amount_cents:
            decision = REJECTED

        return RuleResult(
            self.code,
            decision,
            f"Conta de destino aberta há {age_days} dias.",
            {"destination_age_days": age_days},
        )
