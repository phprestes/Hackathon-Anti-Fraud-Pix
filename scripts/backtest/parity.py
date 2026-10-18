"""Black-box parity: same events through the API (SQL) and the in-memory backtest, compared Pix by Pix."""
import argparse
import copy
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _paths  # noqa: E402,F401

from api_client import send_events  # noqa: E402
from backtest import run_backtest  # noqa: E402
from replay import load_events  # noqa: E402
from rules import ACTIVE_RULES  # noqa: E402

FLOAT_TOLERANCE = 1e-9


def same(api_value, backtest_value):
    both_numbers = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (api_value, backtest_value))
    if both_numbers and (isinstance(api_value, float) or isinstance(backtest_value, float)):
        return math.isclose(api_value, backtest_value, rel_tol=0, abs_tol=FLOAT_TOLERANCE)
    return api_value == backtest_value


def rule_codes(response):
    return [r["rule"] for r in response["metadata"].get("reasons", [])]


def compare(api_event, backtest_event):
    pix_id = api_event["payload"]["id"]
    api, mine = api_event.get("response"), backtest_event["response"]
    if api is None:
        return [(pix_id, "response", f"HTTP {api_event.get('http_status')}", "n/a")]
    found = []
    if api["status"] != mine["status"]:
        found.append((pix_id, "status", api["status"], mine["status"]))
    if rule_codes(api) != rule_codes(mine):
        found.append((pix_id, "rules", rule_codes(api), rule_codes(mine)))
    api_features, my_features = api["metadata"].get("features", {}), mine["metadata"]["features"]
    for name in sorted(set(api_features) | set(my_features)):
        if name not in api_features or name not in my_features or not same(api_features[name], my_features[name]):
            found.append((pix_id, f"features.{name}", api_features.get(name, "<missing>"), my_features.get(name, "<missing>")))
    return found


def parse_args():
    parser = argparse.ArgumentParser(description="SQL x in-memory parity check")
    parser.add_argument("events")
    parser.add_argument("--base-url", default=f"http://localhost:{os.environ.get('API_PORT', '3000')}")
    parser.add_argument("--token", default=os.environ.get("INTERNAL_TOKEN", "default_token"))
    parser.add_argument("--max-print", type=int, default=50)
    return parser.parse_args()


def main():
    args = parse_args()
    api_events = load_events(args.events)
    backtest_events = copy.deepcopy(api_events)

    started = time.perf_counter()
    send_events(api_events, args.base_url.rstrip("/"), args.token)
    api_seconds = time.perf_counter() - started
    backtest_seconds, _ = run_backtest(backtest_events, ACTIVE_RULES)

    divergences = [d for a, b in zip(api_events, backtest_events) for d in compare(a, b)]
    print(f"compared {len(api_events)} Pix: {len(divergences)} divergences")
    print(f"API {api_seconds:.1f} s ({len(api_events) / api_seconds:.0f} Pix/s) | "
          f"backtest {backtest_seconds:.2f} s ({len(api_events) / backtest_seconds:.0f} Pix/s)")
    for pix_id, field, api_value, backtest_value in divergences[: args.max_print]:
        print(f"  {pix_id} {field}: API={api_value!r} backtest={backtest_value!r}")
    return 1 if divergences else 0


if __name__ == "__main__":
    sys.exit(main())
