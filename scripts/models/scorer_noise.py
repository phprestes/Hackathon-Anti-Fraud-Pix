"""Replica of PixSim's S7 scorer-noise sweep on our shadow models in world B: logit(p) + N(0, sigma), no retraining."""
import argparse
import json
import os
import sys

import numpy as np
from sklearn.metrics import roc_auc_score


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _paths  # noqa: E402

from costs import expected_cost  # noqa: E402

OUT = _paths.PIXSIM_OUT
SIGMAS = (0, 1, 2, 3, 6, 8, 12)
TARGET_AUC = 0.82
NOISE_SEED = 20261017 + 17
MODELS = ("lightgbm", "logreg")
VICTIM_ROLES = ("none", "victim_to_mule")


def degrade(p, sigma, seed=NOISE_SEED):
    """pixsim.scoring.Scorer._degrade: same clip and same logit space noise, dedicated generator of fixed seed."""
    if sigma <= 0:
        return p
    q = np.clip(p, 1e-9, 1 - 1e-9)
    z = np.log(q / (1 - q)) + np.random.default_rng(seed).normal(0.0, sigma, size=len(q))
    return 1.0 / (1.0 + np.exp(-np.clip(z, -36.0, 36.0)))


def load_view(path):
    """Victim view of the engine output: legitimate Pix plus the Pix a victim sends to a mule."""
    cols = {k: [] for k in ("status", "fraud", "amount", "weight", "lightgbm", "logreg")}
    thresholds = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["role"] not in VICTIM_ROLES:
                continue
            cols["status"].append(row["status"])
            cols["fraud"].append(row["label"] != "legit")
            cols["amount"].append(row["amount"])
            cols["weight"].append(row["weight"])
            for name in MODELS:
                cols[name].append(row[name])
                thresholds[name] = row[name + "_threshold"]
    view = {k: np.array(v) for k, v in cols.items()}
    view["thresholds"] = thresholds
    return view


def cost_per_1000(view, status):
    """Weighted cost per 1,000 Pix: each fraud Pix counts the mean importance weight, as in pixsim_report.cost_block."""
    fraud = view["fraud"]
    weight = float(view["weight"][fraud].mean())

    def parts(mask, label):
        events = [{"label": label, "payload": {"amount": int(a)}, "response": {"status": s}}
                  for a, s in zip(view["amount"][mask], status[mask])]
        return expected_cost(events)["components_cents"]

    legit_parts, fraud_parts = parts(~fraud, "legit"), parts(fraud, "fraud")
    total = sum(legit_parts.values()) + weight * sum(fraud_parts.values())
    return total * 1000 / ((~fraud).sum() + weight * fraud.sum())


def combined(view, score, threshold):
    """Rules decide; a model flag on an approved Pix becomes 2FA (the same combination as the P2 evaluation)."""
    return np.where((view["status"] == "approved") & (score >= threshold), "two_factor_required", view["status"])


def summarise(view, score, status):
    fraud = view["fraud"]
    flagged = status != "approved"
    return {"auc": float(roc_auc_score(fraud, score, sample_weight=np.where(fraud, view["weight"], 1.0))),
            "cost_per_1000_cents": round(cost_per_1000(view, status)),
            "capture": float(flagged[fraud].mean()), "friction": float(flagged[~fraud].mean())}


def matched_threshold(view, clean, noisy, threshold):
    """Threshold on the noisy score that flags as many approved legitimate Pix as the clean score did."""
    legit_open = (~view["fraud"]) & (view["status"] == "approved")
    target = float((clean[legit_open] >= threshold).mean())
    return float(np.quantile(noisy[legit_open], 1 - target)) if target > 0 else 2.0


def find_sigma(view, name, auc_target=TARGET_AUC):
    """Bisection of sigma on the weighted AUC of the noisy score (the draw is fixed, so AUC falls smoothly with sigma)."""
    fraud, weights = view["fraud"], np.where(view["fraud"], view["weight"], 1.0)
    lo, hi = 0.0, 24.0
    for _ in range(18):
        mid = (lo + hi) / 2
        auc = roc_auc_score(fraud, degrade(view[name], mid), sample_weight=weights)
        lo, hi = (mid, hi) if auc > auc_target else (lo, mid)
    return (lo + hi) / 2


def sweep(view, name, sigmas):
    clean, threshold = view[name], view["thresholds"][name]
    rows = []
    for sigma in sigmas:
        noisy = degrade(clean, sigma)
        fixed = summarise(view, noisy, combined(view, noisy, threshold))
        keep = matched_threshold(view, clean, noisy, threshold)
        same_friction = summarise(view, noisy, combined(view, noisy, keep))
        rows.append({"sigma": round(float(sigma), 2), **fixed, "matched": same_friction})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", default=os.path.join(OUT, "scores-b.jsonl"))
    parser.add_argument("--json", default=os.path.join(OUT, "scorer-noise.json"))
    args = parser.parse_args()
    view = load_view(args.scores)
    rules_status = view["status"]
    rules = summarise(view, np.array([{"rejected": 1.0, "two_factor_required": 0.5, "approved": 0.0}[s] for s in rules_status]),
                      rules_status)
    result = {"rules": rules, "pix": int(len(rules_status)), "fraud_pix": int(view["fraud"].sum()), "models": {}}
    for name in MODELS:
        star = find_sigma(view, name)
        result["models"][name] = {"sweep": sweep(view, name, SIGMAS), "sigma_at_target": round(star, 3),
                                  "at_target": sweep(view, name, [star])[0]}
        print(name, "sigma*", round(star, 3), result["models"][name]["at_target"], file=sys.stderr)
    with open(args.json, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=1)
    print("rules", rules, file=sys.stderr)


if __name__ == "__main__":
    main()
