from datetime import datetime

from sqlalchemy import func, text

from database import Context
from models import PayerSequenceScore, PixTransaction

# Payers active in the lookback window, with their Pix over the history horizon; `local_date` keeps the payload offset.
PAYER_HISTORY_SQL = text("""
SELECT source_document_number AS payer, destination_document_number AS destination, amount,
       payload->>'transaction_date' AS local_date
FROM pix_transaction
WHERE transaction_date > :clock - make_interval(days => :history_days) AND transaction_date <= :clock
  AND source_document_number IN (
      SELECT source_document_number FROM pix_transaction
      WHERE transaction_date > :clock - make_interval(hours => :lookback_hours) AND transaction_date <= :clock
  )
ORDER BY source_document_number, transaction_date, id
""")


class SequenceRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def data_clock(self) -> datetime | None:
        return self.session.query(func.max(PixTransaction.transaction_date)).scalar()

    def transaction_count(self) -> int:
        return self.session.query(func.count(PixTransaction.id)).scalar()

    def payer_history(self, clock: datetime, lookback_hours: int, history_days: int) -> list[dict]:
        rows = self.session.execute(
            PAYER_HISTORY_SQL, {"clock": clock, "lookback_hours": lookback_hours, "history_days": history_days}
        ).mappings()
        return [dict(row) for row in rows]

    def add_scores(self, model: str, computed_at: datetime, scored: list[tuple[str, float, dict]]) -> None:
        self.session.add_all(
            PayerSequenceScore(document_number=payer, model=model, score=score, features=features, computed_at=computed_at)
            for payer, score, features in scored
        )
        self.session.flush()
