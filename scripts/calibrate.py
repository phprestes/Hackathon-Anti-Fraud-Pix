"""Grid search over rule parameters on the batch backtest (no HTTP, no database).

Prints suggested values only; src/constants.py is never edited.
"""
import argparse
import itertools
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from backtest import metrics_from, run_backtest  # noqa: E402
from replay import load_events  # noqa: E402
from report import summarize  # noqa: E402
from rules import build_rules  # noqa: E402
from simulate import generate_events, write_events  # noqa: E402

OUT_DIR = os.path.join(HERE, "out")


def pct(part, total):
    return 100 * part / total if total else 0.0


def evaluate(events, overrides):
    """Runs one backtest and reduces it to the objective counters."""
    elapsed, _ = run_backtest(events, build_rules(overrides))
    metrics = metrics_from(summarize(events), elapsed, len(events))
    friction, total = metrics["friction"], metrics["legit_total"]
    typologies = metrics["capture_by_typology"].values()
    sequences = sum(t["sequences"] for t in typologies)
    caught = sum(t["caught_sequences"] for t in typologies)
    return {
        "legit_total": total,
        "legit_rejected": friction.get("rejected", 0),
        "legit_2fa": friction.get("two_factor_required", 0),
        "legit_rejected_pct": pct(friction.get("rejected", 0), total),
        "legit_2fa_pct": pct(friction.get("two_factor_required", 0), total),
        "fraud_sequences": sequences,
        "fraud_sequences_barred": caught,
        "fraud_sequences_barred_pct": pct(caught, sequences),
        "fraud_approved": sum(t["status"].get("approved", 0) for t in typologies),
        "cost_cents": metrics["cost"]["total_cents"],
        "cost_per_1000_cents": metrics["cost"]["per_1000_cents"],
        "cost_components_cents": metrics["cost"]["components_cents"],
        "p_at_k": metrics["p_at_k"]["rules"],
        "seconds": round(elapsed, 3),
    }


def objective(row):
    r = row["metrics"]
    return (r["legit_rejected"], -r["fraud_sequences_barred"], r["legit_2fa"], r["fraud_approved"])


def cost_objective(row):
    m = row["metrics"]
    return (m["cost_cents"], m["legit_rejected"], -m["fraud_sequences_barred"])


OBJECTIVES = {"lexicographic": objective, "cost": cost_objective}


def frontier(rows):
    """Combinations no other one beats on legit friction (rejected + 2FA), sequences barred and cost."""
    def point(row):
        m = row["metrics"]
        return m["legit_rejected"] + m["legit_2fa"], m["fraud_sequences_barred"], m["cost_cents"]

    result = []
    for row in rows:
        friction, capture, cost = point(row)
        dominated = any(
            f <= friction and c >= capture and k <= cost and (f < friction or c > capture or k < cost)
            for f, c, k in map(point, rows)
        )
        if not dominated:
            result.append(row)
    return result


def label(overrides):
    return ", ".join(f"{k}={v}" for k, v in overrides.items())


def table(rows, winners):
    lines = ["| # | parameters | legit rejected | legit 2FA | sequences barred | fraud approved | cost R$ | cost R$/1000 Pix | s |",
             "|---|---|---|---|---|---|---|---|---|"]
    for rank, row in enumerate(rows, 1):
        m = row["metrics"]
        mark = "".join(f" **({name} winner)**" for name, w in winners.items() if row is w)
        lines.append(
            f"| {rank} | {label(row['overrides'])}{mark} | {m['legit_rejected']} ({m['legit_rejected_pct']:.2f}%) "
            f"| {m['legit_2fa']} ({m['legit_2fa_pct']:.2f}%) "
            f"| {m['fraud_sequences_barred']}/{m['fraud_sequences']} | {m['fraud_approved']} "
            f"| {m['cost_cents'] / 100:,.2f} | {m['cost_per_1000_cents'] / 100:,.2f} | {m['seconds']} |")
    return lines


def render(rows, winners, front, spec, total_seconds, objective_name, defaults):
    lines = ["# Calibration grid", "",
             f"Events: {json.dumps(spec['events'])}. Objective ({objective_name}); rows are sorted by it. "
             "Lexicographic: fewer legit rejected, more fraud sequences barred, fewer legit 2FA, fewer fraud Pix approved. "
             "Cost: lowest expected cost in scripts/cost-model.json, ties by legit rejected, then sequences barred.", "",
             f"Current defaults: cost R$ {defaults['cost_cents'] / 100:,.2f} "
             f"(R$ {defaults['cost_per_1000_cents'] / 100:,.2f} per 1,000 Pix), legit rejected {defaults['legit_rejected']}, "
             f"legit 2FA {defaults['legit_2fa']}, sequences barred "
             f"{defaults['fraud_sequences_barred']}/{defaults['fraud_sequences']}.", "",
             f"{len(rows)} combinations in {total_seconds:.1f} s.", "", "## All combinations", ""]
    lines += table(rows, winners)
    lines += ["", "## Friction x capture x cost frontier (non-dominated)", ""]
    lines += table(front, winners)
    winner = winners[objective_name]
    lines += ["", "## Suggested values (not applied)", "", "```", *[f"{k}={v}" for k, v in winner["overrides"].items()],
              "```", ""]
    return "\n".join(lines)


def run_grid(spec, events_path):
    seed, payers, days = (spec["events"][k] for k in ("seed", "payers", "days"))
    write_events(generate_events(seed, payers, days, "evt"), events_path)
    events = load_events(events_path)
    names = list(spec["grid"])
    rows = []
    for values in itertools.product(*spec["grid"].values()):
        overrides = dict(zip(names, values))
        rows.append({"overrides": overrides, "metrics": evaluate(events, overrides)})
    return rows


def calibrate(grid_path, objective_name):
    started = time.perf_counter()
    with open(grid_path, encoding="utf-8") as handle:
        spec = json.load(handle)
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = run_grid(spec, os.path.join(OUT_DIR, "events-calibration.jsonl"))
    defaults = evaluate(load_events(os.path.join(OUT_DIR, "events-calibration.jsonl")), {})
    winners = {name: min(rows, key=key) for name, key in OBJECTIVES.items()}
    winner = winners[objective_name]
    rows = sorted(rows, key=OBJECTIVES[objective_name])
    front = frontier(rows)
    total = time.perf_counter() - started
    with open(os.path.join(OUT_DIR, "calibration.md"), "w", encoding="utf-8") as handle:
        handle.write(render(rows, winners, front, spec, total, objective_name, defaults))
    with open(os.path.join(OUT_DIR, "calibration.json"), "w", encoding="utf-8") as handle:
        json.dump({"events": spec["events"], "objective": objective_name, "winner": winner,
                   "winners": winners, "defaults": defaults, "frontier": front, "rows": rows,
                   "total_seconds": round(total, 2)}, handle, indent=2)
    print(f"winner: {label(winner['overrides'])}")
    print("suggested (not applied): " + " ".join(f"{k}={v}" for k, v in winner["overrides"].items()))
    print(f"{len(rows)} runs, {total:.1f} s total, {total / len(rows):.2f} s per run, "
          f"{len(front)} on the frontier -> scripts/out/calibration.md")
    return 0


def check(gate_path):
    started = time.perf_counter()
    with open(gate_path, encoding="utf-8") as handle:
        gate = json.load(handle)
    spec = {"events": gate["events"], "grid": {}}
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = run_grid(spec, os.path.join(OUT_DIR, "events-gate.jsonl"))
    m = rows[0]["metrics"]
    checks = [
        ("legit rejected %", m["legit_rejected_pct"], "<=", gate["max_legit_rejected_pct"]),
        ("legit 2FA %", m["legit_2fa_pct"], "<=", gate["max_legit_2fa_pct"]),
        ("fraud sequences barred %", m["fraud_sequences_barred_pct"], ">=", gate["min_fraud_sequences_barred_pct"]),
    ]
    failed = False
    for name, value, op, limit in checks:
        ok = value <= limit if op == "<=" else value >= limit
        failed |= not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name}: {value:.2f} (must be {op} {limit})")
    print(f"gate {'FAILED' if failed else 'passed'} in {time.perf_counter() - started:.1f} s")
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description="Rule parameter grid over the batch backtest")
    parser.add_argument("--grid", default=os.path.join(HERE, "calibration-grid.json"))
    parser.add_argument("--objective", choices=sorted(OBJECTIVES), default="lexicographic")
    parser.add_argument("--check", action="store_true", help="enforce scripts/calibration-gate.json")
    parser.add_argument("--gate", default=os.path.join(HERE, "calibration-gate.json"))
    args = parser.parse_args()
    return check(args.gate) if args.check else calibrate(args.grid, args.objective)


if __name__ == "__main__":
    sys.exit(main())
