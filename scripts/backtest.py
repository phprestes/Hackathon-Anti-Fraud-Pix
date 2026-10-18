"""Batch backtest: runs the rule engine over an events file with no HTTP and no database."""
import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from in_memory_history import InMemoryHistory  # noqa: E402
from replay import iter_events, write_response  # noqa: E402
from report import render_report, summarize  # noqa: E402
from rules import build_rules, engine  # noqa: E402
from rules.pix_snapshot import PixSnapshot  # noqa: E402


def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def digest(payload):
    return hashlib.blake2b(canonical(payload).encode(), digest_size=16).digest()


def slim_metadata(metadata):
    """The fields the aggregates read; duplicates of an id replay this instead of the full metadata."""
    return {"reasons": [{"rule": r["rule"]} for r in metadata.get("reasons", [])],
            "shadow": metadata.get("shadow", []), "rule_set_version": metadata.get("rule_set_version")}


def stream_backtest(events, rules, stats, keep_metadata=False):
    """Yields each event annotated with `response`; only digests and slim responses outlive an event."""
    history = InMemoryHistory()
    seen = {}
    stats["conflicts"] = 0
    stats["elapsed"] = 0.0
    for event in events:
        started = time.perf_counter()
        payload = event["payload"]
        previous = seen.get(payload["id"])
        if previous is not None:
            if previous[0] != digest(payload):
                stats["conflicts"] += 1
            event["response"] = previous[1] if keep_metadata else json.loads(previous[1])
        else:
            snapshot = PixSnapshot.from_payload(payload)
            outcome = engine.evaluate(snapshot, engine.build_context(snapshot, history), rules)
            history.record(snapshot, outcome.status)
            metadata = engine.metadata_from(outcome)
            event["response"] = {"status": outcome.status, "metadata": metadata}
            if keep_metadata:
                remembered = event["response"]
            else:
                remembered = json.dumps({"status": outcome.status, "metadata": slim_metadata(metadata)},
                                        separators=(",", ":"))
            seen[payload["id"]] = (digest(payload), remembered)
        stats["elapsed"] += time.perf_counter() - started
        stats["count"] = stats.get("count", 0) + 1
        yield event


def run_backtest(events, rules):
    """Annotates each event of a list with `response`; returns (elapsed_seconds, id_conflicts)."""
    stats = {}
    for _ in stream_backtest(events, rules, stats, keep_metadata=True):
        pass
    return stats["elapsed"], stats["conflicts"]


def select_rules(rules, disabled):
    """Drops the rules whose code is in `disabled`; an unknown code is an error, not a silent no-op."""
    unknown = sorted(set(disabled) - {rule.code for rule in rules})
    if unknown:
        raise ValueError(f"unknown rule codes: {', '.join(unknown)}")
    return [rule for rule in rules if rule.code not in disabled]


def parse_disable(value):
    return [code.strip() for code in value.split(",") if code.strip()] if value else []


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
        "cost": summary["cost"],
        "p_at_k": summary["p_at_k"],
        "total_seconds": round(elapsed, 3),
        "pix_per_second": round(total / elapsed, 1) if elapsed else None,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Batch rule backtest (no HTTP, no database)")
    parser.add_argument("events")
    parser.add_argument("--set", action="append", default=[], metavar="RULE_X=value")
    parser.add_argument("--disable", default="", metavar="RULE_A,RULE_B",
                        help="rule codes to switch off (ablation: what the others do without them)")
    parser.add_argument("--out", help="Markdown file for the report")
    parser.add_argument("--responses", help="JSONL file with one response per Pix")
    parser.add_argument("--json", help="JSON file with the report metrics")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        rules = select_rules(build_rules(parse_overrides(args.set)), parse_disable(args.disable))
    except ValueError as error:
        raise SystemExit(str(error))
    stats = {}
    responses = open(args.responses, "w", encoding="utf-8") if args.responses else None
    try:
        def consume():
            for event in stream_backtest(iter_events(args.events), rules, stats, keep_metadata=bool(responses)):
                if responses:
                    write_response(responses, event)
                yield event
        summary = summarize(consume())
    finally:
        if responses:
            responses.close()
    total, elapsed = stats["count"], stats["elapsed"]
    rate = total / elapsed if elapsed else 0
    timing = f"- backtest: {total} Pix in {elapsed:.2f} s ({rate:.0f} Pix/s), id conflicts skipped: {stats['conflicts']}"
    summary["timing"] = timing
    report = render_report(summary)
    print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(report)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(metrics_from(summary, elapsed, total), handle, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
