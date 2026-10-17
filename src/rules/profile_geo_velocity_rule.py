from rules.base_rule import BaseRule, RuleResult
from rules.decision import TWO_FACTOR_REQUIRED
from utils.statistics import haversine_km

MIN_ELAPSED_HOURS = 1 / 60


class ProfileGeoVelocityRule(BaseRule):
    code = "PROFILE_GEO_VELOCITY"
    family = "profile"

    def __init__(self, min_distance_km: float, max_speed_kmh: float) -> None:
        self.min_distance_km = min_distance_km
        self.max_speed_kmh = max_speed_kmh

    def evaluate(self, pix, context) -> RuleResult | None:
        previous = context.source_last_geolocation
        if previous is None or pix.latitude is None or pix.longitude is None:
            return None

        latitude, longitude, previous_at = previous
        km = haversine_km(latitude, longitude, float(pix.latitude), float(pix.longitude))
        # Floor avoids dividing by ~0 when two Pix share the same instant.
        hours = max((pix.transaction_date - previous_at).total_seconds() / 3600, MIN_ELAPSED_HOURS)
        speed = km / hours
        if km <= self.min_distance_km or speed <= self.max_speed_kmh:
            return None

        minutes = round(hours * 60)
        return RuleResult(
            self.code,
            TWO_FACTOR_REQUIRED,
            f"Deslocamento de {km:.0f} km em {minutes} min ({speed:.0f} km/h).",
            {"distance_km": round(km, 1), "speed_kmh": round(speed), "elapsed_minutes": minutes},
        )
