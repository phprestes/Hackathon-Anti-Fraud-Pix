"""Report shared by simulate.py, replay.py and backtest.py."""
import math
from collections import Counter, defaultdict

from costs import KS, expected_cost, has_lightgbm, precision_at_k

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
    shadow = {}
    for e in answered:
        for entry in e["response"]["metadata"].get("shadow", []):
            model = shadow.setdefault(entry["rule"], {"legit": 0, "legit_flagged": 0, "typologies": {}})
            flagged = entry["would_decide"] != "approved"
            if e["label"] == "legit":
                model["legit"] += 1
                model["legit_flagged"] += flagged
            else:
                counts = model["typologies"].setdefault(e["label"], [0, 0])
                counts[0] += 1
                counts[1] += flagged
    latencies = [e["latency_ms"] for e in events if "latency_ms" in e]
    versions = {e["response"]["metadata"].get("rule_set_version") for e in answered}
    return {
        "legit_total": len(legit), "legit_status": legit_status, "rules": rules,
        "typologies": typologies, "shadow": shadow, "latencies": latencies,
        "requests": len(latencies),
        "errors": sum(1 for e in events if "http_status" in e and not 200 <= e["http_status"] < 300),
        "versions": sorted(v for v in versions if v),
        "cost": expected_cost(answered),
        "p_at_k": {"rules": precision_at_k(answered),
                   "rules_lightgbm": precision_at_k(answered, with_lightgbm=True) if has_lightgbm(answered) else None},
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
    if summary.get("shadow"):
        lines += ["", "## Shadow models", "",
                  "Share of each typology's Pix the model would have barred, and friction on legitimate Pix.", "",
                  "| model | friction on legitimate | " + " | ".join(summary["typologies"]) + " |",
                  "|---|---|" + "---|" * len(summary["typologies"])]
        for name, data in sorted(summary["shadow"].items()):
            cells = [_pct(data["typologies"].get(t, [0, 0])[1], data["typologies"].get(t, [0, 0])[0])
                     for t in summary["typologies"]]
            lines.append(f"| {name} | {_pct(data['legit_flagged'], data['legit'])} | " + " | ".join(cells) + " |")
    lines += render_cost(summary["cost"]) + render_p_at_k(summary["p_at_k"])
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


def _reais(cents):
    return f"R$ {cents / 100:,.2f}"


def render_cost(cost):
    lines = ["", "## Custo esperado", "",
             "Modelo em scripts/cost-model.json (centavos). Fraude aprovada custa o valor; fraude com 2FA, valor x taxa de escape; "
             "legitimo com 2FA ou reprovado, atrito fixo.", "",
             "| componente | total | por 1.000 Pix |", "|---|---|---|"]
    for name, cents in cost["components_cents"].items():
        lines.append(f"| {name} | {_reais(cents)} | {_reais(cost['components_per_1000_cents'][name])} |")
    lines.append(f"| **total** | {_reais(cost['total_cents'])} | {_reais(cost['per_1000_cents'])} |")
    return lines


def render_p_at_k(p_at_k):
    lines = ["", "## P@k (mesa de k analistas)", "",
             "Por dia local, top-k por score (rejected 1.0, 2FA 0.5, ou o maior score do LightGBM em shadow); "
             "precisao = fraudes no top-k; media diaria.", "",
             "| ranking | " + " | ".join(f"P@{k}" for k in KS) + " |", "|---|" + "---|" * len(KS)]
    for name, label in (("rules", "regras sozinhas"), ("rules_lightgbm", "regras + LightGBM")):
        values = p_at_k[name]
        cells = [_pct(values[k], 1) for k in KS] if values else ["n/a"] * len(KS)
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return lines
