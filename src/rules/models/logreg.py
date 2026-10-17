import math


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def score(model: dict, features: dict) -> float:
    margin = model["intercept"]
    for name, mean, std, coef in zip(model["features"], model["mean"], model["std"], model["coef"]):
        margin += coef * (features[name] - mean) / std
    return _sigmoid(model["platt"]["a"] * margin + model["platt"]["b"])
