import json
import logging
import os
from typing import Callable

from rules.base_rule import BaseRule, RuleResult
from rules.decision import APPROVED, TWO_FACTOR_REQUIRED
from rules.features import build_features
from rules.models import gbdt, iforest, logreg

logger = logging.getLogger(__name__)

# The engine computes the same features right before the rules; reuse them instead of rebuilding 3 times.
_last: tuple = (None, None, None)


def _features_of(pix, context) -> dict:
    global _last
    if _last[0] is not pix or _last[1] is not context:
        _last = (pix, context, build_features(pix, context))
    return _last[2]


class ModelShadowRule(BaseRule):
    family = "model"
    shadow = True

    def __init__(self, code: str, model: dict, scorer: Callable[[dict, dict], float]) -> None:
        self.code = code
        self.model = model
        self.scorer = scorer

    def evaluate(self, pix, context) -> RuleResult | None:
        value = self.scorer(self.model, _features_of(pix, context))
        threshold = self.model["threshold"]
        decision = TWO_FACTOR_REQUIRED if value >= threshold else APPROVED
        return RuleResult(
            self.code,
            decision,
            f"Modelo {self.model['type']} deu score {value:.4f} (limiar {threshold:.4f}); só observação.",
            {"score": round(value, 6), "threshold": threshold},
        )


MODEL_FILES = [
    ("MODEL_LOGREG", "logreg.json", logreg.score),
    ("MODEL_LIGHTGBM", "lightgbm.json", gbdt.score),
    ("MODEL_IFOREST", "iforest.json", iforest.score),
]


def load_model_rules(model_dir: str) -> list[BaseRule]:
    rules = []
    for code, filename, scorer in MODEL_FILES:
        path = os.path.join(model_dir, filename)
        if not os.path.isfile(path):
            logger.warning("model file %s not found; shadow rule %s disabled", path, code)
            continue
        with open(path, encoding="utf-8") as handle:
            rules.append(ModelShadowRule(code, json.load(handle), scorer))
    return rules
