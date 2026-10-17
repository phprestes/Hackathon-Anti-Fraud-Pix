from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PixSnapshot:
    pix_id: str
    amount: int
    transaction_date: datetime
    source_document: str
    source_opening_date: datetime
    destination_document: str
    destination_participant: str
    destination_opening_date: datetime
    device_id: str
    channel: str
    ip: str
    latitude: float | None
    longitude: float | None

    @property
    def is_self_transfer(self) -> bool:
        return self.source_document == self.destination_document

    @property
    def is_legal_entity_source(self) -> bool:
        return "/" in self.source_document
