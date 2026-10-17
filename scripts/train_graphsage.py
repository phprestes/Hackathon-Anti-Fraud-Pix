"""Trains the GraphSAGE destination-risk model in numpy and exports src/worker/model/graphsage.json.

Usage: train_graphsage.py <train-events.jsonl>. Evaluation uses the test sets in scripts/out.
"""
import json
import os
import random
import sys
import time
from collections import defaultdict

import numpy as np

from cold_path import (
    EVAL_SETS, MODEL_DIR, WARNING, WINDOW_HOURS, best_f1_threshold, build_window, first_seen_index, floor5,
    load_pix, pct, roc_auc, upsert_block, window_clocks,
)
from worker import graphsage

SEED = 42
HIDDEN = 16
EPOCHS = 200
LEARNING_RATE = 0.01
BATCH = 64
VERSION = "mock-1"


class Graph:
    def __init__(self, window):
        self.window = window
        self.index = {doc: i for i, doc in enumerate(window.docs)}
        self.raw = np.array([graphsage.node_vector(window.raw[d]) for d in window.docs], dtype=float)
        self.targets = np.array([self.index[d] for d in window.targets])
        self.labels = np.array([1.0 if d in window.typologies else 0.0 for d in window.targets])


def init_weights(rng):
    def glorot(rows, cols):
        return rng.normal(0.0, np.sqrt(2.0 / (rows + cols)), size=(rows, cols))
    features = len(graphsage.NODE_FEATURES)
    return {
        "w_self1": glorot(features, HIDDEN), "w_neigh1": glorot(features, HIDDEN), "b1": np.zeros(HIDDEN),
        "w_self2": glorot(HIDDEN, HIDDEN), "w_neigh2": glorot(HIDDEN, HIDDEN), "b2": np.zeros(HIDDEN),
        "w_out": rng.normal(0.0, 0.1, size=HIDDEN), "b_out": np.zeros(()),
    }


def scatter_mean_back(grad_agg, neighbors, size):
    """Backward of graphsage.aggregate: every neighbor receives its share of the aggregated gradient."""
    mask = neighbors >= 0
    share = grad_agg / np.maximum(mask.sum(axis=1), 1)[:, None]
    out = np.zeros((size, grad_agg.shape[1]))
    rows, cols = np.nonzero(mask)
    np.add.at(out, neighbors[rows, cols], share[rows])
    return out


def gradients(weights, features, neighbors, batch, labels, class_weights):
    cache = {}
    probability = graphsage.forward(weights, features, neighbors, cache)
    count = len(batch)
    weight = np.where(labels == 1, class_weights[1], class_weights[0])
    d_logit = np.zeros(len(features))
    d_logit[batch] = weight * (probability[batch] - labels) / count
    grads = {"w_out": cache["h2"].T @ d_logit, "b_out": d_logit.sum()}
    d_z2 = np.outer(d_logit, weights["w_out"]) * (cache["z2"] > 0)
    grads["w_self2"], grads["w_neigh2"], grads["b2"] = cache["h1"].T @ d_z2, cache["agg2"].T @ d_z2, d_z2.sum(axis=0)
    d_h1 = d_z2 @ weights["w_self2"].T + scatter_mean_back(d_z2 @ weights["w_neigh2"].T, neighbors, len(features))
    d_z1 = d_h1 * (cache["z1"] > 0)
    grads["w_self1"], grads["w_neigh1"], grads["b1"] = features.T @ d_z1, cache["agg1"].T @ d_z1, d_z1.sum(axis=0)
    return grads, probability


def weighted_loss(probability, labels, class_weights):
    p = np.clip(probability, 1e-7, 1 - 1e-7)
    weight = np.where(labels == 1, class_weights[1], class_weights[0])
    return float(np.mean(weight * -(labels * np.log(p) + (1 - labels) * np.log(1 - p))))


def numeric_gradient_check():
    """Guards the hand-written backprop: analytic vs central differences on a tiny random graph."""
    rng = np.random.default_rng(0)
    weights = init_weights(rng)
    features = rng.normal(size=(12, len(graphsage.NODE_FEATURES)))
    neighbors = rng.integers(-1, 12, size=(12, 4))
    batch = np.arange(0, 12, 2)
    labels = (rng.random(len(batch)) > 0.5).astype(float)
    class_weights = (1.0, 2.0)
    grads, _ = gradients(weights, features, neighbors, batch, labels, class_weights)
    worst = 0.0
    for name in ("w_self1", "w_neigh2", "b1", "w_out"):
        flat = weights[name].reshape(-1)
        for k in range(min(4, flat.size)):
            saved = flat[k]
            flat[k] = saved + 1e-6
            up = weighted_loss(graphsage.forward(weights, features, neighbors)[batch], labels, class_weights)
            flat[k] = saved - 1e-6
            down = weighted_loss(graphsage.forward(weights, features, neighbors)[batch], labels, class_weights)
            flat[k] = saved
            worst = max(worst, abs((up - down) / 2e-6 - grads[name].reshape(-1)[k]))
    assert worst < 1e-5, f"backprop mismatch {worst}"


def train(graphs, mean, std):
    rng = np.random.default_rng(SEED)
    sampler = random.Random(SEED)
    weights = init_weights(rng)
    features = [(g.raw - mean) / std for g in graphs]
    positives = sum(int(g.labels.sum()) for g in graphs)
    total = sum(len(g.labels) for g in graphs)
    class_weights = (total / (2 * (total - positives)), total / (2 * positives))
    for epoch in range(EPOCHS):
        loss_sum = 0.0
        for g, x in zip(graphs, features):
            neighbors = graphsage.neighbor_matrix(g.window.docs, g.window.edges, sampler)
            order = rng.permutation(len(g.targets))
            for start in range(0, len(order), BATCH):
                pick = order[start:start + BATCH]
                grads, probability = gradients(weights, x, neighbors, g.targets[pick], g.labels[pick], class_weights)
                loss_sum += weighted_loss(probability[g.targets[pick]], g.labels[pick], class_weights)
                for name, grad in grads.items():
                    weights[name] -= LEARNING_RATE * grad
        if epoch % 50 == 0 or epoch == EPOCHS - 1:
            print(f"epoch {epoch:3d} loss {loss_sum:.3f}", file=sys.stderr)
    return weights


def score_graphs(model, graphs):
    weights = graphsage.load_weights(model)
    scores, labels, meta = [], [], []
    for g in graphs:
        x = (g.raw - np.array(model["mean"])) / np.array(model["std"])
        probability = graphsage.forward(weights, x, graphsage.neighbor_matrix(g.window.docs, g.window.edges))
        for doc, i, label in zip(g.window.targets, g.targets, g.labels):
            scores.append(probability[i])
            labels.append(label)
            meta.append(g.window.typologies.get(doc, set()))
    return np.array(scores), np.array(labels), meta


def evaluate(model, path):
    pix = load_pix(path)
    first = first_seen_index(pix)
    graphs = [Graph(build_window(pix, clock, first)) for clock in window_clocks(pix)]
    scores, labels, meta = score_graphs(model, graphs)
    flagged = scores >= model["threshold"]
    positives = labels == 1
    tp = int((flagged & positives).sum())
    result = {
        "nodes": len(labels), "fraud_nodes": int(positives.sum()), "auc": roc_auc(labels, scores),
        "recall": tp / positives.sum(), "precision": tp / flagged.sum() if flagged.sum() else 0.0,
        "friction": (int((flagged & ~positives).sum()), int((~positives).sum())), "typology": {},
    }
    sequences = defaultdict(lambda: defaultdict(list))
    for flag, tags in zip(flagged, meta):
        for typology, sequence in tags:
            sequences[typology][sequence].append(bool(flag))
    for typology, by_sequence in sorted(sequences.items()):
        flags = [flag for values in by_sequence.values() for flag in values]
        result["typology"][typology] = (sum(flags), len(flags), sum(any(v) for v in by_sequence.values()), len(by_sequence))
    return result


def render(title, result):
    lines = [f"### {title}", "",
             f"{result['nodes']} destination nodes over the 72 h windows ({result['fraud_nodes']} fraud destinations).", "",
             "| AUC | precision | recall | friction on legitimate destinations |", "|---|---|---|---|",
             f"| {result['auc']:.3f} | {result['precision']:.3f} | {result['recall']:.3f} | {pct(*result['friction'])} |",
             "", "Fraud destinations flagged per typology (nodes, sequences with at least one destination flagged):", "",
             "| typology | nodes flagged | sequences caught |", "|---|---|---|"]
    for typology, (hit, total, seq_hit, seq_total) in result["typology"].items():
        lines.append(f"| {typology} | {pct(hit, total)} ({hit}/{total}) | {seq_hit}/{seq_total} |")
    return lines + [""]


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    started = time.perf_counter()
    numeric_gradient_check()
    pix = load_pix(sys.argv[1])
    first = first_seen_index(pix)
    graphs = [Graph(build_window(pix, clock, first)) for clock in window_clocks(pix)]
    stacked = np.vstack([g.raw for g in graphs])
    mean, std = stacked.mean(axis=0), np.maximum(stacked.std(axis=0), 1e-6)
    weights = train(graphs, mean, std)
    model = {
        "type": "graphsage", "version": VERSION, "warning": WARNING, "window_hours": WINDOW_HOURS,
        "trained_on": f"{os.path.basename(sys.argv[1])}, seed {SEED}, {len(graphs)} windows",
        "features": graphsage.NODE_FEATURES, "mean": mean.tolist(), "std": std.tolist(),
        "max_neighbors": graphsage.MAX_NEIGHBORS, "hidden": HIDDEN, "weights": {k: v.tolist() for k, v in weights.items()},
    }
    scores, labels, _ = score_graphs({**model, "threshold": 0.5}, graphs)
    model["threshold"] = floor5(best_f1_threshold(labels, scores))
    model["threshold_rule"] = "max F1 over the training destination nodes (in-sample); scores are class-balanced"
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(os.path.join(MODEL_DIR, "graphsage.json"), "w", encoding="utf-8") as handle:
        json.dump(model, handle, separators=(",", ":"))

    train_seconds = time.perf_counter() - started
    lines = ["## GraphSAGE (cold path, numpy)", "",
             f"Two layers, mean aggregation over at most {graphsage.MAX_NEIGHBORS} neighbors (in and out united), hidden {HIDDEN}, "
             f"ReLU, sigmoid; {EPOCHS} epochs of mini-batch gradient descent (lr {LEARNING_RATE}, batch {BATCH}), balanced class weights, "
             f"seed {SEED}, no search. Node label: destination of a mule, account_takeover, splitting or night_kidnapping Pix "
             f"inside the window (device_farm is not a destination fraud). Windows: {WINDOW_HOURS} h, stride 24 h. "
             f"Threshold {model['threshold']} (max F1 on the training nodes). Training took {train_seconds:.1f} s. "
             "The window contains the fraud Pix being scored, so recall is optimistic for the hot path, which only sees "
             "the score of the previous cycle.", ""]
    for title, path in EVAL_SETS:
        lines += render(title, evaluate(model, path))
    upsert_block("graphsage", lines)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
