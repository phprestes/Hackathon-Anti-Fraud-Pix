from rules.base_rule import BaseRule, RuleResult
from rules.decision import REJECTED, TWO_FACTOR_REQUIRED

TOP_FEATURES = 2


class CounterpartyGraphRiskRule(BaseRule):
    code = "COUNTERPARTY_GRAPH_RISK"
    family = "counterparty"

    def __init__(self, two_factor_permille: int, reject_permille: int) -> None:
        self.two_factor_permille = two_factor_permille
        self.reject_permille = reject_permille

    def evaluate(self, pix, context) -> RuleResult | None:
        score = context.destination_graph_risk
        if pix.is_self_transfer or score is None:
            return None

        permille = score * 1000
        if permille >= self.reject_permille:
            decision = REJECTED
        elif permille >= self.two_factor_permille:
            decision = TWO_FACTOR_REQUIRED
        else:
            return None

        top = sorted(context.destination_graph_risk_contributions, key=lambda item: -item[1])[:TOP_FEATURES]
        top = [(name, value) for name, value in top if value > 0]
        drivers = ", ".join(name for name, _ in top)
        return RuleResult(
            self.code,
            decision,
            f"Destino com risco de grafo {score:.2f} (funil/dispersão de contas){f'; pesou: {drivers}' if drivers else ''}.",
            {
                "score": round(score, 5),
                "age_minutes": round(context.destination_graph_risk_age_minutes, 2),
                "top_features": {name: round(value, 4) for name, value in top},
            },
        )
