from datetime import datetime
from uuid import uuid4

from sqlalchemy import func

from database import Context
from models import AnalysisStatus, PixAnalysis, PixAnalysisReason, PixTransaction
from rules.pix_snapshot import PixSnapshot


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

    def create(self, payload: dict, snapshot: PixSnapshot, status_enumerator: str, metadata: dict, rule_set_version: str, reasons: list) -> PixAnalysis:
        source = payload["source_account"]
        destination = payload["destination_account"]

        pix_transaction = PixTransaction(
            pix_id=snapshot.pix_id,
            amount=snapshot.amount,
            transaction_date=snapshot.transaction_date,
            source_branch=source["branch"],
            source_account_number=source["account_number"],
            source_opening_date=snapshot.source_opening_date,
            source_document_number=snapshot.source_document,
            destination_participant=snapshot.destination_participant,
            destination_branch=destination["branch"],
            destination_account_number=destination["account_number"],
            destination_opening_date=snapshot.destination_opening_date,
            destination_document_number=snapshot.destination_document,
            device_id=snapshot.device_id,
            channel=snapshot.channel,
            ip=snapshot.ip,
            latitude=snapshot.latitude,
            longitude=snapshot.longitude,
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

    def count_source_attempts_since(self, document: str, since: datetime, until: datetime, exclude_pix_id: str) -> int:
        return (
            self.session.query(func.count(PixTransaction.id))
            .filter(
                PixTransaction.source_document_number == document,
                PixTransaction.transaction_date >= since,
                PixTransaction.transaction_date < until,
                PixTransaction.pix_id != exclude_pix_id,
            )
            .scalar()
        )

    def sum_source_not_rejected_since(self, document: str, since: datetime, until: datetime, exclude_pix_id: str) -> int:
        total = (
            self.session.query(func.coalesce(func.sum(PixTransaction.amount), 0))
            .join(PixAnalysis, PixAnalysis.pix_transaction_id == PixTransaction.id)
            .join(AnalysisStatus, AnalysisStatus.id == PixAnalysis.status_id)
            .filter(
                PixTransaction.source_document_number == document,
                PixTransaction.transaction_date >= since,
                PixTransaction.transaction_date < until,
                PixTransaction.pix_id != exclude_pix_id,
                AnalysisStatus.enumerator != AnalysisStatus.REJECTED,
            )
            .scalar()
        )
        return int(total)

    def get_status(self, enumerator: str) -> AnalysisStatus:
        return self.session.query(AnalysisStatus).filter(AnalysisStatus.enumerator == enumerator).one()
