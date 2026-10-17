"""Pure-Python model evaluators (src/rules/models) x sklearn/lightgbm on the test features."""
import json
import math
import os
import pickle
import sys

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from rules.models import gbdt, iforest, logreg  # noqa: E402

OUT = os.path.join(ROOT, "scripts", "out")
MODEL_DIR = os.path.join(ROOT, "src", "rules", "model")
TOLERANCE = 1e-6
SETS = ["test-features.jsonl", "test-perturbed-features.jsonl"]


def load_model(name):
    with open(os.path.join(MODEL_DIR, f"{name}.json"), encoding="utf-8") as handle:
        return json.load(handle)


def main():
    with open(os.path.join(OUT, "models.pkl"), "rb") as handle:
        libs = pickle.load(handle)
    models = {name: load_model(name) for name in libs}
    feature_names = models["logreg"]["features"]
    scaler, lr, platt = libs["logreg"]
    forest = libs["iforest"]
    worst = {"logreg": 0.0, "lightgbm": 0.0, "iforest score": 0.0, "iforest path length": 0.0}
    total = 0
    for name in SETS:
        with open(os.path.join(OUT, name), encoding="utf-8") as handle:
            features = [json.loads(line)["features"] for line in handle if line.strip()]
        X = np.array([[f[n] for n in feature_names] for f in features], dtype=float)
        ref_lr = platt.predict_proba(lr.decision_function(scaler.transform(X)).reshape(-1, 1))[:, 1]
        ref_gb = libs["lightgbm"].predict_proba(X)[:, 1]
        ref_if = -forest.score_samples(X)
        c = iforest.average_path_length(models["iforest"]["n_samples"])
        for i, f in enumerate(features):
            worst["logreg"] = max(worst["logreg"], abs(logreg.score(models["logreg"], f) - ref_lr[i]))
            worst["lightgbm"] = max(worst["lightgbm"], abs(gbdt.score(models["lightgbm"], f) - ref_gb[i]))
            worst["iforest score"] = max(worst["iforest score"], abs(iforest.score(models["iforest"], f) - ref_if[i]))
            ref_path = -math.log2(ref_if[i]) * c
            worst["iforest path length"] = max(
                worst["iforest path length"], abs(iforest.mean_path_length(models["iforest"], f) - ref_path))
        total += len(features)
    print(f"compared {total} Pix (tolerance {TOLERANCE:g})")
    for name, value in worst.items():
        print(f"  {name}: max abs diff {value:.3e}")
    return 1 if any(v >= TOLERANCE for v in worst.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
