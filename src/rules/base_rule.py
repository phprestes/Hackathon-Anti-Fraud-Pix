from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from rules.pix_snapshot import PixSnapshot
from rules.rule_context import RuleContext


@dataclass(frozen=True)
class RuleResult:
    code: str
    decision: str
    reason: str
    signals: dict = field(default_factory=dict)


class BaseRule(ABC):
    code: str
    family: str

    @abstractmethod
    def evaluate(self, pix: PixSnapshot, context: RuleContext) -> RuleResult | None:
        ...
