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


def load_cost_model(path=COST_MODEL_PATH):
    with open(path, encoding="utf-8") as handle:
        return {name: item["value"] for name, item in json.load(handle).items()}


def expected_cost(events, model=None):
    """Total and per-component cost in cents (int), plus the same per 1,000 Pix."""
    model = model or load_cost_model()
    parts = dict.fromkeys(COMPONENTS, 0)
    answered = 0
    for event in events:
        response = event.get("response")
        if not response:
            continue
        answered += 1
        status, amount = response["status"], event["payload"]["amount"]
        if event["label"] == "legit":
            if status == "two_factor_required":
                parts["legit_2fa"] += model["friction_cost_2fa_cents"]
            elif status == "rejected":
                parts["legit_rejected"] += model["friction_cost_reject_cents"]
        elif status == "approved":
            parts["fraud_approved"] += round(amount * model["fraud_loss_factor"])
        elif status == "two_factor_required":
            parts["fraud_2fa_escape"] += round(amount * model["two_factor_escape_rate"])
    total = sum(parts.values())
    scale = 1000 / answered if answered else 0
    return {"pix": answered, "total_cents": total, "components_cents": parts,
            "per_1000_cents": round(total * scale),
            "components_per_1000_cents": {k: round(v * scale) for k, v in parts.items()}}


def lightgbm_score(response):
    scores = [entry["signals"]["score"] for entry in response["metadata"].get("shadow", [])
              if "LIGHTGBM" in entry["rule"] and "score" in entry.get("signals", {})]
    return max(scores) if scores else None


def precision_at_k(events, ks=KS, with_lightgbm=False):
    """Mean over days of the fraud share in the day's top-k; ties break by larger amount first."""
    days = defaultdict(list)
    for event in events:
        response = event.get("response")
        if not response:
            continue
        score = DECISION_SCORE[response["status"]]
        if with_lightgbm:
            score = max(score, lightgbm_score(response) or 0.0)
        day = event["payload"]["transaction_date"][:10]
        days[day].append((score, event["payload"]["amount"], event["label"] != "legit"))
    result = {}
    for k in ks:
        daily = []
        for items in days.values():
            top = sorted(items, key=lambda i: (-i[0], -i[1]))[:k]
            daily.append(sum(i[2] for i in top) / len(top))
        result[k] = sum(daily) / len(daily) if daily else None
    return result


def has_lightgbm(events):
    return any(lightgbm_score(e["response"]) is not None for e in events if e.get("response"))
