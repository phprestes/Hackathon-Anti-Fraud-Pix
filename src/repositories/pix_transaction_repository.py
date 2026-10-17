from datetime import datetime
from uuid import uuid4

from database import Context
from models import AnalysisStatus, PixAnalysis, PixAnalysisReason, PixTransaction


class PixTransactionRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_by_pix_id(self, pix_id: str) -> PixAnalysis | None:
        return (
            self.session.query(PixAnalysis)
            .join(PixTransaction, PixTransaction.id == PixAnalysis.pix_transaction_id)
            .filter(PixTransaction.pix_id == pix_id)
            .first()
        )

    def create(self, payload: dict, status_enumerator: str, metadata: dict, rule_set_version: str, reasons: list) -> PixAnalysis:
        source = payload["source_account"]
        destination = payload["destination_account"]
        origin = payload["source"]
        geolocation = origin.get("geolocation") or {}

        pix_transaction = PixTransaction(
            pix_id=payload["id"],
            amount=payload["amount"],
            transaction_date=datetime.fromisoformat(payload["transaction_date"]),
            source_branch=source["branch"],
            source_account_number=source["account_number"],
            source_opening_date=datetime.fromisoformat(source["opening_date"]),
            source_document_number=source["owner"]["document_number"],
            destination_participant=destination["participant"],
            destination_branch=destination["branch"],
            destination_account_number=destination["account_number"],
            destination_opening_date=datetime.fromisoformat(destination["opening_date"]),
            destination_document_number=destination["owner"]["document_number"],
            device_id=origin["device_id"],
            channel=origin["channel"],
            ip=origin["ip"],
            latitude=geolocation.get("latitude"),
            longitude=geolocation.get("longitude"),
            payload=payload,
        )

        pix_analysis = PixAnalysis(
            analysis_key=str(uuid4()),
            pix_transaction=pix_transaction,
            status=self.get_status(status_enumerator),
            analysis_metadata=metadata,
            rule_set_version=rule_set_version,
        )

        for reason in reasons:
            pix_analysis.reasons.append(
                PixAnalysisReason(
                    rule_code=reason["rule_code"],
                    decision_status=self.get_status(reason["decision"]),
                    reason=reason["reason"],
                )
            )

        self.session.add(pix_analysis)
        self.session.flush()
        return pix_analysis

    def get_status(self, enumerator: str) -> AnalysisStatus:
        return self.session.query(AnalysisStatus).filter(AnalysisStatus.enumerator == enumerator).one()
