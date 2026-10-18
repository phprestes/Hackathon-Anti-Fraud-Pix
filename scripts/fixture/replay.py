"""Send a JSONL events file to the API and print the same report as simulate.py."""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _paths  # noqa: E402,F401

from api_client import send_events  # noqa: E402
from report import render_report, summarize  # noqa: E402


def iter_events(path):
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load_events(path):
    return list(iter_events(path))


def write_response(handle, event):
    response = event.get("response")
    if response is None:
        return
    line = {"pix_id": event["payload"]["id"], "status": response["status"], "metadata": response["metadata"]}
    handle.write(json.dumps(line, separators=(",", ":")) + "\n")


def write_responses(events, path):
    with open(path, "w", encoding="utf-8") as handle:
        for event in events:
            write_response(handle, event)


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
