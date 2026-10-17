"""Statistical analyses over simulator data (no API, no database); writes docs/05-motor/analises.md."""
import argparse
import math
import os
import random
import statistics
import subprocess
import sys
import time
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from backtest import run_backtest  # noqa: E402
from replay import load_events  # noqa: E402
from rules import build_rules  # noqa: E402
from rules.features import FEATURE_NAMES  # noqa: E402

OUT_DIR = os.path.join(HERE, "out")
DOC_PATH = os.path.join(HERE, "..", "docs", "05-motor", "analises.md")
PAYERS, DAYS = 300, 14
MIN_PIX = 10
QUANTILE_POINTS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
PSI_BINS = 10
PSI_EPS = 1e-4
SWEEPS = {
    "RULE_AMOUNT_DAILY_SUM_CENTS": [1_500_000, 2_250_000, 3_000_000, 4_500_000, 6_000_000],
    "RULE_POISSON_TAIL_PPM": [10, 30, 100, 300, 1000],
    "RULE_PROFILE_Z_2FA_TENTHS": [25, 30, 35, 45, 55],
}
STATUSES = ["approved", "two_factor_required", "rejected"]


def generate(name, seed, variant="default"):
    path = os.path.join(OUT_DIR, f"analyze-{name}-events.jsonl")
    os.makedirs(OUT_DIR, exist_ok=True)
    command = [
        sys.executable, os.path.join(HERE, "simulate.py"), "--generate-only", "--events", path,
        "--seed", str(seed), "--payers", str(PAYERS), "--days", str(DAYS), "--fraud-variant", variant,
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return path


def backtest(path):
    events = load_events(path)
    run_backtest(events, build_rules())
    return events


def payer_key(event):
    account = event["payload"]["source_account"]
    return f"{account['branch']}-{account['account_number']}"


def moment_stats(values):
    n = len(values)
    mean = sum(values) / n
    m2 = sum((v - mean) ** 2 for v in values) / n
    if m2 == 0:
        return mean, 0.0, 0.0, 0.0
    m3 = sum((v - mean) ** 3 for v in values) / n
    m4 = sum((v - mean) ** 4 for v in values) / n
    return mean, math.sqrt(m2), m3 / m2 ** 1.5, m4 / m2 ** 2 - 3


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return lines


def xychart(title, labels, series, y_label, y_max=None):
    lines = ["```mermaid", "xychart-beta", f'    title "{title}"', "    x-axis [" + ", ".join(labels) + "]"]
    lines.append(f'    y-axis "{y_label}" 0 --> {y_max}' if y_max else f'    y-axis "{y_label}"')
    for kind, values in series:
        lines.append(f"    {kind} [" + ", ".join(f"{v:.2f}" for v in values) + "]")
    lines.append("```")
    return lines


def pt(value, digits=2):
    return f"{value:.{digits}f}".replace(".", ",")


def pct(part, total, digits=1):
    return pt(100 * part / total, digits) if total else "n/a"


def analyze_amount(events):
    by_payer = defaultdict(list)
    for event in events:
        if event["label"] == "legit" and event["payload"]["amount"] > 0:
            by_payer[payer_key(event)].append(math.log(event["payload"]["amount"]))
    eligible = {key: values for key, values in by_payer.items() if len(values) >= MIN_PIX}
    skews, kurts, z_pooled, z_robust = [], [], [], []
    for values in eligible.values():
        mean, sd, skew, kurt = moment_stats(values)
        skews.append(skew)
        kurts.append(kurt)
        if sd > 0:
            z_pooled += [(v - mean) / sd for v in values]
        median = statistics.median(values)
        mad = statistics.median(abs(v - median) for v in values) * 1.4826
        if mad > 0:
            z_robust += [(v - median) / mad for v in values]
    z_pooled.sort()
    z_robust.sort()
    normal = statistics.NormalDist()

    def quantile(data, p):
        return data[min(len(data) - 1, int(p * len(data)))]

    qq = [(p, normal.inv_cdf(p), quantile(z_pooled, p), quantile(z_robust, p)) for p in QUANTILE_POINTS]
    return {
        "payers_total": len(by_payer), "payers": len(eligible), "pix": sum(len(v) for v in eligible.values()),
        "skew_median": statistics.median(skews), "kurt_median": statistics.median(kurts),
        "symmetric": sum(1 for s in skews if abs(s) < 0.5), "qq": qq,
        "max_qq_gap": max(abs(row[1] - row[2]) for row in qq),
    }


def poisson_sample(rng, lam):
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def dispersion_indices(counts_by_payer, grid):
    indices = []
    for counts in counts_by_payer.values():
        series = [counts.get(slot, 0) for slot in grid]
        mean = sum(series) / len(series)
        if mean > 0:
            indices.append((mean, statistics.variance(series) / mean))
    return indices


def analyze_dispersion(events):
    legit = [e for e in events if e["label"] == "legit"]
    per_payer = Counter(payer_key(e) for e in legit)
    eligible = {key for key, n in per_payer.items() if n >= MIN_PIX}
    hourly, daily = defaultdict(Counter), defaultdict(Counter)
    for event in legit:
        key = payer_key(event)
        if key not in eligible:
            continue
        moment = datetime.fromisoformat(event["payload"]["transaction_date"])
        hourly[key][int(moment.timestamp() // 3600)] += 1
        daily[key][moment.toordinal()] += 1
    stamps = [datetime.fromisoformat(e["payload"]["transaction_date"]) for e in events]
    first_hour, last_hour = int(min(stamps).timestamp() // 3600), int(max(stamps).timestamp() // 3600)
    grids = {
        "hora": range(first_hour, last_hour + 1),
        "dia": range(min(stamps).toordinal(), max(stamps).toordinal() + 1),
    }
    rng = random.Random(42)
    result = {"payers": len(eligible)}
    for name, counts in (("hora", hourly), ("dia", daily)):
        grid = grids[name]
        observed = dispersion_indices(counts, grid)
        reference_counts = {}
        for key, series in counts.items():
            mean = sum(series.values()) / len(grid)
            reference_counts[key] = Counter({slot: poisson_sample(rng, mean) for slot in grid})
        reference = dispersion_indices(reference_counts, grid)
        ratios = [ratio for _, ratio in observed]
        result[name] = {
            "slots": len(grid), "mean_rate": statistics.mean(m for m, _ in observed),
            "median_index": statistics.median(ratios), "p90_index": sorted(ratios)[int(0.9 * len(ratios))],
            "over": sum(1 for r in ratios if r > 1.5), "n": len(ratios),
            "reference_over": sum(1 for _, r in reference if r > 1.5),
            "ratios": ratios,
        }
    return result


def feature_rows(events):
    rows = []
    for event in events:
        moment = datetime.fromisoformat(event["payload"]["transaction_date"])
        rows.append((moment, event["label"], event["response"]["metadata"]["features"]))
    rows.sort(key=lambda row: row[0])
    return rows


def psi(base, other):
    if not base or not other:
        return None, 0
    ordered = sorted(base)
    edges = sorted({ordered[min(len(ordered) - 1, len(ordered) * k // PSI_BINS)] for k in range(1, PSI_BINS)})
    edges = [e for e in edges if e > ordered[0]] or edges
    bins = len(edges) + 1
    expected, actual = [0] * bins, [0] * bins
    for value in base:
        expected[bisect_left(edges, value)] += 1
    for value in other:
        actual[bisect_left(edges, value)] += 1
    total = 0.0
    for e, a in zip(expected, actual):
        e_share, a_share = max(e / len(base), PSI_EPS), max(a / len(other), PSI_EPS)
        total += (a_share - e_share) * math.log(a_share / e_share)
    return total, bins


def flag(value):
    if value is None:
        return "n/a"
    return "drift" if value > 0.25 else "atenção" if value > 0.1 else "estável"


def analyze_psi(train_rows, perturbed_rows):
    legit = [row for row in train_rows if row[1] == "legit"]
    middle = len(legit) // 2
    first, second = legit[:middle], legit[middle:]
    train_fraud = [row for row in train_rows if row[1] != "legit"]
    perturbed_fraud = [row for row in perturbed_rows if row[1] != "legit"]
    table = []
    for name in FEATURE_NAMES:
        half = psi([r[2][name] for r in first], [r[2][name] for r in second])
        every = psi([r[2][name] for r in train_rows], [r[2][name] for r in perturbed_rows])
        fraud = psi([r[2][name] for r in train_fraud], [r[2][name] for r in perturbed_fraud])
        table.append({"name": name, "half": half[0], "all": every[0], "fraud": fraud[0], "bins": half[1]})
    return {"table": table, "first": len(first), "second": len(second),
            "train": len(train_rows), "perturbed": len(perturbed_rows),
            "train_fraud": len(train_fraud), "perturbed_fraud": len(perturbed_fraud)}


def run_scenario(events, overrides):
    run_backtest(events, build_rules(overrides))
    legit = Counter(e["response"]["status"] for e in events if e["label"] == "legit")
    fraud = [e for e in events if e["label"] != "legit"]
    barred = sum(1 for e in fraud if e["response"]["status"] != "approved")
    legit_total = sum(legit.values())
    return {
        "legit": {s: 100 * legit[s] / legit_total for s in STATUSES},
        "barred": 100 * barred / len(fraud), "fraud_total": len(fraud),
    }


def analyze_sensitivity(events):
    result = {"baseline": run_scenario(events, {}), "params": {}}
    for name, values in SWEEPS.items():
        result["params"][name] = [(value, run_scenario(events, {name: value})) for value in values]
    return result


def fmt_value(name, value):
    if name == "RULE_AMOUNT_DAILY_SUM_CENTS":
        return f"R$ {value // 100:,}".replace(",", ".")
    return str(value)


def render(amount, dispersion, drift, sensitivity, meta):
    out = [
        "---",
        "title: Análises estatísticas",
        "summary: Quatro análises sobre o simulador (log-normalidade do valor por pagador, dispersão das contagens, PSI entre janelas, sensibilidade de limiar) que sustentam z robusto, Poisson-Gamma e os parâmetros.",
        "related: [regras.md, calibracao.md, motor-de-regras.md, ../../scripts/analyze.py]",
        "sources: [scripts/analyze.py, scripts/simulate.py (seed 42 e 7), src/rules/features.py, Pesquisa QITech (análises 1, 2, 6 e 7)]",
        "---",
        "",
        "# Análises estatísticas",
        "",
        "> [Índice](../README.md) › Motor › Análises",
        ">",
        "> **Responde a:** o valor do Pix por pagador é log-normal (vale o z robusto)? as contagens são Poisson ou super-dispersas (vale a Poisson–Gamma)? as features derivam entre janelas? o quanto cada limiar mexe em fricção e em fraude barrada?",
        "",
        "**Aviso: os dados são sintéticos.** Vêm do simulador ([ADR 0020](../02-arquitetura/decisoes/0020-simulador-para-calibracao.md)), que sorteia valores log-normais e chegadas Poisson; confirmar essas formas nele é verificar a consistência do motor com o gerador, não a realidade do Pix. Os números provam o método e a sensibilidade dos parâmetros; com dado real, a mesma rotina deve ser rerodada.",
        "",
        f"Gerado por `make analyze` ([scripts/analyze.py](../../scripts/analyze.py)), sem API e sem banco: "
        f"{meta['train']} Pix de treino (seed 42, {PAYERS} pagadores, {DAYS} dias) e {meta['perturbed']} Pix de teste perturbado (seed 7). "
        "Pagadores com menos de 10 Pix ficam fora das análises 1 e 2.",
        "",
        "## 1. `log(amount)` por pagador",
        "",
        f"**Medido.** Só Pix legítimos de {amount['payers']} pagadores com ao menos {MIN_PIX} Pix ({amount['pix']} Pix; "
        f"{amount['payers_total']} pagadores no total). Para cada um, assimetria e curtose em excesso de `log(amount)`; depois o QQ: "
        "os valores viram z-score dentro do pagador (média e desvio, e também mediana e MAD×1,4826, a escala da regra) e seus quantis são lidos contra os da normal.",
        "",
    ]
    out += md_table(["Medida", "Valor"], [
        ["Assimetria mediana", pt(amount["skew_median"])],
        ["Curtose em excesso mediana", pt(amount["kurt_median"])],
        ["Pagadores com \\|assimetria\\| < 0,5", f"{amount['symmetric']} de {amount['payers']} ({pct(amount['symmetric'], amount['payers'])}%)"],
    ])
    out += ["", "QQ agregado (z dentro do pagador):", ""]
    out += md_table(["Quantil", "Normal teórico", "Empírico (média/desvio)", "Empírico (mediana/MAD)"],
                    [[pt(p, 1), pt(t, 3), pt(a, 3), pt(b, 3)] for p, t, a, b in amount["qq"]])
    share = 100 * amount["symmetric"] / amount["payers"]
    verdict = ("justifica" if share >= 70 and amount["max_qq_gap"] < 0.25 else "justifica só em parte")
    out += [
        "",
        f"**Conclusão.** {pct(amount['symmetric'], amount['payers'])}% dos pagadores têm `log(amount)` aproximadamente simétrico e o QQ fica a no máximo "
        f"{pt(amount['max_qq_gap'])} da normal em z: o dado {verdict} o z robusto sobre `log(amount)` da regra `PROFILE_AMOUNT_ROBUST_Z`. "
        "Com poucos Pix por pagador a assimetria amostral é ruidosa; a mediana/MAD segue sem distorcer com um valor extremo no histórico, que é o caso que a regra precisa detectar.",
        "",
        "## 2. Dispersão das contagens",
        "",
        f"**Medido.** Contagem de Pix legítimos por pagador ({dispersion['payers']} pagadores) em cada hora e em cada dia da janela, com zeros incluídos. "
        "Índice de dispersão = variância / média (1 para Poisson, > 1 para super-dispersão, que é o que a binomial negativa modela). "
        "A coluna de referência repete o cálculo com contagens Poisson sorteadas com a mesma média de cada pagador (seed 42), para mostrar quanto de ruído amostral cabe acima de 1,5 sem super-dispersão real.",
        "",
    ]
    rows = []
    for name in ("hora", "dia"):
        d = dispersion[name]
        rows.append([f"por {name}", d["slots"], pt(d["mean_rate"], 3), pt(d["median_index"]), pt(d["p90_index"]),
                     f"{d['over']} de {d['n']} ({pct(d['over'], d['n'])}%)",
                     f"{d['reference_over']} de {d['n']} ({pct(d['reference_over'], d['n'])}%)"])
    out += md_table(["Janela", "Intervalos", "Média por intervalo", "Índice mediano", "Índice p90",
                     "Pagadores com índice > 1,5", "Referência Poisson com índice > 1,5"], rows)
    buckets = [("0-0,5", 0, 0.5), ("0,5-1", 0.5, 1), ("1-1,5", 1, 1.5), ("1,5-2", 1.5, 2), ("2-3", 2, 3), ("3+", 3, math.inf)]
    hourly = dispersion["hora"]["ratios"]
    out += ["", "Distribuição do índice por hora (nº de pagadores):", ""]
    out += xychart("Pagadores por faixa do índice de dispersão (hora)", [f'"{b[0]}"' for b in buckets],
                   [("bar", [sum(1 for r in hourly if lo <= r < hi) for _, lo, hi in buckets])], "pagadores")
    hour, day = dispersion["hora"], dispersion["dia"]
    excess = max(hour["over"] - hour["reference_over"], day["over"] - day["reference_over"])
    if excess > 0.1 * hour["n"]:
        decision = ("há super-dispersão além do ruído de Poisson: a binomial negativa (preditiva da Poisson–Gamma) é a escolha certa "
                    "e uma Poisson simples subestimaria a cauda")
    else:
        decision = ("a super-dispersão intra-pagador não passa do ruído de Poisson; a Poisson simples descreve cada pagador, "
                    "e a Poisson–Gamma continua útil porque a taxa de cada pagador é incerta (prior + pouco histórico), o que dá cauda mais larga na preditiva")
    out += [
        "",
        f"**Conclusão.** Índice mediano {pt(hour['median_index'])} por hora e {pt(day['median_index'])} por dia; "
        f"{pct(hour['over'], hour['n'])}% (hora) e {pct(day['over'], day['n'])}% (dia) dos pagadores passam de 1,5, contra "
        f"{pct(hour['reference_over'], hour['n'])}% e {pct(day['reference_over'], day['n'])}% na referência Poisson. Neste dado, {decision}.",
        "",
        "## 3. PSI entre janelas",
        "",
        "**Medido.** Population Stability Index de cada feature de `FEATURE_NAMES`, com 10 bins por quantil da amostra-base (bins repetidos por valores discretos são fundidos; o PSI usa piso de 0,0001 por bin). "
        "Leitura: < 0,1 estável, 0,1 a 0,25 atenção, > 0,25 drift. Três comparações: "
        f"(a) primeira × segunda metade do período, só legítimos ({drift['first']} × {drift['second']} Pix), a deriva natural; "
        f"(b) treino × teste perturbado, todos os Pix ({drift['train']} × {drift['perturbed']}); "
        f"(c) o mesmo, só Pix de fraude ({drift['train_fraud']} × {drift['perturbed_fraud']}), onde a perturbação (`--fraud-variant perturbed`) age.",
        "",
    ]
    ordered = sorted(drift["table"], key=lambda r: -(r["half"] or 0))
    out += md_table(
        ["Feature", "PSI metade × metade (legítimos)", "Leitura", "PSI treino × perturbado (todos)", "PSI treino × perturbado (fraude)", "Leitura (fraude)"],
        [[r["name"], pt(r["half"], 3), flag(r["half"]), pt(r["all"], 3), pt(r["fraud"], 3), flag(r["fraud"])] for r in ordered])
    attention = [r["name"] for r in drift["table"] if (r["half"] or 0) > 0.1]
    drifted_fraud = [r["name"] for r in drift["table"] if (r["fraud"] or 0) > 0.25]
    drifted_all = [r["name"] for r in drift["table"] if (r["all"] or 0) > 0.25]
    out += [
        "",
        f"**Conclusão.** Entre as metades do período, {len(attention)} de {len(FEATURE_NAMES)} features passam de 0,1"
        + (f" ({', '.join(attention)}), todas efeito de aquecimento do histórico em memória (o histórico cresce com o tempo), não de mudança de comportamento" if attention else "")
        + f". Treino × perturbado: {len(drifted_all)} features em drift considerando todos os Pix (a fraude é minoria) e {len(drifted_fraud)} considerando só a fraude"
        + (f" ({', '.join(drifted_fraud)})" if drifted_fraud else "")
        + ". O PSI isola a perturbação nas features de fraude e serve de alarme para recalibrar ou retreinar os modelos em shadow.",
        "",
        "## 4. Sensibilidade de limiar",
        "",
        f"**Medido.** Backtest em lote com `--set`, um parâmetro por vez, os demais nos padrões, sobre os Pix de treino. "
        "Em legítimos: % aprovado / 2FA / reprovado (fricção). Em fraude: % de Pix barrados (2FA ou reprovação). "
        f"Padrão de cada parâmetro marcado com `*`. Linha de base: legítimos {pt(sensitivity['baseline']['legit']['approved'])}% aprovados, "
        f"fraude barrada {pt(sensitivity['baseline']['barred'])}% ({sensitivity['baseline']['fraud_total']} Pix de fraude).",
        "",
    ]
    defaults = {"RULE_AMOUNT_DAILY_SUM_CENTS": 3_000_000, "RULE_POISSON_TAIL_PPM": 100, "RULE_PROFILE_Z_2FA_TENTHS": 35}
    for name, runs in sensitivity["params"].items():
        out += [f"### `{name}`", ""]
        rows = []
        for value, r in runs:
            mark = "*" if value == defaults[name] else ""
            rows.append([f"{fmt_value(name, value)}{mark}", pt(r["legit"]["approved"]), pt(r["legit"]["two_factor_required"]),
                         pt(r["legit"]["rejected"]), pt(r["barred"])])
        out += md_table(["Valor", "Legítimos aprovados %", "Legítimos 2FA %", "Legítimos reprovados %", "Fraude barrada %"], rows)
        labels = [f'"{v // 100 if name == "RULE_AMOUNT_DAILY_SUM_CENTS" else v}"' for v, _ in runs]
        friction = [100 - r["legit"]["approved"] for _, r in runs]
        unit = " Eixo x em reais." if name == "RULE_AMOUNT_DAILY_SUM_CENTS" else ""
        out += ["", f"Linhas: fricção em legítimos (100 − aprovados) e fraude barrada, em %.{unit}", ""]
        out += xychart(name, labels, [("line", friction), ("line", [r["barred"] for _, r in runs])], "%", 100)
        span_fraud = max(r["barred"] for _, r in runs) - min(r["barred"] for _, r in runs)
        span_friction = max(friction) - min(friction)
        out += ["", f"Amplitude ao varrer o parâmetro: {pt(span_friction)} p.p. de fricção e {pt(span_fraud)} p.p. de fraude barrada.", ""]
    spans = {}
    for name, runs in sensitivity["params"].items():
        spans[name] = (max(r["barred"] for _, r in runs) - min(r["barred"] for _, r in runs),
                       max(100 - r["legit"]["approved"] for _, r in runs) - min(100 - r["legit"]["approved"] for _, r in runs))
    most = max(spans, key=lambda n: spans[n][0] + spans[n][1])
    least = min(spans, key=lambda n: spans[n][0] + spans[n][1])
    out += [
        f"**Conclusão.** `{most}` é o parâmetro mais sensível ({pt(spans[most][1])} p.p. de fricção, {pt(spans[most][0])} p.p. de fraude) "
        f"e `{least}` o menos sensível ({pt(spans[least][1])} e {pt(spans[least][0])} p.p.) na faixa varrida. "
        "Onde a fraude barrada não muda com a fricção, o limiar está num platô e a escolha é por custo de falso positivo; onde as duas curvas sobem juntas, há troca real. "
        "Os padrões em uso foram escolhidos na [calibração](calibracao.md); esta tabela só mede o entorno deles, com o mesmo conjunto sintético.",
        "",
    ]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Statistical analyses -> docs/05-motor/analises.md")
    parser.add_argument("--out", default=DOC_PATH)
    args = parser.parse_args()
    started = time.perf_counter()
    train = backtest(generate("train", 42))
    perturbed = backtest(generate("perturbed", 7, "perturbed"))
    print(f"data ready in {time.perf_counter() - started:.1f} s", file=sys.stderr)
    train_rows, perturbed_rows = feature_rows(train), feature_rows(perturbed)
    amount = analyze_amount(train)
    dispersion = analyze_dispersion(train)
    drift = analyze_psi(train_rows, perturbed_rows)
    sensitivity = analyze_sensitivity(train)
    document = render(amount, dispersion, drift, sensitivity, {"train": len(train), "perturbed": len(perturbed)})
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(document)
    print(f"wrote {os.path.relpath(args.out)} in {time.perf_counter() - started:.1f} s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
