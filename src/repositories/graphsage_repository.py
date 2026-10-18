from datetime import datetime

from sqlalchemy import text

from constants import GRAPH_RISK_DISPERSION_WINDOW_HOURS
from repositories.graph_risk_repository import GraphRiskRepository

# Node features of the trailing window; scripts/models/train_graphsage.py mirrors these definitions in Python.
NODE_FEATURES_SQL = text("""
WITH win AS (
    SELECT source_document_number AS src, destination_document_number AS dst, amount, transaction_date,
           source_opening_date, destination_opening_date
    FROM pix_transaction
    WHERE transaction_date > :clock - make_interval(hours => :lookback_hours) AND transaction_date <= :clock
),
trade AS (SELECT * FROM win WHERE src <> dst),
nodes AS (SELECT src AS doc FROM win UNION SELECT dst FROM win),
inflow AS (
    SELECT dst AS doc, COUNT(DISTINCT src) AS degree, SUM(amount)::bigint AS cents, MIN(transaction_date) AS first_in
    FROM trade GROUP BY dst
),
outflow AS (
    SELECT src AS doc, COUNT(DISTINCT dst) AS degree, SUM(amount)::bigint AS cents
    FROM trade GROUP BY src
),
opening AS (
    SELECT doc, MAX(opened) AS opened
    FROM (SELECT src AS doc, source_opening_date AS opened FROM win
          UNION ALL SELECT dst, destination_opening_date FROM win) o
    GROUP BY doc
),
new_payers AS (
    SELECT p.dst AS doc, COUNT(*) AS payers
    FROM (SELECT DISTINCT src, dst FROM trade) p
    WHERE NOT EXISTS (
        SELECT 1 FROM pix_transaction h
        WHERE h.source_document_number = p.src AND h.destination_document_number = p.dst
          AND h.transaction_date <= :clock - make_interval(hours => :lookback_hours)
    )
    GROUP BY p.dst
),
dispersion AS (
    SELECT i.doc, COUNT(DISTINCT t.dst) AS destinations
    FROM inflow i
    JOIN trade t ON t.src = i.doc
     AND t.transaction_date >= i.first_in
     AND t.transaction_date < i.first_in + make_interval(hours => :dispersion_hours)
    GROUP BY i.doc
)
SELECT n.doc,
       COALESCE(i.degree, 0) AS in_degree,
       COALESCE(o.degree, 0) AS out_degree,
       COALESCE(i.cents, 0) AS in_cents,
       COALESCE(o.cents, 0) AS out_cents,
       GREATEST(FLOOR(EXTRACT(EPOCH FROM (:clock - op.opened)) / 86400), 0)::int AS min_age_days,
       COALESCE(np.payers, 0) AS new_payers,
       COALESCE(d.destinations, 0) AS dispersion,
       EXISTS (SELECT 1 FROM win w WHERE w.dst = n.doc) AS was_destination
FROM nodes n
LEFT JOIN inflow i ON i.doc = n.doc
LEFT JOIN outflow o ON o.doc = n.doc
LEFT JOIN opening op ON op.doc = n.doc
LEFT JOIN new_payers np ON np.doc = n.doc
LEFT JOIN dispersion d ON d.doc = n.doc
ORDER BY n.doc
""")

EDGES_SQL = text("""
SELECT DISTINCT source_document_number AS src, destination_document_number AS dst
FROM pix_transaction
WHERE transaction_date > :clock - make_interval(hours => :lookback_hours) AND transaction_date <= :clock
  AND source_document_number <> destination_document_number
""")


class GraphSageRepository(GraphRiskRepository):
    def node_features(self, clock: datetime, lookback_hours: int) -> list[dict]:
        rows = self.session.execute(
            NODE_FEATURES_SQL,
            {"clock": clock, "lookback_hours": lookback_hours, "dispersion_hours": GRAPH_RISK_DISPERSION_WINDOW_HOURS},
        ).mappings()
        return [dict(row) for row in rows]

    def edges(self, clock: datetime, lookback_hours: int) -> list[tuple[str, str]]:
        rows = self.session.execute(EDGES_SQL, {"clock": clock, "lookback_hours": lookback_hours})
        return [(row.src, row.dst) for row in rows]
