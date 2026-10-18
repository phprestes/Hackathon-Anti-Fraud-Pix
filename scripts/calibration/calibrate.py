"""Grid search over rule parameters on the batch backtest (no HTTP, no database).

Prints suggested values only; src/constants.py is never edited. With --events the search runs on
PixSim worlds (streaming, weighted cost); --check stays on our simulator as the CI regression gate.
"""
import argparse
import hashlib
import itertools
import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _paths  # noqa: E402

from backtest import metrics_from, run_backtest  # noqa: E402
from costs import COMPONENTS, CostAccumulator, group_of, load_cost_model, weighted_per_1000  # noqa: E402
from in_memory_history import InMemoryHistory  # noqa: E402
from replay import iter_events, load_events  # noqa: E402
from report import summarize  # noqa: E402
from rules import PARAMETERS, build_rules  # noqa: E402
from rules.core import engine  # noqa: E402
from rules.core.pix_snapshot import PixSnapshot  # noqa: E402
from simulate import generate_events, write_events  # noqa: E402

OUT_DIR = _paths.OUT
PIXSIM_DIR = os.path.join(OUT_DIR, "pixsim")
CACHE_PATH = os.path.join(PIXSIM_DIR, "calibration-cache.json")
EXIT_INCOMPLETE = 75
STATUSES = ("approved", "two_factor_required", "rejected")


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
             "Cost: lowest expected cost in scripts/backtest/cost-model.json, ties by legit rejected, then sequences barred.", "",
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


def evaluate_file(path, overrides):
    """One streaming pass over a PixSim events file; weighted cost per view (victim, dispersal) plus counters."""
    rules = [rule for rule in build_rules(overrides) if not rule.shadow]
    history, model = InMemoryHistory(), load_cost_model()
    started = time.perf_counter()
    cost = {g: CostAccumulator(model) for g in ("legit", "victim", "dispersal")}
    status = {g: Counter() for g in cost}
    value = {g: Counter() for g in cost}
    weights = {g: [0.0, 0] for g in cost}
    sequences, barred = {}, {}
    for event in iter_events(path):
        payload = event["payload"]
        snapshot = PixSnapshot.from_payload(payload)
        outcome = engine.evaluate(snapshot, engine.build_context(snapshot, history), rules)
        history.record(snapshot, outcome.status)
        if event.get("burn_in"):
            continue
        group = group_of(event)
        cost[group].add({"label": event["label"], "payload": {"amount": payload["amount"]},
                         "response": {"status": outcome.status}})
        status[group][outcome.status] += 1
        value[group][outcome.status] += payload["amount"]
        weights[group][0] += event.get("weight", 1.0)
        weights[group][1] += 1
        if group == "victim":
            sequence = event["sequence"]
            sequences[sequence] = True
            barred[sequence] = barred.get(sequence, False) or outcome.status != "approved"
    legit, result = cost["legit"], {"legit": {"pix": cost["legit"].answered, **{s: status["legit"][s] for s in STATUSES}}}
    for group in ("victim", "dispersal"):
        pix = cost[group].answered
        weight = weights[group][0] / weights[group][1] if pix else 1.0
        parts = cost[group].parts
        friction = {k: v for k, v in legit.parts.items() if k.startswith("legit")}
        fraud_only = {k: parts[k] for k in COMPONENTS if k.startswith("fraud")}
        result[group] = {
            "pix": pix, "weight": round(weight, 6), **{s: status[group][s] for s in STATUSES},
            "value_cents": {s: value[group][s] for s in STATUSES},
            "cost_per_1000_cents": weighted_per_1000(legit.parts, fraud_only, legit.answered, pix, weight),
            "fraud_part_per_1000_cents": weighted_per_1000({}, fraud_only, legit.answered, pix, weight),
            "friction_part_per_1000_cents": weighted_per_1000(friction, {}, legit.answered, pix, weight),
        }
    result["victim"]["sequences"] = len(sequences)
    result["victim"]["sequences_barred"] = sum(barred.values())
    result["seconds"] = round(time.perf_counter() - started, 1)
    return result


def run_key(path, overrides):
    """Cache key: events file plus every effective rule parameter, so a run is reused whenever it is the same rule set."""
    params = sorted({**PARAMETERS, **overrides}.items())
    raw = json.dumps([os.path.basename(path), os.stat(path).st_size, params])
    return hashlib.blake2b(raw.encode(), digest_size=8).hexdigest()


class Runner:
    def __init__(self, budget, fresh):
        self.deadline = time.monotonic() + budget if budget else None
        self.cache = {}
        if not fresh and os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, encoding="utf-8") as handle:
                self.cache = json.load(handle)
        self.last = 0.0

    def run(self, path, overrides, base=None):
        """Returns the row, or None when the time budget cannot fit another run (the cache keeps the progress)."""
        effective = {**(base or {}), **overrides}
        key = run_key(path, effective)
        if key not in self.cache:
            if self.deadline and time.monotonic() + self.last > self.deadline:
                return None
            began = time.monotonic()
            self.cache[key] = {"overrides": effective, "metrics": evaluate_file(path, effective)}
            self.last = time.monotonic() - began
            self.save()
            print(f"  {os.path.basename(path)} {label(overrides) or 'baseline'}: "
                  f"cost {self.cache[key]['metrics']['victim']['cost_per_1000_cents'] / 100:,.2f} "
                  f"({self.last:.0f} s)", file=sys.stderr)
        return {"overrides": overrides, "metrics": self.cache[key]["metrics"]}

    def save(self):
        os.makedirs(PIXSIM_DIR, exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as handle:
            json.dump(self.cache, handle)


def pixsim_cost(row):
    m = row["metrics"]
    return (m["victim"]["cost_per_1000_cents"], m["legit"]["rejected"], -m["victim"]["sequences_barred"])


def sweep_runs(spec):
    """Baseline first, then each parameter moved alone (one-at-a-time keeps the grid under ~30 passes)."""
    base = spec.get("baseline", {})
    runs = [{}]
    for name, values in spec["grid"].items():
        runs += [{name: v} for v in values if v != base.get(name, PARAMETERS[name])]
    return runs


def combine_best(rows, spec):
    """Per parameter, the single value that beats the defaults most; all of them applied together."""
    default = next(r for r in rows if not r["overrides"])
    best = {}
    for name in spec["grid"]:
        if name in spec.get("pinned", []):
            continue
        own = [r for r in rows if set(r["overrides"]) == {name} and pixsim_cost(r) < pixsim_cost(default)]
        if own:
            best[name] = min(own, key=pixsim_cost)["overrides"][name]
    return best


def pct_of(part, total):
    return f"{pct(part, total):.2f}"


def pixsim_table(rows, winner):
    lines = ["| # | parameters | legit 2FA % | legit rejected % | victim Pix barred % | victim sequences barred "
             "| dispersal Pix barred % | victim cost R$/1000 | dispersal cost R$/1000 |", "|---|---|---|---|---|---|---|---|---|"]
    for rank, row in enumerate(rows, 1):
        m = row["metrics"]
        v, d, lg = m["victim"], m["dispersal"], m["legit"]
        mark = " **(winner)**" if row is winner else ""
        lines.append(
            f"| {rank} | {label(row['overrides']) or 'baseline'}{mark} | {pct_of(lg['two_factor_required'], lg['pix'])} "
            f"| {pct_of(lg['rejected'], lg['pix'])} | {pct_of(v['two_factor_required'] + v['rejected'], v['pix'])} "
            f"| {v['sequences_barred']}/{v['sequences']} | {pct_of(d['two_factor_required'] + d['rejected'], d['pix'])} "
            f"| {v['cost_per_1000_cents'] / 100:,.2f} | {d['cost_per_1000_cents'] / 100:,.2f} |")
    return lines


def render_pixsim(world_a, world_b, rows_a, rows_b, winner, spec, applied_hint):
    lines = ["# Calibration grid on PixSim", "",
             f"World A (choose): `{os.path.basename(world_a)}`. World B (confirm): `{os.path.basename(world_b)}`. "
             "Objective: lowest weighted expected cost per 1,000 Pix in the victim view (legit + payer-to-mule fraud), "
             "fraud weighted by the PixSim importance weight; ties by legit rejected, then sequences barred. "
             "Dispersal (mule side) is reported apart and never enters the objective. One parameter moves at a time "
             "from the baseline (the defaults before this calibration, pinned in the grid file), then the per-parameter winners together; "
             "parameters listed as pinned in the grid are measured but never applied.", "",
             f"## World A: {len(rows_a)} combinations", ""]
    lines += pixsim_table(sorted(rows_a, key=pixsim_cost), winner)
    lines += ["", "## World B: confirmation", ""]
    lines += pixsim_table(sorted(rows_b, key=pixsim_cost), None)
    lines += ["", "## Suggested values (not applied by the script)", "", "```",
              *[f"{k}={v}" for k, v in winner["overrides"].items()], "```", "", applied_hint, ""]
    return "\n".join(lines)


def calibrate_pixsim(grid_path, path_a, path_b, budget, fresh):
    started = time.perf_counter()
    with open(grid_path, encoding="utf-8") as handle:
        spec = json.load(handle)
    runner = Runner(budget, fresh)
    base = spec.get("baseline", {})
    rows_a = []
    for overrides in sweep_runs(spec):
        row = runner.run(path_a, overrides, base)
        if row is None:
            print("budget reached; run again to continue (progress is cached)", file=sys.stderr)
            return EXIT_INCOMPLETE
        rows_a.append(row)
    combo = combine_best(rows_a, spec)
    if len(combo) > 1:
        row = runner.run(path_a, combo, base)
        if row is None:
            return EXIT_INCOMPLETE
        rows_a.append(row)
    ranked = sorted((r for r in rows_a if not set(r["overrides"]) & set(spec.get("pinned", []))), key=pixsim_cost)
    winner = ranked[0]
    defaults_a = next(r for r in rows_a if not r["overrides"])
    candidates = [{}] + [r["overrides"] for r in ranked[:4] if r["overrides"]]
    rows_b = []
    for overrides in candidates:
        row = runner.run(path_b, overrides, base)
        if row is None:
            return EXIT_INCOMPLETE
        rows_b.append(row)
    defaults_b = next(r for r in rows_b if not r["overrides"])
    winner_b = next((r for r in rows_b if r["overrides"] == winner["overrides"]), defaults_b)
    improves = bool(winner["overrides"]) and pixsim_cost(winner_b) < pixsim_cost(defaults_b)
    hint = (f"Winner on A: cost R$ {winner['metrics']['victim']['cost_per_1000_cents'] / 100:,.2f} per 1,000 Pix "
            f"(baseline R$ {defaults_a['metrics']['victim']['cost_per_1000_cents'] / 100:,.2f}). On B: "
            f"R$ {winner_b['metrics']['victim']['cost_per_1000_cents'] / 100:,.2f} "
            f"(baseline R$ {defaults_b['metrics']['victim']['cost_per_1000_cents'] / 100:,.2f}). "
            f"{'Improves on B: candidate to apply.' if improves else 'Baseline stays.'}")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "calibration-pixsim.md"), "w", encoding="utf-8") as handle:
        handle.write(render_pixsim(path_a, path_b, rows_a, rows_b, winner, spec, hint))
    with open(os.path.join(OUT_DIR, "calibration-pixsim.json"), "w", encoding="utf-8") as handle:
        json.dump({"grid": spec, "winner": winner, "improves_on_b": improves, "defaults_a": defaults_a,
                   "defaults_b": defaults_b, "rows_a": rows_a, "rows_b": rows_b}, handle, indent=2)
    print(f"winner on A: {label(winner['overrides']) or 'baseline'}\n{hint}")
    print(f"{len(rows_a)} combinations on A, {len(rows_b)} on B, {time.perf_counter() - started:.1f} s "
          "-> scripts/out/calibration-pixsim.md")
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
    parser.add_argument("--check", action="store_true", help="enforce scripts/calibration/calibration-gate.json")
    parser.add_argument("--gate", default=os.path.join(HERE, "calibration-gate.json"))
    parser.add_argument("--events", help="PixSim world A events.jsonl: choose the parameters here (weighted cost)")
    parser.add_argument("--events-b", help="PixSim world B events.jsonl: confirm the winner here")
    parser.add_argument("--budget-seconds", type=int, default=0,
                        help="stop before starting a run that would pass this; exit 75 and resume from the cache")
    parser.add_argument("--fresh", action="store_true", help="ignore the PixSim run cache")
    args = parser.parse_args()
    if args.check:
        return check(args.gate)
    if args.events:
        if args.objective != "cost" or not args.events_b:
            parser.error("--events needs --objective cost and --events-b")
        grid = args.grid if args.grid != parser.get_default("grid") else os.path.join(HERE, "calibration-grid-pixsim.json")
        return calibrate_pixsim(grid, args.events, args.events_b, args.budget_seconds, args.fresh)
    return calibrate(args.grid, args.objective)


if __name__ == "__main__":
    sys.exit(main())
