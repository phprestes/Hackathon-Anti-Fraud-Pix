"""Send a JSONL events file to the API and print the same report as simulate.py."""
import argparse
import json
import os
import sys

from api_client import send_events
from report import render_report, summarize


def load_events(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_responses(events, path):
    with open(path, "w", encoding="utf-8") as handle:
        for event in events:
            response = event.get("response")
            if response is None:
                continue
            line = {"pix_id": event["payload"]["id"], "status": response["status"], "metadata": response["metadata"]}
            handle.write(json.dumps(line, separators=(",", ":")) + "\n")


def parse_args():
    parser = argparse.ArgumentParser(description="Replay an events file through the API")
    parser.add_argument("events")
    parser.add_argument("--base-url", default=f"http://localhost:{os.environ.get('API_PORT', '3000')}")
    parser.add_argument("--token", default=os.environ.get("INTERNAL_TOKEN", "default_token"))
    parser.add_argument("--out", help="Markdown file for the report")
    parser.add_argument("--responses", help="JSONL file with one response per Pix")
    return parser.parse_args()


def main():
    args = parse_args()
    events = load_events(args.events)
    print(f"sending {len(events)} Pix to {args.base_url} ...", file=sys.stderr)
    send_events(events, args.base_url.rstrip("/"), args.token)
    report = render_report(summarize(events))
    print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(report)
    if args.responses:
        write_responses(events, args.responses)
    return 0


if __name__ == "__main__":
    sys.exit(main())
