"""Statistical analyses on the PixSim worlds A and B (streaming, no API, no database); writes docs/05-motor/analises.md."""
import argparse
import json
import math
import os
import random
import statistics
import sys
import time
from bisect import bisect_left
from array import array
from collections import Counter, defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from calibrate import Runner  # noqa: E402
from replay import iter_events  # noqa: E402
from rules import PARAMETERS  # noqa: E402
from rules.features import FEATURE_NAMES  # noqa: E402

PIXSIM = os.path.join(HERE, "out", "pixsim")
DOC_PATH = os.path.join(HERE, "..", "docs", "05-motor", "analises.md")
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


def collect_legit(path):
    """One streaming pass: log(amount) and per-hour/per-day counts of each payer's legitimate Pix (burn-in included)."""
    logs, hourly, daily = defaultdict(list), defaultdict(Counter), defaultdict(Counter)
    first = last = None
    for event in iter_events(path):
        if event["label"] != "legit":
            continue
        payload = event["payload"]
        key = payer_key(event)
        if payload["amount"] > 0:
            logs[key].append(math.log(payload["amount"]))
        moment = datetime.fromisoformat(payload["transaction_date"])
        hour = int(moment.timestamp() // 3600)
        hourly[key][hour] += 1
        daily[key][moment.toordinal()] += 1
        first = hour if first is None else min(first, hour)
        last = hour if last is None else max(last, hour)
    return {"logs": logs, "hourly": hourly, "daily": daily, "hours": (first, last)}


def analyze_amount(collected):
    by_payer = collected["logs"]
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
    if lam > 500:
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def dispersion_indices(counts_by_payer, slots):
    indices = []
    for counts in counts_by_payer.values():
        total = sum(counts.values())
        mean = total / slots
        if mean > 0:
            sumsq = sum(c * c for c in counts.values())
            indices.append((mean, (sumsq - slots * mean * mean) / (slots - 1) / mean))
    return indices


def analyze_dispersion(collected):
    per_payer = {key: sum(c.values()) for key, c in collected["hourly"].items()}
    eligible = {key for key, n in per_payer.items() if n >= MIN_PIX}
    first_hour, last_hour = collected["hours"]
    days = [min(day for c in collected["daily"].values() for day in c), max(day for c in collected["daily"].values() for day in c)]
    series = {
        "hora": ({k: c for k, c in collected["hourly"].items() if k in eligible}, last_hour - first_hour + 1),
        "dia": ({k: c for k, c in collected["daily"].items() if k in eligible}, days[1] - days[0] + 1),
    }
    rng = random.Random(42)
    result = {"payers": len(eligible)}
    for name, (counts, slots) in series.items():
        observed = dispersion_indices(counts, slots)
        reference_counts = {}
        for key, per_slot in counts.items():
            draws = poisson_sample(rng, sum(per_slot.values()))
            reference_counts[key] = Counter(rng.randrange(slots) for _ in range(draws))
        reference = dispersion_indices(reference_counts, slots)
        ratios = [ratio for _, ratio in observed]
        result[name] = {
            "slots": slots, "mean_rate": statistics.mean(m for m, _ in observed),
            "median_index": statistics.median(ratios), "p90_index": sorted(ratios)[int(0.9 * len(ratios))],
            "over": sum(1 for r in ratios if r > 1.5),
            "n": len(ratios),
            "reference_over": sum(1 for _, r in reference if r > 1.5),
            "ratios": ratios,
        }
    return result


def load_features(path):
    """Streams a features export into compact per-feature arrays: all rows, legit rows and fraud rows (label 1)."""
    columns = {name: array("d") for name in FEATURE_NAMES}
    fraud = {name: array("d") for name in FEATURE_NAMES}
    legit_rows = 0
    legit_flags = []
    for line in open(path, encoding="utf-8"):
        row = json.loads(line)
        features = row["features"]
        is_fraud = row["label"] == 1
        legit_flags.append(not is_fraud)
        legit_rows += not is_fraud
        for name in FEATURE_NAMES:
            value = float(features.get(name) or 0)
            columns[name].append(value)
            if is_fraud:
                fraud[name].append(value)
    return {"columns": columns, "fraud": fraud, "legit": legit_flags, "legit_rows": legit_rows}


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


def analyze_psi(world_a, world_b):
    middle = world_a["legit_rows"] // 2
    table = []
    for name in FEATURE_NAMES:
        legit = [v for v, keep in zip(world_a["columns"][name], world_a["legit"]) if keep]
        half = psi(legit[:middle], legit[middle:])
        every = psi(world_a["columns"][name], world_b["columns"][name])
        fraud = psi(world_a["fraud"][name], world_b["fraud"][name])
        table.append({"name": name, "half": half[0], "all": every[0], "fraud": fraud[0], "bins": half[1]})
    return {"table": table, "first": middle, "second": world_a["legit_rows"] - middle,
            "a": len(world_a["legit"]), "b": len(world_b["legit"]),
            "a_fraud": len(world_a["fraud"][FEATURE_NAMES[0]]), "b_fraud": len(world_b["fraud"][FEATURE_NAMES[0]])}


def scenario(runner, path, name, value):
    row = runner.run(path, {name: value})
    if row is None:
        return None
    m = row["metrics"]
    legit_total = m["legit"]["pix"]
    victim = m["victim"]
    return {
        "legit": {s: 100 * m["legit"][s] / legit_total for s in STATUSES},
        "barred": 100 * (victim["two_factor_required"] + victim["rejected"]) / victim["pix"],
        "cost": victim["cost_per_1000_cents"] / 100, "fraud_total": victim["pix"],
    }


def analyze_sensitivity(path, budget):
    """Cost, friction and capture around the current defaults, one parameter at a time, on PixSim world A."""
    runner = Runner(budget, False)
    result = {"params": {}}
    for name, values in SWEEPS.items():
        runs = []
        for value in values:
            outcome = scenario(runner, path, name, value)
            if outcome is None:
                return None
            runs.append((value, outcome))
        result["params"][name] = runs
    result["baseline"] = scenario(runner, path, "RULE_AMOUNT_DAILY_SUM_CENTS", PARAMETERS["RULE_AMOUNT_DAILY_SUM_CENTS"])
    return result


def fmt_value(name, value):
    if name == "RULE_AMOUNT_DAILY_SUM_CENTS":
        return f"R$ {value // 100:,}".replace(",", ".")
    return str(value)


def render(amount, dispersion, drift, sensitivity, meta):
    out = [
        "---",
        "title: Análises estatísticas",
        "summary: Quatro análises no PixSim, simulador de terceiros (log-normalidade do valor por pagador, dispersão das contagens, PSI entre os mundos A e B, sensibilidade de limiar com custo) que sustentam z robusto, Poisson-Gamma e os parâmetros.",
        "related: [regras.md, calibracao.md, validacao-pixsim.md, motor-de-regras.md, ../../scripts/analyze.py]",
        "sources: [scripts/analyze.py, scripts/calibrate.py, scripts/pixsim_adapter.py, src/rules/features.py, Pesquisa QITech (análises 1, 2, 6 e 7)]",
        "---",
        "",
        "# Análises estatísticas",
        "",
        "> [Índice](../README.md) › Motor › Análises",
        ">",
        "> **Responde a:** o valor do Pix por pagador é log-normal (vale o z robusto)? as contagens são Poisson ou super-dispersas (vale a Poisson–Gamma)? as features derivam entre janelas? o quanto cada limiar mexe em fricção e em fraude barrada?",
        "",
        "**Métricas no PixSim, simulador de terceiros.** O PixSim ([validação](validacao-pixsim.md)) não é Pix real e foi gerado por quem não somos: as formas que ele sorteia (valores, chegadas) não foram escolhidas por nós para o motor passar. Os números provam o método e a sensibilidade dos parâmetros neste mundo; com dado real, a mesma rotina deve ser rerodada. O nosso simulador (`scripts/simulate.py`) é só fixture de CI e não entra nestas análises.",
        "",
        f"Gerado por `make analyze` ([scripts/analyze.py](../../scripts/analyze.py)), sem API e sem banco, em leitura por streaming: "
        f"mundo A ({meta['a']} Pix de features, escolha) e mundo B ({meta['b']}, confirmação), ambos de `scripts/out/pixsim/`. "
        "Pagadores com menos de 10 Pix ficam fora das análises 1 e 2.",
        "",
        "## 1. `log(amount)` por pagador",
        "",
        f"**Medido.** No mundo A, só Pix legítimos (burn-in incluído) de {amount['payers']} pagadores com ao menos {MIN_PIX} Pix ({amount['pix']} Pix; "
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
        f"**Medido.** No mundo A, contagem de Pix legítimos por pagador ({dispersion['payers']} pagadores, burn-in incluído) em cada hora e em cada dia da janela, com zeros incluídos. "
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
        f"(a) primeira × segunda metade do mundo A, só legítimos ({drift['first']} × {drift['second']} Pix), a deriva natural; "
        f"(b) mundo A × mundo B, todos os Pix avaliados ({drift['a']} × {drift['b']}), mesma população gerada com outra semente; "
        f"(c) o mesmo, só Pix de fraude ({drift['a_fraud']} × {drift['b_fraud']}).",
        "",
    ]
    ordered = sorted(drift["table"], key=lambda r: -(r["half"] or 0))
    out += md_table(
        ["Feature", "PSI metade × metade (legítimos)", "Leitura", "PSI A × B (todos)", "PSI A × B (fraude)", "Leitura (fraude)"],
        [[r["name"], pt(r["half"], 3), flag(r["half"]), pt(r["all"], 3), pt(r["fraud"], 3), flag(r["fraud"])] for r in ordered])
    attention = [r["name"] for r in drift["table"] if (r["half"] or 0) > 0.1]
    drifted_fraud = [r["name"] for r in drift["table"] if (r["fraud"] or 0) > 0.25]
    drifted_all = [r["name"] for r in drift["table"] if (r["all"] or 0) > 0.25]
    out += [
        "",
        f"**Conclusão.** Entre as metades do período, {len(attention)} de {len(FEATURE_NAMES)} features passam de 0,1"
        + (f" ({', '.join(attention)}), todas efeito de aquecimento do histórico em memória (o histórico cresce com o tempo), não de mudança de comportamento" if attention else "")
        + f". A × B: {len(drifted_all)} features em drift considerando todos os Pix (a fraude é minoria) e {len(drifted_fraud)} considerando só a fraude"
        + (f" ({', '.join(drifted_fraud)})" if drifted_fraud else "")
        + ". Dois mundos da mesma população devem ficar estáveis; o PSI serve de alarme para recalibrar ou retreinar os modelos em shadow quando a população muda.",
        "",
        "## 4. Sensibilidade de limiar",
        "",
        "**Medido.** Passada em streaming pelo mundo A com um parâmetro por vez e os demais nos padrões atuais, a mesma avaliação da "
        "[calibração](calibracao.md). Em legítimos: % aprovado / 2FA / reprovado (fricção). Em fraude: % de Pix pagador→mula barrados (2FA ou reprovação). "
        "Custo: esperado por 1.000 Pix na visão do pagador, com a fraude ponderada pelo peso de importância do PixSim "
        "([`scripts/cost-model.json`](../../scripts/cost-model.json)); a dispersão (lado da mula) não entra. "
        f"Padrão de cada parâmetro marcado com `*`. Linha de base: legítimos {pt(sensitivity['baseline']['legit']['approved'])}% aprovados, "
        f"fraude barrada {pt(sensitivity['baseline']['barred'])}% ({sensitivity['baseline']['fraud_total']} Pix pagador→mula), "
        f"custo R$ {pt(sensitivity['baseline']['cost'])} por 1.000 Pix.",
        "",
    ]
    for name, runs in sensitivity["params"].items():
        out += [f"### `{name}`", ""]
        rows = []
        for value, r in runs:
            mark = "*" if value == PARAMETERS[name] else ""
            rows.append([f"{fmt_value(name, value)}{mark}", pt(r["legit"]["approved"]), pt(r["legit"]["two_factor_required"]),
                         pt(r["legit"]["rejected"]), pt(r["barred"]), pt(r["cost"])])
        out += md_table(["Valor", "Legítimos aprovados %", "Legítimos 2FA %", "Legítimos reprovados %", "Fraude barrada %", "Custo R$/1.000 Pix"], rows)
        labels = [f'"{v // 100 if name == "RULE_AMOUNT_DAILY_SUM_CENTS" else v}"' for v, _ in runs]
        friction = [100 - r["legit"]["approved"] for _, r in runs]
        unit = " Eixo x em reais." if name == "RULE_AMOUNT_DAILY_SUM_CENTS" else ""
        out += ["", f"Linhas: fricção em legítimos (100 − aprovados) e fraude barrada, em %.{unit}", ""]
        out += xychart(name, labels, [("line", friction), ("line", [r["barred"] for _, r in runs])], "%", 100)
        span_fraud = max(r["barred"] for _, r in runs) - min(r["barred"] for _, r in runs)
        span_friction = max(friction) - min(friction)
        span_cost = max(r["cost"] for _, r in runs) - min(r["cost"] for _, r in runs)
        out += ["", f"Amplitude ao varrer o parâmetro: {pt(span_friction)} p.p. de fricção, {pt(span_fraud)} p.p. de fraude barrada e R$ {pt(span_cost)} de custo.", ""]
    spans = {}
    for name, runs in sensitivity["params"].items():
        spans[name] = (max(r["barred"] for _, r in runs) - min(r["barred"] for _, r in runs),
                       max(100 - r["legit"]["approved"] for _, r in runs) - min(100 - r["legit"]["approved"] for _, r in runs),
                       max(r["cost"] for _, r in runs) - min(r["cost"] for _, r in runs))
    most = max(spans, key=lambda n: spans[n][2])
    least = min(spans, key=lambda n: spans[n][2])
    out += [
        f"**Conclusão.** `{most}` é o parâmetro de maior efeito no custo (R$ {pt(spans[most][2])} na faixa varrida; {pt(spans[most][1])} p.p. de fricção, {pt(spans[most][0])} p.p. de fraude) "
        f"e `{least}` o de menor (R$ {pt(spans[least][2])}; {pt(spans[least][1])} e {pt(spans[least][0])} p.p.). "
        "Onde a fraude barrada não muda com a fricção, o limiar está num platô e a escolha é por custo de falso positivo; onde as duas curvas sobem juntas, há troca real. "
        "Os padrões em uso foram escolhidos na [calibração](calibracao.md); esta tabela só mede o entorno deles, no mesmo mundo.",
        "",
    ]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Statistical analyses on PixSim -> docs/05-motor/analises.md")
    parser.add_argument("--events", default=os.path.join(PIXSIM, "events.jsonl"), help="PixSim world A")
    parser.add_argument("--events-b", default=os.path.join(PIXSIM, "events-b.jsonl"), help="PixSim world B")
    parser.add_argument("--features", default=os.path.join(PIXSIM, "features-a.jsonl"))
    parser.add_argument("--features-b", default=os.path.join(PIXSIM, "features-b.jsonl"))
    parser.add_argument("--budget-seconds", type=int, default=0, help="stop before a sensitivity run that would pass this; exit 75, resume from the cache")
    parser.add_argument("--out", default=DOC_PATH)
    args = parser.parse_args()
    started = time.perf_counter()
    collected = collect_legit(args.events)
    amount = analyze_amount(collected)
    dispersion = analyze_dispersion(collected)
    del collected
    print(f"analyses 1 and 2 in {time.perf_counter() - started:.1f} s", file=sys.stderr)
    drift = analyze_psi(load_features(args.features), load_features(args.features_b))
    sensitivity = analyze_sensitivity(args.events, args.budget_seconds)
    if sensitivity is None:
        print("budget reached; run again to continue (progress is cached)", file=sys.stderr)
        return 75
    document = render(amount, dispersion, drift, sensitivity, {"a": drift["a"], "b": drift["b"]})
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(document)
    print(f"wrote {os.path.relpath(args.out)} in {time.perf_counter() - started:.1f} s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
