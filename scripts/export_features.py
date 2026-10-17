"""Runs the in-memory backtest over an events file and writes one labelled feature row per Pix."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from backtest import run_backtest  # noqa: E402
from replay import load_events  # noqa: E402
from rules import build_rules  # noqa: E402


def export(events_path, out_path):
    events = load_events(events_path)
    run_backtest(events, build_rules())
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        for event in events:
            response = event["response"]
            row = {
                "label": 0 if event["label"] == "legit" else 1,
                "typology": event["label"],
                "sequence": event["sequence"],
                "status": response["status"],
                "features": response["metadata"]["features"],
            }
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
    return len(events)


def main():
    parser = argparse.ArgumentParser(description="Export labelled feature rows from the backtest")
    parser.add_argument("events")
    parser.add_argument("out")
    args = parser.parse_args()
    print(f"wrote {export(args.events, args.out)} rows to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
