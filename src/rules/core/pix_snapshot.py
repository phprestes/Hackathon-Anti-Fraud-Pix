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

    @classmethod
    def from_payload(cls, payload: dict) -> "PixSnapshot":
        source = payload["source_account"]
        destination = payload["destination_account"]
        origin = payload["source"]
        geolocation = origin.get("geolocation") or {}

        return cls(
            pix_id=payload["id"],
            amount=payload["amount"],
            transaction_date=datetime.fromisoformat(payload["transaction_date"]),
            source_document=source["owner"]["document_number"],
            source_opening_date=datetime.fromisoformat(source["opening_date"]),
            destination_document=destination["owner"]["document_number"],
            destination_participant=destination["participant"],
            destination_opening_date=datetime.fromisoformat(destination["opening_date"]),
            device_id=origin["device_id"],
            channel=origin["channel"],
            ip=origin["ip"],
            latitude=geolocation.get("latitude"),
            longitude=geolocation.get("longitude"),
        )
