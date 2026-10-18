from rules.core.base_rule import BaseRule, RuleResult
from rules.core.decision import TWO_FACTOR_REQUIRED


class ProfileNewSourceAccountRule(BaseRule):
    code = "PROFILE_NEW_SOURCE_ACCOUNT"
    family = "profile"

    def __init__(self, min_age_days: int, new_max_amount_cents: int) -> None:
        self.min_age_days = min_age_days
        self.new_max_amount_cents = new_max_amount_cents

    def evaluate(self, pix, context) -> RuleResult | None:
        age_days = (pix.transaction_date - pix.source_opening_date).days
        if age_days >= self.min_age_days or pix.amount <= self.new_max_amount_cents:
            return None

        return RuleResult(
            self.code,
            TWO_FACTOR_REQUIRED,
            f"Conta de origem aberta há {age_days} dias movimentando R$ {pix.amount / 100:.2f}.",
            {"source_age_days": age_days, "amount_cents": pix.amount},
        )
