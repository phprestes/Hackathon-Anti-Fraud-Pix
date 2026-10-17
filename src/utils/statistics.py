import math
import statistics

EARTH_RADIUS_KM = 6371.0
MAD_NORMAL_CONSISTENCY = 1.4826


def robust_z(history: list[float], value: float, min_scale: float) -> float:
    median = statistics.median(history)
    mad = statistics.median(abs(x - median) for x in history)
    # Floor: identical history has MAD 0 and any change would be an infinite z.
    scale = max(MAD_NORMAL_CONSISTENCY * mad, min_scale)
    return (value - median) / scale


def negative_binomial_tail(k: int, shape: float, rate: float, window: float) -> float:
    """P(N >= k) of the Poisson-Gamma predictive, N ~ NegBin(shape, rate / (rate + window))."""
    if k <= 0:
        return 1.0
    p = rate / (rate + window)
    log_p, log_q = math.log(p), math.log1p(-p)
    cdf = sum(
        math.exp(math.lgamma(n + shape) - math.lgamma(shape) - math.lgamma(n + 1) + shape * log_p + n * log_q)
        for n in range(k)
    )
    return max(0.0, 1.0 - cdf)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((phi2 - phi1) / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
