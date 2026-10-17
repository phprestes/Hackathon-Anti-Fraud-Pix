"""Batch backtest: runs the rule engine over an events file with no HTTP and no database."""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from in_memory_history import InMemoryHistory  # noqa: E402
from replay import load_events, write_responses  # noqa: E402
from report import render_report, summarize  # noqa: E402
from rules import build_rules, engine  # noqa: E402
from rules.pix_snapshot import PixSnapshot  # noqa: E402


def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def run_backtest(events, rules):
    """Annotates each event with `response`; returns (elapsed_seconds, id_conflicts)."""
    history = InMemoryHistory()
    seen = {}
    conflicts = 0
    started = time.perf_counter()
    for event in events:
        payload = event["payload"]
        previous = seen.get(payload["id"])
        if previous is not None:
            if canonical(previous[0]) != canonical(payload):
                conflicts += 1
            event["response"] = previous[1]
            continue
        snapshot = PixSnapshot.from_payload(payload)
        outcome = engine.evaluate(snapshot, engine.build_context(snapshot, history), rules)
        history.record(snapshot, outcome.status)
        event["response"] = {"status": outcome.status, "metadata": engine.metadata_from(outcome)}
        seen[payload["id"]] = (payload, event["response"])
    return time.perf_counter() - started, conflicts


def parse_overrides(pairs):
    overrides = {}
    for pair in pairs:
        name, _, value = pair.partition("=")
        if not value.lstrip("-").isdigit():
            raise SystemExit(f"--set expects RULE_X=<integer>, got {pair!r}")
        overrides[name] = int(value)
    return overrides


def metrics_from(summary, elapsed, total):
    return {
        "legit_total": summary["legit_total"],
        "friction": dict(summary["legit_status"]),
        "capture_by_typology": {
            name: {"pix": data["count"], "status": dict(data["status"]),
                   "sequences": data["sequences"], "caught_sequences": data["caught_sequences"]}
            for name, data in summary["typologies"].items()
        },
        "rules_on_legit": dict(summary["rules"]),
        "total_seconds": round(elapsed, 3),
        "pix_per_second": round(total / elapsed, 1) if elapsed else None,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Batch rule backtest (no HTTP, no database)")
    parser.add_argument("events")
    parser.add_argument("--set", action="append", default=[], metavar="RULE_X=value")
    parser.add_argument("--out", help="Markdown file for the report")
    parser.add_argument("--responses", help="JSONL file with one response per Pix")
    parser.add_argument("--json", help="JSON file with the report metrics")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        rules = build_rules(parse_overrides(args.set))
    except ValueError as error:
        raise SystemExit(str(error))
    events = load_events(args.events)
    elapsed, conflicts = run_backtest(events, rules)
    rate = len(events) / elapsed if elapsed else 0
    timing = f"- backtest: {len(events)} Pix in {elapsed:.2f} s ({rate:.0f} Pix/s), id conflicts skipped: {conflicts}"
    summary = summarize(events)
    summary["timing"] = timing
    report = render_report(summary)
    print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(report)
    if args.responses:
        write_responses(events, args.responses)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(metrics_from(summary, elapsed, len(events)), handle, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
