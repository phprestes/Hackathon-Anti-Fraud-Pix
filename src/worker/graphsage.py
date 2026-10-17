import math
import random

import numpy as np

NODE_FEATURES = [
    "log_in_degree",
    "log_out_degree",
    "log_in_amount",
    "log_out_amount",
    "log_min_account_age_days",
    "new_payer_share",
    "log_dispersion",
]
MAX_NEIGHBORS = 10
AMOUNT_UNIT_CENTS = 100000


def node_vector(raw: dict) -> list[float]:
    """Raw SQL counts -> the 7 inputs; logs damp heavy tails, the share stays in [0, 1]."""
    in_degree = raw["in_degree"]
    return [
        math.log1p(in_degree),
        math.log1p(raw["out_degree"]),
        math.log1p(raw["in_cents"] / AMOUNT_UNIT_CENTS),
        math.log1p(raw["out_cents"] / AMOUNT_UNIT_CENTS),
        math.log1p(max(raw["min_age_days"], 0)),
        raw["new_payers"] / in_degree if in_degree else 0.0,
        math.log1p(raw["dispersion"]),
    ]


def sample_neighbors(key: str, neighbors: set[str] | list[str], rng: random.Random | None = None) -> list[str]:
    """At most MAX_NEIGHBORS; the default generator is seeded by the node so serving is reproducible."""
    ordered = sorted(neighbors)
    if len(ordered) <= MAX_NEIGHBORS:
        return ordered
    return (rng or random.Random(key)).sample(ordered, MAX_NEIGHBORS)


def neighbor_matrix(docs: list[str], edges: list[tuple[str, str]], rng: random.Random | None = None) -> np.ndarray:
    """(n, MAX_NEIGHBORS) indices of sampled neighbors, -1 padded; in and out edges are united."""
    index = {doc: i for i, doc in enumerate(docs)}
    adjacency: dict[str, set[str]] = {}
    for payer, destination in edges:
        adjacency.setdefault(payer, set()).add(destination)
        adjacency.setdefault(destination, set()).add(payer)
    matrix = np.full((len(docs), MAX_NEIGHBORS), -1, dtype=np.int64)
    for doc, neighbors in adjacency.items():
        chosen = [index[n] for n in sample_neighbors(doc, neighbors, rng) if n in index]
        matrix[index[doc], : len(chosen)] = chosen
    return matrix


def aggregate(values: np.ndarray, neighbors: np.ndarray) -> np.ndarray:
    mask = neighbors >= 0
    gathered = values[np.where(mask, neighbors, 0)] * mask[..., None]
    return gathered.sum(axis=1) / np.maximum(mask.sum(axis=1), 1)[:, None]


def forward(weights: dict, features: np.ndarray, neighbors: np.ndarray, cache: dict | None = None) -> np.ndarray:
    """Two mean-aggregation layers (self + neighbors), ReLU, sigmoid head; returns one score per node."""
    agg1 = aggregate(features, neighbors)
    z1 = features @ weights["w_self1"] + agg1 @ weights["w_neigh1"] + weights["b1"]
    h1 = np.maximum(z1, 0.0)
    agg2 = aggregate(h1, neighbors)
    z2 = h1 @ weights["w_self2"] + agg2 @ weights["w_neigh2"] + weights["b2"]
    h2 = np.maximum(z2, 0.0)
    probability = 1.0 / (1.0 + np.exp(-(h2 @ weights["w_out"] + weights["b_out"])))
    if cache is not None:
        cache.update(agg1=agg1, z1=z1, h1=h1, agg2=agg2, z2=z2, h2=h2)
    return probability


def load_weights(model: dict) -> dict:
    return {name: np.array(value, dtype=float) for name, value in model["weights"].items()}


def score_nodes(model: dict, raw_by_doc: dict[str, dict], edges: list[tuple[str, str]], targets: list[str]) -> dict[str, float]:
    docs = sorted(raw_by_doc)
    raw = np.array([node_vector(raw_by_doc[doc]) for doc in docs], dtype=float)
    features = (raw - np.array(model["mean"])) / np.array(model["std"])
    probability = forward(load_weights(model), features, neighbor_matrix(docs, edges))
    position = {doc: i for i, doc in enumerate(docs)}
    return {doc: float(probability[position[doc]]) for doc in targets}
