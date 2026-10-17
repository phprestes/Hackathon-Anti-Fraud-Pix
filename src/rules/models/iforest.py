import math

EULER_GAMMA = 0.5772156649015329


def average_path_length(n: int) -> float:
    if n <= 1:
        return 0.0
    if n == 2:
        return 1.0
    return 2.0 * (math.log(n - 1) + EULER_GAMMA) - 2.0 * (n - 1) / n


def mean_path_length(model: dict, features: dict) -> float:
    values = [features[name] for name in model["features"]]
    total = 0.0
    for tree in model["trees"]:
        # node = [feature_index, threshold, left, right]; a bare integer is the leaf size.
        depth = 0
        while isinstance(tree, list):
            tree = tree[2] if values[tree[0]] <= tree[1] else tree[3]
            depth += 1
        total += depth + average_path_length(tree)
    return total / len(model["trees"])


def score(model: dict, features: dict) -> float:
    return 2.0 ** (-mean_path_length(model, features) / average_path_length(model["n_samples"]))
