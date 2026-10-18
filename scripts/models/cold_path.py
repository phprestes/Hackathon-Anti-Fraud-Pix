"""Shared pieces of the cold-path training scripts: events, node features per window, metrics, results file."""
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _paths  # noqa: E402

from constants import GRAPH_RISK_DISPERSION_WINDOW_HOURS  # noqa: E402
from replay import load_events  # noqa: E402

OUT = _paths.OUT
RESULTS = os.path.join(HERE, "model-results.md")
MODEL_DIR = os.path.join(_paths.ROOT, "src", "worker", "models", "artifacts")
WINDOW_HOURS = 72
STRIDE_HOURS = 24
WARNING = "mock: synthetic labels, simulator frauds"
TRAIN_EVENTS = os.path.join(OUT, "train-events.jsonl")
EVAL_SETS = [
    ("Test (seed 7, default frauds)", os.path.join(OUT, "test-events.jsonl")),
    ("Perturbed test (seed 7, perturbed fraud ranges)", os.path.join(OUT, "test-perturbed-events.jsonl")),
]
# device_farm reuses the victims' usual destinations, so it is not a destination fraud.
DESTINATION_FRAUDS = {"mule", "account_takeover", "splitting", "night_kidnapping"}


class Pix:
    __slots__ = ("at", "src", "dst", "amount", "src_open", "dst_open", "label", "sequence", "local")

    def __init__(self, event):
        payload = event["payload"]
        self.at = datetime.fromisoformat(payload["transaction_date"])
        self.local = self.at
        self.src = payload["source_account"]["owner"]["document_number"]
        self.dst = payload["destination_account"]["owner"]["document_number"]
        self.amount = payload["amount"]
        self.src_open = datetime.fromisoformat(payload["source_account"]["opening_date"])
        self.dst_open = datetime.fromisoformat(payload["destination_account"]["opening_date"])
        self.label = event["label"]
        self.sequence = event["sequence"]


def load_pix(path):
    return sorted((Pix(e) for e in load_events(path)), key=lambda p: p.at)


def window_clocks(pix):
    """Trailing windows ending at the last Pix and every STRIDE_HOURS before it (full windows only)."""
    first, last = pix[0].at, pix[-1].at
    clock, clocks = last, []
    while clock - timedelta(hours=WINDOW_HOURS) >= first:
        clocks.append(clock)
        clock -= timedelta(hours=STRIDE_HOURS)
    return sorted(clocks)


class Window:
    def __init__(self, docs, raw, edges, targets, typologies):
        self.docs = docs
        self.raw = raw
        self.edges = edges
        self.targets = targets
        self.typologies = typologies


def build_window(pix, clock, first_seen):
    """Python twin of NODE_FEATURES_SQL / EDGES_SQL in src/repositories/graphsage_repository.py."""
    start = clock - timedelta(hours=WINDOW_HOURS)
    win = [p for p in pix if start < p.at <= clock]
    trade = [p for p in win if p.src != p.dst]
    nodes = {p.src for p in win} | {p.dst for p in win}
    in_payers, in_cents, first_in = defaultdict(set), defaultdict(int), {}
    out_dests, out_cents = defaultdict(set), defaultdict(int)
    opened = {}
    for p in trade:
        in_payers[p.dst].add(p.src)
        in_cents[p.dst] += p.amount
        first_in[p.dst] = min(first_in.get(p.dst, p.at), p.at)
        out_dests[p.src].add(p.dst)
        out_cents[p.src] += p.amount
    for p in win:
        opened[p.src] = max(opened.get(p.src, p.src_open), p.src_open)
        opened[p.dst] = max(opened.get(p.dst, p.dst_open), p.dst_open)
    new_payers = {doc: sum(1 for payer in payers if first_seen[(payer, doc)] > start) for doc, payers in in_payers.items()}
    horizon = timedelta(hours=GRAPH_RISK_DISPERSION_WINDOW_HOURS)
    dispersion = defaultdict(set)
    for p in trade:
        if p.src in first_in and first_in[p.src] <= p.at < first_in[p.src] + horizon:
            dispersion[p.src].add(p.dst)
    raw = {}
    for doc in nodes:
        raw[doc] = {
            "in_degree": len(in_payers[doc]),
            "out_degree": len(out_dests[doc]),
            "in_cents": in_cents[doc],
            "out_cents": out_cents[doc],
            "min_age_days": max(math.floor((clock - opened[doc]).total_seconds() / 86400), 0),
            "new_payers": new_payers.get(doc, 0),
            "dispersion": len(dispersion[doc]),
        }
    typologies = defaultdict(set)
    for p in win:
        if p.label in DESTINATION_FRAUDS:
            typologies[p.dst].add((p.label, p.sequence))
    targets = sorted({p.dst for p in win})
    edges = sorted({(p.src, p.dst) for p in trade})
    return Window(sorted(nodes), raw, edges, targets, typologies)


def first_seen_index(pix):
    first = {}
    for p in pix:
        first.setdefault((p.src, p.dst), p.at)
    return first


def roc_auc(y, scores):
    y, scores = np.asarray(y), np.asarray(scores)
    positives = int(y.sum())
    negatives = len(y) - positives
    if positives == 0 or negatives == 0:
        return float("nan")
    order = scores.argsort(kind="mergesort")
    ranks = np.empty(len(scores))
    sorted_scores = scores[order]
    i = 0
    while i < len(scores):
        j = i
        while j + 1 < len(scores) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    return float((ranks[y == 1].sum() - positives * (positives + 1) / 2) / (positives * negatives))


def best_f1_threshold(y, scores):
    y, scores = np.asarray(y), np.asarray(scores)
    best, best_f1 = 0.5, -1.0
    for candidate in np.unique(scores):
        predicted = scores >= candidate
        tp = int((predicted & (y == 1)).sum())
        denominator = int(predicted.sum()) + int(y.sum())
        f1 = 2 * tp / denominator if denominator else 0.0
        if f1 >= best_f1:
            best, best_f1 = float(candidate), f1
    return best


def floor5(value):
    """Scores are stored with 5 decimals; flooring keeps `stored >= threshold` equal to `score >= threshold`."""
    return math.floor(value * 1e5) / 1e5


def pct(part, total):
    return f"{100 * part / total:.1f}%" if total else "n/a"


def upsert_block(name, lines):
    """Replaces (or appends) a marked block of scripts/models/model-results.md without touching the rest."""
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    block = "\n".join([start, *lines, end])
    text = open(RESULTS, encoding="utf-8").read() if os.path.exists(RESULTS) else ""
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    text = pattern.sub(lambda _: block, text) if pattern.search(text) else text.rstrip("\n") + "\n\n" + block + "\n"
    with open(RESULTS, "w", encoding="utf-8") as handle:
        handle.write(text)


def marked_blocks(text):
    return [m.group(0) for m in re.finditer(r"<!-- (\w+):start -->.*?<!-- \1:end -->", text, re.S)]
