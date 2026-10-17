import json
import logging
import os

from rules.base_rule import BaseRule, RuleResult
from rules.decision import APPROVED, TWO_FACTOR_REQUIRED

logger = logging.getLogger(__name__)

# (rule code, model file, RuleContext attribute, label used in the reason)
SCORE_MODELS = [
    ("MODEL_GRAPHSAGE", "graphsage.json", "destination_graphsage_score", "GraphSAGE"),
    ("MODEL_SEQUENCE_HMM", "hmm.json", "source_sequence_score", "HMM de sequência"),
]


class ModelScoreShadowRule(BaseRule):
    """Reads a score the worker already stored; shadow only, so it never changes the decision."""

    family = "model"
    shadow = True

    def __init__(self, code: str, attribute: str, label: str, threshold: float) -> None:
        self.code = code
        self.attribute = attribute
        self.label = label
        self.threshold = threshold

    def evaluate(self, pix, context) -> RuleResult | None:
        score = getattr(context, self.attribute)
        if score is None:
            return None
        decision = TWO_FACTOR_REQUIRED if score >= self.threshold else APPROVED
        return RuleResult(
            self.code,
            decision,
            f"Modelo {self.label} (cold path) deu score {score:.4f} (limiar {self.threshold:.4f}); só observação.",
            {"score": round(score, 6), "threshold": self.threshold},
        )


def load_score_model_rules(model_dir: str) -> list[BaseRule]:
    rules = []
    for code, filename, attribute, label in SCORE_MODELS:
        path = os.path.join(model_dir, filename)
        if not os.path.isfile(path):
            logger.warning("model file %s not found; shadow rule %s disabled", path, code)
            continue
        with open(path, encoding="utf-8") as handle:
            threshold = json.load(handle)["threshold"]
        rules.append(ModelScoreShadowRule(code, attribute, label, threshold))
    return rules
