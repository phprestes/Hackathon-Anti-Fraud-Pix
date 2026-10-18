"""Per-rule ablation and short sensitivity on PixSim world B (victim view, weighted cost).

`run` is resumable (cache in scripts/out/pixsim/ablation.json); `render` writes the section of
docs/05-motor/validacao-pixsim.md. See docs/05-motor/validacao-pixsim.md, "Contribuição de cada regra".
"""
import argparse
import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from constants import RULE_SET_VERSION  # noqa: E402
from backtest import select_rules  # noqa: E402
from costs import group_of, load_cost_model, weighted_per_1000  # noqa: E402
from in_memory_history import InMemoryHistory  # noqa: E402
from replay import iter_events  # noqa: E402
from rules import build_rules, engine  # noqa: E402
from rules.pix_snapshot import PixSnapshot  # noqa: E402
from train_models import replace_between  # noqa: E402

OUT = os.path.join(HERE, "out", "pixsim")
WORLD_B = os.path.join(OUT, "events-b.jsonl")
CACHE = os.path.join(OUT, "ablation.json")
DOC = os.path.join(HERE, "..", "docs", "05-motor", "validacao-pixsim.md")
START, END = "<!-- pixsim:ablation:start -->", "<!-- pixsim:ablation:end -->"
EXIT_INCOMPLETE = 75

SENSITIVITY = {
    "LIMIT_NIGHT_AMOUNT": ("RULE_LIMIT_NIGHT_AMOUNT_CENTS", [50000, 100000, 200000]),
    "LIMIT_SINGLE_AMOUNT": ("RULE_LIMIT_SINGLE_AMOUNT_CENTS", [2500000, 5000000, 10000000]),
    "VELOCITY_SOURCE_COUNT": ("RULE_VELOCITY_2FA_COUNT", [3, 5, 8]),
    "VELOCITY_DEVICE_SOURCES": ("RULE_DEVICE_MAX_SOURCES_24H", [2, 3, 5]),
    "PROFILE_NEW_DEVICE": ("RULE_NEW_DEVICE_MIN_AMOUNT_CENTS", [10000, 20000, 50000]),
    "PROFILE_NEW_SOURCE_ACCOUNT": ("RULE_SOURCE_MIN_AGE_DAYS", [3, 7, 14]),
    "PROFILE_AMOUNT_ROBUST_Z": ("RULE_PROFILE_Z_2FA_TENTHS", [35, 45, 55]),
    "VELOCITY_POISSON_GAMMA": ("RULE_POISSON_TAIL_PPM", [10, 30, 100]),
    "COUNTERPARTY_NEW_ACCOUNT": ("RULE_DESTINATION_MIN_AGE_DAYS", [15, 30, 60]),
    "COUNTERPARTY_FAN_IN": ("RULE_DESTINATION_MAX_SOURCES_1H", [5, 10, 20]),
    "COUNTERPARTY_FIRST_TIME_HIGH": ("RULE_FIRST_TIME_MIN_AMOUNT_CENTS", [50000, 100000, 300000]),
    "TYPOLOGY_ACCOUNT_TAKEOVER": ("RULE_ATO_Z_TENTHS", [20, 30, 40]),
    "TYPOLOGY_MULE": ("RULE_MULE_MIN_SOURCES_1H", [3, 5, 8]),
}
PRE_CALIBRATION = {"RULE_POISSON_TAIL_PPM": 100,
                   "RULE_PROFILE_Z_2FA_TENTHS": 35, "RULE_NEW_DEVICE_MIN_AMOUNT_CENTS": 50000,
                   "RULE_FIRST_TIME_MIN_AMOUNT_CENTS": 300000}
PRE_LABEL = "set:" + ",".join(f"{k}={v}" for k, v in PRE_CALIBRATION.items())
STATUSES = ("approved", "two_factor_required", "rejected")


def rule_codes():
    return [rule.code for rule in build_rules() if not rule.shadow]


def parse_label(label):
    """`baseline`, `off:CODE` or `set:RULE_X=1,RULE_Y=2` -> (overrides, disabled)."""
    kind, _, rest = label.partition(":")
    if kind == "off":
        return {}, [rest]
    if kind == "set":
        return {k: int(v) for k, v in (pair.split("=") for pair in rest.split(","))}, []
    return {}, []


def evaluate(path, overrides, disabled):
    rules = select_rules([r for r in build_rules(overrides) if not r.shadow], disabled)
    history = InMemoryHistory()
    status = {g: Counter() for g in ("legit", "victim")}
    amount = {g: Counter() for g in ("legit", "victim")}
    fires = {g: Counter() for g in status}
    weight_sum = n_victim = 0
    for event in iter_events(path):
        payload = event["payload"]
        snapshot = PixSnapshot.from_payload(payload)
        outcome = engine.evaluate(snapshot, engine.build_context(snapshot, history), rules)
        history.record(snapshot, outcome.status)
        if event.get("burn_in"):
            continue
        group = group_of(event)
        if group == "dispersal":
            continue
        status[group][outcome.status] += 1
        amount[group][outcome.status] += payload["amount"]
        if group == "victim":
            weight_sum += event.get("weight", 1.0)
            n_victim += 1
        for result in outcome.results:
            fires[group][result.code] += 1
    return {
        "legit": {"pix": sum(status["legit"].values()), **{s: status["legit"][s] for s in STATUSES},
                  "amount_cents": {s: amount["legit"][s] for s in STATUSES}},
        "victim": {"pix": n_victim, "weight": weight_sum / n_victim if n_victim else 1.0,
                   **{s: status["victim"][s] for s in STATUSES},
                   "amount_cents": {s: amount["victim"][s] for s in STATUSES}},
        "fires": {g: dict(fires[g]) for g in fires},
    }


def cost_per_1000(run_, model):
    """Weighted cost per 1,000 Pix, recomputed from raw sums so a new cost model needs no new pass."""
    legit, victim = run_["legit"], run_["victim"]
    friction = (legit["two_factor_required"] * model["friction_cost_2fa_cents"]
                + legit["rejected"] * model["friction_cost_reject_cents"]
                + round(legit["amount_cents"]["rejected"] * model.get("friction_cost_reject_share_of_amount", 0)))
    fraud = (round(victim["amount_cents"]["approved"] * model["fraud_loss_factor"])
             + round(victim["amount_cents"]["two_factor_required"] * model["two_factor_escape_rate"]))
    return weighted_per_1000({"friction": friction}, {"fraud": fraud}, legit["pix"], victim["pix"], victim["weight"])


def load():
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as handle:
            return json.load(handle)
    return {}


def save(cache):
    with open(CACHE, "w", encoding="utf-8") as handle:
        json.dump(cache, handle)


def planned(cache):
    """Baseline first; then runs only for rules that fired (a rule that never fires cannot change anything)."""
    labels = ["baseline"]
    if "baseline" not in cache:
        return labels
    labels.append(PRE_LABEL)
    fired = set(cache["baseline"]["fires"]["legit"]) | set(cache["baseline"]["fires"]["victim"])
    for code in rule_codes():
        if code in fired:
            labels.append(f"off:{code}")
    for code, (param, values) in SENSITIVITY.items():
        if code not in fired:
            continue
        current = build_current(param)
        labels += [f"set:{param}={v}" for v in values if v != current]
    return labels


def build_current(param):
    import rules
    return rules.PARAMETERS[param]


def run(budget, only):
    cache = load()
    started = time.monotonic()
    last = 0.0
    while True:
        todo = [label for label in planned(cache) if label not in cache]
        if only:
            todo = [label for label in todo if label in only or label == "baseline"]
        if not todo:
            return 0
        if budget and time.monotonic() - started + last > budget:
            print(f"budget reached, {len(todo)} runs left", file=sys.stderr)
            return EXIT_INCOMPLETE
        label = todo[0]
        began = time.monotonic()
        overrides, disabled = parse_label(label)
        cache[label] = evaluate(WORLD_B, overrides, disabled)
        save(cache)
        last = time.monotonic() - began
        print(f"{label}: cost {cost_per_1000(cache[label], load_cost_model()) / 100:,.2f} ({last:.0f} s)", file=sys.stderr)


def brl(cents, digits=2):
    text = f"{cents / 100:,.{digits}f}"
    return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(value, digits=1):
    return f"{100 * value:.{digits}f}%".replace(".", ",")


def barred(run_):
    victim = run_["victim"]
    return (victim["two_factor_required"] + victim["rejected"]) / victim["pix"]


def stats(cache):
    """Per rule: firing rates, weighted precision and lift from the baseline run."""
    base = cache["baseline"]
    n_l, n_v, w = base["legit"]["pix"], base["victim"]["pix"], base["victim"]["weight"]
    base_rate = w * n_v / (w * n_v + n_l)
    rows = {}
    for code in rule_codes():
        fl, fv = base["fires"]["legit"].get(code, 0), base["fires"]["victim"].get(code, 0)
        precision = w * fv / (w * fv + fl) if fv + fl else None
        rows[code] = {"legit_rate": fl / n_l, "victim_rate": fv / n_v, "fires_legit": fl, "fires_victim": fv,
                      "precision": precision, "lift": precision / base_rate if precision else None}
    return rows, base_rate


def render(cache):
    base = cache["baseline"]
    rows, base_rate = stats(cache)
    model = load_cost_model()
    full = cost_per_1000(base, model)
    lines = ["", f"Mundo B do PixSim (seed 20261017), visão pagador (legítimo + pagador→mula), custo ponderado pelo peso de importância "
             f"({str(round(base['victim']['weight'], 4)).replace('.', ',')}) e por [`scripts/cost-model.json`](../../scripts/cost-model.json). Parâmetros atuais "
             f"(`RULE_SET_VERSION` {RULE_SET_VERSION}). Linha de base com as {len(rule_codes())} regras: **{brl(full)} por 1.000 Pix**; "
             f"{pct(barred(base))} dos Pix de vítima barrados; {pct(base['legit']['two_factor_required'] / base['legit']['pix'], 2)} de 2FA e "
             f"{pct(base['legit']['rejected'] / base['legit']['pix'], 2)} de reprovação em legítimos "
             f"({base['legit']['pix']} legítimos, {base['victim']['pix']} Pix de vítima). "
             f"Taxa base de fraude ponderada: {pct(base_rate, 3)}.", "",
             "**Como ler.** *Disparo* é a fração de Pix do grupo em que a regra aparece nos motivos (qualquer decisão). *Precisão ponderada* é a "
             "fração dos disparos que é fraude de vítima, com a fraude multiplicada pelo peso; *lift* é essa precisão dividida pela taxa base. "
             f"*Sem a regra* é o mesmo mundo com a regra desligada (`scripts/backtest.py --disable`; as outras {len(rule_codes()) - 1} seguem ativas e o histórico "
             "reflete as decisões sem ela). *Contribuição* é o custo sem a regra menos o custo com todas: positiva quer dizer que a regra "
             "economiza dinheiro; negativa, que atrapalha. A ablação é marginal: duas regras que cobrem o mesmo Pix aparecem as duas com contribuição baixa.", "",
             "| Regra | Disparo em legítimos | Disparo em Pix de vítima | Precisão ponderada | Lift | Custo sem a regra (por 1.000 Pix) | "
             "Contribuição (R$ por 1.000 Pix) | Vítima barrada sem a regra | Veredito |",
             "|---|---|---|---|---|---|---|---|---|"]
    verdicts = {}
    for code in rule_codes():
        r = rows[code]
        label = f"off:{code}"
        if r["fires_legit"] + r["fires_victim"] == 0:
            cost, contrib, cap, verdict = brl(full), "R$ 0,00", pct(barred(base)), "sem efeito no PixSim (nunca dispara)"
            delta = 0
        else:
            off = cache[label]
            delta = cost_per_1000(off, model) - full
            cost, contrib, cap = brl(cost_per_1000(off, model)), brl(delta), pct(barred(off))
            verdict = "sem efeito no PixSim" if delta == 0 else ("sem efeito no PixSim (custa mais com ela)" if delta < 0 else "contribui")
        verdicts[code] = (delta, verdict)
        lines.append(f"| `{code}` | {pct(r['legit_rate'], 3)} | {pct(r['victim_rate'])} | "
                     f"{pct(r['precision']) if r['precision'] is not None else 'n/a'} | "
                     f"{('%.1f' % r['lift']).replace('.', ',') + 'x' if r['lift'] else 'n/a'} | {cost} | {contrib} | {cap} | {verdict} |")
    pre = cache[PRE_LABEL]
    lines += ["", f"**Antes da calibração** (os {len(PRE_CALIBRATION)} parâmetros ajustados ainda ativos nos valores anteriores, mesmo modelo de custo): "
              f"{brl(cost_per_1000(pre, model))} por 1.000 Pix e {pct(barred(pre))} dos Pix de vítima barrados, contra "
              f"{brl(full)} e {pct(barred(base))} agora.", "",
              "### Sensibilidade dos parâmetros principais", "",
              "Um parâmetro por vez, os outros nos valores atuais (**negrito**). Custo ponderado por 1.000 Pix, fricção em legítimos "
              "(2FA + reprovação) e Pix de vítima barrados.", "",
              "| Regra | Parâmetro | Valor | Custo por 1.000 Pix | Fricção em legítimos | Vítima barrada |", "|---|---|---|---|---|---|"]
    for code, (param, values) in SENSITIVITY.items():
        if code not in rows or rows[code]["fires_legit"] + rows[code]["fires_victim"] == 0:
            continue
        for value in values:
            entry = base if value == build_current(param) else cache.get(f"set:{param}={value}")
            if entry is None:
                continue
            friction = (entry["legit"]["two_factor_required"] + entry["legit"]["rejected"]) / entry["legit"]["pix"]
            shown = f"{value / 100:,.0f}".replace(",", ".") if "CENTS" in param else str(value)
            unit = "R$ " if "CENTS" in param else ""
            shown = f"{unit}{shown}"
            if value == build_current(param):
                shown = f"**{shown}**"
            lines.append(f"| `{code}` | `{param}` | {shown} | {brl(cost_per_1000(entry, model))} | "
                         f"{pct(friction, 2)} | {pct(barred(entry))} |")
    lines += ["", "Regras que não aparecem na sensibilidade nunca dispararam neste mundo (veja o veredito acima).", ""]
    return lines, verdicts


def main():
    parser = argparse.ArgumentParser(description="Per-rule ablation on PixSim world B")
    parser.add_argument("step", choices=("run", "render", "plan", "json"))
    parser.add_argument("--budget-seconds", type=int, default=0)
    parser.add_argument("--only", default="", help="comma-separated run labels (after the baseline)")
    parser.add_argument("--doc", default=DOC)
    args = parser.parse_args()
    if args.step == "run":
        return run(args.budget_seconds, set(filter(None, args.only.split(","))))
    cache = load()
    if args.step == "plan":
        print("\n".join(f"{'done' if label in cache else 'todo'} {label}" for label in planned(cache)))
        return 0
    if args.step == "json":
        rows, base_rate = stats(cache)
        print(json.dumps({"rows": rows, "base_rate": base_rate}, indent=1))
        return 0
    missing = [label for label in planned(cache) if label not in cache]
    if missing:
        print(f"{len(missing)} runs missing; run `rule_ablation.py run` first", file=sys.stderr)
        return EXIT_INCOMPLETE
    lines, _ = render(cache)
    replace_between(args.doc, START, END, lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
