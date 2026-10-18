from rules.core.base_rule import BaseRule, RuleResult
from rules.core.decision import REJECTED
from rules.core.signals import amount_z, geo_elapsed_hours, geo_speed_kmh


class TypologyAccountTakeoverRule(BaseRule):
    code = "TYPOLOGY_ACCOUNT_TAKEOVER"
    family = "typology"

    def __init__(
        self, min_distance_km: float, max_speed_kmh: float, min_history: int, min_scale: float, z_threshold: float
    ) -> None:
        self.min_distance_km = min_distance_km
        self.max_speed_kmh = max_speed_kmh
        self.min_history = min_history
        self.min_scale = min_scale
        self.z_threshold = z_threshold

    def evaluate(self, pix, context) -> RuleResult | None:
        if context.source_history_size < 1 or context.device_seen_for_source:
            return None

        travel = geo_speed_kmh(pix, context)
        impossible_travel = travel is not None and travel[0] > self.min_distance_km and travel[1] > self.max_speed_kmh
        z = amount_z(pix, context, self.min_history, self.min_scale)
        unusual_amount = z is not None and z > self.z_threshold
        if not (impossible_travel or unusual_amount):
            return None

        signals = {"history_size": context.source_history_size}
        details = []
        if impossible_travel:
            km, speed = travel
            minutes = round(geo_elapsed_hours(pix, context) * 60)
            details.append(f"deslocamento de {km:.0f} km em {minutes} min")
            signals |= {"distance_km": round(km, 1), "speed_kmh": round(speed), "elapsed_minutes": minutes}
        if unusual_amount:
            details.append(f"valor {z:.1f}".replace(".", ",") + " desvios acima do padrão")
            signals["z"] = round(z, 2)

        return RuleResult(
            self.code,
            REJECTED,
            f"Padrão de conta tomada: aparelho novo e {' e '.join(details)}.",
            signals,
        )
