from datetime import datetime
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AccountRiskReading:
    score: float
    computed_at: datetime
    contributions: tuple[tuple[str, float], ...] = ()


class HistoryPort(Protocol):
    """Aggregates the engine needs; every method excludes `exclude_pix_id` and looks only before `until`."""

    def count_source_attempts_since(self, document: str, since: datetime, until: datetime, exclude_pix_id: str) -> int:
        ...

    def sum_source_not_rejected_since(self, document: str, since: datetime, until: datetime, exclude_pix_id: str) -> int:
        ...

    def count_source_history(self, document: str, until: datetime, exclude_pix_id: str) -> int:
        ...

    def source_used_device(self, document: str, device_id: str, until: datetime, exclude_pix_id: str) -> bool:
        ...

    def source_paid_destination_not_rejected(
        self, document: str, destination_document: str, until: datetime, exclude_pix_id: str
    ) -> bool:
        ...

    def count_device_other_sources_since(
        self, device_id: str, document: str, since: datetime, until: datetime, exclude_pix_id: str
    ) -> int:
        ...

    def count_destination_other_sources_since(
        self, destination_document: str, document: str, since: datetime, until: datetime, exclude_pix_id: str
    ) -> int:
        ...

    def list_source_amounts_not_rejected_since(
        self, document: str, since: datetime, until: datetime, exclude_pix_id: str
    ) -> tuple[int, ...]:
        ...

    def first_source_transaction_date(self, document: str, until: datetime, exclude_pix_id: str) -> datetime | None:
        ...

    def last_source_geolocation(
        self, document: str, until: datetime, exclude_pix_id: str
    ) -> tuple[float, float, datetime] | None:
        ...

    def count_source_new_destinations_since(
        self, document: str, since: datetime, until: datetime, exclude_pix_id: str
    ) -> int:
        ...

    def source_used_destination(
        self, document: str, destination_document: str, until: datetime, exclude_pix_id: str
    ) -> bool:
        ...

    def count_source_small_attempts_since(
        self, document: str, max_amount: int, since: datetime, until: datetime, exclude_pix_id: str
    ) -> int:
        ...

    def count_destination_rejected_by_others_since(
        self, destination_document: str, document: str, since: datetime, until: datetime, exclude_pix_id: str
    ) -> int:
        ...

    def latest_account_risk_score(
        self, document: str, model: str, since: datetime, until: datetime
    ) -> "AccountRiskReading | None":
        """Newest score whose computed_at is in [since, until]; None when the cold path has not scored it."""
        ...

    def latest_payer_sequence_score(
        self, document: str, model: str, since: datetime, until: datetime
    ) -> "AccountRiskReading | None":
        """Same contract as latest_account_risk_score, over payer_sequence_score."""
        ...
