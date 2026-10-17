from rules.base_rule import BaseRule, RuleResult
from rules.decision import REJECTED


class VelocityDeviceSourcesRule(BaseRule):
    code = "VELOCITY_DEVICE_SOURCES"
    family = "velocity"

    def __init__(self, max_sources: int) -> None:
        self.max_sources = max_sources

    def evaluate(self, pix, context) -> RuleResult | None:
        sources = context.device_distinct_other_sources_last_24h + 1
        if sources <= self.max_sources:
            return None

        return RuleResult(
            self.code,
            REJECTED,
            f"{sources} pagadores distintos no mesmo dispositivo em 24 horas.",
            {"distinct_sources_24h": sources, "max_sources": self.max_sources},
        )
