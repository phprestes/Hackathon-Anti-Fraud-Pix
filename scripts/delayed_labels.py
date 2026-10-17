"""V5: LightGBM trained with delayed fraud labels (Dal Pozzolo et al., 2018), evaluated on PixSim world B."""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from model_eval import View, _pct, _reais, deciders, evaluate  # noqa: E402
from rules.features import FEATURE_NAMES  # noqa: E402
from train_models import PIXSIM_DOC, VALIDATION_SHARE, train_lightgbm, replace_between  # noqa: E402

PIXSIM_OUT = os.path.join(HERE, "out", "pixsim")
DOC_START, DOC_END = "<!-- pixsim:delayed:start -->", "<!-- pixsim:delayed:end -->"
FIXED_DELAYS_DAYS = (3, 7, 14)
IMMATURE_DAYS = 14
DAY = 86400.0


def known_labels(world, cutoff, delay_days=None):
    """Fraud counts as positive only once reported by the cutoff; the rest is silently legitimate."""
    delay = world.delay_days if delay_days is None else np.full(len(world), float(delay_days))
    reported = world.reported if delay_days is None else np.ones(len(world), dtype=bool)
    return ((world.y == 1) & reported & (world.at + delay * DAY <= cutoff)).astype(int)


def scenarios(world, cutoff):
    out = [("oráculo (todos os rótulos)", world.y.copy(), None),
           ("atraso do PixSim (MED)", known_labels(world, cutoff), None)]
    out += [(f"atraso fixo de {d} dias", known_labels(world, cutoff, d), None) for d in FIXED_DELAYS_DAYS]
    mature = world.at <= cutoff - IMMATURE_DAYS * DAY
    out.append((f"atraso do PixSim, descartando os últimos {IMMATURE_DAYS} dias", known_labels(world, cutoff), mature))
    return out


def delay_summary(world):
    frauds = world.y == 1
    delay = world.delay_days[frauds]
    reported = world.reported[frauds]
    return {"frauds": int(frauds.sum()), "median_days": float(np.median(delay[reported])),
            "p90_days": float(np.percentile(delay[reported], 90)), "unreported": float(1 - reported.mean())}


def fit_scenario(world, labels, keep):
    index = np.arange(len(world)) if keep is None else np.flatnonzero(keep)
    split = int(len(index) * (1 - VALIDATION_SHARE))
    fit, val = index[:split], index[split:]
    model, predict, _ = train_lightgbm(world.X[fit], labels[fit], world.X[val], labels[val])
    return model["threshold"], predict, int(labels[index].sum())


def main():
    started = time.perf_counter()
    world_a = View(os.path.join(PIXSIM_OUT, "features-a.jsonl"), FEATURE_NAMES)
    world_b = View(os.path.join(PIXSIM_OUT, "features-b.jsonl"), FEATURE_NAMES)
    cutoff = float(world_a.at.max())
    summary = delay_summary(world_a)
    total_positives = int(world_a.y.sum())
    results = {}
    for name, labels, keep in scenarios(world_a, cutoff):
        threshold, predict, known = fit_scenario(world_a, labels, keep)
        scores = {"lightgbm": predict(world_b.X)}
        metrics = evaluate(world_b, deciders(world_b, scores, {"lightgbm": threshold}))["lightgbm"]
        results[name] = {"known_positives": known, "threshold": threshold, **metrics}
        print(f"{name}: known {known}/{total_positives} auc {metrics['auc']:.3f} recall {metrics['recall']:.3f}", file=sys.stderr)
    payload = {"cutoff": cutoff, "delays": summary, "total_positives": total_positives, "results": results}
    with open(os.path.join(PIXSIM_OUT, "delayed-labels.json"), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1)
    lines = render(summary, total_positives, results, time.perf_counter() - started)
    replace_between(PIXSIM_DOC, DOC_START, DOC_END, lines)
    print("\n".join(lines))
    return 0


def render(summary, total_positives, results, elapsed):
    pt = lambda x: f"{x:.1f}".replace(".", ",")  # noqa: E731
    lines = [
        "", "### Rótulos atrasados", "",
        "Em produção o rótulo de fraude chega depois do Pix, quando a vítima contesta no MED. O corte de treino T é o fim do mundo A; uma fraude só "
        "vira positiva se `transaction_date + atraso de reporte <= T` (e se foi reportada), e as demais entram como legítimas. "
        f"Atrasos do PixSim (`draw_report_delay`, exportados por `frauds.csv` e levados ao `events.jsonl`) nas {summary['frauds']} fraudes de vítima do mundo A: "
        f"mediana {pt(summary['median_days'])} dias e p90 {pt(summary['p90_days'])} dias entre as reportadas; "
        f"{pt(100 * summary['unreported'])}% nunca são reportadas. LightGBM com os mesmos hiperparâmetros de `--source pixsim`, avaliado no mundo B com rótulos verdadeiros. "
        f"Descartar os últimos {IMMATURE_DAYS} dias é a correção simples: tira do treino os Pix cujo rótulo ainda não amadureceu. "
        f"Gerado em {elapsed:.0f} s por `make delayed-labels`.", "",
        "| cenário de rótulo | positivos conhecidos | AUC | recall | fricção | custo por 1.000 Pix |",
        "|---|---|---|---|---|---|"]
    for name, r in results.items():
        lines.append(f"| {name} | {r['known_positives']} de {total_positives} | {r['auc']:.3f} | {_pct(r['recall'])} | "
                     f"{_pct(r['friction'])} | {_reais(r['cost']['total'])} |".replace(" 0.", " 0,"))
    typologies = list(next(iter(results.values()))["capture"])
    lines += ["", "Captura por tipologia no mundo B (Pix de vítima acima do limiar):", "",
              "| cenário de rótulo | " + " | ".join(typologies) + " |", "|---|" + "---|" * len(typologies)]
    for name, r in results.items():
        lines.append(f"| {name} | " + " | ".join(_pct(r["capture"][t]) for t in typologies) + " |")
    return lines + [""]


if __name__ == "__main__":
    sys.exit(main())
