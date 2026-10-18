"""Trains the payer-sequence HMM (Baum-Welch in numpy) on legitimate payers and exports src/worker/models/artifacts/hmm.json.

Usage: train_hmm.py <train-events.jsonl>. Evaluation uses the test sets in scripts/out.
"""
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _paths  # noqa: E402,F401

from cold_path import EVAL_SETS, MODEL_DIR, WARNING, floor5, load_pix, pct, roc_auc, upsert_block  # noqa: E402
from constants import RULE_NIGHT_END_HOUR, RULE_NIGHT_START_HOUR  # noqa: E402
from worker.models import hmm  # noqa: E402

SEED = 42
STATES = 3
ITERATIONS = 30
WINDOW = 10
MIN_SYMBOLS = 3
SMOOTHING = 1e-3
CDF_POINTS = 201
THRESHOLD_PERCENTILE = 99
VERSION = "mock-1"
PARAMS = {
    "low_ratio": 0.5, "high_ratio": 2.0, "night_start_hour": RULE_NIGHT_START_HOUR, "night_end_hour": RULE_NIGHT_END_HOUR,
}


def payer_sequences(pix):
    """Per payer: (symbols, Pix list) in time order."""
    by_payer = defaultdict(list)
    for p in pix:
        by_payer[p.src].append(p)
    return {
        payer: (hmm.symbol_sequence([(p.dst, p.amount, p.local) for p in rows], PARAMS), rows)
        for payer, rows in by_payer.items()
    }


def forward_backward(pi, a, b, symbols):
    length = len(symbols)
    alpha, scale = np.zeros((length, STATES)), np.zeros(length)
    alpha[0] = pi * b[:, symbols[0]]
    scale[0] = alpha[0].sum()
    alpha[0] /= scale[0]
    for t in range(1, length):
        alpha[t] = (alpha[t - 1] @ a) * b[:, symbols[t]]
        scale[t] = alpha[t].sum()
        alpha[t] /= scale[t]
    beta = np.ones((length, STATES))
    for t in range(length - 2, -1, -1):
        beta[t] = (a @ (b[:, symbols[t + 1]] * beta[t + 1])) / scale[t + 1]
    return alpha, beta, scale


def baum_welch(sequences, rng):
    pi = rng.dirichlet(np.ones(STATES))
    a = 0.5 * np.eye(STATES) + 0.5 * rng.dirichlet(np.ones(STATES), size=STATES)
    b = rng.dirichlet(np.ones(hmm.SYMBOLS), size=STATES)
    history = []
    for _ in range(ITERATIONS):
        pi_acc, a_acc, b_acc = np.zeros(STATES), np.zeros((STATES, STATES)), np.full((STATES, hmm.SYMBOLS), SMOOTHING)
        total = 0.0
        for symbols in sequences:
            alpha, beta, scale = forward_backward(pi, a, b, symbols)
            total += float(np.log(scale).sum())
            gamma = alpha * beta
            pi_acc += gamma[0]
            for t, symbol in enumerate(symbols):
                b_acc[:, symbol] += gamma[t]
            for t in range(len(symbols) - 1):
                a_acc += alpha[t][:, None] * a * (b[:, symbols[t + 1]] * beta[t + 1])[None, :] / scale[t + 1]
        pi = (pi_acc + SMOOTHING) / (pi_acc + SMOOTHING).sum()
        a = (a_acc + SMOOTHING) / (a_acc + SMOOTHING).sum(axis=1, keepdims=True)
        b = b_acc / b_acc.sum(axis=1, keepdims=True)
        history.append(total)
    assert all(later >= earlier - 1e-6 for earlier, later in zip(history, history[1:])), "EM likelihood decreased"
    return pi, a, b, history


def window_nll(model, symbols):
    result = hmm.anomaly_score({**model, "cdf": {"nll": [0.0, 1e9], "probability": [0.0, 1.0]}}, symbols)
    return None if result is None else -result[1]


def build_cdf(pi, a, b, sequences):
    base = {"pi": pi.tolist(), "transition": a.tolist(), "emission": b.tolist(), "window": WINDOW, "min_symbols": MIN_SYMBOLS}
    values = []
    for symbols in sequences:
        for end in range(MIN_SYMBOLS, len(symbols) + 1):
            values.append(window_nll(base, symbols[:end]))
    probabilities = np.linspace(0.0, 1.0, CDF_POINTS)
    return base, np.quantile(values, probabilities), probabilities, float(np.percentile(values, THRESHOLD_PERCENTILE))


def evaluate(model, path):
    pix = load_pix(path)
    sequences = payer_sequences(pix)
    labels, incl, prior, meta = [], [], [], []
    for symbols, rows in sequences.values():
        for i, p in enumerate(rows):
            result_now = hmm.anomaly_score(model, symbols[:i + 1])
            result_before = hmm.anomaly_score(model, symbols[:i]) if i else None
            labels.append(0 if p.label == "legit" else 1)
            incl.append(result_now[0] if result_now else 0.0)
            prior.append(result_before[0] if result_before else 0.0)
            meta.append((p.label, p.sequence))
    labels = np.array(labels)
    out = {}
    for name, scores in (("including the current Pix", np.array(incl)), ("before the current Pix (what the hot path sees)", np.array(prior))):
        flagged = scores >= model["threshold"]
        positives = labels == 1
        tp = int((flagged & positives).sum())
        by_sequence = defaultdict(lambda: defaultdict(list))
        for flag, (label, sequence) in zip(flagged, meta):
            if label != "legit":
                by_sequence[label][sequence].append(bool(flag))
        typology = {}
        for label, sequences_ in sorted(by_sequence.items()):
            flags = [f for v in sequences_.values() for f in v]
            typology[label] = (sum(flags), len(flags), sum(any(v) for v in sequences_.values()), len(sequences_))
        out[name] = {
            "pix": len(labels), "fraud": int(positives.sum()), "auc": roc_auc(labels, scores),
            "recall": tp / positives.sum(), "precision": tp / flagged.sum() if flagged.sum() else 0.0,
            "friction": (int((flagged & ~positives).sum()), int((~positives).sum())), "typology": typology,
        }
    return out


def render(title, results):
    lines = [f"### {title}", ""]
    for name, r in results.items():
        lines += [f"Score {name}: {r['pix']} Pix, {r['fraud']} fraud.", "",
                  "| AUC | precision | recall | friction on legitimate Pix |", "|---|---|---|---|",
                  f"| {r['auc']:.3f} | {r['precision']:.3f} | {r['recall']:.3f} | {pct(*r['friction'])} |", "",
                  "| typology | Pix flagged | sequences caught |", "|---|---|---|"]
        for typology, (hit, total, seq_hit, seq_total) in r["typology"].items():
            lines.append(f"| {typology} | {pct(hit, total)} ({hit}/{total}) | {seq_hit}/{seq_total} |")
        lines.append("")
    return lines


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    started = time.perf_counter()
    pix = load_pix(sys.argv[1])
    payers = payer_sequences(pix)
    legit = [symbols for symbols, rows in payers.values() if all(p.label == "legit" for p in rows)]
    pi, a, b, history = baum_welch(legit, np.random.default_rng(SEED))
    base, nll_table, probabilities, threshold_nll = build_cdf(pi, a, b, legit)
    model = {
        "type": "hmm", "version": VERSION, "warning": WARNING, "states": STATES, "symbols": hmm.SYMBOLS,
        "trained_on": f"{os.path.basename(sys.argv[1])}, seed {SEED}, {len(legit)} legitimate payers",
        **base, **PARAMS,
        "cdf": {"nll": nll_table.tolist(), "probability": probabilities.tolist()},
        "threshold": floor5(THRESHOLD_PERCENTILE / 100), "threshold_nll": threshold_nll,
        "threshold_rule": "p99 of the anomaly scores of the legitimate training windows",
    }
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(os.path.join(MODEL_DIR, "hmm.json"), "w", encoding="utf-8") as handle:
        json.dump(model, handle, separators=(",", ":"))

    lines = ["## HMM de sequência (cold path, numpy)", "",
             f"Discrete HMM, {STATES} states, {hmm.SYMBOLS} symbols (value band vs the payer's own median x new destination x night), "
             f"Baum-Welch with scaling, {ITERATIONS} iterations, seed {SEED}, trained only on the {len(legit)} payers with no fraud Pix "
             f"(log-likelihood {history[0]:.0f} -> {history[-1]:.0f}). Score: mean log-likelihood per symbol of the last {WINDOW} Pix "
             f"mapped to [0, 1] by the empirical CDF of the legitimate windows; threshold = p{THRESHOLD_PERCENTILE} "
             f"({model['threshold']}). Training took {time.perf_counter() - started:.1f} s.", ""]
    for title, path in EVAL_SETS:
        lines += render(title, evaluate(model, path))
    upsert_block("hmm", lines)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
