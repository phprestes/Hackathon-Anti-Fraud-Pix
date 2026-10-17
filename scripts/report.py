"""Report shared by simulate.py, replay.py and backtest.py."""
import math
from collections import Counter, defaultdict

TYPOLOGIES = ["account_takeover", "mule", "splitting", "night_kidnapping", "device_farm"]


def percentile(values, pct):
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def _pct(part, total):
    return f"{100 * part / total:.1f}%" if total else "n/a"


def summarize(events):
    answered = [e for e in events if e.get("response")]
    legit = [e for e in answered if e["label"] == "legit"]
    legit_status = Counter(e["response"]["status"] for e in legit)
    rules = Counter(r["rule"] for e in legit for r in e["response"]["metadata"].get("reasons", []))
    typologies = {}
    for name in TYPOLOGIES:
        items = [e for e in answered if e["label"] == name]
        groups = defaultdict(list)
        for e in items:
            groups[e["sequence"]].append(e["response"]["status"] != "approved")
        typologies[name] = {
            "count": len(items),
            "status": Counter(e["response"]["status"] for e in items),
            "sequences": len(groups),
            "caught_sequences": sum(1 for flags in groups.values() if any(flags)),
        }
    latencies = [e["latency_ms"] for e in events if "latency_ms" in e]
    versions = {e["response"]["metadata"].get("rule_set_version") for e in answered}
    return {
        "legit_total": len(legit), "legit_status": legit_status, "rules": rules,
        "typologies": typologies, "latencies": latencies,
        "requests": len(latencies),
        "errors": sum(1 for e in events if "http_status" in e and not 200 <= e["http_status"] < 300),
        "versions": sorted(v for v in versions if v),
    }


def render_report(summary):
    lines = ["# Simulation results", "", "## Legitimate friction", ""]
    total = summary["legit_total"]
    for status in ("approved", "two_factor_required", "rejected"):
        count = summary["legit_status"].get(status, 0)
        lines.append(f"- {status}: {count} ({_pct(count, total)})")
    lines += ["", "## Fraud by typology", "",
              "| typology | Pix | approved (escaped) | 2FA | rejected | sequences with >=1 barred |",
              "|---|---|---|---|---|---|"]
    for name, data in summary["typologies"].items():
        n, st = data["count"], data["status"]
        lines.append(
            f"| {name} | {n} | {_pct(st.get('approved', 0), n)} | {_pct(st.get('two_factor_required', 0), n)} "
            f"| {_pct(st.get('rejected', 0), n)} | {data['caught_sequences']}/{data['sequences']} |")
    lines += ["", "## Top rules firing on legitimate Pix", ""]
    lines += [f"- {rule}: {count}" for rule, count in summary["rules"].most_common(10)] or ["- none"]
    lines += ["", "## Latency and errors", ""]
    if summary.get("timing"):
        lines.append(summary["timing"])
    if summary["latencies"]:
        p50, p95, p99 = (percentile(summary["latencies"], p) for p in (50, 95, 99))
        lines.append(f"- P50 {p50:.1f} ms, P95 {p95:.1f} ms, P99 {p99:.1f} ms")
    if summary["requests"]:
        lines += [f"- requests: {summary['requests']}", f"- non-2xx errors: {summary['errors']}"]
    lines += [f"- rule_set_version: {', '.join(summary['versions']) or 'n/a'}", ""]
    return "\n".join(lines)
