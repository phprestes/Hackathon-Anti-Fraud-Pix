"""Avalia o motor sobre o events.jsonl do PixSim em streaming e atualiza as tabelas de docs/05-motor/validacao-pixsim.md."""
import argparse
import json
import os
import statistics
import sys
import time
from array import array
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from analyze import psi  # noqa: E402
from costs import DECISION_SCORE, KS, expected_cost, precision_at_k  # noqa: E402
from in_memory_history import InMemoryHistory  # noqa: E402
from rules import build_rules, engine  # noqa: E402
from rules.features import FEATURE_NAMES  # noqa: E402
from rules.pix_snapshot import PixSnapshot  # noqa: E402

OUT = os.path.join(HERE, "out", "pixsim")
DOC = os.path.join(HERE, "..", "docs", "05-motor", "validacao-pixsim.md")
OURS = os.path.join(HERE, "out", "train-events.jsonl")
START_MARK, END_MARK = "<!-- pixsim:tables:start -->", "<!-- pixsim:tables:end -->"
STATUSES = ("approved", "two_factor_required", "rejected")
DISPERSAL_ROLES = {"fraudster_seed", "mule_forward", "cash_out"}


def group_of(event):
    if event["label"] == "legit":
        return "legit"
    return "dispersal" if event.get("role") in DISPERSAL_ROLES else "victim"


def light(event, status, shadow):
    keep = [s for s in shadow if "LIGHTGBM" in s["rule"]]
    return {"label": event["label"], "payload": {"amount": event["payload"]["amount"],
                                                 "transaction_date": event["payload"]["transaction_date"]},
            "response": {"status": status, "metadata": {"shadow": keep}}}


def auc(positives, negatives):
    if not positives or not negatives:
        return None
    ranked = sorted([(s, 1) for s in positives] + [(s, 0) for s in negatives])
    rank_sum, i = 0.0, 0
    while i < len(ranked):
        j = i
        while j < len(ranked) and ranked[j][0] == ranked[i][0]:
            j += 1
        rank_sum += (i + 1 + j) / 2 * sum(label for _, label in ranked[i:j])
        i = j
    n_pos, n_neg = len(positives), len(negatives)
    return (rank_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def evaluate_stream(path):
    rules = build_rules({})
    history = InMemoryHistory()
    status_by = defaultdict(Counter)
    role_status = defaultdict(Counter)
    rules_by = defaultdict(Counter)
    count_by = Counter()
    value_by = defaultdict(Counter)
    sequence_victim, sequence_any, ring_any, ring_seen = {}, {}, {}, set()
    delays = {}
    views = {"victim": [], "dispersal": []}
    legit_view = []
    scores = defaultdict(lambda: defaultdict(lambda: array("d")))
    flagged = defaultdict(Counter)
    rule_scores = defaultdict(lambda: array("d"))
    features_all = {name: [] for name in FEATURE_NAMES}
    features_fraud = {name: [] for name in FEATURE_NAMES}
    latencies = array("d")
    weights = []
    total_seconds = 0.0
    n_total = n_burn_in = 0
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            payload = event["payload"]
            snapshot = PixSnapshot.from_payload(payload)
            started = time.perf_counter()
            outcome = engine.evaluate(snapshot, engine.build_context(snapshot, history), rules)
            history.record(snapshot, outcome.status)
            elapsed = time.perf_counter() - started
            total_seconds += elapsed
            latencies.append(elapsed * 1000)
            n_total += 1
            if event.get("burn_in"):
                n_burn_in += 1
                continue
            meta = engine.metadata_from(outcome)
            status = outcome.status
            group = group_of(event)
            count_by[group] += 1
            status_by[group][status] += 1
            value_by[group][status] += payload["amount"]
            for reason in meta.get("reasons", []):
                rules_by[group][reason["rule"]] += 1
            record = light(event, status, meta.get("shadow", []))
            if group == "legit":
                legit_view.append(record)
            else:
                views[group].append(record)
                weights.append(event.get("weight", 1.0))
                role_status[(event["label"], event.get("role", "victim_to_mule"))][status] += 1
                barred = status != "approved"
                seq = event["sequence"]
                sequence_any[seq] = sequence_any.get(seq, False) or barred
                if group == "victim":
                    sequence_victim[seq] = sequence_victim.get(seq, False) or barred
                    if "report_delay_days" in event:
                        delays[seq] = (event["report_delay_days"], event["reported"])
                    else:
                        delays.setdefault(seq, None)
                ring = event.get("ring_id", -1)
                if ring >= 0:
                    ring_seen.add(ring)
                    ring_any[ring] = ring_any.get(ring, False) or barred
            for entry in meta.get("shadow", []):
                name = entry["rule"]
                if "score" in entry.get("signals", {}):
                    scores[name][group].append(entry["signals"]["score"])
                flagged[name][(group, entry["would_decide"] != "approved")] += 1
            rule_scores[group].append(DECISION_SCORE[status])
            for name in FEATURE_NAMES:
                features_all[name].append(meta["features"][name])
                if group == "victim":
                    features_fraud[name].append(meta["features"][name])
    mean_weight = statistics.fmean(weights) if weights else 1.0
    return {
        "n_total": n_total, "n_burn_in": n_burn_in, "count_by": count_by, "status_by": status_by,
        "value_by": value_by, "role_status": role_status, "rules_by": rules_by,
        "sequence_victim": sequence_victim, "sequence_any": sequence_any, "ring_any": ring_any,
        "ring_seen": ring_seen, "delays": delays, "legit_view": legit_view, "views": views,
        "scores": scores, "flagged": flagged, "rule_scores": rule_scores, "mean_weight": mean_weight,
        "features_all": features_all, "features_fraud": features_fraud, "latencies": latencies,
        "total_seconds": total_seconds,
    }


def percentile(values, pct):
    ordered = sorted(values)
    return ordered[max(1, int(-(-pct * len(ordered) // 100))) - 1]


def cost_block(legit, fraud, weight):
    legit_cost, fraud_cost = expected_cost(legit), expected_cost(fraud)
    parts = {k: legit_cost["components_cents"][k] + weight * fraud_cost["components_cents"][k]
             for k in legit_cost["components_cents"]}
    raw = expected_cost(legit + fraud)
    effective = len(legit) + weight * len(fraud)
    return {"raw_per_1000_cents": raw["per_1000_cents"], "raw_components_per_1000": raw["components_per_1000_cents"],
            "weighted_per_1000_cents": round(sum(parts.values()) * 1000 / effective),
            "weighted_components_per_1000": {k: round(v * 1000 / effective) for k, v in parts.items()},
            "weight": weight, "pix": len(legit) + len(fraud)}


def metrics_for(result, fraud_groups):
    legit = result["legit_view"]
    out = {"n_total": result["n_total"], "n_burn_in": result["n_burn_in"], "counts": dict(result["count_by"]),
           "latency_ms": {"p50": percentile(result["latencies"], 50), "p95": percentile(result["latencies"], 95),
                          "p99": percentile(result["latencies"], 99),
                          "pix_per_second": round(result["n_total"] / result["total_seconds"])}}
    out["friction"] = {s: result["status_by"]["legit"][s] for s in STATUSES}
    out["groups"] = {}
    for group in fraud_groups:
        out["groups"][group] = {s: result["status_by"][group][s] for s in STATUSES}
        out["groups"][group]["value"] = {s: result["value_by"][group][s] for s in STATUSES}
    out["cost"], out["p_at_k"] = {}, {}
    for group in fraud_groups:
        view = result["views"][group]
        out["cost"][group] = cost_block(legit, view, result["mean_weight"]) if view else None
        out["p_at_k"][group] = {
            "rules": precision_at_k(legit + view),
            "rules_lightgbm": precision_at_k(legit + view, with_lightgbm=True)} if view else None
    out["typology"] = {}
    for (typology, role), counter in sorted(result["role_status"].items()):
        out["typology"][f"{typology}|{role}"] = {s: counter[s] for s in STATUSES}
    victim_seqs = result["sequence_victim"]
    out["sequences"] = {"victim_total": len(victim_seqs), "victim_barred": sum(victim_seqs.values()),
                        "any_total": len(result["sequence_any"]), "any_barred": sum(result["sequence_any"].values()),
                        "by_typology": {}}
    for seq, barred in victim_seqs.items():
        entry = out["sequences"]["by_typology"].setdefault(seq.rsplit("-", 1)[0], [0, 0])
        entry[0] += 1
        entry[1] += barred
    out["rings"] = {"total": len(result["ring_seen"]), "barred": sum(result["ring_any"].values())}
    reported = [d for d in result["delays"].values() if d]
    if reported:
        days = sorted(d for d, _ in reported)
        out["report_delay"] = {"median_days": statistics.median(days), "p90_days": days[int(0.9 * len(days))],
                               "reported_share": sum(r for _, r in reported) / len(reported)}
    out["rule_rates"] = {g: {r: c / result["count_by"][g] for r, c in result["rules_by"][g].items()}
                         for g in ("legit", *fraud_groups) if result["count_by"][g]}
    out["models"] = {}
    for name in sorted(result["scores"]):
        entry = {}
        for group in fraud_groups:
            positives, negatives = result["scores"][name][group], result["scores"][name]["legit"]
            entry[group] = {"auc": auc(positives, negatives),
                            "recall": result["flagged"][name][(group, True)] / max(1, result["count_by"][group])}
        entry["legit_friction"] = result["flagged"][name][("legit", True)] / max(1, result["count_by"]["legit"])
        out["models"][name] = entry
    out["rules_auc"] = {g: auc(result["rule_scores"][g], result["rule_scores"]["legit"]) for g in fraud_groups}
    return out


def psi_table(ours, pixsim):
    rows = []
    for name in FEATURE_NAMES:
        base, other = ours["features_all"][name], pixsim["features_all"][name]
        if len(set(base)) <= 1 and len(set(other)) <= 1:
            continue
        rows.append({"name": name, "all": psi(base, other)[0],
                     "fraud": psi(ours["features_fraud"][name], pixsim["features_fraud"][name])[0]})
    return sorted(rows, key=lambda r: -r["all"])


def pct(value, digits=1):
    return "n/a" if value is None else f"{100 * value:.{digits}f}%".replace(".", ",")


def num(value, digits=3):
    return "n/a" if value is None else f"{value:.{digits}f}".replace(".", ",")


def brl(cents):
    text = f"{cents / 100:,.2f}"
    return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


def status_row(counter):
    total = sum(counter[s] for s in STATUSES)
    return [str(total)] + [pct(counter[s] / total, 2) if total else "n/a" for s in STATUSES]


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def render(pix, ours, psi_rows, extra):
    L = []
    c = pix["counts"]
    L += ["### Tamanho avaliado", "",
          table(["Conjunto", "Pix totais", "Burn-in (histórico)", "Legítimos avaliados", "Fraude pagador→mula", "Fraude dispersão"],
                [["PixSim", str(pix["n_total"]), str(pix["n_burn_in"]), str(c["legit"]), str(c["victim"]), str(c["dispersal"])],
                 ["Nosso simulador (seed 42)", str(ours["n_total"]), "0", str(ours["counts"]["legit"]),
                  str(ours["counts"]["victim"]), "n/a"]]), ""]
    L += ["### Fricção em legítimos", "",
          table(["Conjunto", "Legítimos", "approved", "2FA", "rejected"],
                [["PixSim", *status_row(Counter(pix["friction"]))], ["Nosso simulador", *status_row(Counter(ours["friction"]))]]), ""]
    L += ["### Captura por tipologia do PixSim", "",
          "Pagador→mula é o Pix que a vítima faz (a fraude contra o nosso cliente). `fraudster_seed` é o Pix semente do golpe do Pix errado, "
          "enviado pelo fraudador à vítima. Dispersão (`mule_forward`, `cash_out`) é a mula movendo o dinheiro: o nosso motor só a veria "
          "se a mula fosse cliente do mesmo banco.", "",
          table(["Tipologia", "Papel", "Pix", "approved (escapou)", "2FA", "rejected"],
                [[k.split("|")[0], k.split("|")[1], *status_row(Counter(v))] for k, v in pix["typology"].items()]), ""]
    s, r = pix["sequences"], pix["rings"]
    rows = [[name, f"{barred}/{total}", pct(barred / total)] for name, (total, barred) in sorted(s["by_typology"].items())]
    L += ["### Sequências e anéis", "",
          table(["Tipologia (eventos de fraude)", "Eventos com ao menos um Pix de vítima barrado", "Taxa"], rows), "",
          f"- Eventos com ao menos um Pix barrado em qualquer papel (vítima ou dispersão): {s['any_barred']}/{s['any_total']} ({pct(s['any_barred'] / s['any_total'])}).",
          f"- Anéis de mulas com ao menos um Pix barrado (qualquer papel): {r['barred']}/{r['total']} ({pct(r['barred'] / r['total'])}).", ""]
    if "report_delay" in pix:
        d = pix["report_delay"]
        L += [f"- Atraso de reporte ao MED nos eventos: mediana {num(d['median_days'], 2)} dia(s), p90 {num(d['p90_days'], 1)} dias; "
              f"{pct(d['reported_share'])} reportados dentro da janela de contestação.", ""]
    L += ["### Custo esperado (V1)", "",
          "Modelo de [`scripts/cost-model.json`](../../scripts/cost-model.json). \"Bruto\" usa a fração de fraude da amostra; "
          "\"ponderado\" multiplica a fraude pelo peso de importância do PixSim (a amostra tem fraude superamostrada), aproximando a taxa real.", ""]
    rows = []
    for name, data in (("PixSim, visão pagador (legítimo + pagador→mula)", pix["cost"]["victim"]),
                       ("PixSim, visão dispersão (legítimo + dispersão)", pix["cost"]["dispersal"]),
                       ("Nosso simulador", ours["cost"]["victim"])):
        w = data["weighted_components_per_1000"]
        rows.append([name, brl(data["raw_per_1000_cents"]), brl(data["weighted_per_1000_cents"]), brl(w["fraud_approved"] + w["fraud_2fa_escape"]),
                     brl(w["legit_2fa"] + w["legit_rejected"])])
    L += [table(["Visão", "Bruto por 1.000 Pix", "Ponderado por 1.000 Pix", "Parte fraude (pond.)", "Parte fricção (pond.)"], rows),
          f"\nPeso médio de importância da fraude no PixSim: {num(pix['cost']['victim']['weight'], 4)} (um evento de fraude vale {num(pix['cost']['victim']['weight'], 4)} de um real).", ""]
    L += ["### P@k diário (V1)", "", "Média diária da precisão nos k Pix mais bem ranqueados (fraude superamostrada: a precisão é inflada na mesma proporção do peso).", ""]
    rows = []
    for name, data in (("PixSim, visão pagador", pix["p_at_k"]["victim"]), ("PixSim, visão dispersão", pix["p_at_k"]["dispersal"]),
                       ("Nosso simulador", ours["p_at_k"]["victim"])):
        for label, key in (("regras", "rules"), ("regras + LightGBM", "rules_lightgbm")):
            rows.append([f"{name}, {label}", *[pct(data[key][k]) for k in KS]])
    L += [table(["Conjunto, ranking", *[f"P@{k}" for k in KS]], rows), ""]
    L += ["### Regras que disparam", "", "Parcela de cada grupo em que a regra disparou (qualquer decisão).", ""]
    names = sorted({r for g in list(pix["rule_rates"].values()) + list(ours["rule_rates"].values()) for r in g},
                   key=lambda r: -(pix["rule_rates"]["legit"].get(r, 0) + pix["rule_rates"].get("victim", {}).get(r, 0)))
    rows = [[n, pct(pix["rule_rates"]["legit"].get(n, 0)), pct(pix["rule_rates"]["victim"].get(n, 0)),
             pct(pix["rule_rates"]["dispersal"].get(n, 0)), pct(ours["rule_rates"]["legit"].get(n, 0)),
             pct(ours["rule_rates"]["victim"].get(n, 0))] for n in names]
    L += [table(["Regra", "PixSim legítimo", "PixSim pagador→mula", "PixSim dispersão", "Nosso legítimo", "Nosso fraude"], rows), ""]
    L += ["### Modelos em shadow (treinados no nosso simulador)", "",
          "AUC é pontuação do modelo na fraude contra o legítimo; recall e fricção usam o limiar do próprio modelo. "
          "No \"Nosso simulador\" os modelos foram treinados nesse mesmo gerador (seed 42): é desempenho dentro da distribuição.", ""]
    rows = []
    for name, m in pix["models"].items():
        o = ours["models"].get(name, {})
        rows.append([name, num(m["victim"]["auc"]), pct(m["victim"]["recall"]), num(m["dispersal"]["auc"]), pct(m["legit_friction"]),
                     num(o.get("victim", {}).get("auc")), pct(o.get("victim", {}).get("recall")), pct(o.get("legit_friction"))])
    rows.append(["regras (decisão como score)", num(pix["rules_auc"]["victim"]), "", num(pix["rules_auc"]["dispersal"]), "",
                 num(ours["rules_auc"]["victim"]), "", ""])
    L += [table(["Modelo", "PixSim AUC pagador", "PixSim recall pagador", "PixSim AUC dispersão", "PixSim fricção legítimo",
                 "Nosso AUC", "Nosso recall", "Nossa fricção"], rows), ""]
    L += ["### PSI das features (nosso gerador × PixSim)", "",
          "Base: nosso simulador (seed 42); comparado: PixSim. PSI acima de 0,25 é deriva forte, entre 0,1 e 0,25 atenção. "
          "Features constantes nos dois lados ficam de fora.", ""]
    rows = [[row["name"], num(row["all"]), num(row["fraud"])] for row in psi_rows[:15]]
    L += [table(["Feature", "PSI (todos os Pix)", "PSI (Pix de fraude pagador→mula)"], rows), ""]
    L += ["### Latência do backtest", "",
          f"- `scripts/backtest.py`: {extra.get('backtest_line', 'n/a')}.",
          f"- Avaliação em streaming deste relatório (motor + histórico em memória, sem HTTP): {pix['n_total']} Pix, "
          f"{pix['latency_ms']['pix_per_second']} Pix/s; por Pix P50 {num(pix['latency_ms']['p50'], 2)} ms, "
          f"P95 {num(pix['latency_ms']['p95'], 2)} ms, P99 {num(pix['latency_ms']['p99'], 2)} ms.", ""]
    return "\n".join(L)


def update_doc(path, tables):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    start, end = text.index(START_MARK) + len(START_MARK), text.index(END_MARK)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text[:start] + "\n\n" + tables + "\n" + text[end:])


def main():
    parser = argparse.ArgumentParser(description="Avaliação do motor no PixSim")
    parser.add_argument("--events", default=os.path.join(OUT, "events.jsonl"))
    parser.add_argument("--ours", default=OURS)
    parser.add_argument("--backtest-json", default=os.path.join(OUT, "backtest.json"))
    parser.add_argument("--json", default=os.path.join(OUT, "validation.json"))
    parser.add_argument("--doc", default=DOC)
    args = parser.parse_args()
    pix_result = evaluate_stream(args.events)
    pix = metrics_for(pix_result, ("victim", "dispersal"))
    ours_result = evaluate_stream(args.ours)
    ours = metrics_for(ours_result, ("victim",))
    psi_rows = psi_table(ours_result, pix_result)
    extra = {}
    if os.path.exists(args.backtest_json):
        with open(args.backtest_json, encoding="utf-8") as handle:
            bt = json.load(handle)
        extra["backtest_line"] = f"{pix['n_total']} Pix em {num(bt['total_seconds'], 1)} s ({num(bt['pix_per_second'], 0)} Pix/s)"
    with open(args.json, "w", encoding="utf-8") as handle:
        json.dump({"pixsim": pix, "ours": ours, "psi": psi_rows}, handle, indent=1, default=str)
    tables = render(pix, ours, psi_rows, extra)
    if os.path.exists(args.doc):
        update_doc(args.doc, tables)
    else:
        print(tables)
    return 0


if __name__ == "__main__":
    sys.exit(main())
