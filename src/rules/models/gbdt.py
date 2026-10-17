import math


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def raw_score(model: dict, features: dict) -> float:
    values = [features[name] for name in model["features"]]
    total = model["base_score"]
    for tree in model["trees"]:
        # node = [feature_index, threshold, left, right]; a bare number is a leaf.
        while isinstance(tree, list):
            tree = tree[2] if values[tree[0]] <= tree[1] else tree[3]
        total += tree
    return total


def score(model: dict, features: dict) -> float:
    return _sigmoid(raw_score(model, features))
