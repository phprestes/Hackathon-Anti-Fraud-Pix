"""MED feedback experiment on PixSim: `select`, `run <scenario>` and `render` (make feedback runs them in order)."""
import argparse
import json
import os
import resource
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from feedback_core import seed_from_world, simulate  # noqa: E402
from model_eval import _pct, _reais  # noqa: E402
from rules.decision import REJECTED, TWO_FACTOR_REQUIRED  # noqa: E402
from train_models import PIXSIM_DOC, replace_between  # noqa: E402

OUT = os.path.join(HERE, "out", "pixsim")
RESULTS = os.path.join(OUT, "feedback.json")
DOC_START, DOC_END = "<!-- pixsim:feedback:start -->", "<!-- pixsim:feedback:end -->"
MATURITY_DAYS = 7
RNG_SEED = 20261017
SCENARIOS = {
    "a": ("a) regras, sem retroalimentação", {}),
    "b": ("b) + sinal de fraude confirmada", {"signal": True}),
    "c": ("c) + modelo campeão fixo", {"signal": True, "use_model": True}),
    "d": ("d) + retreino semanal, campeão/desafiante", {"signal": True, "use_model": True, "retrain": True}),
    "d-b": ("d') como d, pool só do mundo B", {"signal": True, "use_model": True, "retrain": True, "no_seed": True}),
}


def load():
    if os.path.exists(RESULTS):
        with open(RESULTS, encoding="utf-8") as handle:
            return json.load(handle)
    return {"select": {}, "runs": {}}


def save(data):
    with open(RESULTS, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=1)


def totals(result):
    weeks = result["weeks"]
    keys = ("legit", "fraud", "fraud_w", "caught", "caught_w", "fp2fa", "fprej", "no_outcome_w", "escapes",
            "escape_cents", "n2fa", "tp2fa_w", "nrej", "tprej_w", "confirmed_total", "confirmed_from_2fa")
    total = {k: sum(w[k] for w in weeks) for k in keys}
    parts = {k: sum(w["parts"][k] for w in weeks) for k in weeks[0]["parts"]}
    effective = total["legit"] + total["fraud_w"]
    total["cost"] = sum(parts.values()) * 1000 / effective
    total["capture_w"] = total["caught_w"] / total["fraud_w"] if total["fraud_w"] else 0.0
    total["capture"] = total["caught"] / total["fraud"] if total["fraud"] else 0.0
    total["friction"] = (total["fp2fa"] + total["fprej"]) / total["legit"]
    total["no_outcome"] = total["no_outcome_w"] / total["fraud_w"] if total["fraud_w"] else 0.0
    aucs = [w["auc"] for w in weeks if w["auc"] is not None]
    total["auc"] = sum(aucs) / len(aucs) if aucs else None
    return total


def run_select(data):
    """Chooses the signal's decision by weighted cost on world A, so world B stays untouched by the choice."""
    chosen = {}
    for decision in (TWO_FACTOR_REQUIRED, REJECTED):
        started = time.perf_counter()
        result = simulate(os.path.join(OUT, "events.jsonl"), {"signal": decision, "rng_seed": RNG_SEED})
        t = totals(result)
        chosen[decision] = {"cost": t["cost"], "capture_w": t["capture_w"], "friction": t["friction"]}
        print(f"select {decision}: cost {t['cost']:.0f} in {time.perf_counter() - started:.0f} s", file=sys.stderr)
    data["select"] = chosen
    data["select"]["chosen"] = min(chosen, key=lambda d: chosen[d]["cost"])


def run_scenario(data, name):
    if not data["select"]:
        raise SystemExit("run `select` first")
    label, base = SCENARIOS[name]
    cfg = {**base, "signal": data["select"]["chosen"] if base.get("signal") else None,
           "maturity_days": MATURITY_DAYS, "rng_seed": RNG_SEED}
    started = time.perf_counter()
    seed = None if base.get("no_seed") or not base.get("retrain") else seed_from_world(os.path.join(OUT, "features-a.jsonl"))
    result = simulate(os.path.join(OUT, "events-b.jsonl"), cfg, seed)
    result["label"] = label
    result["elapsed"] = time.perf_counter() - started
    result["peak_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    data["runs"][name] = result
    print(f"{name}: cost {totals(result)['cost']:.0f} in {result['elapsed']:.0f} s, peak {result['peak_mb']:.0f} MB",
          file=sys.stderr)


def pt(value, digits=3):
    return "n/d" if value is None else f"{value:.{digits}f}".replace(".", ",")


def pct2(value):
    return "n/d" if value is None else f"{100 * value:.2f}%".replace(".", ",")


def render(data):
    runs = {k: v for k, v in data["runs"].items() if k in SCENARIOS}
    names = [k for k in SCENARIOS if k in runs]
    tot = {k: totals(runs[k]) for k in names}
    sel = data["select"]
    lines = ["", "### Retroalimentação pelo MED", ""]
    lines += [
        "Regerar: `make feedback` (só no backtest: API, banco e `ACTIVE_RULES` não mudam). O mundo B é reproduzido em ordem de `transaction_date`; "
        "cada fraude de vítima reportada gera um desfecho em `transaction_date + report_delay_days`, aplicado ao histórico quando o relógio dos dados o alcança. "
        "Pix que o motor reprova não liquida e não gera desfecho (viés de seleção); com 2FA, a fração `two_factor_escape_rate` (10%) passa e gera desfecho, "
        "sorteada por hash do id do Pix, igual em todos os cenários. Só o Pix de vítima (`victim_to_mule`) vira desfecho: o MED é o reporte da vítima, "
        "e a dispersão da mula e o cash-out ficam sem rótulo, como nas seções anteriores. Fraude nunca reportada não gera desfecho.", "",
        "Peças (todas em `scripts/feedback_core.py`): heap de desfechos pendentes; regra `COUNTERPARTY_CONFIRMED_FRAUD` (destino que recebeu, de outro pagador, "
        "Pix com fraude confirmada antes do instante t), registrada só no backtest com `build_rules() + [regra]`; LightGBM instalado (treinado no mundo A) como regra extra "
        "(score ≥ limiar → `two_factor_required`); retreino a cada 7 dias com os hiperparâmetros fixos de `--source pixsim`, em pool formado pelas linhas do mundo A "
        f"(com os rótulos conhecidos no fim do A, a história anterior) mais as linhas do mundo B já passadas: positivo = desfecho já chegado, negativo = Pix com mais de {MATURITY_DAYS} dias sem desfecho "
        "(mais novos ficam fora). O desafiante treinado na virada da semana k roda em sombra na semana k+1 e é promovido se o custo ponderado dessa semana, "
        "com a decisão final (regras + modelo), for menor que o do campeão.", "",
        f"Decisão do sinal escolhida no mundo A (para não usar o B na escolha): "
        f"2FA custa R$ {sel['two_factor_required']['cost'] / 100:.2f} por 1.000 Pix e reprovar custa R$ {sel['rejected']['cost'] / 100:.2f}; "
        f"usado: `{sel['chosen']}`.".replace(".", ",").replace(",00", ",00"), ""]
    lines += ["| cenário | custo ponderado por 1.000 Pix | captura ponderada | captura bruta | fricção em legítimos | AUC médio do campeão | fraudes sem desfecho possível | escapes confirmados |",
              "|---|---|---|---|---|---|---|---|"]
    for k in names:
        t = tot[k]
        lines.append(f"| {runs[k]['label']} | {_reais(round(t['cost']))} | {_pct(t['capture_w'])} | {_pct(t['capture'])} | {_pct(t['friction'])} | "
                     f"{pt(t['auc'])} | {_pct(t['no_outcome'])} | {t['escapes']} ({_reais(t['escape_cents'])}) |")
    lines += ["", "O AUC é o do LightGBM instalado ou promovido, calculado por semana sobre os Pix de vítima e legítimos (rótulo verdadeiro) e tirado a média; "
              "nos cenários a e b o modelo não decide, só é medido. \"Fraudes sem desfecho possível\" é o peso das fraudes de vítima reprovadas, com 2FA que barrou ou nunca reportadas, sobre o peso total das fraudes.", ""]
    weeks = max(len(runs[k]["weeks"]) for k in names)
    for title, field, fmt in [("Custo ponderado por 1.000 Pix, semana a semana", "cost", lambda w: _reais(round(w["cost"]))),
                              ("Captura ponderada de vítimas, semana a semana", "capture", lambda w: _pct(w["caught_w"] / w["fraud_w"] if w["fraud_w"] else 0.0)),
                              ("AUC do campeão, semana a semana", "auc", lambda w: pt(w["auc"]))]:
        lines += [f"**{title}**", "", "| semana | " + " | ".join(SCENARIOS[k][0].split(")")[0] for k in names) + " |", "|---|" + "---|" * len(names)]
        for i in range(weeks):
            cells = [fmt(runs[k]["weeks"][i]) if i < len(runs[k]["weeks"]) else "" for k in names]
            lines.append(f"| {i} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["A semana 4 tem só 2 dias de dados (o mundo B tem 30 dias de avaliação).", ""]
    lines += mermaid(runs, names)
    for k in ("d", "d-b"):
        if k in runs:
            lines += promotions_table(runs[k], SCENARIOS[k][0])
    lines += monitoring_table(runs, names)
    meta = [f"{k}: {runs[k]['elapsed']:.0f} s, pico {runs[k]['peak_mb']:.0f} MB" for k in names]
    lines += ["Tempo e pico de memória por cenário (um processo por cenário, `ulimit -v 2500000`): " + "; ".join(meta) + ".", ""]
    return lines


def mermaid(runs, names):
    xs = ", ".join(str(i) for i in range(max(len(runs[k]["weeks"]) for k in names)))
    top = max(w["cost"] for k in names for w in runs[k]["weeks"])
    lines = ["```mermaid", "xychart-beta", '    title "Custo ponderado por 1.000 Pix (R$) por semana: a, b, c, d"',
             f"    x-axis [{xs}]", f'    y-axis "R$ por 1.000 Pix" 0 --> {int(top / 100) + 10}']
    for k in names:
        if k == "d-b":
            continue
        values = ", ".join(f"{w['cost'] / 100:.1f}" for w in runs[k]["weeks"])
        lines.append(f"    line [{values}]")
    return lines + ["```", "", "Linhas, na ordem: " + ", ".join(SCENARIOS[k][0].split(")")[0] for k in names if k != "d-b") + ".", ""]


def promotions_table(result, label):
    lines = [f"**Promoções, cenário {label}**", "",
             "| semana avaliada | linhas do treino | positivos no treino | custo do campeão | custo do desafiante | promovido |", "|---|---|---|---|---|---|"]
    for p in result["promotions"]:
        if p.get("skipped"):
            lines.append(f"| {p['week']} | {p['rows']} | {p['positives']} | | | sem treino (poucos positivos) |")
        else:
            lines.append(f"| {p['week']} | {p['rows']} | {p['positives']} | {_reais(round(p['champion_cost']))} | "
                         f"{_reais(round(p['challenger_cost']))} | {'sim' if p['promoted'] else 'não'} |")
    return lines + [""]


def monitoring_table(runs, names):
    key = "d" if "d" in runs else names[-1]
    result = runs[key]
    lines = [f"**Monitoramento semanal, cenário {SCENARIOS[key][0]}**", "",
             "| semana | escapes confirmados na semana | valor dos escapes | 2FA: precisão real | 2FA: precisão observada | reprovação: precisão real | reprovação: precisão observada | reprovações (% dos Pix) | fraudes sem desfecho possível |",
             "|---|---|---|---|---|---|---|---|---|"]
    for w in result["weeks"]:
        p2 = w["tp2fa_w"] / (w["tp2fa_w"] + w["fp2fa"]) if w["tp2fa_w"] + w["fp2fa"] else None
        pr = w["tprej_w"] / (w["tprej_w"] + w["fprej"]) if w["tprej_w"] + w["fprej"] else None
        observed = w["confirmed_from_2fa_w"] / (w["tp2fa_w"] + w["fp2fa"]) if w["tp2fa_w"] + w["fp2fa"] else None
        lines.append(f"| {w['week']} | {w['escapes']} | {_reais(w['escape_cents'])} | {pct2(p2)} | "
                     f"{pct2(observed)} | {pct2(pr)} | 0,00% | "
                     f"{_pct(w['nrej'] / w['pix'])} | {_pct(w['no_outcome_w'] / w['fraud_w'] if w['fraud_w'] else 0.0)} |")
    return lines + ["", "Precisão real usa o rótulo do simulador; a observada é o que o banco enxergaria: desfechos chegados na semana "
                    "(só dos Pix com 2FA que escaparam, 10%) sobre os Pix com 2FA; ambas com o peso de importância. Escapes e valores são contagens brutas (a fraude está superamostrada). Reprovação nunca gera desfecho, então a precisão observada é 0 por construção.", ""]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["select", "run", "render"])
    parser.add_argument("scenario", nargs="?", choices=list(SCENARIOS))
    args = parser.parse_args()
    data = load()
    if args.command == "select":
        run_select(data)
        save(data)
    elif args.command == "run":
        run_scenario(data, args.scenario)
        save(data)
    else:
        lines = render(data)
        replace_between(PIXSIM_DOC, DOC_START, DOC_END, lines)
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
