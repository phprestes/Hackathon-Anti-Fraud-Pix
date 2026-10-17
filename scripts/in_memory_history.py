"""In-memory HistoryPort; semantics mirror PixTransactionRepository (the SQL is the reference)."""
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Record:
    pix_id: str
    date: datetime
    amount: int
    source: str
    destination: str
    device_id: str
    latitude: float | None
    longitude: float | None
    rejected: bool


class _Series:
    """Records of one key ordered by transaction_date."""

    def __init__(self) -> None:
        self.dates: list[datetime] = []
        self.records: list[Record] = []

    def add(self, record: Record) -> None:
        index = bisect_left(self.dates, record.date)
        # Equal dates keep insertion order, like a stable scan would.
        while index < len(self.dates) and self.dates[index] == record.date:
            index += 1
        self.dates.insert(index, record.date)
        self.records.insert(index, record)

    def before(self, until: datetime, exclude: str) -> list[Record]:
        return [r for r in self.records[: bisect_left(self.dates, until)] if r.pix_id != exclude]

    def window(self, since: datetime, until: datetime, exclude: str) -> list[Record]:
        start, end = bisect_left(self.dates, since), bisect_left(self.dates, until)
        return [r for r in self.records[start:end] if r.pix_id != exclude]


class InMemoryHistory:
    def __init__(self) -> None:
        self._by_source: dict[str, _Series] = defaultdict(_Series)
        self._by_device: dict[str, _Series] = defaultdict(_Series)
        self._by_destination: dict[str, _Series] = defaultdict(_Series)
        self._by_pair: dict[tuple[str, str], _Series] = defaultdict(_Series)
        self._by_source_device: dict[tuple[str, str], _Series] = defaultdict(_Series)

    def record(self, pix, status: str) -> None:
        item = Record(
            pix.pix_id, pix.transaction_date, pix.amount, pix.source_document, pix.destination_document,
            pix.device_id, pix.latitude, pix.longitude, status == "rejected",
        )
        self._by_source[item.source].add(item)
        self._by_device[item.device_id].add(item)
        self._by_destination[item.destination].add(item)
        self._by_pair[(item.source, item.destination)].add(item)
        self._by_source_device[(item.source, item.device_id)].add(item)

    def count_source_attempts_since(self, document, since, until, exclude_pix_id):
        return len(self._by_source[document].window(since, until, exclude_pix_id))

    def sum_source_not_rejected_since(self, document, since, until, exclude_pix_id):
        return sum(r.amount for r in self._by_source[document].window(since, until, exclude_pix_id) if not r.rejected)

    def count_source_history(self, document, until, exclude_pix_id):
        return len(self._by_source[document].before(until, exclude_pix_id))

    def source_used_device(self, document, device_id, until, exclude_pix_id):
        return bool(self._by_source_device[(document, device_id)].before(until, exclude_pix_id))

    def source_paid_destination_not_rejected(self, document, destination_document, until, exclude_pix_id):
        series = self._by_pair[(document, destination_document)]
        return any(not r.rejected for r in series.before(until, exclude_pix_id))

    def count_device_other_sources_since(self, device_id, document, since, until, exclude_pix_id):
        window = self._by_device[device_id].window(since, until, exclude_pix_id)
        return len({r.source for r in window if r.source != document})

    def count_destination_other_sources_since(self, destination_document, document, since, until, exclude_pix_id):
        window = self._by_destination[destination_document].window(since, until, exclude_pix_id)
        return len({r.source for r in window if r.source != document})

    def list_source_amounts_not_rejected_since(self, document, since, until, exclude_pix_id):
        window = self._by_source[document].window(since, until, exclude_pix_id)
        return tuple(r.amount for r in window if not r.rejected)

    def first_source_transaction_date(self, document, until, exclude_pix_id):
        earlier = self._by_source[document].before(until, exclude_pix_id)
        return earlier[0].date if earlier else None

    def last_source_geolocation(self, document, until, exclude_pix_id):
        for r in reversed(self._by_source[document].before(until, exclude_pix_id)):
            if r.latitude is not None and r.longitude is not None:
                return float(r.latitude), float(r.longitude), r.date
        return None

    def count_source_new_destinations_since(self, document, since, until, exclude_pix_id):
        destinations = {r.destination for r in self._by_source[document].window(since, until, exclude_pix_id)}
        return sum(
            1 for destination in destinations
            if not self._by_pair[(document, destination)].before(since, exclude_pix_id)
        )

    def source_used_destination(self, document, destination_document, until, exclude_pix_id):
        return bool(self._by_pair[(document, destination_document)].before(until, exclude_pix_id))

    def count_source_small_attempts_since(self, document, max_amount, since, until, exclude_pix_id):
        window = self._by_source[document].window(since, until, exclude_pix_id)
        return sum(1 for r in window if r.amount <= max_amount)

    def count_destination_rejected_by_others_since(self, destination_document, document, since, until, exclude_pix_id):
        window = self._by_destination[destination_document].window(since, until, exclude_pix_id)
        return sum(1 for r in window if r.source != document and r.rejected)
