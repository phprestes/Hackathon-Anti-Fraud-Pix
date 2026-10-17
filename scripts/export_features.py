"""Runs the in-memory backtest over an events file and writes one labelled feature row per Pix."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from backtest import stream_backtest  # noqa: E402
from replay import iter_events  # noqa: E402
from rules import build_rules  # noqa: E402


def export(events_path, out_path):
    """Streams the backtest and writes one row per evaluated Pix; burn-in Pix only feed the history."""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    written = 0
    with open(out_path, "w", encoding="utf-8") as handle:
        for event in stream_backtest(iter_events(events_path), build_rules(), {}, keep_metadata=False):
            if event.get("burn_in"):
                continue
            response = event["response"]
            payload = event["payload"]
            if "features" not in response["metadata"]:
                continue  # replayed duplicate id: its slim response has no features
            row = {
                "label": 0 if event["label"] == "legit" else 1,
                "typology": event["label"],
                "sequence": event["sequence"],
                "status": response["status"],
                "amount": payload["amount"],
                "day": payload["transaction_date"][:10],
                "features": response["metadata"]["features"],
            }
            for extra in ("role", "weight"):
                if extra in event:
                    row[extra] = event[extra]
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")
            written += 1
    return written


def main():
    parser = argparse.ArgumentParser(description="Export labelled feature rows from the backtest")
    parser.add_argument("events")
    parser.add_argument("out")
    args = parser.parse_args()
    print(f"wrote {export(args.events, args.out)} rows to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
