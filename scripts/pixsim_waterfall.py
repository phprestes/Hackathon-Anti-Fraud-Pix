"""Runs PixSim's own MED clock over our engine's decisions on world B (PixSim venv, python -I; third-party code is read-only)."""
import argparse
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out" / "pixsim"
sys.path.insert(0, str(OUT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from pixsim import load_config  # noqa: E402
from pixsim.experiment import burn_in_world, fraud_world, load_config_like  # noqa: E402
from pixsim.med import MedRules, MedWorld, run_med_world  # noqa: E402
from pixsim.metrics import compute_metrics  # noqa: E402

SEED_B = 20261017
ESCAPE_RATE = 0.1
OVERRIDES = {"seed": SEED_B, "population": {"n_accounts": 5000}, "simulation": {"days": 30, "burn_in_days": 30},
             "fraud": {"target_accepted_per_month": 1000}}
WF = ("wf_caught_share", "wf_held_hop_share", "wf_med_share", "wf_cautelary_share", "wf_lost_share")
POLICIES = ("pass_all", "rules", "rules+lightgbm")


def base_config():
    return load_config(OUT / "src" / "configs" / "baseline.yaml", overrides=OVERRIDES)


def our_ids(cfg, pop, n_tx, t_tx):
    """Position of each tx row after the exporter's stable sort by time (burn-in first in the concat)."""
    burn = burn_in_world(cfg, pop)
    t_all = np.concatenate([burn["t"].to_numpy(), t_tx])
    order = np.argsort(t_all, kind="stable")
    rank = np.empty(len(order), dtype=np.int64)
    rank[order] = np.arange(len(order))
    return rank[len(burn):len(burn) + n_tx]


def load_scores(path):
    rows = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows[row["id"]] = row
    return rows


def final_status(row, policy):
    status = row["status"]
    if policy == "rules+lightgbm" and status == "approved" and row["lightgbm"] >= row["lightgbm_threshold"]:
        return "two_factor_required"
    return status


def decisions(tx, ids, scores, policy, cfg):
    """approved passes; rejected blocks; a fraud 2FA blocks unless the victim confirms (hash draw per Pix, as in the feedback loop)."""
    n = len(tx)
    block = np.zeros(n, dtype=bool)
    if policy != "pass_all":
        is_fraud = (tx["label"].astype(str) == "fraud").to_numpy()
        for i in range(n):
            pix = f"pixsim-{ids[i]:07d}"
            status = final_status(scores[pix], policy)
            if status == "rejected":
                block[i] = True
            elif status == "two_factor_required" and is_fraud[i]:
                block[i] = random.Random(f"{SEED_B}:{pix}").random() >= ESCAPE_RATE
    legit = (tx["label"].astype(str) == "legit").to_numpy()
    false_block = block & legit
    amount = tx["amount"].to_numpy()
    harm = np.where(false_block, cfg.rail.false_block_cost_fixed_brl + cfg.rail.false_block_cost_share_of_amount * amount, 0.0)
    return pd.DataFrame({
        "tx_id": tx["tx_id"].to_numpy(), "decision": np.where(block, "block", "pass"), "settled": ~block,
        "settle_t": tx["t"].to_numpy(), "hold_s": 0.0, "queued": False, "reviewed": False, "expired": False,
        "analyst_flag": False, "false_block": false_block, "wait_s": 0.0, "harm_cost": harm,
        "blocked_by": np.where(block, "policy", "")})


def run_ours(scores_path):
    cfg, pop, _, _, tx, frauds, contrib = fraud_world(base_config(), use_cache=False)
    ids = our_ids(cfg, pop, len(tx), tx["t"].to_numpy())
    scores = load_scores(scores_path)
    cents = np.rint(tx["amount"].to_numpy() * 100).astype(np.int64)
    mismatch = sum(1 for i in range(len(tx)) if abs(scores[f"pixsim-{ids[i]:07d}"]["amount"] - max(1, cents[i])) > 1)
    if mismatch:
        raise SystemExit(f"id mapping broken: {mismatch} amount mismatches")
    days = int(cfg.simulation.days)
    result = {}
    for policy in POLICIES:
        dec = decisions(tx, ids, scores, policy, cfg)
        world = MedWorld(tx, contrib, dec, pop)
        med_out, agg = run_med_world(world, frauds, cfg, MedRules.from_config(cfg), np.random.default_rng(int(cfg.seed) + 2))
        row = compute_metrics(tx, frauds, dec, med_out, None, cfg, days).iloc[0]
        result[policy] = {k: float(row[k]) for k in (*WF, "loss_share", "fraud_value_total_w", "false_block_count", "harm_cost")}
        result[policy]["wf_sum"] = sum(result[policy][k] for k in WF)
        result[policy]["med_recovery_rate"] = float(agg.get("recovery_rate", float("nan")))
        print(policy, {k: round(v, 4) for k, v in result[policy].items()}, flush=True)
    return result


def run_reference():
    from pixsim.chunked import run_chunked
    cfg = load_config_like(base_config(), None)
    rows, _, auc, _ = run_chunked(cfg, segment_days=30, log=lambda m: print("  " + m, flush=True), traffic_block_days=5,
                                  policies=["pass_all", "threshold_block"])
    result = {r["policy"]: {**{k: float(r[k]) for k in (*WF, "loss_share", "false_block_count", "harm_cost")},
                            "wf_sum": sum(float(r[k]) for k in WF)} for r in rows}
    result["heldout_auc_victim"] = float(auc.get("heldout_auc_victim", float("nan")))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--part", choices=("ours", "reference"), required=True)
    parser.add_argument("--scores", default=str(OUT / "scores-b.jsonl"))
    args = parser.parse_args()
    result = run_ours(args.scores) if args.part == "ours" else run_reference()
    with open(OUT / f"waterfall-{args.part}.json", "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=1)


if __name__ == "__main__":
    main()
