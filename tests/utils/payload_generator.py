from uuid import uuid4

from tests.utils.random_generator import RandomGenerator

DEFAULT_AT = "2026-10-17T14:00:00-03:00"
OLD_OPENING_DATE = "2024-03-02T10:00:00-03:00"


class PayloadGenerator:
    @staticmethod
    def pix(
        pix_id: str = None,
        amount: int = 15000,
        at: str = DEFAULT_AT,
        payer_document: str = None,
        destination_document: str = None,
        device_id: str = None,
        source_opening_date: str = OLD_OPENING_DATE,
        destination_opening_date: str = OLD_OPENING_DATE,
        geolocation: dict = None,
        channel: str = "app",
        ip: str = "198.51.100.23",
    ) -> dict:
        source = {
            "device_id": device_id or f"dvc-{uuid4().hex[:12]}",
            "channel": channel,
            "ip": ip,
        }
        if geolocation is not None:
            source["geolocation"] = geolocation

        return {
            "id": pix_id or f"pix-{uuid4()}",
            "amount": amount,
            "transaction_date": at,
            "source_account": {
                "branch": "0001",
                "account_number": "88213",
                "opening_date": source_opening_date,
                "owner": {"document_number": payer_document or RandomGenerator.generate_cpf()},
            },
            "destination_account": {
                "participant": "60701190",
                "branch": "3675",
                "account_number": "10442",
                "opening_date": destination_opening_date,
                "owner": {"document_number": destination_document or RandomGenerator.generate_cpf()},
            },
            "source": source,
        }
