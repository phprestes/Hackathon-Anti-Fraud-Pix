"""Trains LogReg+Platt, LightGBM and Isolation Forest on mock labels and exports them as JSON (docs/05-motor)."""
import json
import os
import pickle
import sys
import time
from collections import defaultdict

import numpy as np
from lightgbm import LGBMClassifier
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from rules.features import FEATURE_NAMES  # noqa: E402

OUT = os.path.join(ROOT, "scripts", "out")
MODEL_DIR = os.path.join(ROOT, "src", "rules", "model")
RESULTS = os.path.join(ROOT, "scripts", "model-results.md")
MODEL_VERSION = "mock-1"
WARNING = "mock: synthetic labels"
SEED = 42
VALIDATION_SHARE = 0.25
TRAINED_ON = "train-events seed 42, 300 payers, 14 days (scripts/simulate.py)"
MODELS = ["logreg", "lightgbm", "iforest"]


def load_rows(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    X = np.array([[row["features"][n] for n in FEATURE_NAMES] for row in rows], dtype=float)
    y = np.array([row["label"] for row in rows])
    return rows, X, y


def best_f1_threshold(y, scores):
    best, best_f1 = 0.5, -1.0
    for candidate in np.unique(scores):
        predicted = scores >= candidate
        tp = int(np.sum(predicted & (y == 1)))
        f1 = 2 * tp / (int(predicted.sum()) + int(y.sum())) if predicted.sum() + y.sum() else 0.0
        if f1 >= best_f1:
            best, best_f1 = float(candidate), f1
    return best


def meta(extra):
    return {"version": MODEL_VERSION, "trained_on": TRAINED_ON, "warning": WARNING, "features": FEATURE_NAMES, **extra}


def train_logreg(X_fit, y_fit, X_val, y_val):
    scaler = StandardScaler().fit(X_fit)
    clf = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=SEED)
    clf.fit(scaler.transform(X_fit), y_fit)
    margin_val = clf.decision_function(scaler.transform(X_val)).reshape(-1, 1)
    platt = LogisticRegression(C=1e6, max_iter=1000).fit(margin_val, y_val)
    a, b = float(platt.coef_[0][0]), float(platt.intercept_[0])

    def predict(X):
        return platt.predict_proba(clf.decision_function(scaler.transform(X)).reshape(-1, 1))[:, 1]

    threshold = best_f1_threshold(y_val, predict(X_val))
    model = meta({
        "type": "logreg", "mean": scaler.mean_.tolist(), "std": scaler.scale_.tolist(),
        "coef": clf.coef_[0].tolist(), "intercept": float(clf.intercept_[0]),
        "platt": {"a": a, "b": b}, "threshold": threshold,
        "threshold_rule": "max F1 on the validation slice; Platt fitted on the same slice",
    })
    return model, predict, (scaler, clf, platt)


def compact_lightgbm(node):
    if "leaf_value" in node:
        return node["leaf_value"]
    assert node["decision_type"] == "<=" and node["missing_type"] == "None", node
    return [node["split_feature"], node["threshold"], compact_lightgbm(node["left_child"]), compact_lightgbm(node["right_child"])]


def train_lightgbm(X_fit, y_fit, X_val, y_val):
    pos = int(y_fit.sum())
    clf = LGBMClassifier(
        n_estimators=100, num_leaves=15, learning_rate=0.1, scale_pos_weight=(len(y_fit) - pos) / pos,
        random_state=SEED, verbose=-1, n_jobs=1,
    ).fit(X_fit, y_fit)
    trees = [compact_lightgbm(t["tree_structure"]) for t in clf.booster_.dump_model()["tree_info"]]

    def predict(X):
        return clf.predict_proba(X)[:, 1]

    model = meta({
        "type": "gbdt", "trees": trees, "base_score": 0.0, "threshold": best_f1_threshold(y_val, predict(X_val)),
        "threshold_rule": "max F1 on the validation slice; boost_from_average is folded into the first tree",
    })
    return model, predict, clf


def compact_iforest(tree, feature_map, node=0):
    if tree.children_left[node] == -1:
        return int(tree.n_node_samples[node])
    return [
        int(feature_map[tree.feature[node]]), float(tree.threshold[node]),
        compact_iforest(tree, feature_map, tree.children_left[node]),
        compact_iforest(tree, feature_map, tree.children_right[node]),
    ]


def train_iforest(X_train, y_train):
    clf = IsolationForest(n_estimators=100, max_samples=256, random_state=SEED).fit(X_train[y_train == 0])

    def predict(X):
        return -clf.score_samples(X)

    threshold = float(np.percentile(predict(X_train[y_train == 0]), 99))
    trees = [compact_iforest(e.tree_, f) for e, f in zip(clf.estimators_, clf.estimators_features_)]
    model = meta({
        "type": "iforest", "trees": trees, "n_samples": int(clf.max_samples_), "threshold": threshold,
        "threshold_rule": "p99 of the scores of the legitimate training Pix; unsupervised, no labels used",
    })
    return model, predict, clf


def write_model(name, model):
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(os.path.join(MODEL_DIR, f"{name}.json"), "w", encoding="utf-8") as handle:
        json.dump(model, handle, separators=(",", ":"))


def pct(part, total):
    return f"{100 * part / total:.1f}%" if total else "n/a"


def sequences_caught(rows, flagged):
    seqs = defaultdict(list)
    for row, flag in zip(rows, flagged):
        if row["label"]:
            seqs[row["sequence"]].append(flag)
    return sum(any(v) for v in seqs.values()), len(seqs)


def evaluate_set(rows, y, scores_by_model, thresholds, supervised):
    typologies = sorted({r["typology"] for r in rows if r["label"]})
    rule_flag = np.array([r["status"] != "approved" for r in rows])
    flags = {m: scores_by_model[m] >= thresholds[m] for m in MODELS}
    flags["rules"] = rule_flag
    flags["rules+lightgbm"] = rule_flag | flags["lightgbm"]
    legit, fraud = y == 0, y == 1
    metrics = {}
    for m in MODELS:
        tp = int((flags[m] & fraud).sum())
        metrics[m] = {
            "auc": roc_auc_score(y, scores_by_model[m]),
            "precision": tp / flags[m].sum() if flags[m].sum() else 0.0,
            "recall": tp / fraud.sum(),
            "brier": brier_score_loss(y, scores_by_model[m]) if m in supervised else None,
        }
    typology_table = {}
    for t in typologies:
        mask = np.array([r["typology"] == t for r in rows])
        typology_table[t] = {
            name: (int((flag & mask).sum()), int(mask.sum()), *sequences_caught([r for r, k in zip(rows, mask) if k], flag[mask]))
            for name, flag in flags.items()
        }
    friction = {name: (int((flag & legit).sum()), int(legit.sum())) for name, flag in flags.items()}
    barred = {name: (int((flag & fraud).sum()), int(fraud.sum())) for name, flag in flags.items()}
    return metrics, typology_table, friction, barred


def render_set(title, result):
    metrics, typology_table, friction, barred = result
    lines = [f"## {title}", "", "| model | AUC | precision | recall | Brier |", "|---|---|---|---|---|"]
    for m, v in metrics.items():
        brier = f"{v['brier']:.4f}" if v["brier"] is not None else "n/a (score is not a probability)"
        lines.append(f"| {m} | {v['auc']:.3f} | {v['precision']:.3f} | {v['recall']:.3f} | {brier} |")
    names = list(friction)
    lines += ["", "Fraud captured per typology (Pix barred / Pix, sequences with at least one Pix barred):", "",
              "| typology | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for t, row in typology_table.items():
        cells = [f"{pct(v[0], v[1])} ({v[2]}/{v[3]} seq)" for v in row.values()]
        lines.append(f"| {t} | " + " | ".join(cells) + " |")
    lines += ["", "Rules x models (barred = status other than approved for rules, score >= threshold for models):", "",
              "| decider | frauds barred | friction on legitimate |", "|---|---|---|"]
    for name in names:
        lines.append(f"| {name} | {pct(*barred[name])} | {pct(*friction[name])} |")
    return lines + [""]


def main():
    started = time.perf_counter()
    train_rows, X, y = load_rows("train-features.jsonl")
    split = int(len(y) * (1 - VALIDATION_SHARE))
    X_fit, y_fit, X_val, y_val = X[:split], y[:split], X[split:], y[split:]
    timings, models, predictors, libraries = {}, {}, {}, {}
    for name, trainer, args in [
        ("logreg", train_logreg, (X_fit, y_fit, X_val, y_val)),
        ("lightgbm", train_lightgbm, (X_fit, y_fit, X_val, y_val)),
        ("iforest", train_iforest, (X, y)),
    ]:
        t0 = time.perf_counter()
        models[name], predictors[name], libraries[name] = trainer(*args)
        timings[name] = time.perf_counter() - t0
        write_model(name, models[name])
    # The parity check compares the pure-Python evaluators with these exact fitted objects.
    with open(os.path.join(OUT, "models.pkl"), "wb") as handle:
        pickle.dump(libraries, handle)
    thresholds = {m: models[m]["threshold"] for m in MODELS}

    lines = ["# Model results (mock: synthetic labels)", "",
             "Fixed simple hyperparameters, no search. Labels come from the simulator, so these numbers prove the "
             "pipeline fits the hot path; they say nothing about real fraud. Regenerate with `make train-models`.", "",
             f"Train: {len(y)} Pix ({int(y.sum())} fraud); fit slice {split}, validation slice {len(y) - split} "
             f"({int(y_val.sum())} fraud), split by time. Thresholds: {json.dumps({m: round(t, 4) for m, t in thresholds.items()})}.",
             "", "Training time: " + ", ".join(f"{m} {s:.2f} s" for m, s in timings.items()) + ".", ""]
    for title, name in [("Test (seed 7, default frauds)", "test-features.jsonl"),
                        ("Perturbed test (seed 7, perturbed fraud ranges)", "test-perturbed-features.jsonl")]:
        rows, Xt, yt = load_rows(name)
        scores = {m: predictors[m](Xt) for m in MODELS}
        lines += render_set(title, evaluate_set(rows, yt, scores, thresholds, {"logreg", "lightgbm"}))
    with open(RESULTS, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    print("\n".join(lines))
    print(f"total {time.perf_counter() - started:.1f} s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
