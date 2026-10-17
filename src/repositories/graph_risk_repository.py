from datetime import datetime

from sqlalchemy import func, text

from constants import (
    GRAPH_RISK_DISPERSION_WINDOW_HOURS,
    GRAPH_RISK_INFLOW_WINDOW_HOURS,
    GRAPH_RISK_TWO_HOP_WINDOW_DAYS,
)
from database import Context
from models import AccountRiskScore, PixTransaction

# Graph features per candidate destination, all relative to the data clock (ADR 0007).
GRAPH_FEATURES_SQL = text("""
WITH candidates AS (
    SELECT DISTINCT destination_document_number AS doc
    FROM pix_transaction
    WHERE transaction_date > :clock - make_interval(hours => :lookback_hours) AND transaction_date <= :clock
),
pairs AS (
    SELECT t.destination_document_number AS doc, t.source_document_number AS payer,
           SUM(t.amount) AS amount_cents, MIN(t.transaction_date) AS first_in
    FROM pix_transaction t
    JOIN candidates c ON c.doc = t.destination_document_number
    WHERE t.transaction_date > :clock - make_interval(hours => :inflow_hours)
      AND t.transaction_date <= :clock
      AND t.source_document_number <> t.destination_document_number
    GROUP BY t.destination_document_number, t.source_document_number
),
inflow AS (
    SELECT doc, COUNT(*) AS payers, SUM(amount_cents) AS amount_cents, MIN(first_in) AS first_in
    FROM pairs GROUP BY doc
),
dispersion AS (
    SELECT i.doc, COUNT(DISTINCT o.destination_document_number) AS destinations
    FROM inflow i
    JOIN pix_transaction o
      ON o.source_document_number = i.doc
     AND o.destination_document_number <> i.doc
     AND o.transaction_date >= i.first_in
     AND o.transaction_date < i.first_in + make_interval(hours => :dispersion_hours)
     AND o.transaction_date <= :clock
    GROUP BY i.doc
),
flagged AS (
    SELECT p.doc, COUNT(*) AS payers
    FROM pairs p
    WHERE EXISTS (
        SELECT 1
        FROM pix_transaction x
        JOIN pix_analysis a ON a.pix_transaction_id = x.id
        JOIN analysis_status s ON s.id = a.status_id
        WHERE x.source_document_number = p.payer
          AND x.destination_document_number <> p.doc
          AND x.transaction_date > :clock - make_interval(days => :two_hop_days)
          AND x.transaction_date <= :clock
          AND s.enumerator = 'rejected'
    )
    GROUP BY p.doc
),
age AS (
    SELECT t.destination_document_number AS doc,
           FLOOR(EXTRACT(EPOCH FROM (:clock - MAX(t.destination_opening_date))) / 86400)::int AS days
    FROM pix_transaction t
    JOIN candidates c ON c.doc = t.destination_document_number
    WHERE t.transaction_date <= :clock
    GROUP BY t.destination_document_number
)
SELECT c.doc,
       COALESCE(i.payers, 0) AS in_distinct_payers_24h,
       COALESCE(i.amount_cents, 0) AS in_amount_24h_cents,
       COALESCE(d.destinations, 0) AS dispersion_out_distinct_6h,
       COALESCE(f.payers, 0) AS two_hop_flagged,
       COALESCE(a.days, 0) AS account_age_days
FROM candidates c
LEFT JOIN inflow i ON i.doc = c.doc
LEFT JOIN dispersion d ON d.doc = c.doc
LEFT JOIN flagged f ON f.doc = c.doc
LEFT JOIN age a ON a.doc = c.doc
ORDER BY c.doc
""")


class GraphRiskRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def data_clock(self) -> datetime | None:
        return self.session.query(func.max(PixTransaction.transaction_date)).scalar()

    def transaction_count(self) -> int:
        return self.session.query(func.count(PixTransaction.id)).scalar()

    def destination_graph_features(self, clock: datetime, lookback_hours: int) -> list[dict]:
        rows = self.session.execute(
            GRAPH_FEATURES_SQL,
            {
                "clock": clock,
                "lookback_hours": lookback_hours,
                "inflow_hours": GRAPH_RISK_INFLOW_WINDOW_HOURS,
                "dispersion_hours": GRAPH_RISK_DISPERSION_WINDOW_HOURS,
                "two_hop_days": GRAPH_RISK_TWO_HOP_WINDOW_DAYS,
            },
        ).mappings()
        return [dict(row) for row in rows]

    def add_scores(self, model: str, computed_at: datetime, scored: list[tuple[str, float, dict]]) -> None:
        self.session.add_all(
            AccountRiskScore(document_number=document, model=model, score=score, features=features, computed_at=computed_at)
            for document, score, features in scored
        )
        self.session.flush()
