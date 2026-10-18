"""Converte o CSV do PixSim para o events.jsonl do contrato do enunciado (streaming; Python do projeto)."""
import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

import jsonschema

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _paths  # noqa: E402


DATA = os.path.join(_paths.PIXSIM_OUT, "data")
SCHEMA = os.path.join(_paths.ROOT, "src", "schemas", "post_pix_transaction.json")
TZ = timezone(timedelta(hours=-3))
START = datetime(2026, 9, 1, tzinfo=TZ)
CHANNELS = {"mobile": "app", "internet": "internet_banking", "crypto": "crypto_exit",
            "withdrawal": "cash_withdrawal", "purchase": "merchant_purchase"}
ISPBS = ["60701190", "00000000", "60746948", "90400888", "18236120", "00416968", "17298092", "00360305"]


def check_digit(digits, weights):
    rest = sum(d * w for d, w in zip(digits, weights)) % 11
    return 0 if rest < 2 else 11 - rest


def make_document(account_id, is_company):
    # Multiplicador coprimo com 10^n: o mapa e bijetor, entao contas distintas nunca colidem.
    if is_company:
        digits = [int(c) for c in f"{(account_id * 7919 + 12345678) % 10**8:08d}"] + [0, 0, 0, 1]
        digits.append(check_digit(digits, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]))
        digits.append(check_digit(digits, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]))
        s = "".join(map(str, digits))
        return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"
    digits = [int(c) for c in f"{(account_id * 7919 + 123456789) % 10**9:09d}"]
    digits.append(check_digit(digits, range(10, 1, -1)))
    digits.append(check_digit(digits, range(11, 1, -1)))
    s = "".join(map(str, digits))
    return f"{s[:3]}.{s[3:6]}.{s[6:9]}-{s[9:]}"


def to_cents(amount):
    return max(1, int((Decimal(amount) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)))


def fake_ip(device):
    digest = hashlib.sha256(device.encode()).digest()
    return f"198.{18 + digest[0] % 2}.{digest[1]}.{1 + digest[2] % 254}"


def load_accounts(path):
    shift = None
    accounts = {}
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if shift is None:
                shift = START.date() - date.fromisoformat(row["start_date"])
            account_id = int(row["account_id"])
            opened = date.fromisoformat(row["opening_date"]) + shift
            accounts[account_id] = {
                "branch": f"{1000 + account_id * 31 % 9000:04d}",
                "number": str(100000 + account_id),
                "participant": ISPBS[account_id % len(ISPBS)],
                "opening": datetime(opened.year, opened.month, opened.day, tzinfo=TZ).isoformat(),
                "document": make_document(account_id, row["type"] == "PJ"),
            }
    return accounts


def load_frauds(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return {int(r["scenario_id"]): {"report_delay_days": round(float(r["report_delay_s"]) / 86400, 4),
                                        "reported": r["reported"] == "True"} for r in csv.DictReader(handle)}


def account_payload(account, with_participant):
    body = {"branch": account["branch"], "account_number": account["number"],
            "opening_date": account["opening"], "owner": {"document_number": account["document"]}}
    return {"participant": account["participant"], **body} if with_participant else body


def convert(data_dir, out_path, limit=None):
    accounts = load_accounts(os.path.join(data_dir, "accounts.csv"))
    frauds = load_frauds(os.path.join(data_dir, "frauds.csv"))
    with open(SCHEMA, encoding="utf-8") as handle:
        validator = jsonschema.Draft7Validator(json.load(handle))
    stats = Counter()
    by_type = Counter()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(os.path.join(data_dir, "transactions.csv"), newline="", encoding="utf-8") as source, \
            open(out_path, "w", encoding="utf-8") as sink:
        for row in csv.DictReader(source):
            if limit is not None and stats["total"] >= limit:
                break
            when = START + timedelta(seconds=float(row["t"]))
            payload = {
                "id": f"pixsim-{int(row['tx_id']):07d}",
                "amount": to_cents(row["amount"]),
                "transaction_date": when.isoformat(timespec="milliseconds"),
                "source_account": account_payload(accounts[int(row["sender"])], False),
                "destination_account": account_payload(accounts[int(row["receiver"])], True),
                "source": {"device_id": row["device"], "channel": CHANNELS[row["channel"]], "ip": fake_ip(row["device"])},
            }
            stats["total"] += 1
            if next(validator.iter_errors(payload), None) is not None:
                stats["invalid"] += 1
                continue
            typology = row["fraud_type"]
            scenario = int(row["scenario_id"])
            event = {"label": "legit" if typology == "legit" else typology,
                     "sequence": None if typology == "legit" else f"{typology}-{scenario}",
                     "payload": payload, "typology": typology, "role": row["role"],
                     "burn_in": row["burn_in"] == "True", "weight": float(row["weight"]),
                     "ring_id": int(row["ring_id"])}
            if scenario in frauds:
                event.update(frauds[scenario])
            sink.write(json.dumps(event, separators=(",", ":")) + "\n")
            stats["written"] += 1
            by_type[(typology, row["role"])] += 1
    return stats, by_type


def main():
    parser = argparse.ArgumentParser(description="PixSim CSV -> events.jsonl")
    parser.add_argument("--data", default=DATA)
    parser.add_argument("--out", default=os.path.join(_paths.PIXSIM_OUT, "events.jsonl"))
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    stats, by_type = convert(args.data, args.out, args.limit)
    print(f"events: {stats['written']} written, {stats['invalid']} invalid payloads of {stats['total']} -> {args.out}",
          file=sys.stderr)
    for (typology, role), count in sorted(by_type.items()):
        print(f"  {typology} / {role}: {count}", file=sys.stderr)
    return 1 if stats["invalid"] else 0


if __name__ == "__main__":
    sys.exit(main())
