"""Streams a PixSim events file through the engine and keeps one compact line per evaluated Pix (status and shadow model scores)."""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from in_memory_history import InMemoryHistory  # noqa: E402
from rules import build_rules, engine  # noqa: E402
from rules.pix_snapshot import PixSnapshot  # noqa: E402

OUT = os.path.join(HERE, "out", "pixsim")
MODELS = {"MODEL_LOGREG": "logreg", "MODEL_LIGHTGBM": "lightgbm"}


def score_of(shadow, code):
    for entry in shadow:
        if entry["rule"] == code and "score" in entry.get("signals", {}):
            return entry["signals"]["score"], entry["signals"]["threshold"]
    return None, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", default=os.path.join(OUT, "events-b.jsonl"))
    parser.add_argument("--out", default=os.path.join(OUT, "scores-b.jsonl"))
    args = parser.parse_args()
    rules, history = build_rules({}), InMemoryHistory()
    written = 0
    with open(args.events, encoding="utf-8") as source, open(args.out, "w", encoding="utf-8") as sink:
        for line in source:
            event = json.loads(line)
            snapshot = PixSnapshot.from_payload(event["payload"])
            outcome = engine.evaluate(snapshot, engine.build_context(snapshot, history), rules)
            history.record(snapshot, outcome.status)
            if event.get("burn_in"):
                continue
            shadow = engine.metadata_from(outcome).get("shadow", [])
            row = {"id": event["payload"]["id"], "label": event["label"], "role": event.get("role"),
                   "amount": event["payload"]["amount"], "weight": event.get("weight", 1.0),
                   "day": event["payload"]["transaction_date"][:10], "status": outcome.status}
            for code, name in MODELS.items():
                row[name], row[name + "_threshold"] = score_of(shadow, code)
            sink.write(json.dumps(row, separators=(",", ":")) + "\n")
            written += 1
    print(f"{written} evaluated Pix -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
