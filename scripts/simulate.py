"""Calibration traffic simulator (ADR 0020). See scripts/README.md."""
import argparse
import json
import math
import os
import random
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import requests

TZ = timezone(timedelta(hours=-3))
START = datetime(2026, 9, 1, tzinfo=TZ)
CAPITALS = [
    (-23.55, -46.63), (-22.91, -43.17), (-15.79, -47.88),
    (-19.92, -43.94), (-30.03, -51.23), (-12.97, -38.50),
]
ISPBS = ["60701190", "00000000", "60746948", "90400888", "18236120", "00416968"]
TYPOLOGIES = ["account_takeover", "mule", "splitting", "night_kidnapping", "device_farm"]
FRAUD_SHARE = 0.025
TOP_LEVEL_KEYS = {"id", "amount", "transaction_date", "source_account", "destination_account", "source"}
SOURCE_ACCOUNT_KEYS = {"branch", "account_number", "opening_date", "owner"}
DESTINATION_ACCOUNT_KEYS = SOURCE_ACCOUNT_KEYS | {"participant"}
SOURCE_KEYS = {"device_id", "channel", "ip", "geolocation"}


def _check_digit(digits, weights):
    total = sum(d * w for d, w in zip(digits, weights))
    rest = total % 11
    return 0 if rest < 2 else 11 - rest


def make_cpf(rng):
    base = [rng.randint(0, 9) for _ in range(9)]
    base.append(_check_digit(base, range(10, 1, -1)))
    base.append(_check_digit(base, range(11, 1, -1)))
    s = "".join(map(str, base))
    return f"{s[:3]}.{s[3:6]}.{s[6:9]}-{s[9:]}"


def make_cnpj(rng):
    base = [rng.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]
    base.append(_check_digit(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]))
    base.append(_check_digit(base, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]))
    s = "".join(map(str, base))
    return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"


def make_account(rng, age_days, cnpj_share=0.0):
    document = make_cnpj(rng) if rng.random() < cnpj_share else make_cpf(rng)
    return {
        "participant": rng.choice(ISPBS),
        "branch": f"{rng.randint(1, 9999):04d}",
        "account_number": str(rng.randint(10000, 999999)),
        "opening_age_days": age_days,
        "document": document,
    }


def old_age(rng):
    return rng.randint(365, 365 * 8)


def make_payer(rng, index):
    capital = rng.choice(CAPITALS)
    median = math.exp(rng.uniform(math.log(2000), math.log(200000)))
    payer = {
        "index": index,
        "account": make_account(rng, rng.randint(365, 365 * 5), cnpj_share=0.1),
        "devices": [f"dvc-{rng.getrandbits(32):08x}" for _ in range(rng.randint(1, 2))],
        "capital": capital,
        "ip": f"198.51.100.{rng.randint(1, 254)}",
        "per_day": math.exp(rng.uniform(math.log(0.2), math.log(6))),
        "median": int(median),
        "recurring": [make_account(rng, old_age(rng)) for _ in range(rng.randint(3, 8))],
        "rent": None,
    }
    if rng.random() < 0.3:
        payer["rent"] = {
            "account": make_account(rng, old_age(rng)),
            "amount": int(payer["median"] * rng.uniform(8, 15)) // 100 * 100,
            "day": rng.randint(1, 28),
        }
    return payer


def generate_population(rng, count):
    return [make_payer(rng, i) for i in range(count)]


def geo_near(rng, capital):
    return {"latitude": round(capital[0] + rng.gauss(0, 0.02), 4),
            "longitude": round(capital[1] + rng.gauss(0, 0.02), 4)}


def build_payload(event_id, when, amount, payer, destination, device_id, geolocation):
    return {
        "id": event_id,
        "amount": int(amount),
        "transaction_date": when.isoformat(),
        "source_account": {
            "branch": payer["account"]["branch"],
            "account_number": payer["account"]["account_number"],
            "opening_date": (START - timedelta(days=payer["account"]["opening_age_days"])).isoformat(),
            "owner": {"document_number": payer["account"]["document"]},
        },
        "destination_account": {
            "participant": destination["participant"],
            "branch": destination["branch"],
            "account_number": destination["account_number"],
            "opening_date": (START + timedelta(days=destination.get("created_offset", 0))
                             - timedelta(days=destination["opening_age_days"])).isoformat(),
            "owner": {"document_number": destination["document"]},
        },
        "source": {
            "device_id": device_id,
            "channel": "app",
            "ip": payer["ip"],
            "geolocation": geolocation,
        },
    }


class EventFactory:
    def __init__(self, rng, run_tag):
        self.rng = rng
        self.run_tag = run_tag
        self.counter = 0
        self.events = []

    def add(self, label, group, when, amount, payer, destination, device_id, geolocation):
        self.counter += 1
        payload = build_payload(f"sim-{self.run_tag}-{self.counter:07d}", when, amount,
                                payer, destination, device_id, geolocation)
        self.events.append({"label": label, "group": group, "payload": payload})


def fresh_destination(rng, age_days, when):
    destination = make_account(rng, age_days)
    # opening age is relative to the Pix date, not to the simulation start
    destination["created_offset"] = (when - START).total_seconds() / 86400
    return destination


def random_legit_time(rng, day_start):
    while True:
        hour = rng.gauss(14, 4)
        if 7 <= hour < 22:
            return day_start + timedelta(hours=hour)


def poisson(rng, lam):
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def generate_legit_events(rng, factory, payers, days):
    for payer in payers:
        for day in range(days):
            day_start = START + timedelta(days=day)
            for _ in range(poisson(rng, payer["per_day"])):
                when = random_legit_time(rng, day_start)
                if rng.random() < 0.10:
                    age = old_age(rng) if rng.random() < 0.8 else rng.randint(30, 365)
                    destination = fresh_destination(rng, age, when)
                else:
                    destination = rng.choice(payer["recurring"])
                amount = max(100, rng.lognormvariate(math.log(payer["median"]), 0.6))
                factory.add("legit", None, when, amount, payer, destination,
                            rng.choice(payer["devices"]), geo_near(rng, payer["capital"]))
            rent = payer["rent"]
            if rent and day_start.day == rent["day"]:
                when = day_start + timedelta(hours=rng.uniform(8, 12))
                factory.add("legit", None, when, rent["amount"], payer, rent["account"],
                            payer["devices"][0], geo_near(rng, payer["capital"]))


def random_moment(rng, days, margin_hours=3):
    span = days * 24 - margin_hours
    return START + timedelta(hours=rng.uniform(0, span))


def inject_account_takeover(rng, factory, payers, days, tag):
    payer = rng.choice(payers)
    when = random_moment(rng, days)
    device = f"dvc-{rng.getrandbits(32):08x}"
    other = rng.choice([c for c in CAPITALS if c != payer["capital"]])
    geolocation = geo_near(rng, other)
    destination = fresh_destination(rng, rng.randint(1, 20), when)
    for _ in range(rng.randint(2, 4)):
        amount = payer["median"] * rng.uniform(5, 20)
        factory.add("account_takeover", tag, when, amount, payer, destination, device, geolocation)
        when += timedelta(minutes=rng.uniform(0.5, 3))


def inject_mule(rng, factory, payers, days, tag):
    when = random_moment(rng, days)
    destination = fresh_destination(rng, rng.randint(0, 2), when)
    victims = rng.sample(payers, rng.randint(8, 15))
    for victim in victims:
        moment = when + timedelta(minutes=rng.uniform(0, 40))
        factory.add("mule", tag, moment, rng.randint(200, 3000) * 100, victim, destination,
                    rng.choice(victim["devices"]), geo_near(rng, victim["capital"]))


def inject_splitting(rng, factory, payers, days, tag):
    payer = rng.choice(payers)
    when = random_moment(rng, days)
    for _ in range(rng.randint(6, 12)):
        moment = when + timedelta(minutes=rng.uniform(0, 120))
        destination = fresh_destination(rng, rng.randint(30, 700), moment)
        factory.add("splitting", tag, moment, rng.randint(900, 1900) * 100, payer, destination,
                    payer["devices"][0], geo_near(rng, payer["capital"]))


def inject_night_kidnapping(rng, factory, payers, days, tag):
    payer = rng.choice(payers)
    day = START + timedelta(days=rng.randint(0, days - 2))
    when = day + timedelta(hours=22 + rng.uniform(0, 6))
    destination = fresh_destination(rng, rng.randint(1, 60), when)
    factory.add("night_kidnapping", tag, when, rng.randint(2000, 8000) * 100, payer, destination,
                payer["devices"][0], geo_near(rng, payer["capital"]))


def inject_device_farm(rng, factory, payers, days, tag):
    when = random_moment(rng, days)
    device = f"dvc-{rng.getrandbits(32):08x}"
    for payer in rng.sample(payers, rng.randint(4, 6)):
        moment = when + timedelta(minutes=rng.uniform(0, 60))
        destination = rng.choice(payer["recurring"])
        factory.add("device_farm", tag, moment, rng.randint(100, 1500) * 100, payer, destination,
                    device, geo_near(rng, payer["capital"]))


INJECTORS = {
    "account_takeover": inject_account_takeover,
    "mule": inject_mule,
    "splitting": inject_splitting,
    "night_kidnapping": inject_night_kidnapping,
    "device_farm": inject_device_farm,
}


def inject_frauds(rng, factory, payers, days):
    legit = len(factory.events)
    target = legit * FRAUD_SHARE / (1 - FRAUD_SHARE)
    injected, scenario = 0, 0
    # round-robin keeps every typology represented even in small runs
    while injected < target or scenario < len(TYPOLOGIES):
        typology = TYPOLOGIES[scenario % len(TYPOLOGIES)]
        before = len(factory.events)
        INJECTORS[typology](rng, factory, payers, days, f"{typology}-{scenario}")
        injected += len(factory.events) - before
        scenario += 1


def generate_events(seed, payers, days, run_tag):
    rng = random.Random(seed)
    population = generate_population(rng, payers)
    factory = EventFactory(rng, run_tag)
    generate_legit_events(rng, factory, population, days)
    inject_frauds(rng, factory, population, max(days, 3))
    return sorted(factory.events, key=lambda e: datetime.fromisoformat(e["payload"]["transaction_date"]))


def validate_contract(payload):
    checks = [
        (payload, TOP_LEVEL_KEYS),
        (payload["source_account"], SOURCE_ACCOUNT_KEYS),
        (payload["destination_account"], DESTINATION_ACCOUNT_KEYS),
        (payload["source"], SOURCE_KEYS),
    ]
    for obj, keys in checks:
        if set(obj) != keys:
            raise ValueError(f"payload keys {sorted(obj)} differ from contract {sorted(keys)}")
    for account in (payload["source_account"], payload["destination_account"]):
        if set(account["owner"]) != {"document_number"}:
            raise ValueError("owner must have only document_number")
    if set(payload["source"]["geolocation"]) != {"latitude", "longitude"}:
        raise ValueError("geolocation must have latitude and longitude")


def percentile(values, pct):
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def send_events(events, base_url, token):
    session = requests.Session()
    headers = {"INTERNAL-TOKEN": token}
    for event in events:
        started = time.perf_counter()
        try:
            response = session.post(f"{base_url}/pix/transaction", json=event["payload"],
                                    headers=headers, timeout=30)
            status_code = response.status_code
            body = response.json() if response.ok else None
        except (requests.RequestException, ValueError):
            status_code, body = 0, None
        event["latency_ms"] = (time.perf_counter() - started) * 1000
        event["http_status"] = status_code
        event["response"] = body


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
            groups[e["group"]].append(e["response"]["status"] != "approved")
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
        "errors": sum(1 for e in events if not 200 <= e.get("http_status", 0) < 300),
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
    if summary["latencies"]:
        p50, p95, p99 = (percentile(summary["latencies"], p) for p in (50, 95, 99))
        lines.append(f"- P50 {p50:.1f} ms, P95 {p95:.1f} ms, P99 {p99:.1f} ms")
    lines += [f"- requests: {summary['requests']}", f"- non-2xx errors: {summary['errors']}",
              f"- rule_set_version: {', '.join(summary['versions']) or 'n/a'}", ""]
    return "\n".join(lines)


def render_dry_run(events):
    for event in events:
        validate_contract(event["payload"])
    by_label = Counter(e["label"] for e in events)
    dates = [e["payload"]["transaction_date"] for e in events]
    fraud = sum(v for k, v in by_label.items() if k != "legit")
    first_legit = next(e for e in events if e["label"] == "legit")
    first_fraud = next(e for e in events if e["label"] != "legit")
    lines = ["# Dry run (no HTTP)", "", f"total events: {len(events)}",
             f"fraud share: {100 * fraud / len(events):.2f}%"]
    lines += [f"- {label}: {count}" for label, count in sorted(by_label.items())]
    lines += [f"date range: {min(dates)} .. {max(dates)}", "contract check: OK for all payloads",
              "", "legit sample:", json.dumps(first_legit["payload"], indent=2),
              f"fraud sample ({first_fraud['label']}):", json.dumps(first_fraud["payload"], indent=2)]
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="Pix calibration traffic simulator")
    parser.add_argument("--base-url", default=f"http://localhost:{os.environ.get('API_PORT', '3000')}")
    parser.add_argument("--token", default=os.environ.get("INTERNAL_TOKEN", "default_token"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--payers", type=int, default=200)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", help="optional Markdown file for the results")
    return parser.parse_args()


def main():
    args = parse_args()
    run_tag = "dry" if args.dry_run else uuid.uuid4().hex[:8]
    events = generate_events(args.seed, args.payers, args.days, run_tag)
    if args.dry_run:
        print(render_dry_run(events))
        return 0
    print(f"sending {len(events)} Pix to {args.base_url} ...", file=sys.stderr)
    send_events(events, args.base_url.rstrip("/"), args.token)
    report = render_report(summarize(events))
    print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
