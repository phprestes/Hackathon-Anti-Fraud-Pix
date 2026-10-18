"""Report shared by simulate.py, replay.py and backtest.py."""
import math
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _paths  # noqa: E402,F401

from costs import KS, CostAccumulator, PrecisionAccumulator, lightgbm_score  # noqa: E402

TYPOLOGIES = ["account_takeover", "mule", "splitting", "night_kidnapping", "device_farm"]


def percentile(values, pct):
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def _pct(part, total):
    return f"{100 * part / total:.1f}%" if total else "n/a"


def summarize(events):
    """Single pass over any iterable of events; keeps counters and per-Pix score tuples, never the events."""
    legit_total = 0
    legit_status = Counter()
    rules = Counter()
    type_status = {name: Counter() for name in TYPOLOGIES}
    type_groups = {name: {} for name in TYPOLOGIES}
    shadow = {}
    latencies = []
    errors = 0
    versions = set()
    cost = CostAccumulator()
    rank_rules, rank_lgbm = PrecisionAccumulator(), PrecisionAccumulator(with_lightgbm=True)
    lgbm_seen = False
    for e in events:
        if "latency_ms" in e:
            latencies.append(e["latency_ms"])
        if "http_status" in e and not 200 <= e["http_status"] < 300:
            errors += 1
        response = e.get("response")
        if not response:
            continue
        status, metadata, label = response["status"], response["metadata"], e["label"]
        versions.add(metadata.get("rule_set_version"))
        cost.add(e)
        rank_rules.add(e)
        rank_lgbm.add(e)
        lgbm_seen = lgbm_seen or lightgbm_score(response) is not None
        if label == "legit":
            legit_total += 1
            legit_status[status] += 1
            rules.update(r["rule"] for r in metadata.get("reasons", []))
        elif label in type_status:
            type_status[label][status] += 1
            flags = type_groups[label]
            flags[e["sequence"]] = flags.get(e["sequence"], False) or status != "approved"
        for entry in metadata.get("shadow", []):
            model = shadow.setdefault(entry["rule"], {"legit": 0, "legit_flagged": 0, "typologies": {}})
            flagged = entry["would_decide"] != "approved"
            if label == "legit":
                model["legit"] += 1
                model["legit_flagged"] += flagged
            else:
                counts = model["typologies"].setdefault(label, [0, 0])
                counts[0] += 1
                counts[1] += flagged
    typologies = {
        name: {"count": sum(type_status[name].values()), "status": type_status[name],
               "sequences": len(type_groups[name]), "caught_sequences": sum(type_groups[name].values())}
        for name in TYPOLOGIES
    }
    return {
        "legit_total": legit_total, "legit_status": legit_status, "rules": rules,
        "typologies": typologies, "shadow": shadow, "latencies": latencies,
        "requests": len(latencies), "errors": errors,
        "versions": sorted(v for v in versions if v),
        "cost": cost.result(),
        "p_at_k": {"rules": rank_rules.result(), "rules_lightgbm": rank_lgbm.result() if lgbm_seen else None},
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
             "Modelo em scripts/backtest/cost-model.json (centavos). Fraude aprovada custa o valor; fraude com 2FA, valor x taxa de escape; "
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
