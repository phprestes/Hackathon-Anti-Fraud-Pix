"""Asymmetric cost model and daily P@k over labelled, answered events (no HTTP, no database)."""
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
COST_MODEL_PATH = os.path.join(HERE, "cost-model.json")
KS = (5, 10, 25, 50)
COMPONENTS = ("fraud_approved", "fraud_2fa_escape", "legit_2fa", "legit_rejected")
# Score for ranking when no model score exists: the rules' own decision.
DECISION_SCORE = {"rejected": 1.0, "two_factor_required": 0.5, "approved": 0.0}


DISPERSAL_ROLES = {"fraudster_seed", "mule_forward", "cash_out"}


def group_of(event):
    """PixSim view of a labelled event: legit, victim (payer to mule) or dispersal (mule side)."""
    if event["label"] == "legit":
        return "legit"
    return "dispersal" if event.get("role") in DISPERSAL_ROLES else "victim"


def weighted_per_1000(legit_parts, fraud_parts, legit_pix, fraud_pix, weight):
    """Cost per 1,000 Pix when each fraud Pix counts `weight` of a legitimate one (PixSim importance weight)."""
    total = sum(legit_parts.values()) + weight * sum(fraud_parts.values())
    effective = legit_pix + weight * fraud_pix
    return round(total * 1000 / effective) if effective else 0


def load_cost_model(path=COST_MODEL_PATH):
    with open(path, encoding="utf-8") as handle:
        return {name: item["value"] for name, item in json.load(handle).items()}


class CostAccumulator:
    def __init__(self, model=None):
        self.model = model or load_cost_model()
        self.parts = dict.fromkeys(COMPONENTS, 0)
        self.answered = 0

    def add(self, event):
        response = event.get("response")
        if not response:
            return
        self.answered += 1
        model = self.model
        status, amount = response["status"], event["payload"]["amount"]
        if event["label"] == "legit":
            if status == "two_factor_required":
                self.parts["legit_2fa"] += model["friction_cost_2fa_cents"]
            elif status == "rejected":
                self.parts["legit_rejected"] += model["friction_cost_reject_cents"]
        elif status == "approved":
            self.parts["fraud_approved"] += round(amount * model["fraud_loss_factor"])
        elif status == "two_factor_required":
            self.parts["fraud_2fa_escape"] += round(amount * model["two_factor_escape_rate"])

    def result(self):
        parts, answered = self.parts, self.answered
        total = sum(parts.values())
        scale = 1000 / answered if answered else 0
        return {"pix": answered, "total_cents": total, "components_cents": dict(parts),
                "per_1000_cents": round(total * scale),
                "components_per_1000_cents": {k: round(v * scale) for k, v in parts.items()}}


def expected_cost(events, model=None):
    """Total and per-component cost in cents (int), plus the same per 1,000 Pix."""
    accumulator = CostAccumulator(model)
    for event in events:
        accumulator.add(event)
    return accumulator.result()


def lightgbm_score(response):
    scores = [entry["signals"]["score"] for entry in response["metadata"].get("shadow", [])
              if "LIGHTGBM" in entry["rule"] and "score" in entry.get("signals", {})]
    return max(scores) if scores else None


class PrecisionAccumulator:
    """Keeps one (score, amount, is_fraud) tuple per Pix, grouped by day; never the event itself."""

    def __init__(self, with_lightgbm=False):
        self.with_lightgbm = with_lightgbm
        self.days = defaultdict(list)

    def add(self, event):
        response = event.get("response")
        if not response:
            return
        score = DECISION_SCORE[response["status"]]
        if self.with_lightgbm:
            score = max(score, lightgbm_score(response) or 0.0)
        day = event["payload"]["transaction_date"][:10]
        self.days[day].append((score, event["payload"]["amount"], event["label"] != "legit"))

    def add_scored(self, score, amount, day, is_fraud):
        self.days[day].append((score, amount, is_fraud))

    def result(self, ks=KS):
        result = {}
        for k in ks:
            daily = []
            for items in self.days.values():
                top = sorted(items, key=lambda i: (-i[0], -i[1]))[:k]
                daily.append(sum(i[2] for i in top) / len(top))
            result[k] = sum(daily) / len(daily) if daily else None
        return result


def precision_at_k(events, ks=KS, with_lightgbm=False):
    """Mean over days of the fraud share in the day's top-k; ties break by larger amount first."""
    accumulator = PrecisionAccumulator(with_lightgbm)
    for event in events:
        accumulator.add(event)
    return accumulator.result(ks)


def has_lightgbm(events):
    return any(lightgbm_score(e["response"]) is not None for e in events if e.get("response"))
