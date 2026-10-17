from rules.base_rule import BaseRule, RuleResult
from rules.decision import TWO_FACTOR_REQUIRED
from rules.signals import geo_elapsed_hours, geo_speed_kmh


class ProfileGeoVelocityRule(BaseRule):
    code = "PROFILE_GEO_VELOCITY"
    family = "profile"

    def __init__(self, min_distance_km: float, max_speed_kmh: float) -> None:
        self.min_distance_km = min_distance_km
        self.max_speed_kmh = max_speed_kmh

    def evaluate(self, pix, context) -> RuleResult | None:
        travel = geo_speed_kmh(pix, context)
        if travel is None:
            return None

        km, speed = travel
        if km <= self.min_distance_km or speed <= self.max_speed_kmh:
            return None

        minutes = round(geo_elapsed_hours(pix, context) * 60)
        return RuleResult(
            self.code,
            TWO_FACTOR_REQUIRED,
            f"Deslocamento de {km:.0f} km em {minutes} min ({speed:.0f} km/h).",
            {"distance_km": round(km, 1), "speed_kmh": round(speed), "elapsed_minutes": minutes},
        )
